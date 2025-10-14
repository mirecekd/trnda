variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "eu-central-1"
}

variable "aws_profile" {
  description = "AWS CLI profile to use"
  type        = string
  default     = "default"
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

variable "s3_bucket_name" {
  description = "S3 bucket name for TRNDA diagrams (existing bucket)"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID for EC2 instance"
  type        = string
}

variable "subnet_id" {
  description = "Subnet ID for EC2 instance (public subnet recommended for easier access)"
  type        = string
}

variable "instance_type" {
  description = "EC2 instance type (ARM-based)"
  type        = string
  default     = "t4g.medium"
}

variable "ssh_key_name" {
  description = "SSH key pair name for EC2 access"
  type        = string
  default     = "ai-tool-box"
}

variable "ses_sender_email" {
  description = "SES sender email address for TRNDA notifications"
  type        = string
  default     = "trnda@ai.aws.thetrasklab.com"
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 7
}
