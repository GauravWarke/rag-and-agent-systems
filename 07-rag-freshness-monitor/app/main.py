"""RAG Freshness and Drift Monitor.

Watches a small RAG knowledge base for stale sources, changed content, and
retrieval drift, and tells the team when the index needs rebuilding.

Endpoints:
  GET  /health                readiness probe
  POST /v1/index/build        (re)build the index manifest from the corpus on disk
  GET  /v1/index/manifest     return the currently saved manifest
  POST /v1/freshness/scan     diff the corpus against the saved manifest, with priority
  POST /v1/probes/run         run the probe set against the current corpus,
                               and report drift against the previous run
  POST /v1/answers/run        generate answers for the probe set against the current corpus
  POST /v1/answers/drift      re-run answers now and compare to the last /v1/answers/run
  POST /v1/answers/stale-risk find probes whose source chunk changed but whose
                               answer did not, relative to the saved manifest
  GET  /v1/scorecard          roll up freshness, probe drift, answer drift, and
                               stale-answer risk into one dashboard summary
  POST /v1/alerts/check       recompute the scorecard and dispatch any alerts
                               it triggers (Slack if configured, else logged)
  POST /v1/rebuild            one-click rebuild: re-index, re-run probes and
                               answers, recompute the scorecard, and alert
"""
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request

from app.alerts.client import AlertClient, NullAlertClient, SlackAlertClient
from app.alerts.dispatch import dispatch_alerts
from app.answers.drift import compare_answer_runs, detect_stale_answer_risk
from app.answers.generator import (
    AnswerGenerator,
    OpenAIAnswerGenerator,
    StubAnswerGenerator,
    generate_answers,
)
from app.answers.judge import (
    AnswerJudgeClient,
    OpenAIAnswerJudgeClient,
    StubAnswerJudgeClient,
)
from app.core.config import settings
from app.core.models import (
    AlertDispatchResult,
    AnswerDriftReport,
    AnswerRunSummary,
    DriftReport,
    FreshnessReport,
    FreshnessScorecard,
    IndexManifest,
    ProbeRunSummary,
    RebuildResult,
    StaleAnswerReport,
)
from app.core.rate_limit import RateLimiter
from app.dashboard.scorecard import build_scorecard
from app.drift.probes import compare_runs, load_probes, run_probes
from app.freshness.diff import diff_against_manifest
from app.freshness.priority import prioritize_diff
from app.indexing.chunker import build_chunks
from app.indexing.manifest import build_manifest, load_manifest, save_manifest

_BASE_DIR = Path(__file__).resolve().parents[1]


def _resolve(path_str: str) -> Path:
    path = Path(path_str)
    return path if path.is_absolute() else _BASE_DIR / path


app = FastAPI(title="RAG Freshness and Drift Monitor", version="0.1.0")

_limiter = RateLimiter(settings.rate_limit_per_minute)
_last_probe_run: ProbeRunSummary | None = None
_last_answer_run: AnswerRunSummary | None = None


def _answer_generator() -> AnswerGenerator:
    return OpenAIAnswerGenerator(api_key=settings.openai_api_key, model=settings.answer_model) if settings.openai_api_key else StubAnswerGenerator()


def _answer_judge() -> AnswerJudgeClient:
    return OpenAIAnswerJudgeClient(api_key=settings.openai_api_key, model=settings.answer_model) if settings.openai_api_key else StubAnswerJudgeClient()


def _alert_client() -> AlertClient:
    return SlackAlertClient(webhook_url=settings.slack_webhook_url) if settings.slack_webhook_url else NullAlertClient()


def _rate_limited(request: Request) -> bool:
    client_key = request.client.host if request.client else "unknown"
    return not _limiter.allow(client_key)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/index/build", response_model=IndexManifest)
def build_index(request: Request) -> IndexManifest:
    if _rate_limited(request):
        raise HTTPException(status_code=429, detail="Rate limit exceeded, try again shortly.")
    manifest = build_manifest(
        docs_dir=_resolve(settings.docs_dir),
        docs_meta_path=_resolve(settings.docs_meta_path),
        embedding_model=settings.embedding_model,
        embedding_version=settings.embedding_version,
        chunking_strategy=settings.chunking_strategy,
    )
    save_manifest(manifest, _resolve(settings.manifest_path))
    return manifest


@app.get("/v1/index/manifest", response_model=IndexManifest)
def get_manifest(request: Request) -> IndexManifest:
    if _rate_limited(request):
        raise HTTPException(status_code=429, detail="Rate limit exceeded, try again shortly.")
    manifest = load_manifest(_resolve(settings.manifest_path))
    if manifest is None:
        raise HTTPException(status_code=404, detail="No manifest built yet. Call POST /v1/index/build first.")
    return manifest


