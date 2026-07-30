"""Load and validate versioned prompt YAML files from `/prompts`."""
from __future__ import annotations

from pathlib import Path

import yaml

from app.prompts.spec import PromptSpec

_PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"


def load_prompt(name: str, prompts_dir: Path | None = None) -> PromptSpec:
    """Load a single prompt YAML file by name (without the `.yaml` suffix)."""
    directory = prompts_dir or _PROMPTS_DIR
    path = directory / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Prompt file not found: {path}")
    with path.open("r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    return PromptSpec.model_validate(raw)


def list_prompts(prompts_dir: Path | None = None) -> list[str]:
    """List available prompt names (without the `.yaml` suffix)."""
    directory = prompts_dir or _PROMPTS_DIR
    return sorted(p.stem for p in directory.glob("*.yaml"))
