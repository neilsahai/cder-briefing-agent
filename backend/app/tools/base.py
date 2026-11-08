"""Tool registry. Each certified tool is a plain Python function with a Pydantic input model.
The registry produces Anthropic tool specs so the planner sees exactly the same contract the
tests exercise. No tool ever calls an LLM. No tool ever returns a number without RowRefs."""
from __future__ import annotations

import inspect
import typing
from dataclasses import dataclass
from typing import Any, Callable

from pydantic import BaseModel

from ..models import ToolResult


@dataclass
class Tool:
    name: str
    description: str
    input_model: type[BaseModel]
    fn: Callable[..., ToolResult]
    certified: bool = True
    decision_refs: tuple[str, ...] = ()

    def spec(self) -> dict[str, Any]:
        schema = self.input_model.model_json_schema()
        schema.pop("title", None)
        return {"name": self.name, "description": self.description, "input_schema": schema}


REGISTRY: dict[str, Tool] = {}


def tool(name: str, description: str, decision_refs: tuple[str, ...] = (), certified: bool = True):
    def deco(fn: Callable[..., ToolResult]):
        hints = typing.get_type_hints(fn)
        params = [p for p in inspect.signature(fn).parameters]
        model = hints.get(params[0]) if params else None
        if model is None or not (inspect.isclass(model) and issubclass(model, BaseModel)):
            raise TypeError(f"tool {name} must take a single Pydantic model argument")
        REGISTRY[name] = Tool(name, description.strip(), model, fn, certified, decision_refs)
        return fn
    return deco


def get_tool(name: str) -> Tool:
    return REGISTRY[name]


def call_tool(name: str, args: dict[str, Any]) -> ToolResult:
    t = REGISTRY[name]
    model = t.input_model(**args)
    res = t.fn(model)
    res.tool = name
    from .warnings_util import consolidate
    res.warnings = consolidate(res.warnings)
    # Expose computed alternate readings as an addressable, citable path so the narrator can state them
    # via placeholders ({{E1.alternate_readings["in shortage"].distinct_drugs}}) instead of "not computed".
    alts = {i.term: {"chosen": i.chosen, "result": i.alternate_result, "differs": i.differs}
            for i in res.interpretations if i.alternate_result is not None}
    if alts and isinstance(res.value, dict) and "alternate_readings" not in res.value:
        res.value["alternate_readings"] = alts
    return res


def anthropic_tool_specs(names: list[str] | None = None) -> list[dict[str, Any]]:
    return [t.spec() for n, t in REGISTRY.items() if names is None or n in names]
