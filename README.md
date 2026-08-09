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

## Architecture

Server-rendered Django, one legal user / one store (no multitenancy). Apps:

| App | Responsibility |
| --- | --- |
| `apps.core` | `Store` singleton, effective-dated base, money (integer KRW + Decimal), app crypto |
| `apps.identity` | `Employee` (independent `AccountRole` vs `CompensationProfile`), manager TOTP, employee PIN |
| `apps.devices` | Kiosk pairing (one-time codes, revocable device secrets, `__Host-kiosk` cookie) |
| `apps.auditlog` | Append-only audit log (model guard + DB trigger), object authz, log redaction, retention/purge |
| `apps.attendance` | Idempotent punch state machine, corrections/approvals, Decimal payable-time calculation |
| `apps.payroll` | Effective-dated policies, base pay + weekly allowance, insurance estimate/reconcile, immutable monthly close |
| `apps.exports` | PII-free, formula-free XLSX pay statements + manager summary + ZIP/manifest (5-min private download) |
| `apps.health` | `/health/live`, `/health/ready` probes |

Key invariants: audit entries and close snapshots are immutable at the model **and**
database (trigger) layers; effective-dated policies forbid overlapping periods via
PostgreSQL exclusion constraints; punches and closes are concurrency-safe (row
locks + constraints); all money is integer KRW rounded up once at the end; legal
applicability of weekly allowance / insurance is always a manager decision, never
automatic. There is no `base × 0.2`, no volatile spreadsheet formulas, no PII in
exports, and no JWT / web-storage tokens.

Design system (`DESIGN.md`, `assets/`): theme-aware tokens (light + dark, WCAG 2.2
AA) on locally-bundled `@carbon/web-components`; a full-screen kiosk cover and a
fixed-sidenav manager console.

## Health probes

- `GET /health/live`  — process is up (never touches the DB) → `200`
- `GET /health/ready` — DB reachable → `200`, otherwise → `503` (no internals leaked)

## Verification

One reproducible command runs every gate (fails fast):

```bash
bash scripts/verify.sh
```

It runs ruff, basedpyright, migration-drift + system checks, `pip-audit`, Biome,
`tsc`, `bun audit`, the bundle build, the full `pytest` suite against **real
PostgreSQL**, the Playwright + axe end-to-end suite (chromium), and — when
`terraform` is on `PATH` — `terraform fmt/validate` for `infra/terraform`.

```bash
uv run pytest -q                 # Python suite (needs PostgreSQL)
bun run test:e2e -- --project=chromium   # kiosk / manager / design-system e2e
```

Settings are split under `config/settings/`: `base` (shared), `local` (dev),
`test` (real PostgreSQL, fast hashing), `production` (fails closed, full hardening).

## Operations

- `python manage.py prepare_payroll_periods` — idempotently prepare the previous
  month's DRAFT period (scheduled daily in production via EventBridge).
- `python manage.py purge_expired [--confirm]` — retention purge (dry-run by
  default; legal holds protect subjects).
- Infrastructure (AWS Seoul, `ap-northeast-2`) is defined in `infra/terraform/`;
  operational runbooks (deploy, restore, incident, quarterly access review,
  insurance-rate update, legal hold/purge) are in `docs/runbooks/`. **No real AWS
  apply happens without the operator's account, domain, image and explicit
  approval.**

## CI

`.github/workflows/ci.yml` runs `scripts/verify.sh` on a `postgres:18` service,
the production deploy check, a Lighthouse job (100 in every category), and a
container image build.
