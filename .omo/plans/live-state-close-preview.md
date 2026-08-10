# Live State and Close Preview

## TL;DR
> Summary:      Replace the static kiosk/manager shells with server-rendered live context and truthful empty states, then resolve payroll close weekly-rest blockers from the effective `EmploymentTerms` record with the existing caller value as fallback.
> Deliverables:
> - Live `/kiosk/` and authenticated `/manager/console/` pages backed by the existing device/attendance integration contracts, with no synthetic rows
> - Effective-date `weekly_rest_weekday` resolution in the close-blocker seam, preserving caller fallback
> - Complete browser QA, diagnostics, test, cleanup, and four-lane review evidence
> Effort:       Short
> Risk:         Medium - two existing static/client-synthetic paths must be replaced without changing their integration contracts, and payroll date-boundary precedence must remain backward-compatible

## Scope
### Must have
- Exactly three work units: W1 live server-rendered pages, W2 payroll effective-term derivation, and W3 verification/review.
- W1 owns `config/urls.py`, `apps/devices/views.py`, `apps/attendance/views.py`, `templates/kiosk/states.html`, `templates/manager/console.html`, `assets/ts/kiosk.ts`, `assets/ts/manager.ts`, `tests/smoke/test_routes.py`, and any narrowly scoped live-state QA fixture/helper under `tests/support/`.
- W2 owns `apps/payroll/services/close.py` and `tests/payroll/test_close.py`.
- W3 owns no product/source files; it only creates evidence beneath `<attemptDir>` and runs the gate.
- Keep the existing device and attendance integration response contracts intact while sharing their live query/serialization source with the HTML views.
- Use half-open effective ranges: the start date is included and the end date is excluded.
- Prefer an effective `EmploymentTerms.weekly_rest_weekday`; use the caller-supplied weekday only when no applicable non-null term value exists.
- Use `./.venv/Scripts/python.exe` for Django/pytest and `bun` for TypeScript diagnostics.

### Must NOT have (guardrails, anti-slop, scope boundaries)
- No insurance-rate code, model, migration, fixture, or test changes.
- No new API endpoint, schema change, background polling protocol, or client-side synthetic/fake row.
- No duplication of the existing device/attendance live-query rules inside templates or TypeScript.
- No deletion or mutation of unrelated developer data during browser setup or cleanup.
- No wall-clock date lookup for payroll terms; resolve against the same business date already evaluated by the close blocker.
- No source edits in W3; a failed gate returns the work to W1 or W2 and requires a new atomic fix commit there.

## Verification strategy
> Zero human intervention - all verification is agent-executed.
- Test decision: TDD with pytest for route/rendering and payroll service behavior; TypeScript is checked with `bunx tsc --noEmit` and exercised in a real browser.
- QA policy: every task has agent-executed scenarios. W1 and W2 must capture a failing RED receipt before implementation and a passing GREEN receipt afterward.
- Evidence: `<attemptDir>/task-<N>-<slug>.<ext>` — under ulw-loop, `<attemptDir>` is the `currentAttemptDir` from `omo ulw-loop status --json` (`.omo/evidence/ulw/<session>/<goalId>/a<attempt>`); outside ulw-loop use `.omo/evidence/`.
- RED rule: failure must be an assertion showing missing requested behavior, not import/configuration failure. GREEN rule: the identical targeted command exits `0`.

## Execution strategy
### Parallel execution waves
> Target 5-8 tasks per wave. <3 per wave (except final) = under-splitting.
> The caller-mandated three-work-unit cap is the explicit exception: W1 and W2 are independent, atomic implementation units; W3 is the final gate.
> Extract shared dependencies as Wave-1 tasks to maximize parallelism.

Wave 1 (no dependencies):
- Task 1 / W1: server-rendered kiosk and manager live context with honest empty states
- Task 2 / W2: effective `EmploymentTerms` weekly-rest derivation with caller fallback

