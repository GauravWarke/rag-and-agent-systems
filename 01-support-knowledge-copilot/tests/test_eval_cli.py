from app.eval.cli import main


def test_main_writes_markdown_report_and_html_dashboard(tmp_path, capsys):
    out_dir = tmp_path / "reports"

    code = main(["--strategy", "hybrid", "--out", str(out_dir)])

    assert code == 0
    md_path = out_dir / "eval_hybrid.md"
    dashboard_path = out_dir / "dashboard.html"
    assert md_path.exists()
    assert dashboard_path.exists()
    assert "strategy: `hybrid`" in md_path.read_text()
    assert "dense" in dashboard_path.read_text()

    out = capsys.readouterr().out
    assert "Wrote" in out
    assert "answer_correct_rate" in out


def test_main_skips_dense_comparison_when_strategy_is_dense(tmp_path):
    out_dir = tmp_path / "reports"

    code = main(["--strategy", "dense", "--out", str(out_dir)])

    assert code == 0
    assert (out_dir / "eval_dense.md").exists()
    assert (out_dir / "dashboard.html").exists()
