# SPDX-License-Identifier: PROPRIETARY
# Terraform variables for Behavior Convergence Explorer

variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod"
  }
}

variable "app_name" {
  description = "Application name"
  type        = string
  default     = "hbc"
}

variable "domain_name" {
  description = "Domain name for application"
  type        = string
  default     = ""
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "db_password" {
  description = "Database password (should use secrets manager)"
  type        = string
  sensitive   = true
  default     = ""
}
