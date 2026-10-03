"""Kimi (Moonshot AI) chat client with structured output.

OpenAI-compatible API at https://api.moonshot.ai/v1, key in `MOONSHOT_API_KEY` (.env). The answer
is constrained to a pydantic model through `response_format = json_schema` (strict) and received as
a stream: without streaming the server drops the connection while the model is still reasoning.
"""

from __future__ import annotations

import json
import os
import time

import requests
from pydantic import BaseModel, ValidationError

import esgx.config  # noqa: F401  (loads .env)

BASE_URL = os.environ.get("MOONSHOT_BASE_URL", "https://api.moonshot.ai/v1")


def has_key() -> bool:
    return bool(os.environ.get("MOONSHOT_API_KEY", "").strip())


def _stream(key: str, body: dict) -> tuple[str, dict]:
    """POST with server-sent events; return (content, usage)."""
    text, usage = [], {}
    with requests.post(f"{BASE_URL}/chat/completions", headers={"Authorization": f"Bearer {key}"},
                       json={**body, "stream": True, "stream_options": {"include_usage": True}}, timeout=(30, 300), stream=True) as r:
        if r.status_code == 429 or r.status_code >= 500:
            raise requests.HTTPError(f"kimi {r.status_code}: {r.text[:200]}")
        if r.status_code != 200:
            raise RuntimeError(f"kimi {r.status_code}: {r.text[:300]}")
        for raw in r.iter_lines():
            line = raw.decode("utf-8", errors="replace")
            if not line.startswith("data:") or line.strip() == "data: [DONE]":
                continue
            chunk = json.loads(line[5:])
            usage = chunk.get("usage") or usage
            for choice in chunk.get("choices", []):
                usage = choice.get("usage") or usage
                text.append((choice.get("delta") or {}).get("content") or "")
    return "".join(text), usage


def kimi_parse[T: BaseModel](system: str, user: str, schema: type[T], model: str = "kimi-k3", max_tokens: int = 8000, retries: int = 2) -> tuple[T, dict]:
    """One agent call: system prompt + user message -> validated `schema` object and token usage.
    Retried on rate limits, server errors, dropped connections and invalid JSON."""
    key = os.environ.get("MOONSHOT_API_KEY", "").strip()
    if not key:
        raise RuntimeError("MOONSHOT_API_KEY is not set (add it to .env)")
    body = {
        "model": model, "max_tokens": max_tokens,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "response_format": {"type": "json_schema", "json_schema": {"name": schema.__name__, "strict": True, "schema": schema.model_json_schema()}},
    }
    last: Exception | None = None
    for attempt in range(retries + 1):
        try:
            content, u = _stream(key, body)
            return schema.model_validate_json(content), {"input_tokens": u.get("prompt_tokens", 0), "output_tokens": u.get("completion_tokens", 0), "model": model}
        except (requests.RequestException, ValidationError, ValueError) as e:
            last = e
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"kimi call failed after {retries + 1} attempts: {last}")
