import json
from pathlib import Path

import pytest

from app.indexing.manifest import build_manifest, load_manifest, save_manifest


@pytest.fixture
def corpus(tmp_path: Path) -> tuple[Path, Path]:
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "policies.md").write_text("# Refund Policy\nRefunds within 30 days.\n", encoding="utf-8")
    meta_path = tmp_path / "docs_meta.json"
    meta_path.write_text(json.dumps({"policies.md": {"doc_type": "policy", "last_modified": "2025-01-01"}}), encoding="utf-8")
    return docs_dir, meta_path


def test_build_manifest_rejects_unknown_strategy(corpus: tuple[Path, Path]):
    docs_dir, meta_path = corpus
    with pytest.raises(ValueError, match="chunking strategy"):
        build_manifest(docs_dir, meta_path, "stub", "stub-v1", "fixed-size")


def test_build_manifest_records_settings(corpus: tuple[Path, Path]):
    docs_dir, meta_path = corpus
    manifest = build_manifest(docs_dir, meta_path, "stub", "stub-v1", "heading")
    assert manifest.embedding_model == "stub"
    assert manifest.embedding_version == "stub-v1"
    assert manifest.chunking_strategy == "heading"
    assert len(manifest.chunks) == 1


def test_save_and_load_manifest_round_trips(corpus: tuple[Path, Path], tmp_path: Path):
    docs_dir, meta_path = corpus
    manifest = build_manifest(docs_dir, meta_path, "stub", "stub-v1", "heading")
    manifest_path = tmp_path / "index" / "manifest.json"

    save_manifest(manifest, manifest_path)
    loaded = load_manifest(manifest_path)

    assert loaded is not None
    assert loaded == manifest


def test_load_manifest_returns_none_when_missing(tmp_path: Path):
    assert load_manifest(tmp_path / "does_not_exist.json") is None
