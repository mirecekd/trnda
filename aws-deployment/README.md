# TRNDA AWS Deployment

Automated TRNDA deployment to AWS using ECS Fargate.

## Quick Start

```bash
# 1. Build Docker image
docker build -t trnda-agent:latest .

# 2. Package Lambda
cd lambda-trigger && zip lambda.zip lambda_function.py && cd ..

# 3. Configure Terraform
cd terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars

# 4. Deploy
terraform init
terraform apply

# 5. Push Docker image
ECR_URL=$(terraform output -raw ecr_repository_url)
aws ecr get-login-password --region eu-central-1 | \
  docker login --username AWS --password-stdin $ECR_URL
docker tag trnda-agent:latest $ECR_URL:latest
docker push $ECR_URL:latest
```

## Structure

```
aws-deployment/
├── Dockerfile                    # Docker image for ECS
├── trnda-s3-handler.py          # S3 event handler for ECS
│
├── lambda-trigger/
│   ├── lambda_function.py       # Lambda trigger for ECS tasks
│   └── lambda.zip              # Package for deployment
│
└── terraform/
    ├── main.tf                  # Main infrastructure
    ├── variables.tf             # Input variables
    ├── outputs.tf               # Output values
    └── terraform.tfvars.example # Configuration example
```

## Architecture

**S3 Upload → EventBridge → Lambda → ECS Fargate → S3 Output**

- **S3 Bucket**: Input/output storage
- **EventBridge**: Triggers on S3 uploads
- **Lambda**: Lightweight trigger (starts ECS task)
- **ECS Fargate**: Runs TRNDA agent (no time limits)
- **ECR**: Docker image registry
- **CloudWatch**: Logging

## Prerequisites

- AWS Account with Bedrock access
- Claude 4.5 Sonnet model enabled (eu-central-1)
- AWS CLI, Docker, Terraform
- Existing VPC with subnets

## Costs

**~$0.15 + $3-5 per processing (15 min)**

- ECS Fargate: ~$0.15
- Bedrock: ~$3-5 (depends on size)
- S3/Lambda: negligible

**Monthly (100 processings): ~$325-525**

## Usage

```bash
# Upload diagram
BUCKET=$(terraform output -raw s3_bucket_name)
aws s3 cp diagram.jpg s3://$BUCKET/input/

# With client
aws s3 cp diagram.jpg s3://$BUCKET/input/ClientName/

# Monitor
aws logs tail /ecs/trnda --follow

# Download output
aws s3 cp s3://$BUCKET/output/... ./
```

## Configuration

**terraform.tfvars:**
```hcl
bucket_name = "your-unique-bucket-name"
vpc_id      = "vpc-xxxxx"
subnet_ids  = ["subnet-xxxxx", "subnet-yyyyy"]
task_cpu    = "2048"  # 2 vCPU
task_memory = "4096"  # 4 GB
```

## FAQ

**Q: Why ECS Fargate and not Lambda?**  
A: Lambda has 15 min limit, TRNDA runs 5-20 minutes. Fargate has no limits.

**Q: How much does it cost?**  
A: ~$0.15 per processing (ECS) + $3-5 (Bedrock). Total ~$325-525/month for 100 processings.

**Q: Where can I see logs?**  
A: CloudWatch Logs → `/ecs/trnda`

**Q: How to increase performance?**  
A: Increase `task_cpu` and `task_memory` in terraform.tfvars

**Q: How to scale?**  
A: ECS automatically starts new task for each upload. Max limit can be set.

## Troubleshooting

**Task fails to start:**
```bash
aws logs tail /ecs/trnda --since 5m
aws ecs describe-tasks --cluster trnda-cluster --tasks <task-id>
```

**Lambda not triggering:**
```bash
aws logs tail /aws/lambda/trnda-trigger --follow
```

**Bedrock access denied:**
```bash
aws bedrock list-foundation-models --region eu-central-1
```

## Cleanup

```bash
cd terraform
terraform destroy

# Delete ECR images
aws ecr batch-delete-image \
  --repository-name trnda-agent \
  --image-ids imageTag=latest
```

## Notes

- Region: `eu-central-1` (Bedrock Claude 4.5)
- VPC: You need existing VPC with subnets
- NAT: Recommended for private subnets
- Security: IAM roles, encrypted S3, VPC isolation
