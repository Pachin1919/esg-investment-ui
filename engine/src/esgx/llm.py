"""Provider-neutral structured LLM calls.

Primary model: Kimi K3 (Moonshot AI, OpenAI-compatible chat API, `MOONSHOT_API_KEY`). Claude models
(`ANTHROPIC_API_KEY`) stay available as a second rater: scores from two models are never comparable,
so every caller keeps the model id next to its output and in its cache key (Berg, Koelbel & Rigobon
2022 make the same point about ESG raters).

`parse(model, system, user, schema)` returns a validated pydantic object plus a usage dict with
`input_tokens`, `output_tokens`, `cache_read`, `model` for both providers.
"""

from __future__ import annotations

import json
import os
import random
import time

import requests
from pydantic import BaseModel, ValidationError

PRIMARY_MODEL = "kimi-k3"
KIMI_BASE_URL = os.environ.get("MOONSHOT_BASE_URL", "https://api.moonshot.ai/v1")
KEY_ENV = {"kimi": "MOONSHOT_API_KEY", "anthropic": "ANTHROPIC_API_KEY"}


def provider(model: str) -> str:
    """'kimi' for kimi-* / moonshot-* model ids, otherwise 'anthropic'."""
    return "kimi" if model.startswith(("kimi", "moonshot")) else "anthropic"


def key_env(model: str) -> str:
    return KEY_ENV[provider(model)]


def has_key(model: str) -> bool:
    return bool(os.environ.get(key_env(model), "").strip())


def _kimi_stream(key: str, body: dict) -> tuple[str, dict]:
    """POST with server-sent events, return (content, usage). Streaming keeps the connection alive while
    the model reasons; the server drops plain requests on long answers."""
    text, usage = [], {}
    with requests.post(f"{KIMI_BASE_URL}/chat/completions", headers={"Authorization": f"Bearer {key}"},
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


def kimi_parse[T: BaseModel](model: str, system: str, user: str, schema: type[T], max_tokens: int = 8000, retries: int = 6) -> tuple[T, dict]:
    """Chat completion with a strict JSON schema; retried on rate limits, server errors and invalid JSON."""
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
            content, u = _kimi_stream(key, body)
            parsed = schema.model_validate_json(content)
            return parsed, {"input_tokens": u.get("prompt_tokens", 0), "output_tokens": u.get("completion_tokens", 0),
                            "cache_read": (u.get("prompt_tokens_details") or {}).get("cached_tokens", 0), "model": model}
        except (requests.RequestException, ValidationError, ValueError) as e:
            last = e
            if attempt < retries:  # exponential backoff with jitter: parallel tasks share one rate limit
                time.sleep(min(90.0, 2.0 * 2**attempt) * (0.5 + random.random()))
    raise RuntimeError(f"kimi call failed after {retries + 1} attempts: {last}")


def claude_parse[T: BaseModel](model: str, system: str, user: str, schema: type[T], effort: str = "medium", max_tokens: int = 8000) -> tuple[T, dict]:
    """anthropic messages.parse with structured output and a cached system prompt."""
    from esgx.config import anthropic_client

    resp = anthropic_client().messages.parse(
        model=model, max_tokens=max_tokens,
        system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user}],
        output_config={"effort": effort}, output_format=schema,
    )
    if resp.stop_reason == "refusal":
        raise RuntimeError(f"model refused: {resp.stop_details}")
    usage = {"input_tokens": resp.usage.input_tokens, "output_tokens": resp.usage.output_tokens,
             "cache_read": getattr(resp.usage, "cache_read_input_tokens", 0), "model": model}
    return resp.parsed_output, usage


def parse[T: BaseModel](model: str, system: str, user: str, schema: type[T], effort: str = "medium", max_tokens: int = 8000) -> tuple[T, dict]:
    """Route to the model's provider. `effort` only applies to Claude models."""
    if provider(model) == "kimi":
        return kimi_parse(model, system, user, schema, max_tokens=max_tokens)
    return claude_parse(model, system, user, schema, effort=effort, max_tokens=max_tokens)
