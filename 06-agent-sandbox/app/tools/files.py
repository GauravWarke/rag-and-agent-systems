"""File reader tool, sandboxed to a single folder.

Every requested path is resolved and checked against the sandbox root
before the file is opened, so `../../etc/passwd`-style traversal never
reaches the filesystem.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.models import ToolSpec

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_MAX_CHARS = 5000


class FileReaderArgs(BaseModel):
    path: str = Field(min_length=1, max_length=200)


def _sandbox_root() -> Path:
    configured = Path(settings.sandbox_dir)
    root = configured if configured.is_absolute() else _PROJECT_ROOT / configured
    return root.resolve()


def handle(args: FileReaderArgs) -> dict[str, Any]:
    root = _sandbox_root()
    target = (root / args.path).resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise ValueError("Path escapes the sandbox directory.") from exc
    if not target.is_file():
        raise ValueError(f"No such file in sandbox: {args.path!r}")

    text = target.read_text(encoding="utf-8", errors="replace")
    return {
        "path": args.path,
        "content": text[:_MAX_CHARS],
        "truncated": len(text) > _MAX_CHARS,
    }


SPEC = ToolSpec(
    name="file_reader",
    description="Read a text file from the workspace sandbox folder.",
    input_schema=FileReaderArgs.model_json_schema(),
    output_schema={
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "content": {"type": "string"},
            "truncated": {"type": "boolean"},
        },
    },
    allowed_roles=["analyst", "operator", "admin"],
    rate_limit_per_minute=60,
    risk_level="low",
    requires_approval=False,
)
