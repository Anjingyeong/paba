# Runbook — Insurance rate update

Rates are versioned files in `apps/payroll/data/insurance_rates/<version>.json`;
they are never fetched at runtime.

1. Obtain the new official rates from the source URLs recorded in the current file
   (NPS / NHIS / MOEL). **Verify each figure against the primary source.**
2. Create a new `<version>.json` (e.g. `2027.1.json`) with rates, `source_url`,
   `published_on`, `effective_from`, per-insurance rounding, and set
   `verification_status` to `VERIFIED` with your name/date.
3. Add golden tests in `tests/payroll/test_insurance_estimates.py` for the new
   version (component-exact expected values).
4. Point new estimates at the new version from its `effective_from`. Do **not**
   edit prior versions — closed snapshots must remain reproducible.
5. Run `scripts/verify.sh`; open a PR; a second reviewer re-checks the figures.
6. Managers still reconcile against the institution notice (RECONCILED) — the file
   is an estimate aid, not the authority.
