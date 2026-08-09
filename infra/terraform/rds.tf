# Private, Multi-AZ, encrypted PostgreSQL 18 with 35-day PITR. Not publicly
# accessible; deletion protected; final snapshot on destroy.

resource "aws_db_subnet_group" "main" {
  name       = "${var.project}-db"
  subnet_ids = aws_subnet.private[*].id
}

resource "random_password" "db" {
  length  = 32
  special = false
}

resource "aws_secretsmanager_secret_version" "db" {
  secret_id     = aws_secretsmanager_secret.db.id
  secret_string = jsonencode({ username = "pbadmin", password = random_password.db.result })
}

resource "aws_db_instance" "main" {
  identifier     = "${var.project}-db"
  engine         = "postgres"
  engine_version = "18"
  instance_class = var.db_instance_class

  allocated_storage     = 20
  max_allocated_storage = 100
  storage_type          = "gp3"
  storage_encrypted     = true
  kms_key_id            = aws_kms_key.data.arn

  db_name  = "paris_baguette"
  username = "pbadmin"
  password = random_password.db.result

  multi_az               = true
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.db.id]
  publicly_accessible    = false

  backup_retention_period   = var.backup_retention_days
  backup_window             = "17:00-17:30"
  maintenance_window        = "Mon:18:00-Mon:18:30"
  deletion_protection       = true
  copy_tags_to_snapshot     = true
  final_snapshot_identifier = "${var.project}-db-final"

  performance_insights_enabled          = true
  performance_insights_kms_key_id       = aws_kms_key.data.arn
  enabled_cloudwatch_logs_exports       = ["postgresql"]
  auto_minor_version_upgrade            = true
  iam_database_authentication_enabled   = true
}
