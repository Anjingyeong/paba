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

- **Manager MFA attempt throttling — FIXED.** The TOTP step now locks out after
  `MFA_MAX_ATTEMPTS` (5) failures for `MFA_LOCKOUT` (15 min), via a database-backed
  `ManagerMfaThrottle` (shared across app instances — correct behind multiple
  Fargate tasks, unlike a per-process cache). The MFA view returns `429` while
  locked and clears the throttle on success. Mirrors the employee-PIN lockout.
- **Weekly-allowance month-boundary completeness — IMPLEMENTED.**
  `is_month_boundary_week_complete(month, weekly_rest_weekday, as_of)` derives, from
  the calendar alone, whether every labour week whose paid rest day falls in the
  month has fully elapsed; an incomplete boundary week now blocks the close
  (`collect_blockers` computes it from a line's `weekly_rest_weekday`, falling back
  to the explicit flag). This affects only *whether* a close is allowed, never a pay
  amount. Remaining follow-up: have the close *preview* populate `weekly_rest_weekday`
  per employee from `EmploymentTerms` (today the caller supplies it).
- **Insurance rates — updated to 2026, still pending primary-source sign-off.**
  `apps/payroll/data/insurance_rates/2026.1.json` now carries the *confirmed* 2026
  figures for **National Pension** (9.5% total → 4.75% employee) and **Health**
  (7.19% total → 3.595% employee), sourced from the 2025 announcements (`confirmed_2026:
  true`). **Long-term care** and **Employment** were still pre-notice (잠정) and are
  carried at 2025 values with `confirmed_2026: false`. `verification_status` stays
  `PENDING_OFFICIAL_VERIFICATION`: every figure needs primary-source human sign-off,
  and the manager's RECONCILED step is authoritative regardless. See
  `docs/runbooks/insurance-rate-update.md`.
- **Manager/kiosk Django routes — WIRED.** `/kiosk/` and `/manager/console/`
  (login-required) now render `templates/kiosk/states.html` and
  `templates/manager/console.html` as real Django routes. Setting
  `STATIC_URL="/assets/"` lets the templates' single literal `/assets/…` paths
  resolve both through Django's static machinery (dev + prod) and when the same
  files are served to the Playwright e2e — no template duplication, and the 35 e2e
  tests still pass. Remaining follow-up: inject *live* per-request state into these
  shells (they currently render the static state set the e2e exercises; the dynamic
  backend flows are covered by the Django integration tests).

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
