from app.demo import run_demo


def test_run_demo_shows_read_only_chain_and_high_risk_scenarios():
    transcript = run_demo()

    assert "Read-only request (auto-completes)" in transcript
    assert "Multi-step chain (pauses before the write step)" in transcript
    assert "Multi-step chain, resumed (confirmed and completed)" in transcript
    assert "High-risk write (pauses for human approval)" in transcript
    assert "High-risk write, resumed (approved and executed)" in transcript

    assert transcript.count("status: completed") == 3
    assert "status: awaiting_confirmation" in transcript
    assert "status: awaiting_approval" in transcript
