from app.core.models import FreshnessDiff, SectionChange
from app.freshness.priority import classify_change, prioritize_diff


def test_security_keyword_is_critical():
    change = SectionChange(
        chunk_id="policies::security-incident-policy",
        doc_source="policies.md",
        section_heading="Security Incident Policy",
        change_type="modified",
        old_text="old",
        new_text="Report any security breach within 1 hour.",
        semantic_change_score=0.5,
    )
    result = classify_change(change)
    assert result.priority == "critical"


def test_pricing_keyword_is_high():
    change = SectionChange(
        chunk_id="product::pricing-tiers",
        doc_source="product.md",
        section_heading="Pricing Tiers",
        change_type="modified",
        old_text="old",
        new_text="The Growth plan pricing changed.",
        semantic_change_score=0.4,
    )
    result = classify_change(change)
    assert result.priority == "high"


def test_trivial_edit_below_threshold_is_low_even_with_keyword():
    change = SectionChange(
        chunk_id="product::pricing-tiers",
        doc_source="product.md",
        section_heading="Pricing Tiers",
        change_type="modified",
        old_text="The Growth plan costs 49 dollars per month.",
        new_text="The Growth plan costs 49 dollars per month.",
        semantic_change_score=0.0,
    )
    result = classify_change(change)
    assert result.priority == "low"


def test_added_section_without_keywords_defaults_medium():
    change = SectionChange(
        chunk_id="product::new-feature",
        doc_source="product.md",
        section_heading="New Feature",
        change_type="added",
        new_text="We shipped a new dashboard widget.",
    )
    result = classify_change(change)
    assert result.priority == "medium"


def test_prioritize_diff_sorts_critical_first():
    diff = FreshnessDiff(
        manifest_created_at="2025-01-01T00:00:00+00:00",
        scanned_at="2025-01-02T00:00:00+00:00",
        modified=[
            SectionChange(
                chunk_id="troubleshooting::sync-errors",
                doc_source="troubleshooting.md",
                section_heading="Sync Errors",
                change_type="modified",
                old_text="a",
                new_text="Sync errors happen sometimes.",
                semantic_change_score=0.4,
            ),
            SectionChange(
                chunk_id="policies::security-incident-policy",
                doc_source="policies.md",
                section_heading="Security Incident Policy",
                change_type="modified",
                old_text="a",
                new_text="A new security breach process.",
                semantic_change_score=0.4,
            ),
        ],
    )
    prioritized = prioritize_diff(diff)
    assert prioritized[0].change.chunk_id == "policies::security-incident-policy"
    assert prioritized[0].priority == "critical"
