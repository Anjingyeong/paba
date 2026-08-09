# Security groups: the ALB is the only internet-facing surface; the app accepts
# traffic only from the ALB; the database accepts traffic only from the app. Egress
# is restricted to what each tier needs.

resource "aws_security_group" "alb" {
  name        = "${var.project}-alb"
  description = "Public HTTPS to the load balancer"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "HTTPS from the internet"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description     = "To the app tier only"
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.app.id]
  }
}

resource "aws_security_group" "app" {
  name        = "${var.project}-app"
  description = "Fargate tasks"
  vpc_id      = aws_vpc.main.id

  egress {
    description = "HTTPS out (Secrets Manager, ECR, S3, CloudWatch)"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group_rule" "app_from_alb" {
  type                     = "ingress"
  description              = "App accepts traffic only from the ALB"
  from_port                = 8000
  to_port                  = 8000
  protocol                 = "tcp"
  security_group_id        = aws_security_group.app.id
  source_security_group_id = aws_security_group.alb.id
}

resource "aws_security_group_rule" "app_to_db" {
  type                     = "egress"
  description              = "App reaches PostgreSQL"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  security_group_id        = aws_security_group.app.id
  source_security_group_id = aws_security_group.db.id
}

resource "aws_security_group" "db" {
  name        = "${var.project}-db"
  description = "PostgreSQL, private only"
  vpc_id      = aws_vpc.main.id
}

resource "aws_security_group_rule" "db_from_app" {
  type                     = "ingress"
  description              = "DB accepts traffic only from the app tier"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  security_group_id        = aws_security_group.db.id
  source_security_group_id = aws_security_group.app.id
}
