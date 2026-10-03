"""Tool registry. A tool is a plain Python function registered with `@tool(...)`; agents receive a
`ToolBox` that exposes only the tools their definition allows, so an agent cannot call a paid or
network tool it was not granted."""

from __future__ import annotations

import inspect
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Literal

ToolKind = Literal["api", "scrape", "compute", "llm", "storage"]
ToolCost = Literal["free", "network", "paid"]


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    kind: ToolKind
    cost: ToolCost
    fn: Callable[..., Any]
    params: dict[str, str] = field(default_factory=dict)
    module: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "description": self.description, "kind": self.kind, "cost": self.cost,
                "params": self.params, "module": self.module}


TOOLS: dict[str, Tool] = {}


def tool(kind: ToolKind, cost: ToolCost, name: str | None = None) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Register `fn` as a tool. Description = first line of the docstring; params from the signature."""

    def deco(fn: Callable[..., Any]) -> Callable[..., Any]:
        tool_name = name or fn.__name__
        sig = inspect.signature(fn)
        params = {p.name: (str(p.annotation.__name__) if hasattr(p.annotation, "__name__") else str(p.annotation)) + ("" if p.default is inspect.Parameter.empty else f" = {p.default!r}")
                  for p in sig.parameters.values()}
        TOOLS[tool_name] = Tool(name=tool_name, description=(fn.__doc__ or "").strip().splitlines()[0] if fn.__doc__ else "",
                                kind=kind, cost=cost, fn=fn, params=params, module=fn.__module__)
        return fn

    return deco


class ToolBox:
    """Attribute access to allowed tools only: `tools.edgar_load_documents(...)`."""

    def __init__(self, allowed: tuple[str, ...] | list[str]):
        unknown = [a for a in allowed if a not in TOOLS]
        if unknown:
            raise KeyError(f"unknown tools: {unknown}")
        self._allowed = tuple(allowed)

    def __getattr__(self, name: str) -> Callable[..., Any]:
        if name.startswith("_"):
            raise AttributeError(name)
        if name not in self._allowed:
            raise PermissionError(f"tool '{name}' is not allowed for this agent (allowed: {list(self._allowed)})")
        return TOOLS[name].fn

    def allowed(self) -> list[Tool]:
        return [TOOLS[n] for n in self._allowed]
