# infra/terraform — AWS Seoul (ap-northeast-2)

Managed deployment for the payroll app: ECS/Fargate behind an ALB (ACM TLS), a
private Multi-AZ PostgreSQL 18 with 35-day PITR, a private KMS-encrypted S3 exports
bucket, Secrets Manager, CloudWatch logs/alarms, and an EventBridge daily
`prepare_payroll_periods` task.

## Validate (no cloud calls)

```bash
terraform -chdir=infra/terraform fmt -check
terraform -chdir=infra/terraform init -backend=false
terraform -chdir=infra/terraform validate
tflint --chdir=infra/terraform
checkov -d infra/terraform
```

## Applying — requires explicit approval

Do **not** run `terraform apply` or change DNS until the user provides their AWS
account, domain, and ECR image, and explicitly approves the run. Set
`container_image`, `domain_name`, and a real remote state backend first, then
review `terraform plan` together. See `docs/runbooks/`.

## Controls

- Private subnets for app + DB; ALB is the only public surface (443 only).
- RDS: `storage_encrypted`, Multi-AZ, `publicly_accessible=false`, PITR 35 days,
  deletion protection, final snapshot. Target RPO ≤ 5 min, RTO ≤ 4 h.
- S3: public access blocked, versioning, KMS SSE, lifecycle expiry, insecure
  transport denied. Exports are reached only via 5-minute presigned URLs with
  employee-id filenames.
- Least-privilege task role (scoped S3 + two secrets + data KMS key only).
- KMS key rotation; CloudWatch alarms to an encrypted SNS topic.
