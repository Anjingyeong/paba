# Runbook — Quarterly access review

Cadence: once per quarter.

1. **AWS IAM**: review the execution and task roles; confirm they still grant only
   scoped S3 (exports bucket), the two secrets, and the data KMS key. Remove any
   drift. Review who can assume deploy/admin roles.
2. **Secrets**: confirm rotation of `app`/`db` secrets; rotate if overdue.
3. **Application managers**: list Django manager accounts; disable departed staff;
   confirm every manager has a confirmed TOTP.
4. **Kiosk devices**: list paired devices; revoke any that are lost/retired.
5. **Audit sampling**: pull a sample of privileged actions from the audit log and
   confirm each has a legitimate actor + reason.
6. Record findings and actions; file the review with a date and reviewer.
