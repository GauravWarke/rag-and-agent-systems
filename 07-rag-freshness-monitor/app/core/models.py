"""Shared data contracts for indexing, freshness diffing, and drift probes."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

DocType = Literal["policy", "product", "troubleshooting", "changelog"]
PriorityLevel = Literal["critical", "high", "medium", "low"]


class ChunkRecord(BaseModel):
    """One section of a source document, as it existed at index time."""

    chunk_id: str
    doc_source: str
    doc_type: DocType
    section_heading: str
    text: str
    chunk_hash: str
    last_modified: str
    embedding_version: str


class IndexManifest(BaseModel):
    """Records what was indexed, when, and with which settings.

    Comparing a fresh scan of the corpus against this manifest is how
    freshness drift is detected (Phase 2) and how retrieval probes are
    run "before vs. after" (Phase 3).
    """

    created_at: str
    embedding_model: str
    embedding_version: str
    chunking_strategy: str
    chunks: list[ChunkRecord] = Field(default_factory=list)


class SectionChange(BaseModel):
    """A single added/removed/modified section detected during a scan."""

    chunk_id: str
    doc_source: str
    section_heading: str
    change_type: Literal["added", "removed", "modified"]
    old_text: str | None = None
    new_text: str | None = None
    semantic_change_score: float | None = Field(default=None, ge=0.0, le=1.0)


class FreshnessDiff(BaseModel):
    """The result of comparing the current corpus to a saved manifest."""

    manifest_created_at: str
    scanned_at: str
    added: list[SectionChange] = Field(default_factory=list)
    removed: list[SectionChange] = Field(default_factory=list)
    modified: list[SectionChange] = Field(default_factory=list)

    @property
    def has_changes(self) -> bool:
        return bool(self.added or self.removed or self.modified)


class PrioritizedChange(BaseModel):
    """A section change ranked by how urgently it needs re-indexing."""

    change: SectionChange
    priority: PriorityLevel
    reasons: list[str] = Field(default_factory=list)


class FreshnessReport(BaseModel):
    diff: FreshnessDiff
    prioritized: list[PrioritizedChange] = Field(default_factory=list)


class ProbeQuestion(BaseModel):
    """A recurring question tied to a known source section."""

    probe_id: str
    question: str
    expected_chunk_id: str


class ProbeResult(BaseModel):
    probe_id: str
    question: str
    expected_chunk_id: str
    retrieved_chunk_id: str | None
    retrieval_score: float
    matched_expected: bool


class ProbeRunSummary(BaseModel):
    run_at: str
    total_probes: int
    matched: int
    match_rate: float
    results: list[ProbeResult] = Field(default_factory=list)


class DriftedProbe(BaseModel):
    probe_id: str
    question: str
    previous_chunk_id: str | None
    current_chunk_id: str | None
    expected_chunk_id: str
    now_matches_expected: bool


class DriftReport(BaseModel):
    previous_run_at: str
    current_run_at: str
    drifted: list[DriftedProbe] = Field(default_factory=list)

    @property
    def drift_count(self) -> int:
        return len(self.drifted)


class AnswerRecord(BaseModel):
    """A generated answer for one probe question, grounded in whichever
    chunk retrieval currently returns for it."""

    probe_id: str
    question: str
    chunk_id: str | None
    answer_text: str


class AnswerRunSummary(BaseModel):
    run_at: str
    answers: list[AnswerRecord] = Field(default_factory=list)


class AnswerDriftVerdict(BaseModel):
    """LLM-as-judge comparison of the same probe's answer across two runs."""

    probe_id: str
    question: str
    chunk_id: str | None
    previous_answer: str
    current_answer: str
    meaning_changed: bool
    citation_supports_answer: bool
    rationale: str = ""


class AnswerDriftReport(BaseModel):
    previous_run_at: str
    current_run_at: str
    verdicts: list[AnswerDriftVerdict] = Field(default_factory=list)

    @property
    def changed_count(self) -> int:
        return sum(1 for v in self.verdicts if v.meaning_changed)


class StaleAnswerRisk(BaseModel):
    """A probe whose source section changed but whose generated answer
    did not — the system may be serving knowledge that's gone stale."""

    probe_id: str
    question: str
    chunk_id: str | None
    reason: str


class StaleAnswerReport(BaseModel):
    checked_at: str
    risks: list[StaleAnswerRisk] = Field(default_factory=list)

    @property
    def at_risk_count(self) -> int:
        return len(self.risks)


class FreshnessScorecard(BaseModel):
    """A single dashboard-style rollup of every freshness signal: docs
    changed, chunks needing re-index, probe drift, answer drift, and
    stale-answer risk. Built from whichever snapshots are available so it
    degrades gracefully before the full pipeline has been run."""

    generated_at: str
    manifest_available: bool
    docs_changed: int
    chunks_needing_reindex: int
    probes_total: int
    probes_drifting: int
    answer_drift_checked: int
    answer_drift_changed: int
    stale_answer_risks: int
    recommendations: list[PrioritizedChange] = Field(default_factory=list)
