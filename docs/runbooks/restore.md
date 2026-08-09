# Runbook — Restore & quarterly rehearsal

Targets: **RPO ≤ 5 min** (PITR), **RTO ≤ 4 h**.

## Point-in-time restore (rehearsal or real)
1. Choose the restore timestamp (within the 35-day PITR window).
2. Restore to a **new** instance id (never overwrite prod):
   `aws rds restore-db-instance-to-point-in-time --source-db-instance-identifier <prod>
    --target-db-instance-identifier <prod>-restore --restore-time <ISO8601>`
3. Point a throwaway app task at the restored endpoint; run
   `manage.py migrate --check` and a synthetic-snapshot checksum verification.
4. Record measured RPO/RTO to `docs/runbooks/restore-metrics.json`.
5. **Manual approval gate** before any cutover or deletion of the restored instance.
6. Tear down the rehearsal instance after sign-off.

## Quarterly automation
CI/scheduled job runs steps 1–4 against an isolated instance and fails if the
checksum mismatches or RTO/RPO exceed targets. It stops at the manual approval gate
(step 5) and never touches production.