Wave 2 (after Wave 1):
- Task 3 / W3: browser/manual QA, diagnostics, full tests, cleanup, and review gate; depends [W1, W2]

Critical path: W1 + W2 -> W3

### Dependency matrix
| Task | Depends on | Blocks | Can parallelize with |
|------|------------|--------|----------------------|
| W1 / 1 | none | W3 / 3 | W2 / 2 |
| W2 / 2 | none | W3 / 3 | W1 / 1 |
| W3 / 3 | W1 / 1, W2 / 2 | final handoff | F1-F4 lanes within W3 only |

## Todos
> Implementation + Test = ONE task. Never separate.
> Every task MUST have: References + Acceptance Criteria + QA Scenarios + Commit.

- [ ] 1. W1 — Render `/kiosk/` and `/manager/console/` from live server context

  What to do: First add route tests named `test_kiosk_live_context`, `test_kiosk_empty_state`, `test_manager_console_live_context`, and `test_manager_console_empty_state`, preserving the existing manager-auth assertion. Capture RED. Refactor the existing device and attendance integration views so each contract and its HTML view consume one shared query/serialization helper in the same owning app. Replace `TemplateView` route wiring with named callable views; keep `login_required` on `/manager/console/`. Render stable context collections named `device_states` and `attendance_rows`; templates must iterate those collections and use `{% empty %}` to emit exactly `실시간 기기 상태가 없습니다.` and `표시할 실시간 근태 기록이 없습니다.`. Update the two TypeScript entry points to enhance only rows already rendered by the server and to preserve genuine state transitions without inserting a placeholder or synthetic row. Add a narrowly scoped test-support seeder/cleanup helper only if needed for W3; tag every object it creates with a unique `qa-live-state-<run-id>` marker and expose idempotent `seed(run_id)` and `cleanup(run_id)` operations.
  Must NOT do: Do not alter JSON payload field names/status semantics in the existing integration contracts, weaken manager authentication, fetch the same page data a second time on initial load, or manufacture display data when a collection is empty. Do not touch W2-owned payroll files.

  Parallelization: Can parallel: YES | Wave 1 | Blocks: [W3] | Blocked by: []

  References (executor has NO interview context - be exhaustive):
  - Pattern:  `config/urls.py:12-16` - replace only the two static `TemplateView` bindings while preserving route paths/names and `login_required` behavior.
  - Pattern:  `apps/devices/views.py:77-96` - canonical device integration contract; extract/reuse its live source rather than reimplementing it.
  - Pattern:  `apps/attendance/views.py:22-58` - canonical attendance integration contract; extract/reuse its live source for manager HTML context.
  - Pattern:  `templates/kiosk/states.html:15-80` - replace static state markup with the `device_states` loop and exact honest empty message.
  - Pattern:  `templates/manager/console.html:22-90` - replace static/synthetic rows with the `attendance_rows` loop and exact honest empty message.
  - Pattern:  `assets/ts/kiosk.ts` - retain real state behavior while removing any initial synthetic-row/data fallback.
  - Pattern:  `assets/ts/manager.ts` - retain row interaction behavior while making server-rendered rows the sole initial data source.
  - Test:     `tests/smoke/test_routes.py` - existing route-shell and authentication test conventions; extend in place.
  - Pattern:  `docs/SELF-REVIEW.md:27-52` - source statement for the two follow-ups; use as scope confirmation only, not as an additional documentation deliverable.

  Acceptance criteria (agent-executable only):
  - [ ] RED: after adding the four named tests but before implementation, run `$attemptDir = if ($env:OMO_ATTEMPT_DIR) {$env:OMO_ATTEMPT_DIR} else {'.omo/evidence'}; New-Item -ItemType Directory -Force $attemptDir | Out-Null; ./.venv/Scripts/python.exe -m pytest tests/smoke/test_routes.py -q -k 'kiosk_live_context or kiosk_empty_state or manager_console_live_context or manager_console_empty_state' *> "$attemptDir/task-1-live-context-red.txt"; if ($LASTEXITCODE -eq 0) { throw 'RED did not fail' }`; receipt contains an expected content/empty-state assertion failure.
  - [ ] GREEN: rerun the identical pytest selection after implementation, write to `<attemptDir>/task-1-live-context-green.txt`, and require exit code `0` with all four selected tests passing.
  - [ ] `./.venv/Scripts/python.exe -m pytest tests/smoke/test_routes.py -q` exits `0`; unauthenticated manager access still follows the existing login redirect and kiosk access keeps its existing auth posture.
  - [ ] `bunx tsc --noEmit` exits `0`, and `rg -n "synthetic|placeholder|fake|mock" assets/ts/kiosk.ts assets/ts/manager.ts` finds no executable row-construction fallback (comments/test labels alone are reviewed and removed if misleading).
  - [ ] Response assertions prove live fixture values appear in server HTML, empty fixtures show the exact empty messages, and neither empty response contains a data-row selector.

  QA scenarios (MANDATORY - task incomplete without these):
  ```
  Scenario: live fixture values are server-rendered and manager auth remains enforced
    Tool:     bash (PowerShell invocation)
    Steps:    Run `./.venv/Scripts/python.exe -m pytest tests/smoke/test_routes.py -q -k 'kiosk_live_context or manager_console_live_context'` and save stdout/stderr to `<attemptDir>/task-1-live-context.txt`.
    Expected: Exit code 0; both selected tests pass, assert unique seeded values in response HTML, and the manager test authenticates before asserting content.
    Evidence: <attemptDir>/task-1-live-context.txt

  Scenario: zero live records produces truthful empty markup and no synthetic row
    Tool:     bash (PowerShell invocation)
    Steps:    Run `./.venv/Scripts/python.exe -m pytest tests/smoke/test_routes.py -q -k 'kiosk_empty_state or manager_console_empty_state'` and save stdout/stderr to `<attemptDir>/task-1-live-context-error.txt`.
    Expected: Exit code 0; both selected tests pass, each exact Korean empty message is present, and the asserted data-row selector count is zero.
    Evidence: <attemptDir>/task-1-live-context-error.txt
  ```

  Commit: YES | Message: `feat(live-state): render kiosk and console from live context` | Files: [`config/urls.py`, `apps/devices/views.py`, `apps/attendance/views.py`, `templates/kiosk/states.html`, `templates/manager/console.html`, `assets/ts/kiosk.ts`, `assets/ts/manager.ts`, `tests/smoke/test_routes.py`, `tests/support/<narrow-live-state-helper-if-needed>`]

