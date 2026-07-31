from app.eval.cli import main


def test_gate_cli_writes_reports_and_returns_pass_exit_code(tmp_path):
    exit_code = main([
        "--baseline", "crm_summary_v1",
        "--candidate", "crm_summary_v1",
        "--out", str(tmp_path),
    ])
    assert exit_code == 0
    assert (tmp_path / "release_report.md").exists()
    assert (tmp_path / "pr_comment.md").exists()
    assert "Prompt Release Report" in (tmp_path / "release_report.md").read_text()


def test_gate_cli_blocks_on_regressed_candidate(tmp_path):
    """Demo scenario: v2 is an intentionally verbose, more expensive
    candidate (see prompts/crm_summary_v2.yaml). The gate must catch the
    cost regression and block the release.
    """
    exit_code = main([
        "--baseline", "crm_summary_v1",
        "--candidate", "crm_summary_v2",
        "--out", str(tmp_path),
        "--report-url", "https://example.test/artifact",
    ])
    comment = (tmp_path / "pr_comment.md").read_text()
    assert "Prompt Release Gate" in comment
    assert "BLOCK" in comment
    assert "cost rose" in comment
    assert exit_code == 1
