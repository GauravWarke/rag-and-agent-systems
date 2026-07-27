import json
from pathlib import Path

import pytest

from app.ingestion.cli import IndexAlreadyExistsError, build_index, main

_SAMPLE_DIR = Path(__file__).resolve().parents[1] / "data" / "sample_docs"


def test_build_index_writes_manifest_and_chunks(tmp_path):
    out_dir = tmp_path / "index"

    manifest = build_index(_SAMPLE_DIR, out_dir, chunking_strategy="heading")

    assert manifest["chunk_count"] > 0
    assert manifest["chunking_strategy"] == "heading"
    assert sum(manifest["documents"].values()) == manifest["chunk_count"]

    manifest_path = out_dir / "manifest.json"
    chunks_path = out_dir / "chunks.jsonl"
    assert manifest_path.exists()
    assert chunks_path.exists()
    assert json.loads(manifest_path.read_text()) == manifest

    lines = chunks_path.read_text().splitlines()
    assert len(lines) == manifest["chunk_count"]
    first = json.loads(lines[0])
    assert "chunk_id" in first and "text" in first


def test_build_index_supports_fixed_strategy(tmp_path):
    manifest = build_index(_SAMPLE_DIR, tmp_path / "index", chunking_strategy="fixed")
    assert manifest["chunking_strategy"] == "fixed"
    assert manifest["chunk_count"] > 0


def test_build_index_rejects_missing_source_dir(tmp_path):
    with pytest.raises(NotADirectoryError):
        build_index(tmp_path / "does-not-exist", tmp_path / "index")


def test_build_index_refuses_to_overwrite_without_rebuild(tmp_path):
    out_dir = tmp_path / "index"
    build_index(_SAMPLE_DIR, out_dir)

    with pytest.raises(IndexAlreadyExistsError):
        build_index(_SAMPLE_DIR, out_dir)


def test_build_index_rebuild_overwrites_existing_index(tmp_path):
    out_dir = tmp_path / "index"
    build_index(_SAMPLE_DIR, out_dir, chunking_strategy="heading")

    manifest = build_index(_SAMPLE_DIR, out_dir, chunking_strategy="fixed", rebuild=True)

    assert manifest["chunking_strategy"] == "fixed"
    assert json.loads((out_dir / "manifest.json").read_text())["chunking_strategy"] == "fixed"


def test_main_returns_zero_on_success(tmp_path, capsys):
    out_dir = tmp_path / "index"
    code = main(["--source", str(_SAMPLE_DIR), "--out", str(out_dir)])

    assert code == 0
    assert (out_dir / "manifest.json").exists()
    assert "Indexed" in capsys.readouterr().out


def test_main_returns_nonzero_for_missing_source(tmp_path, capsys):
    code = main(["--source", str(tmp_path / "missing"), "--out", str(tmp_path / "index")])

    assert code == 1
    assert "error" in capsys.readouterr().out


def test_main_returns_nonzero_without_rebuild_when_index_exists(tmp_path, capsys):
    out_dir = tmp_path / "index"
    assert main(["--source", str(_SAMPLE_DIR), "--out", str(out_dir)]) == 0

    code = main(["--source", str(_SAMPLE_DIR), "--out", str(out_dir)])

    assert code == 1
    assert "--rebuild" in capsys.readouterr().out
