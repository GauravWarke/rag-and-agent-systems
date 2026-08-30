from app.metrics import format_report, run_operational_metrics


def test_run_operational_metrics_reports_deterministic_routing_split():
    report = run_operational_metrics()

    assert report.total_documents == 20
    assert report.auto_approved == 11
    assert report.needs_review == 9
    assert report.auto_approval_rate == 0.55

    reasons = {(r.field, r.severity): r.count for r in report.issue_reasons}
    assert reasons[("vendor", "warning")] == 2
    assert reasons[("claim_date", "error")] == 2
    assert reasons[("total", "error")] == 1
    assert reasons[("invoice_number", "error")] == 1
    assert reasons[("vendor", "error")] == 1
    assert reasons[("email", "error")] == 1
    assert reasons[("contract_value", "error")] == 1


def test_format_report_reads_as_a_one_line_headline_plus_reasons():
    report = run_operational_metrics()
    text = format_report(report)

    assert "Auto-approved 55% of 20 sample documents" in text
    assert "11 auto-approved" in text
    assert "9 routed to review" in text
    assert "Top reasons routed to review:" in text
