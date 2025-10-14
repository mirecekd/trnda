terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region  = var.aws_region
  profile = var.aws_profile
}

# Data: Get Ubuntu 24.04 LTS ARM64 AMI
data "aws_ami" "ubuntu_arm64" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-arm64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# S3 Bucket (import existing bucket)
resource "aws_s3_bucket" "trnda" {
  bucket = var.s3_bucket_name

  tags = {
    Name        = "TRNDA Architecture Diagrams"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }

  lifecycle {
    prevent_destroy = true
  }
}

# Enable EventBridge notifications on S3
resource "aws_s3_bucket_notification" "trnda_notification" {
  bucket      = aws_s3_bucket.trnda.id
  eventbridge = true
}

# IAM Role for EC2 Instance
resource "aws_iam_role" "ec2_trnda_role" {
  name = "${var.project_name}-ec2-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name        = "${var.project_name} EC2 Role"
    Environment = var.environment
  }
}

# IAM Policy for S3 Access
resource "aws_iam_role_policy" "s3_access" {
  name = "${var.project_name}-s3-policy"
  role = aws_iam_role.ec2_trnda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:GetObjectMetadata",
          "s3:HeadObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.trnda.arn,
          "${aws_s3_bucket.trnda.arn}/*"
        ]
      }
    ]
  })
}

# IAM Policy for Bedrock Access
resource "aws_iam_role_policy" "bedrock_access" {
  name = "${var.project_name}-bedrock-policy"
  role = aws_iam_role.ec2_trnda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream"
        ]
        Resource = [
          "arn:aws:bedrock:*::foundation-model/*anthropic.claude-sonnet-4-5-*",
          "arn:aws:bedrock:*:*:inference-profile/*anthropic.claude-sonnet-4-5-*",
          "arn:aws:bedrock:*:*:inference-profile/global.anthropic.claude-sonnet-4-5-*"
        ]
      }
    ]
  })
}

# IAM Policy for SES Access
resource "aws_iam_role_policy" "ses_access" {
  name = "${var.project_name}-ses-policy"
  role = aws_iam_role.ec2_trnda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ses:SendEmail",
          "ses:SendRawEmail"
        ]
        Resource = "*"
        Condition = {
          StringEquals = {
            "ses:FromAddress" = var.ses_sender_email
          }
        }
      }
    ]
  })
}

# IAM Policy for Pricing API Access
resource "aws_iam_role_policy" "pricing_access" {
  name = "${var.project_name}-pricing-policy"
  role = aws_iam_role.ec2_trnda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "pricing:GetProducts",
          "pricing:DescribeServices",
          "pricing:GetAttributeValues"
        ]
        Resource = "*"
      }
    ]
  })
}

# Attach SSM Managed Instance Policy
resource "aws_iam_role_policy_attachment" "ssm_managed" {
  role       = aws_iam_role.ec2_trnda_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

# Attach CloudWatch Agent Policy
resource "aws_iam_role_policy_attachment" "cloudwatch_agent" {
  role       = aws_iam_role.ec2_trnda_role.name
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy"
}

# IAM Instance Profile
resource "aws_iam_instance_profile" "ec2_trnda_profile" {
  name = "${var.project_name}-ec2-profile"
  role = aws_iam_role.ec2_trnda_role.name

  tags = {
    Name        = "${var.project_name} EC2 Profile"
    Environment = var.environment
  }
}

# Security Group for EC2
resource "aws_security_group" "ec2_trnda" {
  name        = "${var.project_name}-ec2-sg"
  description = "Security group for TRNDA EC2 instance"
  vpc_id      = var.vpc_id

  # Inbound: SSH from specific IP
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["91.232.85.63/32"]
    description = "SSH access from allowed IP"
  }

  # Outbound: Allow all (for git clone, pip install, AWS API calls)
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound traffic"
  }

  tags = {
    Name        = "${var.project_name} EC2 SG"
    Environment = var.environment
  }
}

