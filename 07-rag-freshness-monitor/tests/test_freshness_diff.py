import json
from pathlib import Path

from app.freshness.diff import diff_against_manifest, semantic_change_score
from app.indexing.manifest import build_manifest


def _write_corpus(base: Path, body: str) -> tuple[Path, Path]:
    docs_dir = base / "docs"
    docs_dir.mkdir(exist_ok=True)
    (docs_dir / "policies.md").write_text(f"# Refund Policy\n{body}\n", encoding="utf-8")
    meta_path = base / "docs_meta.json"
    meta_path.write_text(json.dumps({"policies.md": {"doc_type": "policy", "last_modified": "2025-01-01"}}), encoding="utf-8")
    return docs_dir, meta_path


def test_semantic_change_score_zero_for_identical_text():
    assert semantic_change_score("Refunds within 30 days.", "Refunds within 30 days.") == 0.0


def test_semantic_change_score_positive_for_different_text():
    score = semantic_change_score("Refunds within 30 days.", "Enterprise pricing is custom.")
    assert score > 0.5


def test_diff_detects_no_changes_when_corpus_unchanged(tmp_path: Path):
    docs_dir, meta_path = _write_corpus(tmp_path, "Refunds within 30 days.")
    manifest = build_manifest(docs_dir, meta_path, "stub", "stub-v1", "heading")

    diff = diff_against_manifest(manifest, docs_dir, meta_path)

    assert diff.has_changes is False
    assert diff.added == []
    assert diff.removed == []
    assert diff.modified == []


def test_diff_detects_modified_section(tmp_path: Path):
    docs_dir, meta_path = _write_corpus(tmp_path, "Refunds within 30 days.")
    manifest = build_manifest(docs_dir, meta_path, "stub", "stub-v1", "heading")

    (docs_dir / "policies.md").write_text("# Refund Policy\nRefunds within 60 days now.\n", encoding="utf-8")
    diff = diff_against_manifest(manifest, docs_dir, meta_path)

    assert diff.has_changes is True
    assert len(diff.modified) == 1
    change = diff.modified[0]
    assert change.chunk_id == "policies::refund-policy"
    assert change.old_text == "Refunds within 30 days."
    assert change.new_text == "Refunds within 60 days now."
    assert change.semantic_change_score is not None


def test_diff_detects_added_and_removed_sections(tmp_path: Path):
    docs_dir, meta_path = _write_corpus(tmp_path, "Refunds within 30 days.")
    manifest = build_manifest(docs_dir, meta_path, "stub", "stub-v1", "heading")

    (docs_dir / "policies.md").write_text("# New Section\nBrand new content.\n", encoding="utf-8")
    diff = diff_against_manifest(manifest, docs_dir, meta_path)

    assert len(diff.added) == 1
    assert diff.added[0].chunk_id == "policies::new-section"
    assert len(diff.removed) == 1
    assert diff.removed[0].chunk_id == "policies::refund-policy"
    assert diff.modified == []
