"""Calculator tool: evaluates basic arithmetic without a bare eval(), which
would let arbitrary expressions (or attribute/call chains) run as code.
"""
from __future__ import annotations

import ast
import operator
from typing import Any

from pydantic import BaseModel, Field

from app.core.models import ToolSpec

_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
}
_UNARY_OPS = {ast.USub: operator.neg, ast.UAdd: operator.pos}


class CalculatorArgs(BaseModel):
    expression: str = Field(min_length=1, max_length=200)


def _eval_node(node: ast.AST) -> float:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
        return _BIN_OPS[type(node.op)](_eval_node(node.left), _eval_node(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
        return _UNARY_OPS[type(node.op)](_eval_node(node.operand))
    raise ValueError("Expression may only contain numbers, + - * / % ** and parentheses.")


def handle(args: CalculatorArgs) -> dict[str, Any]:
    try:
        tree = ast.parse(args.expression, mode="eval")
        result = _eval_node(tree.body)
    except SyntaxError as exc:
        raise ValueError(f"Could not parse expression: {exc.msg}") from exc
    except ZeroDivisionError as exc:
        raise ValueError("Division by zero.") from exc
    return {"expression": args.expression, "result": result}


SPEC = ToolSpec(
    name="calculator",
    description="Evaluate a basic arithmetic expression (+ - * / % ** and parentheses).",
    input_schema=CalculatorArgs.model_json_schema(),
    output_schema={
        "type": "object",
        "properties": {"expression": {"type": "string"}, "result": {"type": "number"}},
    },
    allowed_roles=["viewer", "analyst", "operator", "admin"],
    rate_limit_per_minute=60,
    risk_level="low",
    requires_approval=False,
)
