output "ec2_instance_id" {
  description = "EC2 instance ID"
  value       = aws_instance.trnda.id
}

output "ec2_instance_public_ip" {
  description = "EC2 instance public IP address"
  value       = aws_instance.trnda.public_ip
}

output "ec2_instance_private_ip" {
  description = "EC2 instance private IP address"
  value       = aws_instance.trnda.private_ip
}

output "ssh_command" {
  description = "SSH command to connect to EC2 instance"
  value       = "ssh -i ~/.ssh/${var.ssh_key_name}.pem ubuntu@${aws_instance.trnda.public_ip}"
}

output "ssm_connect_command" {
  description = "AWS SSM command to connect to EC2 instance"
  value       = "aws ssm start-session --target ${aws_instance.trnda.id} --profile ${var.aws_profile}"
}

output "lambda_function_name" {
  description = "Lambda function name"
  value       = aws_lambda_function.trnda_trigger.function_name
}

output "s3_bucket_name" {
  description = "S3 bucket name for TRNDA"
  value       = var.s3_bucket_name
}

output "cloudwatch_log_group" {
  description = "CloudWatch log group for SSM output"
  value       = aws_cloudwatch_log_group.ssm_output.name
}

output "usage_instructions" {
  description = "Usage instructions"
  value       = <<EOT

=== TRNDA EC2 Standalone Deployment ===

EC2 Instance: ${aws_instance.trnda.id}
Public IP: ${aws_instance.trnda.public_ip}

To use the system:

1. Upload diagram to S3:
   aws s3 cp diagram.jpg s3://${var.s3_bucket_name}/input/ --profile ${var.aws_profile}

2. Monitor logs:
   aws logs tail ${aws_cloudwatch_log_group.ssm_output.name} --follow --profile ${var.aws_profile}

3. SSH to EC2 (for debugging):
   ssh -i ~/.ssh/${var.ssh_key_name}.pem ubuntu@${aws_instance.trnda.public_ip}
   
   Or via SSM:
   aws ssm start-session --target ${aws_instance.trnda.id} --profile ${var.aws_profile}

4. Check EC2 bootstrap logs:
   ssh -i ~/.ssh/${var.ssh_key_name}.pem ubuntu@${aws_instance.trnda.public_ip}
   sudo cat /var/log/user-data.log

5. Manual test on EC2:
   ssh -i ~/.ssh/${var.ssh_key_name}.pem ubuntu@${aws_instance.trnda.public_ip}
   cd /home/ubuntu/trnda
   python3 trnda-cli.py s3://${var.s3_bucket_name}/input/sample.jpg

EventBridge → Lambda → SSM → EC2 pipeline is active!

EOT
}