- [ ] 2. W2 — Resolve close blockers from effective `EmploymentTerms` with caller fallback

  What to do: First add tests named `test_close_uses_effective_terms_weekly_rest_weekday`, `test_close_effective_end_is_exclusive`, and `test_close_falls_back_to_caller_weekday_without_active_terms`; retain the existing caller-weekday test and capture RED. In the existing close-blocker seam, add one private resolver that receives the same employee and business date already being evaluated. Query `EmploymentTerms` using the inherited effective-range fields defined by the cited models: include `start <= business_date`, exclude `end <= business_date`, and deterministically select the most recent applicable start (with primary-key tie-break only if the model permits overlapping records). Return the effective term's non-null `weekly_rest_weekday`; otherwise return the caller-provided weekday. Feed the resolved value into the existing blocker decision and leave all other caller fields and blocker messages unchanged.
  Must NOT do: Do not change `EmploymentTerms`, migrations, insurance rates, close API signatures, unrelated payroll calculations, or the meaning of an existing caller weekday. Do not use `date.today()`/timezone-now, and do not let the caller override an applicable non-null effective term.

  Parallelization: Can parallel: YES | Wave 1 | Blocks: [W3] | Blocked by: []

  References (executor has NO interview context - be exhaustive):
  - Pattern:  `apps/payroll/services/close.py:59-110` - exact blocker seam and current caller-field behavior; localize the resolver and replacement here.
  - API/Type: `apps/payroll/models/policies.py:85-133` - `EmploymentTerms` and `weekly_rest_weekday` contract.
  - API/Type: `apps/core/models.py:57-87` - inherited effective-range field names and half-open `[start, end)` semantics.
  - Test:     `tests/payroll/test_close.py:100-125` - existing caller-weekday regression and payroll fixture/assertion style.
  - Pattern:  `docs/SELF-REVIEW.md:27-52` - source follow-up confirming this close-preview gap; no insurance-rate expansion is permitted.

  Acceptance criteria (agent-executable only):
  - [ ] RED: after adding the three named tests but before changing the service, run `$attemptDir = if ($env:OMO_ATTEMPT_DIR) {$env:OMO_ATTEMPT_DIR} else {'.omo/evidence'}; New-Item -ItemType Directory -Force $attemptDir | Out-Null; ./.venv/Scripts/python.exe -m pytest tests/payroll/test_close.py -q -k 'effective_terms_weekly_rest_weekday or effective_end_is_exclusive or falls_back_to_caller_weekday_without_active_terms' *> "$attemptDir/task-2-effective-terms-red.txt"; if ($LASTEXITCODE -eq 0) { throw 'RED did not fail' }`; receipt shows the service ignored an applicable term or mishandled the exclusive end, not fixture/import failure.
  - [ ] GREEN: rerun the identical selection after implementation, write to `<attemptDir>/task-2-effective-terms-green.txt`, and require exit code `0` with all three tests passing.
  - [ ] `./.venv/Scripts/python.exe -m pytest tests/payroll/test_close.py -q` exits `0`, including the pre-existing caller-weekday case at `tests/payroll/test_close.py:100-125`.
  - [ ] Tests prove all precedence/boundary rules: effective start included; effective end excluded; effective non-null term beats a conflicting caller value; no applicable/non-null term falls back to caller; the resolver uses the supplied business date.
  - [ ] `git diff -- apps/payroll` contains changes only in `apps/payroll/services/close.py` and `tests/payroll/test_close.py`, and `git diff --name-only | Select-String -Pattern 'insurance|rate'` returns no W2-owned match.

  QA scenarios (MANDATORY - task incomplete without these):
  ```
  Scenario: applicable employment term controls the weekly-rest blocker
    Tool:     bash (PowerShell invocation)
    Steps:    Run `./.venv/Scripts/python.exe -m pytest tests/payroll/test_close.py -q -k 'effective_terms_weekly_rest_weekday'` with fixtures containing a term weekday that conflicts with the caller weekday; save output to `<attemptDir>/task-2-effective-terms.txt`.
    Expected: Exit code 0; the blocker/result matches the effective term weekday and not the conflicting caller value.
    Evidence: <attemptDir>/task-2-effective-terms.txt

  Scenario: exclusive end and missing-term fallback are both safe
    Tool:     bash (PowerShell invocation)
    Steps:    Run `./.venv/Scripts/python.exe -m pytest tests/payroll/test_close.py -q -k 'effective_end_is_exclusive or falls_back_to_caller_weekday_without_active_terms'` and save output to `<attemptDir>/task-2-effective-terms-error.txt`.
    Expected: Exit code 0; a term whose end equals the business date is not selected, and the existing caller weekday determines the result when no applicable non-null term remains.
    Evidence: <attemptDir>/task-2-effective-terms-error.txt
  ```

  Commit: YES | Message: `fix(payroll): derive weekly rest weekday from effective terms` | Files: [`apps/payroll/services/close.py`, `tests/payroll/test_close.py`]

