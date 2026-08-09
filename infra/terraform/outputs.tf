output "alb_dns_name" {
  description = "Point the domain's DNS at this ALB."
  value       = aws_lb.main.dns_name
}

output "db_endpoint" {
  description = "Private RDS endpoint (reachable only from the app tier)."
  value       = aws_db_instance.main.address
}

output "exports_bucket" {
  value = aws_s3_bucket.exports.bucket
}

output "acm_certificate_arn" {
  value = aws_acm_certificate.main.arn
}
