"""Tool registry: every callable tool, its Pydantic argument model, and its
handler function, keyed by name. This is the single place new tools get
wired in.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

from app.core.models import ToolSpec
from app.tools import calculator, csv_query, files, ticketing, web_search


@dataclass(frozen=True)
class ToolDefinition:
    spec: ToolSpec
    args_model: type[BaseModel]
    handler: Callable[[Any], dict[str, Any]]


REGISTRY: dict[str, ToolDefinition] = {
    calculator.SPEC.name: ToolDefinition(calculator.SPEC, calculator.CalculatorArgs, calculator.handle),
    files.SPEC.name: ToolDefinition(files.SPEC, files.FileReaderArgs, files.handle),
    web_search.SPEC.name: ToolDefinition(web_search.SPEC, web_search.WebSearchArgs, web_search.handle),
    csv_query.SPEC.name: ToolDefinition(csv_query.SPEC, csv_query.CsvQueryArgs, csv_query.handle),
    ticketing.SPEC.name: ToolDefinition(ticketing.SPEC, ticketing.TicketCreateArgs, ticketing.handle),
}


def get_tool(name: str) -> ToolDefinition | None:
    return REGISTRY.get(name)


def list_tools() -> list[ToolSpec]:
    return [definition.spec for definition in REGISTRY.values()]
