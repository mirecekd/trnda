# TRNDA EC2 Standalone Deployment

Simple, reliable deployment of TRNDA on a single EC2 instance running 24/7.

## Architecture

```
S3 Upload (your-trnda-s3-bucket/input/)
    ↓
EventBridge Rule (Object Created)
    ↓
Lambda Function (SSM Trigger)
    ↓
SSM Run Command
    ↓
EC2 Instance (t4g.medium, Ubuntu 24.04, running 24/7)
    ↓
/home/ubuntu/trnda/trnda-cli.py
    ↓
Output → S3 (your-trnda-s3-bucket/output/)
```

## Structure

```
ec2-standalone/
├── terraform/
│   ├── main.tf                  # Main infrastructure
│   ├── variables.tf             # Input variables
│   ├── outputs.tf               # Output values
│   ├── user-data.sh            # EC2 bootstrap script
│   └── terraform.tfvars.example # Configuration example
├── lambda-trigger/
│   ├── lambda_function.py      # SSM trigger Lambda
│   └── lambda.zip              # Lambda deployment package
└── README.md                    # This file
```

## Quick Start

### 1. Prerequisites

- AWS CLI configured with your AWS profile
- Terraform >= 1.0
- Existing S3 bucket: `your-trnda-s3-bucket`
- Existing VPC and subnet
- Existing SSH key pair: `ai-tool-box`

### 2. Configure Terraform

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values
```

Required values:
- `vpc_id`: Your VPC ID
- `subnet_id`: Public subnet ID (for easy SSH access)

### 3. Deploy

```bash
terraform init
terraform plan
terraform apply
```

This will create:
- EC2 instance (t4g.medium) with TRNDA installed
- IAM roles (S3, Bedrock, SES, SSM access)
- Lambda function (SSM trigger)
- EventBridge rule (S3 upload monitoring)
- CloudWatch alarms (monitoring)
- Security groups

### 4. Verify Deployment

After deployment completes (~5 minutes for EC2 to bootstrap):

```bash
# Check EC2 bootstrap logs
INSTANCE_ID=$(terraform output -raw ec2_instance_id)
aws ssm start-session --target $INSTANCE_ID --profile your-profile

# On EC2:
sudo cat /var/log/user-data.log
cd /home/ubuntu/trnda
./health-check.sh
```

### 5. Test

```bash
# Upload a test image
aws s3 cp samples/sample1.jpg \
  s3://your-trnda-s3-bucket/input/ \
  --profile your-profile

# Monitor logs
aws logs tail /aws/ssm/trnda --follow --profile your-profile

# Check Lambda logs
aws logs tail /aws/lambda/trnda-ssm-trigger --follow --profile your-profile
```

## Costs

- **EC2 t4g.medium**: ~$30/month (24/7)
- **Bedrock**: $3-5 per processing
- **S3, Lambda, CloudWatch**: ~$1/month
- **Total**: ~$331-536/month for 100 processings

## Operations

### SSH Access

```bash
# Get SSH command
terraform output ssh_command

# Or use SSM (no SSH key needed)
terraform output ssm_connect_command
```

### Monitor Processing

```bash
# CloudWatch logs (SSM output)
aws logs tail /aws/ssm/trnda --follow --profile your-profile

# Lambda logs
aws logs tail /aws/lambda/trnda-ssm-trigger --follow --profile your-profile

# On EC2 instance
ssh -i ~/.ssh/ai-tool-box.pem ubuntu@<public-ip>
cd /home/ubuntu/trnda/logs
tail -f trnda-*.log
```

### Manual Test on EC2

```bash
ssh -i ~/.ssh/ai-tool-box.pem ubuntu@<public-ip>
cd /home/ubuntu/trnda
python3 trnda-cli.py s3://your-trnda-s3-bucket/input/sample.jpg
```

### Update TRNDA Code

```bash
# SSH to EC2
ssh -i ~/.ssh/ai-tool-box.pem ubuntu@<public-ip>

# Pull latest changes
cd /home/ubuntu/trnda
git pull origin main

# Update dependencies if needed
pip3 install --break-system-packages -r requirements.txt
```

### Check SSM Command Status

```bash
# List recent commands
aws ssm list-commands \
  --instance-id $(terraform output -raw ec2_instance_id) \
  --profile your-profile

# Get command details
aws ssm get-command-invocation \
  --command-id <command-id> \
  --instance-id $(terraform output -raw ec2_instance_id) \
  --profile your-profile
```

## Troubleshooting

### EC2 Not Responding

```bash
# Check instance status
aws ec2 describe-instance-status \
  --instance-ids $(terraform output -raw ec2_instance_id) \
  --profile your-profile

# Check CloudWatch alarms
aws cloudwatch describe-alarms \
  --alarm-name-prefix trnda \
  --profile your-profile
```

### Lambda Not Triggering

```bash
# Check Lambda logs
aws logs tail /aws/lambda/trnda-ssm-trigger --since 1h --profile your-profile

# Test Lambda manually
aws lambda invoke \
  --function-name trnda-ssm-trigger \
  --payload '{"detail":{"bucket":{"name":"your-trnda-s3-bucket"},"object":{"key":"input/test.jpg"}}}' \
  --profile your-profile \
  response.json
```

### SSM Command Failing

```bash
# Check SSM agent status on EC2
ssh -i ~/.ssh/ai-tool-box.pem ubuntu@<public-ip>
sudo systemctl status amazon-ssm-agent

# Restart if needed
sudo systemctl restart amazon-ssm-agent
```

### Python Dependencies Missing

```bash
# SSH to EC2 and reinstall
ssh -i ~/.ssh/ai-tool-box.pem ubuntu@<public-ip>
cd /home/ubuntu/trnda
pip3 install --break-system-packages -r requirements.txt
```

## Updates

### Update Infrastructure

```bash
cd terraform
terraform plan
terraform apply
```

### Update Lambda Function

```bash
cd lambda-trigger
# Modify lambda_function.py
zip lambda.zip lambda_function.py

cd ../terraform
terraform apply -target=aws_lambda_function.trnda_trigger
```

## Cleanup

```bash
cd terraform
terraform destroy
```

**Note**: This will NOT delete the S3 bucket (as intended).

## Monitoring

CloudWatch Alarms are configured for:
- EC2 Status Check Failed
- Lambda Errors

View alarms:
```bash
aws cloudwatch describe-alarms --profile your-profile | grep trnda
```

## FAQ

**Q: Why EC2 instead of ECS/Fargate?**  
A: Simpler, more reliable, easier to debug. No container orchestration overhead.

**Q: Why t4g.medium (ARM)?**  
A: ~30% cheaper than equivalent t3.medium (x86), same performance.

**Q: Can I use a smaller instance?**  
A: t4g.small might work, but t4g.medium is recommended for stable performance.

**Q: How do I add more processing capacity?**  
A: For now, scale vertically (larger instance type). For horizontal scaling, consider adding more EC2 instances with a load balancer.

**Q: What if EC2 goes down?**  
A: CloudWatch alarm will notify you. Simply restart the instance or redeploy with Terraform.

## Security

- IAM roles (no hardcoded credentials)
- SSM for command execution (no open SSH ports needed)
- VPC security groups
- Encrypted EBS volumes
- CloudWatch logging

## Notes

- EC2 instance runs Ubuntu 24.04 LTS ARM64
- Python 3.12 is used
- Git repo is cloned from `github.com/mirecekd/trnda` (main branch)
- All dependencies are installed via pip
- SSM Agent is pre-installed on Ubuntu AMI
- CloudWatch logs are retained for 7 days (configurable)
