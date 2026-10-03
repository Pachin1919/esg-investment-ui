"""Tool registry. Importing this package registers every tool module; `TOOLS` maps name -> Tool.

Kinds: api (structured HTTP APIs: HKEXnews, TWSE/TPEx open data, yfinance), scrape (HTML/PDF
fetching), compute (pure functions), llm (paid model calls), storage (local parquet/csv).
Cost: free, network (rate-limited downloads), paid (LLM tokens). An agent only sees the tools
listed in its definition.
"""

from pipeline.tools import (  # noqa: F401  (registration)
    hard_data,
    hkex,
    llm,
    llm_sources,
    market,
    sources,
    storage,
    text,
    web,
)
from pipeline.tools.base import TOOLS, Tool, ToolBox, tool

__all__ = ["TOOLS", "Tool", "ToolBox", "tool"]


def catalogue() -> list[dict]:
    return [t.to_dict() for t in TOOLS.values()]
