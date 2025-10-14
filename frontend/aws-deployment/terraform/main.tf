terraform {
  required_version = ">= 1.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.0"
    }
  }
}

provider "aws" {
  region  = var.aws_region
  profile = var.aws_profile
}

# AWS provider for us-east-1 (required for CloudFront ACM certificates)
provider "aws" {
  alias   = "us_east_1"
  region  = "us-east-1"
  profile = var.aws_profile
}

# S3 bucket for frontend hosting
resource "aws_s3_bucket" "frontend" {
  bucket = var.frontend_bucket_name
  
  tags = {
    Name    = "TRNDA Frontend"
    Project = "TRNDA"
  }
}

# S3 bucket website configuration
resource "aws_s3_bucket_website_configuration" "frontend" {
  bucket = aws_s3_bucket.frontend.id
  
  index_document {
    suffix = "index.html"
  }
}

# S3 bucket public access
resource "aws_s3_bucket_public_access_block" "frontend" {
  bucket = aws_s3_bucket.frontend.id
  
  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

# S3 bucket policy
resource "aws_s3_bucket_policy" "frontend" {
  bucket = aws_s3_bucket.frontend.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "PublicRead"
      Effect    = "Allow"
      Principal = "*"
      Action    = "s3:GetObject"
      Resource  = "${aws_s3_bucket.frontend.arn}/*"
    }]
  })
  
  depends_on = [aws_s3_bucket_public_access_block.frontend]
}

# IAM role for Lambda
resource "aws_iam_role" "lambda" {
  name = "trnda-upload-lambda-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
      Action = "sts:AssumeRole"
    }]
  })
}

# IAM policy for Lambda
resource "aws_iam_role_policy" "lambda" {
  name = "trnda-upload-lambda-policy"
  role = aws_iam_role.lambda.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:PutObjectAcl"
        ]
        Resource = "arn:aws:s3:::${var.diagrams_bucket_name}/input/*"
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      }
    ]
  })
}

# Package Lambda
data "archive_file" "lambda" {
  type        = "zip"
  source_file = "../../lambda/upload.py"
  output_path = "${path.module}/lambda.zip"
}

# Lambda function
resource "aws_lambda_function" "upload" {
  filename         = data.archive_file.lambda.output_path
  function_name    = "trnda-upload"
  role            = aws_iam_role.lambda.arn
  handler         = "upload.lambda_handler"
  source_code_hash = data.archive_file.lambda.output_base64sha256
  runtime         = "python3.11"
  timeout         = 30
  memory_size     = 256
  
  environment {
    variables = {
      UPLOAD_PASSWORD = var.upload_password
      BUCKET_NAME     = var.diagrams_bucket_name
    }
  }
}

# API Gateway
resource "aws_apigatewayv2_api" "main" {
  name          = "trnda-upload-api"
  protocol_type = "HTTP"
  
  cors_configuration {
    allow_origins = ["*"]
    allow_methods = ["POST", "OPTIONS"]
    allow_headers = ["content-type"]
  }
}

# API Gateway integration
resource "aws_apigatewayv2_integration" "lambda" {
  api_id             = aws_apigatewayv2_api.main.id
  integration_type   = "AWS_PROXY"
  integration_uri    = aws_lambda_function.upload.invoke_arn
  integration_method = "POST"
  payload_format_version = "2.0"
}

# API Gateway routes
resource "aws_apigatewayv2_route" "auth" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "POST /auth"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_route" "upload" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "POST /upload"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

# API Gateway stage
resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.main.id
  name        = "$default"
  auto_deploy = true
}

# Lambda permission for API Gateway
resource "aws_lambda_permission" "api" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.upload.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
}

# Generate configured app.js
resource "local_file" "app_js" {
  content = templatefile("${path.module}/templates/app.js.tpl", {
    api_url = aws_apigatewayv2_api.main.api_endpoint
  })
  filename = "${path.module}/../../app-configured.js"
}

# Get Route 53 hosted zone for custom domain
data "aws_route53_zone" "main" {
  count        = var.custom_domain != "" ? 1 : 0
  name         = join(".", slice(split(".", var.custom_domain), 1, length(split(".", var.custom_domain))))
  private_zone = false
}

# ACM Certificate for custom domain (must be in us-east-1 for CloudFront)
resource "aws_acm_certificate" "frontend" {
  count             = var.custom_domain != "" ? 1 : 0
  provider          = aws.us_east_1
  domain_name       = var.custom_domain
  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true
  }

  tags = {
    Name    = "TRNDA Frontend Certificate"
    Project = "TRNDA"
  }
}

