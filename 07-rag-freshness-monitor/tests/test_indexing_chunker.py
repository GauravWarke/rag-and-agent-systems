import json
from pathlib import Path

import pytest

from app.indexing.chunker import build_chunks, hash_text, slugify, split_sections


def test_slugify_basic():
    assert slugify("Refund Policy") == "refund-policy"
    assert slugify("Version 2.4 Release Notes") == "version-2-4-release-notes"
    assert slugify("  Multiple   Spaces!!") == "multiple-spaces"


def test_split_sections_splits_on_headings():
    md = "# Heading One\nBody one.\nMore body.\n\n# Heading Two\nBody two.\n"
    sections = split_sections(md)
    assert sections == [
        ("Heading One", "Body one.\nMore body."),
        ("Heading Two", "Body two."),
    ]


def test_split_sections_ignores_preamble_without_heading():
    md = "Some preamble text.\n# First\nBody.\n"
    sections = split_sections(md)
    assert sections == [("First", "Body.")]


def test_hash_text_is_stable_and_sensitive_to_content():
    assert hash_text("hello world") == hash_text("hello world")
    assert hash_text("hello world") != hash_text("hello there")


def test_build_chunks_from_sample_corpus(tmp_path: Path):
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "policies.md").write_text("# Refund Policy\nRefunds within 30 days.\n", encoding="utf-8")
    meta_path = tmp_path / "docs_meta.json"
    meta_path.write_text(json.dumps({"policies.md": {"doc_type": "policy", "last_modified": "2025-01-01"}}), encoding="utf-8")

    chunks = build_chunks(docs_dir, meta_path, embedding_version="stub-v1")

    assert len(chunks) == 1
    chunk = chunks[0]
    assert chunk.chunk_id == "policies::refund-policy"
    assert chunk.doc_type == "policy"
    assert chunk.last_modified == "2025-01-01"
    assert chunk.text == "Refunds within 30 days."


def test_build_chunks_missing_metadata_raises(tmp_path: Path):
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "orphan.md").write_text("# Heading\nBody.\n", encoding="utf-8")
    meta_path = tmp_path / "docs_meta.json"
    meta_path.write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="orphan.md"):
        build_chunks(docs_dir, meta_path, embedding_version="stub-v1")


def test_bundled_corpus_produces_expected_chunk_ids():
    repo_docs = Path(__file__).resolve().parents[1] / "data" / "docs"
    repo_meta = Path(__file__).resolve().parents[1] / "data" / "docs_meta.json"
    chunks = build_chunks(repo_docs, repo_meta, embedding_version="stub-v1")
    chunk_ids = {c.chunk_id for c in chunks}
    assert "policies::refund-policy" in chunk_ids
    assert "product::api-rate-limits" in chunk_ids
    assert "troubleshooting::sync-errors" in chunk_ids
    assert "changelog::version-2-4-release-notes" in chunk_ids
    assert len(chunks) == 16
