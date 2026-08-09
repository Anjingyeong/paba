# Self-review notes & known limitations

A record of the self-review pass after the initial build: what was fixed, and the
honest gaps a reviewer/operator should know about. This is deliberately candid so
the eventual multi-agent review (`/code-review ultra`) and operators start informed.

## Bugs found and fixed in self-review

- **Close blocker scoped to the period** (`6f20507`) — `collect_blockers` treated
  *any* globally open shift as an `OPEN_SHIFT` blocker, so an employee currently
  clocked in (a later month) wrongly blocked a prior month's close. Now scoped to
  shifts with a punch inside the month being closed. Regression tests added.
- **Idempotent concurrent duplicate punches** (`c1416d0`) — a concurrent duplicate
  of a BREAK/CLOCK_OUT punch (same idempotency key — a real double-tap) made the
  loser raise `NO_OPEN_SHIFT`/`ILLEGAL_TRANSITION` instead of returning the
  already-recorded event. Now re-checks the key under the shift lock and returns
  the canonical event. "Exactly one event" always held; the response is now
  idempotent for every punch kind. Concurrency test added.

## Known limitations / hardening opportunities

- **Manager MFA has no attempt throttling.** Employee PINs lock out after 10
  failures, but TOTP verification at the MFA step is unlimited. With the password
  already known, TOTP is brute-forceable over time (valid_window=1 → ~3 valid codes
  per 30 s). *Recommended:* per-user attempt limiting via a shared cache (Redis in
  production; `LocMemCache` is per-process and unsuitable), plus a short backoff.
  Left out because it needs a shared cache backend not yet provisioned.
- **Weekly-allowance month attribution is not auto-computed.** The engine computes
  the amount from confirmed facts, but "the allowance belongs to the month
  containing the paid weekly rest day" and "an incomplete month-boundary week blocks
  close" are represented as payload flags (`month_boundary_week_complete`) rather
  than derived by a service. A future service should compute these from the
  employee's terms + shifts feeding the close preview.
- **Insurance rates are unverified.** `apps/payroll/data/insurance_rates/2026.1.json`
  carries `verification_status: PENDING_OFFICIAL_VERIFICATION`. The figures must be
  checked against the official sources before production; the manager's RECONCILED
  step is authoritative regardless. See `docs/runbooks/insurance-rate-update.md`.
- **Manager/kiosk pages are validated as static-served templates.** `templates/
  kiosk/states.html` and `templates/manager/console.html` are exercised by
  Playwright over a static server (mirroring the design-system showcase). Wiring
  server-rendered Django routes that inject live state via `{% static %}` is a
  follow-up; the dynamic backend flows are covered by the Django integration tests.

## Verified only in CI (tools unavailable / killed locally in this environment)

- **LibreOffice PDF render** (`tests/exports/test_render.py`) auto-skips when
  `soffice` is absent; runs in CI. Three attempts to install LibreOffice locally
  were terminated by the environment.
- **`terraform validate`** was run locally (v1.9.8) — *passes* — and is also in CI
  alongside `tflint`/`checkov`.

## Requires the operator (never done autonomously)

- **AWS apply / DNS** — needs the operator's account, domain, ECR image, and
  explicit approval (`infra/terraform/README.md`, `docs/runbooks/deploy.md`).
- **`/code-review ultra`** — the plan's final F1-F4 multi-agent review is
  user-triggered.
