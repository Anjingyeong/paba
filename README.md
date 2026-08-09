# Paris Baguette — Single-Store Payroll & Attendance

Server-rendered Django + PostgreSQL web app for one store: a shared-tablet
attendance kiosk (employee PIN punches) and a manager console (TOTP MFA) for
corrections, approvals, effective-dated pay/insurance policies, immutable monthly
close, and compliant XLSX pay-statement export.

> Scope, guardrails and the full build plan live in
> `.omo/plans/paris-baguette-payroll-automation.md`.

## Requirements

- Python 3.13 (`py -3.13` on Windows)
- [uv](https://docs.astral.sh/uv/) for Python dependency management
- PostgreSQL 18 (native install **or** Docker) — **required**; SQLite is never used
- [Bun](https://bun.sh/) for bundling `@carbon/web-components`

## Local setup

```bash
cp .env.example .env            # then edit secrets/DB credentials

uv sync --all-groups            # Python deps
bun install --frozen-lockfile   # frontend deps
bun run build                   # bundle Carbon web components -> assets/vendor

# PostgreSQL: either `docker compose up -d db` OR a native PostgreSQL 18 service.
uv run python manage.py migrate
uv run python manage.py runserver
```

## Health probes

- `GET /health/live`  — process is up (never touches the DB) → `200`
- `GET /health/ready` — DB reachable → `200`, otherwise → `503` (no internals leaked)

## Tests

```bash
uv run pytest tests/smoke -q    # smoke shell
uv run pytest -q                # full suite (needs PostgreSQL)
```

Settings are split under `config/settings/`: `base` (shared), `local` (dev),
`test` (real PostgreSQL, fast hashing), `production` (fails closed, full hardening).
