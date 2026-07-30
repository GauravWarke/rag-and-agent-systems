"""Versioned prompt contract (Phase 1, step 2).

Every prompt used by the CRM summary feature is a YAML file under
`/prompts` validated against this schema, so a prompt change is reviewable
as a structured diff rather than free-text.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class ModelSettings(BaseModel):
    model: str = "stub"
    temperature: float = 0.0
    max_output_tokens: int = 200
    style: str = "concise"  # concise | verbose — verbose stub output costs more tokens


class FewShotExample(BaseModel):
    input: str
    output: dict


class PromptSpec(BaseModel):
    name: str
    version: str
    owner: str
    description: str
    model_settings: ModelSettings
    system_prompt: str
    few_shot_examples: list[FewShotExample] = Field(default_factory=list)
    output_schema: str = "NoteSummary"
