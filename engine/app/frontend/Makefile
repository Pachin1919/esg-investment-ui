# Frontend (React + TypeScript + Vite). Mirrors the Dentio frontend Makefile.
#   make dev                       - Vite on PORT (8001), API on BACKEND_PORT (8000)
#   make dev PORT=8003 BACKEND_PORT=8002
SHELL := /bin/bash
PORT ?= 8001
BACKEND_PORT ?= 8000

.PHONY: help install dev build preview lint format type-check clean

help:
	@echo "make dev | build | preview | lint | format | type-check | install | clean"

install:
	npm ci --no-audit --no-fund

dev: node_modules
	PORT=$(PORT) BACKEND_PORT=$(BACKEND_PORT) npm run dev

node_modules:
	npm install --no-audit --no-fund

build: node_modules
	npm run build

preview: build
	PORT=$(PORT) npm run preview

lint: node_modules
	npm run lint

format: node_modules
	npm run format

type-check: node_modules
	npm run type-check

clean:
	rm -rf dist node_modules
