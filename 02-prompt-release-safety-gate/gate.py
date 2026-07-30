#!/usr/bin/env python
"""Release gate CLI entry point.

    python gate.py --baseline crm_summary_v1 --candidate crm_summary_v2

Exits non-zero (blocking a CI merge) when the gate decision is BLOCK.
See `app.eval.cli` for the implementation.
"""
from __future__ import annotations

from app.eval.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