@app.post("/v1/freshness/scan", response_model=FreshnessReport)
def freshness_scan(request: Request) -> FreshnessReport:
    if _rate_limited(request):
        raise HTTPException(status_code=429, detail="Rate limit exceeded, try again shortly.")
    manifest = load_manifest(_resolve(settings.manifest_path))
    if manifest is None:
        raise HTTPException(status_code=404, detail="No manifest built yet. Call POST /v1/index/build first.")
    diff = diff_against_manifest(manifest, _resolve(settings.docs_dir), _resolve(settings.docs_meta_path))
    return FreshnessReport(diff=diff, prioritized=prioritize_diff(diff))


@app.post("/v1/probes/run", response_model=ProbeRunSummary)
def probes_run(request: Request) -> ProbeRunSummary:
    if _rate_limited(request):
        raise HTTPException(status_code=429, detail="Rate limit exceeded, try again shortly.")
    global _last_probe_run
    probes = load_probes(_resolve(settings.probes_path))
    chunks = build_chunks(_resolve(settings.docs_dir), _resolve(settings.docs_meta_path), settings.embedding_version)
    current = run_probes(probes, chunks)
    _last_probe_run = current
    return current


@app.post("/v1/probes/drift", response_model=DriftReport)
def probes_drift(request: Request) -> DriftReport:
    """Re-run the probe set now and compare it to the last `/v1/probes/run`
    snapshot, to see whether retrieval results changed in between."""
    if _rate_limited(request):
        raise HTTPException(status_code=429, detail="Rate limit exceeded, try again shortly.")
    if _last_probe_run is None:
        raise HTTPException(status_code=404, detail="No probe runs recorded yet. Call POST /v1/probes/run first.")
    probes = load_probes(_resolve(settings.probes_path))
    chunks = build_chunks(_resolve(settings.docs_dir), _resolve(settings.docs_meta_path), settings.embedding_version)
    current = run_probes(probes, chunks)
    return compare_runs(_last_probe_run, current)


@app.post("/v1/answers/run", response_model=AnswerRunSummary)
def answers_run(request: Request) -> AnswerRunSummary:
    if _rate_limited(request):
        raise HTTPException(status_code=429, detail="Rate limit exceeded, try again shortly.")
    global _last_answer_run
    probes = load_probes(_resolve(settings.probes_path))
    chunks = build_chunks(_resolve(settings.docs_dir), _resolve(settings.docs_meta_path), settings.embedding_version)
    current = generate_answers(probes, chunks, _answer_generator())
    _last_answer_run = current
    return current


@app.post("/v1/answers/drift", response_model=AnswerDriftReport)
def answers_drift(request: Request) -> AnswerDriftReport:
    """Re-run probe answers now and compare them to the last
    `/v1/answers/run` snapshot, to see whether answer meaning changed."""
    if _rate_limited(request):
        raise HTTPException(status_code=429, detail="Rate limit exceeded, try again shortly.")
    if _last_answer_run is None:
        raise HTTPException(status_code=404, detail="No answer runs recorded yet. Call POST /v1/answers/run first.")
    probes = load_probes(_resolve(settings.probes_path))
    chunks = build_chunks(_resolve(settings.docs_dir), _resolve(settings.docs_meta_path), settings.embedding_version)
    current = generate_answers(probes, chunks, _answer_generator())
    return compare_answer_runs(_last_answer_run, current, chunks, _answer_judge())


@app.post("/v1/answers/stale-risk", response_model=StaleAnswerReport)
def answers_stale_risk(request: Request) -> StaleAnswerReport:
    """Cross-reference source-level freshness changes with answer drift:
    flag probes whose grounding chunk changed but whose answer did not."""
    if _rate_limited(request):
        raise HTTPException(status_code=429, detail="Rate limit exceeded, try again shortly.")
    if _last_answer_run is None:
        raise HTTPException(status_code=404, detail="No answer runs recorded yet. Call POST /v1/answers/run first.")
    manifest = load_manifest(_resolve(settings.manifest_path))
    if manifest is None:
        raise HTTPException(status_code=404, detail="No manifest built yet. Call POST /v1/index/build first.")
    diff = diff_against_manifest(manifest, _resolve(settings.docs_dir), _resolve(settings.docs_meta_path))
    probes = load_probes(_resolve(settings.probes_path))
    chunks = build_chunks(_resolve(settings.docs_dir), _resolve(settings.docs_meta_path), settings.embedding_version)
    current = generate_answers(probes, chunks, _answer_generator())
    drift = compare_answer_runs(_last_answer_run, current, chunks, _answer_judge())
    return detect_stale_answer_risk(diff, drift)


