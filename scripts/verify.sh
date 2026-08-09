#!/usr/bin/env bash
# Single reproducible verification entry point. Runs the full non-Lighthouse gate
# set; Lighthouse runs as its own CI step against the served pages. Fails fast.
set -euo pipefail

export UV_LINK_MODE="${UV_LINK_MODE:-copy}"
export UV_CACHE_DIR="${UV_CACHE_DIR:-.uvcache}"
# UTF-8 so tools decode process output correctly even under a non-ASCII repo path.
export PYTHONUTF8=1
export PYTHONIOENCODING=utf-8

step() { printf '\n=== %s ===\n' "$1"; }

step "python: ruff"
python -m uv run ruff check .

step "python: basedpyright"
python -m uv run basedpyright

step "django: migration drift"
python -m uv run python manage.py makemigrations --check --dry-run

step "django: system check"
python -m uv run python manage.py check

step "python: dependency audit"
python -m uv run pip-audit

step "frontend: biome"
bun run biome

step "frontend: tsc"
bun run typecheck

step "frontend: dependency audit"
bun audit

step "frontend: build bundle"
bun run build

step "python: full test suite (real PostgreSQL)"
python -m uv run pytest -q

step "e2e: Playwright + axe (chromium)"
bun run test:e2e -- --project=chromium

printf '\nAll verification gates passed.\n'
