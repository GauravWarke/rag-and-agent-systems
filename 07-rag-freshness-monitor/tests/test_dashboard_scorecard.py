from app.core.models import (
    AnswerDriftReport,
    AnswerDriftVerdict,
    DriftedProbe,
    DriftReport,
    FreshnessDiff,
    FreshnessReport,
    PrioritizedChange,
    ProbeRunSummary,
    SectionChange,
    StaleAnswerReport,
    StaleAnswerRisk,
)
from app.dashboard.scorecard import build_scorecard


def test_build_scorecard_with_no_snapshots_yet():
    card = build_scorecard(None, None, None, None, None)
    assert card.manifest_available is False
    assert card.docs_changed == 0
    assert card.chunks_needing_reindex == 0
    assert card.probes_total == 0
    assert card.probes_drifting == 0
    assert card.answer_drift_checked == 0
    assert card.answer_drift_changed == 0
    assert card.stale_answer_risks == 0
    assert card.recommendations == []


def test_build_scorecard_counts_docs_changed_and_recommendations():
    critical_change = SectionChange(
        chunk_id="policies::security-incident-policy",
        doc_source="policies.md",
        section_heading="Security Incident Policy",
        change_type="modified",
        old_text="old",
        new_text="new",
        semantic_change_score=0.5,
    )
    low_change = SectionChange(
        chunk_id="changelog::v1",
        doc_source="changelog.md",
        section_heading="v1",
        change_type="added",
        new_text="new section",
    )
    diff = FreshnessDiff(manifest_created_at="t0", scanned_at="t1", added=[low_change], modified=[critical_change])
    freshness = FreshnessReport(
        diff=diff,
        prioritized=[
            PrioritizedChange(change=critical_change, priority="critical", reasons=["matched keyword 'security'"]),
            PrioritizedChange(change=low_change, priority="medium", reasons=["no impact keywords found"]),
        ],
    )

    card = build_scorecard(freshness, None, None, None, None)

    assert card.manifest_available is True
    assert card.docs_changed == 2
    assert card.chunks_needing_reindex == 1
    assert len(card.recommendations) == 1
    assert card.recommendations[0].change.chunk_id == "policies::security-incident-policy"


def test_build_scorecard_summarizes_probe_and_answer_drift():
    probes = ProbeRunSummary(run_at="t1", total_probes=20, matched=18, match_rate=0.9, results=[])
    probe_drift = DriftReport(
        previous_run_at="t0",
        current_run_at="t1",
        drifted=[
            DriftedProbe(
                probe_id="p01",
                question="q",
                previous_chunk_id="a",
                current_chunk_id="b",
                expected_chunk_id="a",
                now_matches_expected=False,
            )
        ],
    )
    answer_drift = AnswerDriftReport(
        previous_run_at="t0",
        current_run_at="t1",
        verdicts=[
            AnswerDriftVerdict(
                probe_id="p01",
                question="q",
                chunk_id="a",
                previous_answer="x",
                current_answer="y",
                meaning_changed=True,
                citation_supports_answer=True,
            )
        ],
    )
    stale_answer = StaleAnswerReport(
        checked_at="t1",
        risks=[StaleAnswerRisk(probe_id="p02", question="q2", chunk_id="c", reason="stale")],
    )

    card = build_scorecard(None, probes, probe_drift, answer_drift, stale_answer)

    assert card.probes_total == 20
    assert card.probes_drifting == 1
    assert card.answer_drift_checked == 1
    assert card.answer_drift_changed == 1
    assert card.stale_answer_risks == 1
