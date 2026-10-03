"""Generic web tools: rate-limited HTTP GET with the project User-Agent, HTML to text."""

from __future__ import annotations

import time

import requests

from esgx.config import REQUEST_USER_AGENT
from esgx.ingest.text_filter import html_to_text as _html_to_text
from pipeline.tools.base import tool

_last_call = 0.0


@tool(kind="scrape", cost="network")
def http_get(url: str, min_interval: float = 0.11, timeout: int = 30) -> str:
    """Fetch a URL as text with the project User-Agent and a minimum interval between calls."""
    global _last_call
    wait = min_interval - (time.time() - _last_call)
    if wait > 0:
        time.sleep(wait)
    r = requests.get(url, headers={"User-Agent": REQUEST_USER_AGENT}, timeout=timeout)
    _last_call = time.time()
    r.raise_for_status()
    return r.text


@tool(kind="compute", cost="free")
def html_to_text(html: str) -> str:
    """Strip an HTML document to plain text with paragraph breaks preserved."""
    return _html_to_text(html)
