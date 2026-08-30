#!/usr/bin/env python
"""Operational metrics report entry point.

    python operational_metrics.py

See `app.metrics` for the implementation.
"""
from __future__ import annotations

from app.metrics import format_report, run_operational_metrics

if __name__ == "__main__":
    print(format_report(run_operational_metrics()))