def _current_scorecard() -> FreshnessScorecard:
    """Recompute freshness, probe drift, answer drift, and stale-answer
    risk from whichever snapshots are available, and roll them up into one
    scorecard. Shared by /v1/scorecard, /v1/alerts/check, and /v1/rebuild
    so all three agree on the same signals."""
    docs_dir = _resolve(settings.docs_dir)
    docs_meta_path = _resolve(settings.docs_meta_path)
    manifest = load_manifest(_resolve(settings.manifest_path))

    freshness: FreshnessReport | None = None
    if manifest is not None:
        diff = diff_against_manifest(manifest, docs_dir, docs_meta_path)
        freshness = FreshnessReport(diff=diff, prioritized=prioritize_diff(diff))

    current_probes: ProbeRunSummary | None = None
    probe_drift: DriftReport | None = None
    if _last_probe_run is not None:
        probes = load_probes(_resolve(settings.probes_path))
        chunks = build_chunks(docs_dir, docs_meta_path, settings.embedding_version)
        current_probes = run_probes(probes, chunks)
        probe_drift = compare_runs(_last_probe_run, current_probes)

    answer_drift: AnswerDriftReport | None = None
    stale_answer: StaleAnswerReport | None = None
    if _last_answer_run is not None:
        probes = load_probes(_resolve(settings.probes_path))
        chunks = build_chunks(docs_dir, docs_meta_path, settings.embedding_version)
        current_answers = generate_answers(probes, chunks, _answer_generator())
        answer_drift = compare_answer_runs(_last_answer_run, current_answers, chunks, _answer_judge())
        if freshness is not None:
            stale_answer = detect_stale_answer_risk(freshness.diff, answer_drift)

    return build_scorecard(freshness, current_probes, probe_drift, answer_drift, stale_answer)


@app.get("/v1/scorecard", response_model=FreshnessScorecard)
def scorecard(request: Request) -> FreshnessScorecard:
    """Roll up freshness, probe drift, answer drift, and stale-answer risk
    into one dashboard summary, using whichever snapshots are available.
    Call POST /v1/index/build, /v1/probes/run, and /v1/answers/run first
    to populate the full picture — this degrades gracefully otherwise."""
    if _rate_limited(request):
        raise HTTPException(status_code=429, detail="Rate limit exceeded, try again shortly.")
    return _current_scorecard()


@app.post("/v1/alerts/check", response_model=AlertDispatchResult)
def alerts_check(request: Request) -> AlertDispatchResult:
    """Recompute the scorecard and dispatch any alerts it triggers: a
    Slack notification when SLACK_WEBHOOK_URL is configured, otherwise the
    alerts are just recorded (offline default)."""
    if _rate_limited(request):
        raise HTTPException(status_code=429, detail="Rate limit exceeded, try again shortly.")
    return dispatch_alerts(_current_scorecard(), _alert_client())


@app.post("/v1/rebuild", response_model=RebuildResult)
def rebuild(request: Request) -> RebuildResult:
    """One-click rebuild: re-index the corpus from disk, re-run the probe
    and answer baselines against the fresh index, recompute the
    scorecard, and dispatch any alerts it triggers."""
    if _rate_limited(request):
        raise HTTPException(status_code=429, detail="Rate limit exceeded, try again shortly.")
    global _last_probe_run, _last_answer_run

    manifest = build_manifest(
        docs_dir=_resolve(settings.docs_dir),
        docs_meta_path=_resolve(settings.docs_meta_path),
        embedding_model=settings.embedding_model,
        embedding_version=settings.embedding_version,
        chunking_strategy=settings.chunking_strategy,
    )
    save_manifest(manifest, _resolve(settings.manifest_path))

    probes = load_probes(_resolve(settings.probes_path))
    chunks = build_chunks(_resolve(settings.docs_dir), _resolve(settings.docs_meta_path), settings.embedding_version)
    probe_run = run_probes(probes, chunks)
    _last_probe_run = probe_run

    answer_run = generate_answers(probes, chunks, _answer_generator())
    _last_answer_run = answer_run

    card = _current_scorecard()
    alerts = dispatch_alerts(card, _alert_client())

    return RebuildResult(
        rebuilt_at=datetime.now(UTC).isoformat(),
        manifest=manifest,
        probes=probe_run,
        answers=answer_run,
        scorecard=card,
        alerts=alerts,
    )
