"""Paths and global settings. Paths are relative to the repo root unless ESGX_DATA_DIR /
ESGX_OUTPUT_DIR point elsewhere (a mounted Cloud Storage bucket in Cloud Run Jobs)."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]

# Load secrets and local settings from <repo>/.env (git-ignored). Existing
# environment variables take precedence over the file.
load_dotenv(ROOT / ".env", override=False)
DATA_DIR = Path(os.environ.get("ESGX_DATA_DIR") or ROOT / "data")
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
OUTPUT_DIR = Path(os.environ.get("ESGX_OUTPUT_DIR") or ROOT / "outputs")

for _d in (RAW_DIR, PROCESSED_DIR, OUTPUT_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# Generic web fetching sends a descriptive User-Agent with contact info on every request.
REQUEST_USER_AGENT = os.environ.get("ESGX_USER_AGENT") or os.environ.get("ESGX_SEC_USER_AGENT", "esgx research bot contact@example.com")

# Organization-scoped Anthropic API keys must send a workspace id on every request.
# Workspace-scoped keys can leave this empty.
ANTHROPIC_WORKSPACE_ID = os.environ.get("ANTHROPIC_WORKSPACE_ID", "").strip() or None


def anthropic_client():
    """Anthropic client with the workspace header attached when configured."""
    import anthropic

    headers = {"anthropic-workspace-id": ANTHROPIC_WORKSPACE_ID} if ANTHROPIC_WORKSPACE_ID else None
    return anthropic.Anthropic(default_headers=headers)


# Sample window for phase 0.
START_YEAR = 2010
END_YEAR = 2025

# Fallback availability assumption: fiscal-year-end December + seven months = July t+1.
# This is a modeling convention, not an assertion of actual publication dates. A supplied
# available_date takes precedence (and is used only after its month has completed).
EMISSIONS_PUBLICATION_LAG_MONTHS = 7
