# Runbook — Legal hold & data destruction

## Place a legal hold
1. Create a `LegalHold` for the subject (`subject_type="Employee"`, `subject_id`=
   employee code) with a reason. While active, retention purges skip that subject.
2. Confirm the hold via the audit log.

## Release a hold
- Set `released_at`; record why. The subject becomes eligible for purge again once
  past its retention window.

## Destruction (past retention)
1. Dry run: `manage.py purge_expired` — lists candidates, writes nothing.
2. Review the candidate list; confirm no active legal holds apply.
3. Execute: `manage.py purge_expired --confirm` — destroys expired personal data
   and writes a `PURGE` completion entry to the append-only audit log.
4. Backups: expired data ages out of PITR (35 days) and S3 lifecycle; the retention
   window already includes this backup grace before a subject becomes a candidate.
5. Never delete audit entries or closed snapshots — they are append-only by design.
