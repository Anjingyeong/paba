<div align="center">

# 🧾 PABA

### Single-Store Payroll & Attendance Backend

**한 매장의 근태 입력부터 월 급여 마감, 급여명세서 출력까지 하나의 데이터 흐름으로 관리하는 Django 기반 업무 자동화 웹앱입니다.**

![Django](https://img.shields.io/badge/Django-092E20?style=flat-square&logo=django&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-18-4169E1?style=flat-square&logo=postgresql&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.13-3776AB?style=flat-square&logo=python&logoColor=white)
![Playwright](https://img.shields.io/badge/Playwright-E2E-2EAD33?style=flat-square&logo=playwright&logoColor=white)

`Attendance · Payroll · Audit Log · Monthly Close · XLSX Export · PostgreSQL`

</div>

---

## Why I built it

소규모 매장에서는 출퇴근 기록, 근무시간 수정, 급여 계산, 월말 마감, 급여명세서 생성이 각각 따로 관리되기 쉽습니다.

이 프로젝트는 이 과정을 하나의 백엔드 데이터 흐름으로 연결하는 것을 목표로 합니다.

```text
Employee Punch
      ↓
Attendance State
      ↓
Correction / Approval
      ↓
Payable Time
      ↓
Payroll Policy
      ↓
Immutable Monthly Close
      ↓
XLSX Pay Statement
```

단순 CRUD보다 **급여 데이터의 정합성, 변경 이력, 동시성, 마감 이후 불변성**을 중요하게 설계했습니다.

---

## Backend design highlights

- Server-rendered Django architecture
- PostgreSQL 18 only — SQLite 미사용
- employee PIN 기반 attendance kiosk
- manager TOTP MFA
- idempotent punch state machine
- correction / approval workflow
- append-only audit log
- effective-dated payroll policies
- PostgreSQL exclusion constraint로 기간 중복 방지
- row lock + DB constraint 기반 concurrency control
- immutable monthly close snapshot
- PII-free / formula-free XLSX export
- readiness / liveness health probes
- real PostgreSQL 기반 test suite
- Playwright + axe E2E 검증

---

## Architecture

| App | Responsibility |
| --- | --- |
| `apps.core` | Store singleton, effective-dated base, money / crypto primitives |
| `apps.identity` | Employee, account roles, manager TOTP, employee PIN |
| `apps.devices` | Kiosk pairing, device secret, kiosk cookie |
| `apps.auditlog` | Append-only audit log, redaction, retention / purge |
| `apps.attendance` | Punch state machine, correction / approval, payable time |
| `apps.payroll` | Pay policies, allowance, insurance, immutable monthly close |
| `apps.exports` | XLSX statements, manager summary, ZIP / manifest |
| `apps.health` | Liveness / readiness probes |

### Important invariants

Audit entries and monthly close snapshots are immutable at both model and database layers.

Effective-dated policies cannot overlap because PostgreSQL exclusion constraints enforce the rule in the database.

Punches and closes use row locks and constraints to protect concurrency-sensitive operations.

Money is handled as integer KRW with `Decimal` where calculation precision is required, and final rounding is performed once at the end.

---

## Requirements

- Python 3.13
- `uv`
- PostgreSQL 18 — native or Docker
- Bun

---

## Local setup

```bash
cp .env.example .env

uv sync --all-groups
bun install --frozen-lockfile
bun run build

# PostgreSQL
# docker compose up -d db

uv run python manage.py migrate
uv run python manage.py runserver
```

---

## Design system

`DESIGN.md`와 `assets/`에는 theme-aware token 기반 UI 시스템이 정의되어 있습니다.

- light / dark theme
- WCAG 2.2 AA 고려
- locally bundled `@carbon/web-components`
- full-screen kiosk UI
- fixed-sidenav manager console

---

## Health probes

```text
GET /health/live
```

Process liveness 확인. DB를 조회하지 않습니다.

```text
GET /health/ready
```

DB 연결 가능 시 `200`, 불가능하면 내부 정보를 노출하지 않고 `503`을 반환합니다.

---

## Verification

전체 검증:

```bash
bash scripts/verify.sh
```

검증 항목:

- Ruff
- basedpyright
- migration drift / Django system checks
- `pip-audit`
- Biome
- TypeScript compiler
- `bun audit`
- frontend bundle build
- full pytest against real PostgreSQL
- Playwright E2E
- axe accessibility checks
- Terraform fmt / validate — Terraform 설치 시

개별 실행:

```bash
uv run pytest -q
bun run test:e2e -- --project=chromium
```

Settings:

```text
config/settings/
├─ base
├─ local
├─ test
└─ production
```

---

## Operations

지난달 DRAFT payroll period 준비:

```bash
python manage.py prepare_payroll_periods
```

Retention purge dry-run:

```bash
python manage.py purge_expired
```

실제 purge:

```bash
python manage.py purge_expired --confirm
```

Operational runbook은 `docs/runbooks/`에 정리되어 있습니다.

Infrastructure definition은 `infra/terraform/`에 있으며, 실제 cloud apply는 운영자 승인 없이 수행하지 않습니다.

---

## CI

`.github/workflows/ci.yml`은 다음을 검증합니다.

```text
scripts/verify.sh
→ PostgreSQL 18 service tests
→ production deploy checks
→ Lighthouse
→ container image build
```

---

<div align="center">

**From attendance input to an auditable monthly payroll close.**

</div>
