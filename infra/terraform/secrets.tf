# Application secrets live in Secrets Manager, encrypted with the data KMS key.
# Values are set out-of-band (never in Terraform state as plaintext).

resource "aws_secretsmanager_secret" "app" {
  name       = "${var.project}/app"
  kms_key_id = aws_kms_key.data.arn
}

resource "aws_secretsmanager_secret" "db" {
  name       = "${var.project}/db"
  kms_key_id = aws_kms_key.data.arn
}
