output "s3_bucket_name" {
  description = "Name of the S3 bucket for diagrams"
  value       = aws_s3_bucket.trnda_bucket.id
}

output "s3_bucket_arn" {
  description = "ARN of the S3 bucket"
  value       = aws_s3_bucket.trnda_bucket.arn
}

output "ecr_repository_url" {
  description = "URL of the ECR repository for Docker images"
  value       = aws_ecr_repository.trnda.repository_url
}

output "ecs_cluster_name" {
  description = "Name of the ECS cluster"
  value       = aws_ecs_cluster.trnda.name
}

output "ecs_cluster_arn" {
  description = "ARN of the ECS cluster"
  value       = aws_ecs_cluster.trnda.arn
}

output "task_definition_arn" {
  description = "ARN of the ECS task definition"
  value       = aws_ecs_task_definition.trnda.arn
}

output "lambda_function_name" {
  description = "Name of the Lambda trigger function"
  value       = aws_lambda_function.trnda_trigger.function_name
}

output "lambda_function_arn" {
  description = "ARN of the Lambda trigger function"
  value       = aws_lambda_function.trnda_trigger.arn
}

output "cloudwatch_log_group" {
  description = "Name of the CloudWatch log group"
  value       = aws_cloudwatch_log_group.trnda_logs.name
}

output "usage_instructions" {
  description = "How to use the deployed system"
  value       = <<-EOT
    TRNDA deployment complete!
    
    To use the system:
    1. Upload architecture diagram to: s3://${aws_s3_bucket.trnda_bucket.id}/input/
    2. Optional: Use subdirectory for client name: s3://${aws_s3_bucket.trnda_bucket.id}/input/ClientName/diagram.jpg
    3. Results will be saved to: s3://${aws_s3_bucket.trnda_bucket.id}/output/
    4. Monitor logs: CloudWatch log group ${aws_cloudwatch_log_group.trnda_logs.name}
    
    ECR Repository: ${aws_ecr_repository.trnda.repository_url}
  EOT
}
