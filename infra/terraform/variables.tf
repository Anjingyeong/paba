variable "region" {
  description = "AWS region. Seoul by default."
  type        = string
  default     = "ap-northeast-2"
}

variable "project" {
  type    = string
  default = "paris-baguette-payroll"
}

variable "environment" {
  type    = string
  default = "production"
}

variable "vpc_cidr" {
  type    = string
  default = "10.40.0.0/16"
}

variable "az_count" {
  description = "Number of AZs for Multi-AZ subnets."
  type        = number
  default     = 2
}

variable "domain_name" {
  description = "Public DNS name served over HTTPS (ACM certificate SAN)."
  type        = string
  default     = "payroll.example.com"
}

variable "container_image" {
  description = "ECR image URI for the app container."
  type        = string
  default     = "REPLACE_WITH_ECR_IMAGE_URI"
}

variable "db_instance_class" {
  type    = string
  default = "db.t4g.small"
}

variable "backup_retention_days" {
  type    = number
  default = 35
}

variable "log_retention_days" {
  type    = number
  default = 365
}