- [ ] 3. W3 — Execute browser QA, diagnostics, full tests, cleanup, and review gate

  What to do: After W1 and W2 commits are present, resolve `<attemptDir>`; run checks from a clean process state. Use W1's uniquely tagged helper to seed only task-owned live records and one temporary authenticated manager in an isolated QA database/process configuration, start Django at `127.0.0.1:8000` with `--noreload`, and drive both URLs with the browser. Capture live and empty-state screenshots/DOM evidence, including a narrow viewport. Run Django checks, migration drift check, TypeScript diagnostics, targeted suites, then the full pytest suite. Run F1-F4 in parallel; all must APPROVE, surface their receipts, and wait for explicit caller `okay`. Finally invoke idempotent cleanup for the run id, terminate only the recorded server PID, prove the port is released and no tagged objects remain, and write a cleanup receipt. If any check fails, do not edit in W3: route the defect to W1 or W2, create a new atomic commit in that owner, then rerun W3 in full.
  Must NOT do: Do not use the developer's normal database, leave a server/background process running, retain QA users/data, edit product files, amend/squash W1 or W2, skip full tests after targeted tests, or declare completion before explicit `okay` after F1-F4.

  Parallelization: Can parallel: NO | Wave 2 | Blocks: [final handoff] | Blocked by: [W1, W2]

  References (executor has NO interview context - be exhaustive):
  - Test:     `tests/smoke/test_routes.py` - live/empty route fixtures, exact response selectors, and manager authentication setup delivered by W1.
  - Test:     `tests/payroll/test_close.py` - effective-term, half-open boundary, and fallback regression suite delivered by W2.
  - Pattern:  `templates/kiosk/states.html:15-80` - browser selectors and kiosk live/empty observables.
  - Pattern:  `templates/manager/console.html:22-90` - browser selectors and manager live/empty observables.
  - Pattern:  `assets/ts/kiosk.ts` - browser-visible state enhancement behavior to exercise without synthetic data.
  - Pattern:  `assets/ts/manager.ts` - browser-visible row behavior to exercise against server rows.
  - Pattern:  `config/urls.py:12-16` - exact `/kiosk/` and `/manager/console/` route/auth shell.
  - API/Type: `apps/payroll/services/close.py:59-110` - final scope audit seam.

  Acceptance criteria (agent-executable only):
  - [ ] `./.venv/Scripts/python.exe manage.py check`, `./.venv/Scripts/python.exe manage.py makemigrations --check --dry-run`, and `bunx tsc --noEmit` each exit `0`; combined logs are saved as `<attemptDir>/task-3-diagnostics.txt`.
  - [ ] `./.venv/Scripts/python.exe -m pytest tests/smoke/test_routes.py tests/payroll/test_close.py -q` exits `0`, followed by `./.venv/Scripts/python.exe -m pytest -q` exiting `0`; logs prove test collection is non-zero and contain no interrupted/skipped-by-command run.
  - [ ] Browser evidence proves live unique values are present in both pages, manager authentication is required, the empty state contains each exact message with zero data rows, and 390x844 rendering has no horizontal overflow or clipped primary controls.
  - [ ] Cleanup receipt records run id, isolated database path/config, seeded object identifiers, cleanup counts, server PID termination, `Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue` returning no task-owned listener, and a zero-object post-cleanup query.
  - [ ] F1-F4 each produce `APPROVE`; any rejection blocks completion and returns work to its owning unit.

  QA scenarios (MANDATORY - task incomplete without these):
  ```
  Scenario: real browser shows server-rendered live kiosk and authenticated manager data
    Tool:     browser:control-in-app-browser
    Steps:    Set `<run-id>` to a new UUID; invoke W1's `seed(<run-id>)` helper in the isolated QA configuration; start `./.venv/Scripts/python.exe manage.py runserver 127.0.0.1:8000 --noreload` with `Start-Process -WindowStyle Hidden -PassThru` and record its PID. Open `http://127.0.0.1:8000/kiosk/`, wait for network idle, assert the unique `qa-live-state-<run-id>` text and at least one server data-row selector, interact once with the existing kiosk state control, and capture `<attemptDir>/task-3-kiosk-live.png`. Open `http://127.0.0.1:8000/manager/console/`, assert redirect/login before authentication, authenticate with the temporary manager emitted by the seeder, revisit the URL, assert the same unique marker and a server attendance-row selector, then capture `<attemptDir>/task-3-manager-live.png`. Resize to 390x844 and capture `<attemptDir>/task-3-mobile.png` after asserting `document.documentElement.scrollWidth <= document.documentElement.clientWidth`.
    Expected: Both pages display the seeded live values from initial HTML; manager data is inaccessible before login; the existing interactions operate on server rows; no synthetic/placeholder row appears; mobile viewport has no horizontal overflow.
    Evidence: <attemptDir>/task-3-kiosk-live.png

  Scenario: real browser shows honest empty states and cleanup leaves no residue
    Tool:     browser:control-in-app-browser + bash (PowerShell invocation)
    Steps:    Invoke W1's idempotent `cleanup(<run-id>)`; reload both URLs (reauthenticating only if the session was removed), assert exact text `실시간 기기 상태가 없습니다.` and `표시할 실시간 근태 기록이 없습니다.`, assert zero data-row selectors after scripts settle, and capture `<attemptDir>/task-3-empty-states.png`. Stop only the PID recorded above. Invoke `cleanup(<run-id>)` again, query for the unique marker, run `Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue`, and save run id, deletion counts, zero remaining objects, and listener result to `<attemptDir>/task-3-cleanup.txt`.
    Expected: Both exact empty messages remain after client initialization; no row is synthesized; second cleanup succeeds idempotently; tagged object count is zero; the recorded server is stopped and no task-owned port-8000 listener remains.
    Evidence: <attemptDir>/task-3-cleanup.txt
  ```

  Commit: NO | Message: `N/A — verification/evidence only; failures return to W1 or W2 for a new owner-scoped commit` | Files: [`<attemptDir>/task-3-*`]

## Final verification wave (MANDATORY - after all implementation tasks)
> Runs in PARALLEL. ALL must APPROVE. Surface results to the caller and wait for an explicit "okay" before declaring complete.
> F1-F4 are parallel approval lanes inside W3, not additional implementation work units.
- [ ] F1. Plan compliance audit - verify exactly W1-W3 completed, each acceptance criterion has a command/result receipt, ownership boundaries held, and no requested behavior is self-reported without evidence.
- [ ] F2. Code quality review - verify diagnostics are clean, shared live-query helpers avoid duplicated business rules, effective-term resolution is local and typed/idiomatic, and no dead/synthetic path remains.
- [ ] F3. Real manual QA - independently repeat every W3 browser scenario with evidence, including auth redirect, live values, empty states, client interaction, and 390x844 overflow assertion.
- [ ] F4. Scope fidelity - inspect the final diff and approve only if no insurance-rate, schema/migration, unrelated API, or extra feature change shipped and W1/W2 file ownership remains atomic.

## Commit strategy
- Commit W1 and its direct tests together: `feat(live-state): render kiosk and console from live context`.
- Commit W2 and its direct tests together: `fix(payroll): derive weekly rest weekday from effective terms`.
- W1 and W2 may be developed in parallel but must not stage each other's files; before each commit inspect `git diff --staged --stat` and the full staged diff, then verify `git log -1 --oneline`.
- W3 creates evidence only and makes no commit. Any correction becomes a new, owner-scoped W1 or W2 commit; do not amend an already reviewed commit.
- One logical change per commit. Conventional Commits (`<type>(<scope>): <subject>` body + footer).
- Atomic: every commit builds and passes its targeted tests on its own.
- No "WIP" / "fix typo squash later" commits on the final branch - clean up before merge.
- Reference the plan file path in the final implementation commit footer: `Plan: .omo/plans/live-state-close-preview.md`.

## Success criteria
- All Must-Have shipped; all QA scenarios pass with captured evidence; F1-F4 approved; commit history clean.
- Exactly two implementation commits cover W1 and W2; W3 has a complete test/browser/review/cleanup evidence set and no source diff.
- The executor has surfaced F1-F4 results and received explicit caller `okay` before declaring execution complete.
