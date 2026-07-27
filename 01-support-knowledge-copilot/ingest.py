#!/usr/bin/env python
"""Re-index CLI entry point.

    python ingest.py --source data/sample_docs --rebuild

See `app.ingestion.cli` for the implementation.
"""
from __future__ import annotations

from app.ingestion.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
