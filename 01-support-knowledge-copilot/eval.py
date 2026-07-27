#!/usr/bin/env python
"""Eval CLI entry point.

    python eval.py --strategy hybrid

See `app.eval.cli` for the implementation.
"""
from __future__ import annotations

from app.eval.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
