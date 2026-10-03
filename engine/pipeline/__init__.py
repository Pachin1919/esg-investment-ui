"""Agentic pipeline package: `pipeline.tools` (what agents may call) and `pipeline.agents`
(one sub-package per agent: role, allowed tools, inputs, outputs, run function).

The orchestrator in `esgx.agents.pipeline` runs these agents in the order of a `PipelineSpec`.
The dashboard's Pipeline page and `scripts/run_pipeline.py` both go through that orchestrator.
"""
