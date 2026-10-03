# =============================================================================
# ESG Exposure Engine – root Makefile
# =============================================================================
# Follows the Dentio pattern: one command surface per service, dev servers on
# separate ports (API 8000, web 8001), both overridable for parallel instances.
#
#   make help                 - list commands
#   make install              - python deps into .venv (uv) + npm ci for the frontend
#   make api                  - FastAPI dev server (uvicorn, reload) on PORT (default 8000)
#   make web                  - Vite dev server on WEB_PORT (default 8001), proxies /api to PORT
#   make dev                  - both, in one terminal (Ctrl-C stops both)
#   make test / make lint     - pytest + ruff, and frontend type-check + eslint
#   make build                - production build of the frontend into app/frontend/dist
# =============================================================================

SHELL := /bin/bash
PORT ?= 8000
WEB_PORT ?= 8001
PY := .venv/bin/python
FRONTEND := app/frontend

.PHONY: help install install-py install-web api web dev test lint build clean brain-push

help:
	@echo "ESG Exposure Engine"
	@echo ""
	@echo "  make install        install python (.venv via uv) and frontend (npm) dependencies"
	@echo "  make api            FastAPI dev server on http://localhost:$(PORT)  (docs at /docs)"
	@echo "  make web            Vite dev server on http://localhost:$(WEB_PORT)"
	@echo "  make dev            api + web together"
	@echo "  make test           pytest + frontend type-check"
	@echo "  make lint           ruff + eslint"
	@echo "  make build          production frontend build"
	@echo "  make brain-push     mirror brain/ (Obsidian vault) to the ESG-Investing-Brain repo"
	@echo ""
	@echo "  Override ports: make dev PORT=8002 WEB_PORT=8003"

install: install-py install-web

install-py:
	@command -v uv >/dev/null 2>&1 || { echo "uv not found: https://docs.astral.sh/uv/"; exit 1; }
	@[ -d .venv ] || uv venv --python 3.12 .venv
	uv pip install --python $(PY) -e ".[dev,api]"

install-web:
	@command -v npm >/dev/null 2>&1 || { echo "npm not found: install Node 18+ (brew install node)"; exit 1; }
	cd $(FRONTEND) && npm ci --no-audit --no-fund

api:
	@echo "API on http://localhost:$(PORT)  (OpenAPI docs: /docs)"
	$(PY) -m uvicorn esgx.api.main:app --host 127.0.0.1 --port $(PORT) --reload --reload-dir src

web:
	@echo "Web on http://localhost:$(WEB_PORT)  (API proxied from port $(PORT))"
	cd $(FRONTEND) && PORT=$(WEB_PORT) BACKEND_PORT=$(PORT) npm run dev

dev:
	@trap 'kill 0' INT TERM EXIT; \
	$(MAKE) api PORT=$(PORT) & \
	$(MAKE) web PORT=$(PORT) WEB_PORT=$(WEB_PORT) & \
	wait

test:
	$(PY) -m pytest -q
	cd $(FRONTEND) && npm run type-check

lint:
	.venv/bin/ruff check src tests scripts pipeline kimi-agents
	cd $(FRONTEND) && npm run lint

build:
	cd $(FRONTEND) && npm run build

brain-push:
	git subtree push --prefix=brain brain main

clean:
	rm -rf $(FRONTEND)/dist .pytest_cache .ruff_cache
