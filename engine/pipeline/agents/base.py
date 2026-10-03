"""Agent definitions. An agent = a role, the tools it may use, the inputs it reads from the shared
context, the outputs it writes, and a `run` function. LLM agents also carry a default model, effort
and base prompt; deterministic agents have `llm=False` and never touch the network for model calls."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from pipeline.spec import DEFAULT_MODEL, AgentSpec, Mode, PipelineSpec, StageKind, StageSpec
from pipeline.tools.base import TOOLS, ToolBox


class RunLog(Protocol):
    """What an agent may do with the run: append to the log. Nothing else."""

    def emit(self, stage: str, msg: str) -> None: ...


@dataclass
class StageTask:
    """Everything one agent gets for one stage of one run."""

    run: RunLog
    spec: PipelineSpec
    stage: StageSpec
    mode: Mode
    tickers: list[str]
    ctx: dict[str, Any]
    run_dir: Path
    tools: ToolBox

    @property
    def agent(self) -> AgentSpec:
        return self.stage.agent or AgentSpec()

    def param(self, key: str, default: Any = None) -> Any:
        return self.stage.params.get(key, default)

    def log(self, msg: str) -> None:
        self.run.emit(self.stage.id, msg)


@dataclass(frozen=True)
class AgentDefinition:
    id: str
    kind: StageKind
    name: str
    role: str
    description: str
    tools: tuple[str, ...]
    run: Callable[[StageTask], dict[str, Any]]
    inputs: tuple[str, ...] = ()
    outputs: tuple[str, ...] = ()
    llm: bool = False
    default_model: str | None = None
    default_effort: str = "medium"
    default_role_prompt: str = ""
    default_params: dict[str, Any] = field(default_factory=dict)
    enabled_by_default: bool = True

    def __post_init__(self) -> None:
        unknown = [t for t in self.tools if t not in TOOLS]
        if unknown:
            raise KeyError(f"agent {self.id} lists unknown tools {unknown}")

    def toolbox(self) -> ToolBox:
        return ToolBox(self.tools)

    def default_stage(self) -> StageSpec:
        return StageSpec(
            id=self.id, kind=self.kind, name=self.name, description=self.description, enabled=self.enabled_by_default,
            agent=AgentSpec(name=self.name.split(" ")[0], model=self.default_model or DEFAULT_MODEL,
                            effort=self.default_effort, role_prompt=self.default_role_prompt) if self.llm else None,
            params=dict(self.default_params),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id, "kind": self.kind, "name": self.name, "role": self.role, "description": self.description,
            "llm": self.llm, "default_model": self.default_model, "default_effort": self.default_effort,
            "default_role_prompt": self.default_role_prompt, "inputs": list(self.inputs), "outputs": list(self.outputs),
            "tools": [TOOLS[t].to_dict() for t in self.tools], "default_params": self.default_params,
            "folder": f"pipeline/agents/{self.id}",
        }