# Route 53 records for ACM validation
resource "aws_route53_record" "cert_validation" {
  for_each = var.custom_domain != "" ? {
    for dvo in aws_acm_certificate.frontend[0].domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      type   = dvo.resource_record_type
      record = dvo.resource_record_value
    }
  } : {}

  zone_id = data.aws_route53_zone.main[0].zone_id
  name    = each.value.name
  type    = each.value.type
  records = [each.value.record]
  ttl     = 60
}

# ACM Certificate Validation
resource "aws_acm_certificate_validation" "frontend" {
  count                   = var.custom_domain != "" ? 1 : 0
  provider                = aws.us_east_1
  certificate_arn         = aws_acm_certificate.frontend[0].arn
  validation_record_fqdns = [for record in aws_route53_record.cert_validation : record.fqdn]
}

# CloudFront Origin Access Identity
resource "aws_cloudfront_origin_access_identity" "main" {
  comment = "TRNDA Frontend OAI"
}

# CloudFront Distribution
resource "aws_cloudfront_distribution" "main" {
  enabled             = true
  is_ipv6_enabled     = true
  comment             = "TRNDA Frontend"
  default_root_object = "index.html"
  price_class         = "PriceClass_100"
  aliases             = var.custom_domain != "" ? [var.custom_domain] : []

  origin {
    domain_name = aws_s3_bucket.frontend.bucket_regional_domain_name
    origin_id   = "S3-${aws_s3_bucket.frontend.id}"

    s3_origin_config {
      origin_access_identity = aws_cloudfront_origin_access_identity.main.cloudfront_access_identity_path
    }
  }

  default_cache_behavior {
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "S3-${aws_s3_bucket.frontend.id}"
    viewer_protocol_policy = "redirect-to-https"

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    min_ttl     = 0
    default_ttl = 0
    max_ttl     = 0
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = var.custom_domain == "" ? true : false
    acm_certificate_arn           = var.custom_domain != "" ? (var.acm_certificate_arn != "" ? var.acm_certificate_arn : aws_acm_certificate.frontend[0].arn) : null
    ssl_support_method            = var.custom_domain != "" ? "sni-only" : null
    minimum_protocol_version      = var.custom_domain != "" ? "TLSv1.2_2021" : null
  }

  tags = {
    Name    = "TRNDA Frontend"
    Project = "TRNDA"
  }
}

# Update S3 bucket policy for CloudFront
resource "aws_s3_bucket_policy" "frontend_cloudfront" {
  bucket = aws_s3_bucket.frontend.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "CloudFrontRead"
        Effect    = "Allow"
        Principal = {
          AWS = aws_cloudfront_origin_access_identity.main.iam_arn
        }
        Action   = "s3:GetObject"
        Resource = "${aws_s3_bucket.frontend.arn}/*"
      }
    ]
  })

  depends_on = [aws_s3_bucket_public_access_block.frontend]
}

# Route 53 CNAME record pointing to CloudFront
resource "aws_route53_record" "frontend" {
  count   = var.custom_domain != "" ? 1 : 0
  zone_id = data.aws_route53_zone.main[0].zone_id
  name    = var.custom_domain
  type    = "CNAME"
  ttl     = 300
  records = [aws_cloudfront_distribution.main.domain_name]

  depends_on = [aws_acm_certificate_validation.frontend]
}

# Upload files to S3
resource "aws_s3_object" "index" {
  bucket       = aws_s3_bucket.frontend.id
  key          = "index.html"
  source       = "../../index.html"
  content_type = "text/html"
  etag         = filemd5("../../index.html")
  depends_on   = [aws_s3_bucket_policy.frontend_cloudfront]
}

resource "aws_s3_object" "styles" {
  bucket       = aws_s3_bucket.frontend.id
  key          = "styles.css"
  source       = "../../styles.css"
  content_type = "text/css"
  etag         = filemd5("../../styles.css")
  depends_on   = [aws_s3_bucket_policy.frontend_cloudfront]
}

resource "aws_s3_object" "app" {
  bucket       = aws_s3_bucket.frontend.id
  key          = "app.js"
  content      = local_file.app_js.content
  content_type = "application/javascript"
  etag         = md5(local_file.app_js.content)
  depends_on   = [aws_s3_bucket_policy.frontend_cloudfront]
}
