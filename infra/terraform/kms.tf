# Customer-managed KMS keys with rotation for data at rest (RDS, S3, backups, logs).

resource "aws_kms_key" "data" {
  description             = "${var.project} data-at-rest encryption"
  enable_key_rotation     = true
  deletion_window_in_days = 30
}

resource "aws_kms_alias" "data" {
  name          = "alias/${var.project}-data"
  target_key_id = aws_kms_key.data.key_id
}
