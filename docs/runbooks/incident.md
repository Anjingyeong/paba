# Runbook — Incident response

## Triage
1. Acknowledge the CloudWatch alarm (SNS). Identify scope: availability, data, or
   security.
2. Check `/health/ready`, ECS service events, RDS status, ALB 5xx metric.

## Containment
- **Availability**: scale the ECS service; check RDS failover (Multi-AZ) completed.
- **Security (suspected credential/exposure)**: rotate the affected Secrets Manager
  secret, cycle the Django `SECRET_KEY` (invalidates sessions), revoke suspect kiosk
  devices, and, if needed, restrict the ALB security group.
- **Data integrity**: audit log and snapshots are append-only — never edit them.
  Investigate via the audit trail; correct forward with a new correction/reclose.

## Recovery & review
- Restore from PITR only if data loss is confirmed (see `restore.md`).
- Write a blameless postmortem; capture the audit `request_id` timeline.