# EC2 Instance
resource "aws_instance" "trnda" {
  ami                    = data.aws_ami.ubuntu_arm64.id
  instance_type          = var.instance_type
  key_name               = var.ssh_key_name
  iam_instance_profile   = aws_iam_instance_profile.ec2_trnda_profile.name
  vpc_security_group_ids = [aws_security_group.ec2_trnda.id]
  subnet_id              = var.subnet_id

  user_data = templatefile("${path.module}/user-data.sh", {
    s3_bucket_name = var.s3_bucket_name
  })

  root_block_device {
    volume_size = 20
    volume_type = "gp3"
    encrypted   = true
  }

  tags = {
    Name        = "${var.project_name}-ec2"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }

  lifecycle {
    ignore_changes = [user_data]
  }
}

# CloudWatch Log Group for SSM Output
resource "aws_cloudwatch_log_group" "ssm_output" {
  name              = "/aws/ssm/${var.project_name}"
  retention_in_days = var.log_retention_days

  tags = {
    Name        = "${var.project_name} SSM Logs"
    Environment = var.environment
  }
}

# IAM Role for Lambda
resource "aws_iam_role" "lambda_role" {
  name = "${var.project_name}-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name        = "${var.project_name} Lambda Role"
    Environment = var.environment
  }
}

# Lambda Basic Execution Policy
resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Lambda SSM Policy
resource "aws_iam_role_policy" "lambda_ssm" {
  name = "${var.project_name}-lambda-ssm-policy"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ssm:SendCommand",
          "ssm:GetCommandInvocation"
        ]
        Resource = "*"
      }
    ]
  })
}

# Lambda S3 Read Policy
resource "aws_iam_role_policy" "lambda_s3" {
  name = "${var.project_name}-lambda-s3-policy"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:GetObjectMetadata",
          "s3:HeadObject"
        ]
        Resource = "${aws_s3_bucket.trnda.arn}/*"
      }
    ]
  })
}

# Lambda Function
resource "aws_lambda_function" "trnda_trigger" {
  filename         = "${path.module}/../lambda-trigger/lambda.zip"
  function_name    = "${var.project_name}-ssm-trigger"
  role            = aws_iam_role.lambda_role.arn
  handler         = "lambda_function.lambda_handler"
  runtime         = "python3.11"
  timeout         = 60
  source_code_hash = filebase64sha256("${path.module}/../lambda-trigger/lambda.zip")

  environment {
    variables = {
      INSTANCE_ID       = aws_instance.trnda.id
      WORKING_DIRECTORY = "/home/ubuntu/trnda"
      S3_BUCKET         = var.s3_bucket_name
    }
  }

  tags = {
    Name        = "${var.project_name} SSM Trigger"
    Environment = var.environment
  }
}

# EventBridge Rule for S3 uploads
resource "aws_cloudwatch_event_rule" "s3_upload" {
  name        = "${var.project_name}-s3-upload"
  description = "Trigger on S3 upload to input/ folder"

  event_pattern = jsonencode({
    source      = ["aws.s3"]
    detail-type = ["Object Created"]
    detail = {
      bucket = {
        name = [var.s3_bucket_name]
      }
      object = {
        key = [{
          prefix = "input/"
        }]
      }
    }
  })

  tags = {
    Name        = "${var.project_name} S3 Upload Rule"
    Environment = var.environment
  }
}

# EventBridge Target (Lambda)
resource "aws_cloudwatch_event_target" "lambda" {
  rule      = aws_cloudwatch_event_rule.s3_upload.name
  target_id = "TRNDALambdaTrigger"
  arn       = aws_lambda_function.trnda_trigger.arn
}

# Lambda Permission for EventBridge
resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.trnda_trigger.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.s3_upload.arn
}

# CloudWatch Alarm: EC2 Status Check Failed
resource "aws_cloudwatch_metric_alarm" "ec2_status_check" {
  alarm_name          = "${var.project_name}-ec2-status-check-failed"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "StatusCheckFailed"
  namespace           = "AWS/EC2"
  period              = 60
  statistic           = "Maximum"
  threshold           = 0
  alarm_description   = "EC2 instance status check failed"
  treat_missing_data  = "notBreaching"

  dimensions = {
    InstanceId = aws_instance.trnda.id
  }

  tags = {
    Name        = "${var.project_name} EC2 Status Alarm"
    Environment = var.environment
  }
}

# CloudWatch Alarm: Lambda Errors
resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  alarm_name          = "${var.project_name}-lambda-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = 0
  alarm_description   = "Lambda function errors detected"
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.trnda_trigger.function_name
  }

  tags = {
    Name        = "${var.project_name} Lambda Error Alarm"
    Environment = var.environment
  }
}
