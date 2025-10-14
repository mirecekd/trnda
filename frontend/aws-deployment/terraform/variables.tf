variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "eu-central-1"
}

variable "aws_profile" {
  description = "AWS CLI profile (set in terraform.tfvars)"
  type        = string
  # No default - must be set in terraform.tfvars
}

variable "frontend_bucket_name" {
  description = "S3 bucket for frontend (set in terraform.tfvars)"
  type        = string
  # No default - must be set in terraform.tfvars
}

variable "diagrams_bucket_name" {
  description = "S3 bucket for diagrams (set in terraform.tfvars)"
  type        = string
  # No default - must be set in terraform.tfvars
}

variable "upload_password" {
  description = "Password for upload authentication (set in terraform.tfvars)"
  type        = string
  sensitive   = true
  # No default - must be set in terraform.tfvars
}

variable "custom_domain" {
  description = "Custom domain for CloudFront (optional, e.g., trnda.ai.aws.thetrasklab.com)"
  type        = string
  default     = ""
}

variable "acm_certificate_arn" {
  description = "ACM certificate ARN for custom domain (required if custom_domain is set)"
  type        = string
  default     = ""
}
