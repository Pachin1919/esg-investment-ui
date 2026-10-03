"""Routes for the method snapshot and the agentic pipeline (agents, tools, configs, estimate, runs)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from esgx import llm
from esgx.agents.method import method_snapshot
from esgx.agents.pipeline import (
    Mode,
    Orchestrator,
    PipelineSpec,
    default_pipeline,
    estimate_cost,
    list_configs,
    save_config,
)

router = APIRouter(prefix="/api")
_orchestrator = Orchestrator()


@router.get("/method")
def method() -> dict:
    """The parameters the pipeline actually runs with (rubric, weights, terms, formulas)."""
    return method_snapshot()


@router.get("/pipeline/agents")
def pipeline_agents() -> list[dict]:
    """Agent definitions from pipeline/agents/<id>/: role, allowed tools, inputs, outputs."""
    from pipeline.agents import catalogue

    return catalogue()


@router.get("/pipeline/tools")
def pipeline_tools() -> list[dict]:
    """Tool registry from pipeline/tools/: name, kind (api/scrape/compute/llm/storage), cost, params."""
    from pipeline.tools import catalogue

    return catalogue()


@router.get("/pipeline/default")
def pipeline_default() -> dict:
    return default_pipeline().model_dump()


@router.get("/pipeline/configs")
def pipeline_configs() -> list[dict]:
    return list_configs()


class SaveConfigBody(BaseModel):
    name: str
    spec: PipelineSpec


@router.post("/pipeline/configs")
def pipeline_save_config(body: SaveConfigBody) -> dict:
    p = save_config(body.name, body.spec)
    return {"saved": p.name, "path": str(p)}


class EstimateBody(BaseModel):
    spec: PipelineSpec
    tickers: list[str]


@router.post("/pipeline/estimate")
def pipeline_estimate(body: EstimateBody) -> dict:
    """Rough cost before a live run: one picked report per firm and fiscal year in the window."""
    years = max(1, 2026 - int(body.spec.start[:4]))
    n_sections = len(body.tickers) * years
    n_fy = len(body.tickers) * years
    return {"sections": n_sections, "firm_years": n_fy, **estimate_cost(body.spec, n_sections, n_fy)}


class RunBody(BaseModel):
    spec: PipelineSpec
    tickers: list[str]
    mode: Mode = "dry_run"
    confirm_cost: bool = False


@router.post("/pipeline/runs")
def pipeline_start(body: RunBody) -> dict:
    if not body.tickers:
        raise HTTPException(400, "give at least one ticker")
    if body.mode == "live":
        missing = sorted({llm.key_env(s.agent.model) for s in body.spec.stages if s.enabled and s.agent and not llm.has_key(s.agent.model)})
        if missing:
            raise HTTPException(400, f"live mode needs {', '.join(missing)} in .env")
        est = pipeline_estimate(EstimateBody(spec=body.spec, tickers=body.tickers))
        if est["total_usd"] > 20 and not body.confirm_cost:
            raise HTTPException(400, f"estimated {est['total_usd']} USD > 20 USD; set confirm_cost=true to proceed")
    run = _orchestrator.start(body.spec, [t.upper() for t in body.tickers], body.mode)
    return run.to_dict(full=False)


@router.get("/pipeline/runs")
def pipeline_runs() -> list[dict]:
    return _orchestrator.list()


@router.get("/pipeline/runs/{run_id}")
def pipeline_run(run_id: str) -> dict:
    run = _orchestrator.get(run_id)
    if not run:
        raise HTTPException(404, "unknown run")
    return run.to_dict()
