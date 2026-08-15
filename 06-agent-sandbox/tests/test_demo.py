from app.demo import run_demo


def test_run_demo_shows_a_completed_safe_task_and_a_paused_unsafe_task():
    transcript = run_demo()

    assert "Safe task: low-risk analysis (auto-completes)" in transcript
    assert "Unsafe task: high-risk write (paused for human approval)" in transcript
    assert "status: completed" in transcript
    assert "status: awaiting_approval" in transcript
    assert "pending approval: ticket_create (risk=high)" in transcript
