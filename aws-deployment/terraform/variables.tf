variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "eu-central-1"
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "trnda"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "prod"
}

variable "bucket_name" {
  description = "S3 bucket name for diagrams (must be globally unique)"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID for ECS tasks"
  type        = string
}

variable "subnet_ids" {
  description = "List of subnet IDs for ECS tasks (private subnets with NAT recommended)"
  type        = list(string)
}

variable "task_cpu" {
  description = "CPU units for ECS task (256, 512, 1024, 2048, 4096)"
  type        = string
  default     = "2048"  # 2 vCPU
}

variable "task_memory" {
  description = "Memory for ECS task in MB"
  type        = string
  default     = "4096"  # 4 GB
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 7
}

variable "ses_sender_email" {
  description = "SES sender email address for TRNDA notifications"
  type        = string
  default     = "trnda@ai.aws.thetrasklab.com"
}
