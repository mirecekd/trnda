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
  region = var.aws_region
}

# S3 Bucket for input/output
resource "aws_s3_bucket" "trnda_bucket" {
  bucket = var.bucket_name
  
  tags = {
    Name        = "TRNDA Architecture Diagrams"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# Enable EventBridge notifications
resource "aws_s3_bucket_notification" "trnda_notification" {
  bucket      = aws_s3_bucket.trnda_bucket.id
  eventbridge = true
}

# ECR Repository for Docker image
resource "aws_ecr_repository" "trnda" {
  name                 = "trnda-agent"
  image_tag_mutability = "MUTABLE"
  
  image_scanning_configuration {
    scan_on_push = true
  }
  
  tags = {
    Name        = "TRNDA Agent"
    Environment = var.environment
  }
}

# ECS Cluster
resource "aws_ecs_cluster" "trnda" {
  name = "${var.project_name}-cluster"
  
  setting {
    name  = "containerInsights"
    value = "enabled"
  }
  
  tags = {
    Name        = "TRNDA Cluster"
    Environment = var.environment
  }
}

# CloudWatch Log Group for ECS tasks
resource "aws_cloudwatch_log_group" "trnda_logs" {
  name              = "/ecs/${var.project_name}"
  retention_in_days = var.log_retention_days
  
  tags = {
    Name        = "TRNDA Logs"
    Environment = var.environment
  }
}

# IAM Role for ECS Task Execution
resource "aws_iam_role" "ecs_task_execution_role" {
  name = "${var.project_name}-ecs-execution-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })
  
  tags = {
    Name        = "TRNDA ECS Execution Role"
    Environment = var.environment
  }
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution_policy" {
  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# IAM Role for ECS Task (with Bedrock and S3 permissions)
resource "aws_iam_role" "ecs_task_role" {
  name = "${var.project_name}-ecs-task-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })
  
  tags = {
    Name        = "TRNDA ECS Task Role"
    Environment = var.environment
  }
}

# Policy for S3 access
resource "aws_iam_role_policy" "ecs_task_s3_policy" {
  name = "${var.project_name}-s3-policy"
  role = aws_iam_role.ecs_task_role.id

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
          aws_s3_bucket.trnda_bucket.arn,
          "${aws_s3_bucket.trnda_bucket.arn}/*"
        ]
      }
    ]
  })
}

# Policy for Bedrock access
resource "aws_iam_role_policy" "ecs_task_bedrock_policy" {
  name = "${var.project_name}-bedrock-policy"
  role = aws_iam_role.ecs_task_role.id
  
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

# Policy for Pricing API access
resource "aws_iam_role_policy" "ecs_task_pricing_policy" {
  name = "${var.project_name}-pricing-policy"
  role = aws_iam_role.ecs_task_role.id
  
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

# Policy for SES access (email notifications)
resource "aws_iam_role_policy" "ecs_task_ses_policy" {
  name = "${var.project_name}-ses-policy"
  role = aws_iam_role.ecs_task_role.id
  
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

# ECS Task Definition
resource "aws_ecs_task_definition" "trnda" {
  family                   = var.project_name
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.task_cpu
  memory                   = var.task_memory
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn
  
  container_definitions = jsonencode([
    {
      name      = "trnda-container"
      image     = "${aws_ecr_repository.trnda.repository_url}:latest"
      essential = true
      
      environment = [
        {
          name  = "AWS_DEFAULT_REGION"
          value = var.aws_region
        }
      ]
      
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.trnda_logs.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "trnda"
        }
      }
    }
  ])
  
  tags = {
    Name        = "TRNDA Task Definition"
    Environment = var.environment
  }
}

# Security Group for ECS Tasks
resource "aws_security_group" "ecs_tasks" {
  name        = "${var.project_name}-ecs-tasks-sg"
  description = "Security group for TRNDA ECS tasks"
  vpc_id      = var.vpc_id
  
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound traffic (needed for MCP servers)"
  }
  
  tags = {
    Name        = "TRNDA ECS Tasks SG"
    Environment = var.environment
  }
}

# Lambda Function for triggering ECS tasks
resource "aws_lambda_function" "trnda_trigger" {
  filename         = "${path.module}/../lambda-trigger/lambda.zip"
  function_name    = "${var.project_name}-trigger"
  role            = aws_iam_role.lambda_execution_role.arn
  handler         = "lambda_function.lambda_handler"
  runtime         = "python3.11"
  timeout         = 60
  
  environment {
    variables = {
      ECS_CLUSTER_NAME      = aws_ecs_cluster.trnda.name
      TASK_DEFINITION_ARN   = aws_ecs_task_definition.trnda.arn
      SUBNET_IDS            = join(",", var.subnet_ids)
      SECURITY_GROUP_IDS    = aws_security_group.ecs_tasks.id
      CONTAINER_NAME        = "trnda-container"
    }
  }
  
  tags = {
    Name        = "TRNDA Lambda Trigger"
    Environment = var.environment
  }
}

# IAM Role for Lambda
resource "aws_iam_role" "lambda_execution_role" {
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
    Name        = "TRNDA Lambda Role"
    Environment = var.environment
  }
}

resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  role       = aws_iam_role.lambda_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Policy for Lambda to start ECS tasks
resource "aws_iam_role_policy" "lambda_ecs_policy" {
  name = "${var.project_name}-lambda-ecs-policy"
  role = aws_iam_role.lambda_execution_role.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ecs:RunTask",
          "ecs:DescribeTasks",
          "iam:PassRole"
        ]
        Resource = "*"
      }
    ]
  })
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
        name = [aws_s3_bucket.trnda_bucket.id]
      }
      object = {
        key = [{
          prefix = "input/"
        }]
      }
    }
  })
  
  tags = {
    Name        = "TRNDA S3 Upload Rule"
    Environment = var.environment
  }
}

# EventBridge Target (Lambda)
resource "aws_cloudwatch_event_target" "lambda" {
  rule      = aws_cloudwatch_event_rule.s3_upload.name
  target_id = "TRNDALambdaTrigger"
  arn       = aws_lambda_function.trnda_trigger.arn
}

# Lambda permission for EventBridge
resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.trnda_trigger.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.s3_upload.arn
}
