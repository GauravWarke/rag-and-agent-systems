"""Re-index CLI (Phase 2, step 4 of the build guide).

Usage:
    python ingest.py --source data/sample_docs --rebuild
    python ingest.py --source docs/ --strategy fixed --out storage/index

Loads every supported document under `--source`, normalizes and chunks it,
builds the in-memory hybrid index once to fail fast on bad input, and writes
a JSON manifest plus a JSONL chunk dump to `--out`. This is the artifact a
teammate would run after editing the docs, mirroring how ingestion works in
production RAG systems rather than only rebuilding the index implicitly at
app startup.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.ingestion.loader import load_corpus_from_dir
from app.retrieval.hybrid import HybridRetriever

_DEFAULT_OUT = Path("storage/index")


class IndexAlreadyExistsError(Exception):
    """Raised when an index manifest already exists and --rebuild was not passed."""


def build_index(source_dir: Path, out_dir: Path, *, chunking_strategy: str = "heading",
                 rebuild: bool = False) -> dict:
    if not source_dir.is_dir():
        raise NotADirectoryError(f"--source is not a directory: {source_dir}")

    manifest_path = out_dir / "manifest.json"
    if manifest_path.exists() and not rebuild:
        raise IndexAlreadyExistsError(
            f"Index already exists at {manifest_path}. Pass --rebuild to overwrite it."
        )

    chunks = load_corpus_from_dir(source_dir, chunking_strategy=chunking_strategy)

    # Build once so a broken corpus (e.g. embedding failure) fails the CLI run
    # instead of silently producing a manifest for an index that can't load.
    HybridRetriever().index(chunks)

    per_source: dict[str, int] = {}
    for c in chunks:
        per_source[c.metadata.source_name] = per_source.get(c.metadata.source_name, 0) + 1

    manifest = {
        "source_dir": str(source_dir),
        "chunking_strategy": chunking_strategy,
        "chunk_count": len(chunks),
        "documents": per_source,
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    chunks_path = out_dir / "chunks.jsonl"
    with chunks_path.open("w", encoding="utf-8") as f:
        for c in chunks:
            f.write(c.model_dump_json() + "\n")

    return manifest


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ingest.py",
        description="Rebuild the retrieval index from a directory of support documents.",
    )
    parser.add_argument("--source", type=Path, required=True,
                        help="Directory of Markdown/HTML/text/PDF documents to ingest.")
    parser.add_argument("--strategy", choices=["heading", "fixed"], default="heading",
                        help="Chunking strategy to use (default: heading).")
    parser.add_argument("--out", type=Path, default=_DEFAULT_OUT,
                        help=f"Output directory for the index manifest (default: {_DEFAULT_OUT}).")
    parser.add_argument("--rebuild", action="store_true",
                        help="Overwrite an existing index at --out.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    try:
        manifest = build_index(
            args.source, args.out,
            chunking_strategy=args.strategy,
            rebuild=args.rebuild,
        )
    except (NotADirectoryError, IndexAlreadyExistsError) as exc:
        print(f"error: {exc}")
        return 1

    print(f"Indexed {manifest['chunk_count']} chunks from {manifest['source_dir']} "
          f"({manifest['chunking_strategy']} strategy) -> {args.out}/manifest.json")
    return 0
