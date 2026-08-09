# Runbook — Deploy

## Preconditions
- CI green on the commit (verify + lighthouse + container jobs).
- `container_image` points at the new immutable ECR tag; `domain_name` set.
- Remote state backend configured; you have reviewed `terraform plan` with a peer.

## Steps
1. Build & push the image (CI or `docker build`/`docker push` to ECR).
2. `terraform -chdir=infra/terraform plan -out tf.plan` — review resource diffs.
3. Apply **only after explicit approval**: `terraform -chdir=infra/terraform apply tf.plan`.
4. Migrations run automatically on task start (`manage.py migrate`); confirm the ECS
   service reaches steady state and `/health/ready` returns 200 via the ALB.
5. Verify the EventBridge schedule `*-prepare-periods` is ENABLED.

## Rollback
- Update `container_image` to the previous tag and re-apply, or roll the ECS
  service back to the prior task-definition revision. DB migrations are additive;
  if a migration must be reversed, use the reverse migration and restore from PITR
  only as a last resort (see `restore.md`).
