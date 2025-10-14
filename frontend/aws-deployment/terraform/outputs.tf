output "website_url" {
  description = "Frontend website URL (HTTPS via CloudFront)"
  value       = "https://${aws_cloudfront_distribution.main.domain_name}"
}

output "s3_website_url" {
  description = "S3 website URL (fallback)"
  value       = "http://${aws_s3_bucket.frontend.bucket}.s3-website.${var.aws_region}.amazonaws.com"
}

output "api_url" {
  description = "API Gateway URL"
  value       = aws_apigatewayv2_api.main.api_endpoint
}

output "cloudfront_domain" {
  description = "CloudFront domain name"
  value       = aws_cloudfront_distribution.main.domain_name
}

output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID"
  value       = aws_cloudfront_distribution.main.id
}

output "acm_certificate_arn" {
  description = "ACM certificate ARN (if custom domain is used)"
  value       = var.custom_domain != "" && var.acm_certificate_arn == "" ? aws_acm_certificate.frontend[0].arn : null
}

output "acm_validation_records" {
  description = "DNS validation records for ACM certificate (add these to your DNS)"
  value = var.custom_domain != "" && var.acm_certificate_arn == "" ? {
    for dvo in aws_acm_certificate.frontend[0].domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      type   = dvo.resource_record_type
      value  = dvo.resource_record_value
    }
  } : null
}

output "password" {
  description = "Upload password (from terraform.tfvars)"
  value       = var.upload_password
  sensitive   = true
}
