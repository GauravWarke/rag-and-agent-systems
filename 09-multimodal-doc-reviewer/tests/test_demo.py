from app.demo import run_demo


def test_run_demo_walks_a_messy_document_from_upload_to_reviewed_correction():
    transcript = run_demo()

    assert "Messy document walkthrough" in transcript
    assert "rotation_correction" in transcript
    assert "low_resolution" in transcript
    assert "source: vision_fallback" in transcript
    assert "routing: needs_review" in transcript
    assert "required field 'vendor' is missing" in transcript
    assert "reviewer 'alex' filled in" in transcript
    assert "routing: auto_approved" in transcript
