# TRNDA - Architecture Documentation

**Generated**: 2025-01-14  
**Version**: v0.5

This document provides a comprehensive overview of the TRNDA (Trask Ručně Nakreslí, Dokončí AWS) architecture, including all deployment options, components, and data flows.

## Table of Contents

1. [Overview](#overview)
2. [Architecture Diagrams](#architecture-diagrams)
3. [System Components](#system-components)
4. [Deployment Options](#deployment-options)
5. [Data Flow](#data-flow)
6. [Frontend Architecture](#frontend-architecture)
7. [Cost Analysis](#cost-analysis)
8. [Security & IAM](#security--iam)

---

## Overview

TRNDA is an AI-powered system that converts hand-drawn AWS architecture diagrams into professional designs with cost calculations. The system leverages:

- **AWS Bedrock** with Claude 4.5 Sonnet (1M context window)
- **MCP Servers** for AWS knowledge, diagram generation, and pricing
- **Event-driven architecture** for automated processing
- **Multiple deployment options** (EC2, ECS Fargate, local CLI)
- **Web-based frontend** for easy diagram uploads

### Key Capabilities

- Analyzes hand-drawn architecture diagrams
- Generates As-Is architecture documentation
- Proposes Well-Architected improvements
- Calculates costs for 6 scenarios (As-Is and Well-Arch: Low/Medium/High)
- Generates professional PDF reports (3-4 pages)
- Sends reports via email (AWS SES)
- Tracks complete AWS costs (Bedrock, compute, storage)

---

## Architecture Diagrams

Five comprehensive diagrams have been generated to illustrate different aspects of the system:

### 1. Complete Architecture
**File**: `generated-diagrams/trnda_complete_architecture.png`

Shows the entire TRNDA ecosystem including:
- Frontend web interface with CloudFront and S3
- Both EC2 and ECS Fargate deployment options
- Event-driven trigger chain (EventBridge → Lambda)
- AI services (Bedrock, MCP servers)
- Monitoring and security components

### 2. EC2 Standalone Deployment
**File**: `generated-diagrams/trnda_ec2_deployment.png`

Production deployment using a single EC2 instance:
- t4g.medium instance running 24/7
- EventBridge → Lambda → SSM → EC2 trigger chain
- Ubuntu 24.04 ARM64 with Python 3.12
- Direct trnda-cli.py execution
- **Cost**: ~$30/month + $1.58/report (Bedrock)

### 3. ECS Fargate Deployment
**File**: `generated-diagrams/trnda_ecs_deployment.png`

Serverless deployment using ECS Fargate:
- On-demand task execution (2 vCPU, 4GB)
- EventBridge → Lambda → ECS trigger chain
- Docker container with trnda-s3-handler.py
- No idle costs, scales automatically
- **Cost**: ~$0.15/task + $1.58/report (Bedrock)

### 4. Data Flow & Processing
**File**: `generated-diagrams/trnda_data_flow.png`

Six-stage processing pipeline:
1. **Upload**: User uploads diagram with metadata
2. **Storage**: S3 input folder receives file
3. **Trigger**: EventBridge detects and triggers Lambda
4. **AI Analysis**: Claude 4.5 processes with MCP servers (10-15 min)
5. **Report Generation**: Creates MD, PDF, diagrams, cost analysis
6. **Delivery**: S3 output + optional email delivery

### 5. Frontend Web Interface
**File**: `generated-diagrams/trnda_frontend_architecture.png`

Password-protected upload interface:
- CloudFront CDN for HTTPS delivery
- S3 static website hosting
- API Gateway + Lambda for uploads
- Camera capture support for mobile
- Image rotation and metadata input
- **Cost**: ~$1-2/month

---

## System Components

### Core Processing Components

#### 1. trnda-agent.py
**Purpose**: Core business logic for architecture analysis

- Input: Local file path or S3 path
- Output: design.md, design.pdf, cost.md, diagrams
- S3 Support: Yes (auto-detects and handles S3 paths)
- Email: Yes (sends PDF via SES when email detected)
- Used by: Both CLI and S3 handler
- Runtime: 10-15 minutes typical

#### 2. trnda-cli.py
**Purpose**: Command-line interface with S3 support

- Input: Local image files or S3 paths
- Output: Local folders or S3
- S3 Support: Full (download/upload)
- Use cases: Development, testing, manual processing

#### 3. trnda-s3-handler.py
**Purpose**: EventBridge-triggered processing on ECS

- Receives EventBridge S3 ObjectCreated events
- Downloads image from S3
- Calls process_image_standalone() from trnda-agent.py
- Uploads results back to S3
- Use case: Production AWS deployment (ECS Fargate)

### AI & MCP Components

#### AWS Bedrock
- Model: Claude 4.5 Sonnet (eu.anthropic.claude-sonnet-4-5-20250929-v1:0)
- Region: eu-central-1
- Context: 1M tokens
- Cost: $3.00/1M input tokens, $15.00/1M output tokens

#### MCP Servers (Model Context Protocol)
1. **AWS Knowledge Server**: Documentation, recommendations, regional availability
2. **Diagram Server**: Visual architecture diagram generation
3. **Pricing Server**: AWS cost calculations and estimates

### Frontend Components

#### Static Website
- **S3 Bucket**: Hosts index.html, styles.css, app.js
- **CloudFront**: HTTPS delivery with CDN
- **ACM**: SSL/TLS certificates
- **Route 53**: Custom domain support (optional)

#### Upload API
- **API Gateway**: HTTPS API with CORS
- **Lambda**: Password validation + S3 upload
- **Features**: Password protection, camera capture, rotation, metadata

### Storage Components

#### S3 Bucket Structure
```
s3://your-trnda-s3-bucket/
├── input/                    # Upload diagrams here
│   └── diagram.jpg
└── output/                   # Results saved here
    └── 20250113001530/       # Timestamp folder
        ├── design.md
        ├── design.pdf
        ├── cost.md
        ├── diagram_input.png
        └── generated-diagrams/
            ├── diagram_as_is.png
            └── diagram_well_architected.png
```

---

## Deployment Options

### Local Development
```
User → trnda-cli.py → trnda-agent.py → Local output/
                         ↓
                    S3 (optional)
```

**Use Cases**:
- Development and testing
- Manual processing
- Local S3 operations

**Requirements**:
- Python 3.10+
- AWS credentials configured
- pandoc, uvx installed

### EC2 Standalone (Production)
```
S3 Upload → EventBridge → Lambda → SSM → EC2 (24/7)
                                           ↓
                                      trnda-cli.py
                                           ↓
                                      S3 Output
```

**Characteristics**:
- Single t4g.medium instance (ARM64)
- Ubuntu 24.04 LTS
- Runs 24/7 (always ready)
- Simple, reliable architecture
- Easy to debug and monitor
- SSM for remote command execution

**Cost**: ~$30/month + $1.58/report

**Best For**:
- Production deployments
- Predictable workloads
- Organizations wanting dedicated resources

### ECS Fargate (Serverless)
```
S3 Upload → EventBridge → Lambda → ECS Fargate Task
                                           ↓
                                   trnda-s3-handler.py
                                           ↓
                                      S3 Output
```

**Characteristics**:
- On-demand execution (2 vCPU, 4GB)
- Docker container
- Scales automatically
- No idle costs
- No server management
- VPC networking

**Cost**: ~$0.15/task + $1.58/report

**Best For**:
- Variable workloads
- Cost optimization (pay per use)
- Horizontal scalability needs
- Serverless-first organizations

---

## Data Flow

### Upload Phase
1. **User Action**: Uploads diagram via web UI or CLI
2. **Metadata**: Includes client info and optional email
3. **S3 Storage**: File saved to `s3://bucket/input/`
4. **Event**: EventBridge detects ObjectCreated event

### Trigger Phase
5. **EventBridge**: Matches rule for input/ prefix
6. **Lambda Trigger**: 
   - EC2: Sends SSM command
   - ECS: Starts Fargate task
7. **Processing Start**: Handler begins execution

### Analysis Phase (10-15 minutes)
8. **Image Download**: Retrieves from S3
9. **Claude Analysis**: Bedrock API calls
10. **MCP Queries**:
    - AWS Knowledge: Documentation lookups
    - Diagram: Visual generation
    - Pricing: Cost calculations
11. **Report Generation**: Creates all outputs

### Delivery Phase
12. **S3 Upload**: Saves to `s3://bucket/output/timestamp/`
13. **Email Delivery**: If email detected in metadata
14. **Completion**: Logs success to CloudWatch

---

## Frontend Architecture

### Components

#### CloudFront Distribution
- HTTPS delivery
- Global CDN caching
- Custom domain support
- ACM certificate integration
- Origin: S3 static website

#### S3 Static Website
- Hosts HTML, CSS, JavaScript
- Public read access (via CloudFront OAI)
- Website configuration enabled
- No server-side processing

#### API Gateway
- HTTP API type
- CORS enabled
- Routes: /auth, /upload
- Lambda integration
- Regional endpoint

#### Lambda Upload Function
- Python 3.11 runtime
- Password validation (from env var)
- S3 PutObject permission
- Metadata extraction
- CloudWatch logging

### User Experience

1. **Access**: User visits CloudFront URL
2. **Authentication**: Enters configured password
3. **Upload Options**:
   - Select file from device
   - Capture photo (mobile camera)
   - Rotate image (90° increments)
   - Add client info (max 1900 chars)
4. **Submission**: Direct upload to S3 via API
5. **Feedback**: Success confirmation

### Security

- Password protection (Lambda env variable)
- HTTPS only (CloudFront + API Gateway)
- No AWS credentials in JavaScript
- IAM roles for Lambda
- CORS configuration
- CloudWatch logging

---

## Cost Analysis

### EC2 Standalone Deployment

**Fixed Monthly Costs**:
- EC2 t4g.medium: ~$30/month (24/7)
- S3 storage: ~$0.50/month (1GB typical)
- CloudWatch logs: ~$0.50/month
- **Total Fixed**: ~$31/month

**Per Report Costs**:
- Bedrock (Claude 4.5): ~$1.58 (500K input, 5K output)
- S3 operations: <$0.01
- SES email: <$0.01
- **Total Per Report**: ~$1.60

**100 Reports/Month**: ~$191 total

### ECS Fargate Deployment

**Fixed Monthly Costs**:
- S3 storage: ~$0.50/month
- CloudWatch logs: ~$0.50/month
- ECR storage: ~$0.10/month
- **Total Fixed**: ~$1.10/month

**Per Report Costs**:
- ECS Fargate: ~$0.15 (15 min @ 2vCPU, 4GB)
- Bedrock (Claude 4.5): ~$1.58
- S3 operations: <$0.01
- SES email: <$0.01
- **Total Per Report**: ~$1.75

**100 Reports/Month**: ~$176 total

### Frontend Costs

**Monthly Costs**:
- CloudFront: ~$1.00 (assuming low traffic)
- S3 hosting: ~$0.02
- Lambda: Free tier (first 1M requests)
- API Gateway: Free tier (first 1M calls)
- **Total**: ~$1-2/month

### Cost Comparison

| Deployment | Fixed/Month | Per Report | 100 Reports/Month |
|------------|-------------|------------|-------------------|
| EC2        | $31         | $1.60      | $191              |
| ECS        | $1.10       | $1.75      | $176              |
| Frontend   | $1-2        | -          | $1-2              |

**Recommendation**:
- **EC2**: Better for high volume (>200 reports/month)
- **ECS**: Better for variable/low volume (<200 reports/month)

---

## Security & IAM

### IAM Roles

#### EC2 Instance Role
Permissions:
- S3: GetObject, PutObject, ListBucket
- Bedrock: InvokeModel, InvokeModelWithResponseStream
- SES: SendEmail, SendRawEmail
- Pricing: GetProducts, DescribeServices
- SSM: Managed instance core (for SSM commands)
- CloudWatch: PutLogEvents

#### ECS Task Role
Permissions:
- S3: GetObject, PutObject, ListBucket
- Bedrock: InvokeModel, InvokeModelWithResponseStream
- SES: SendEmail, SendRawEmail
- Pricing: GetProducts, DescribeServices

#### ECS Task Execution Role
Permissions:
- ECR: GetAuthorizationToken, BatchGetImage
- CloudWatch: CreateLogGroup, PutLogEvents

#### Lambda Trigger Role (EC2)
Permissions:
- SSM: SendCommand, GetCommandInvocation
- S3: GetObject, GetObjectMetadata

#### Lambda Trigger Role (ECS)
Permissions:
- ECS: RunTask, DescribeTasks
- IAM: PassRole (for task roles)

#### Lambda Upload Role (Frontend)
Permissions:
- S3: PutObject (diagrams bucket only)
- CloudWatch: CreateLogGroup, PutLogEvents

### Security Best Practices

1. **No Hardcoded Credentials**: All access via IAM roles
2. **Principle of Least Privilege**: Minimal required permissions
3. **Encryption**:
   - S3: Server-side encryption
   - EBS: Encrypted volumes
   - CloudWatch: Encrypted log groups
4. **Network Security**:
   - VPC isolation
   - Security groups
   - Private subnets recommended
5. **API Security**:
   - Password protection
   - HTTPS only
   - CORS configuration
6. **Monitoring**:
   - CloudWatch logs for all components
   - CloudWatch alarms for failures
   - Cost tracking and reporting

### SES Email Security

- Sender: trnda@ai.aws.thetrasklab.com
- Requires verified sender email
- Recipient emails must be verified (sandbox mode)
- Production mode: Can send to any email
- Condition in IAM: Only allowed FromAddress

---

## Monitoring & Logging

### CloudWatch Log Groups

- `/ecs/trnda` - ECS Fargate task logs
- `/aws/ssm/trnda` - SSM command output (EC2)
- `/aws/lambda/trnda-trigger` - Lambda trigger logs
- `/aws/lambda/trnda-ssm-trigger` - Lambda SSM trigger logs
- `/aws/lambda/trnda-upload` - Frontend upload Lambda

### CloudWatch Alarms

- EC2 Status Check Failed
- Lambda Error Count
- ECS Task Failed

### Cost Tracking

TRNDA automatically tracks and reports:
- Bedrock token usage and costs
- ECS Fargate compute time
- S3 storage and transfer
- Complete cost per report
- Saved in cost.md output file

---

## Terraform Infrastructure

### EC2 Deployment
- File: `aws-deployment/ec2-standalone/terraform/main.tf`
- Resources: EC2, Lambda, EventBridge, IAM, CloudWatch
- Bootstrap: user-data.sh (git clone, pip install, setup)

### ECS Deployment
- File: `aws-deployment/terraform/main.tf`
- Resources: ECS, ECR, Lambda, EventBridge, IAM, CloudWatch
- Container: Docker image from ECR

### Frontend Deployment
- File: `frontend/aws-deployment/terraform/main.tf`
- Resources: S3, CloudFront, API Gateway, Lambda, ACM, Route 53
- Static files auto-uploaded

---

## Technical Stack

### Languages & Frameworks
- Python 3.10+ (backend processing)
- JavaScript ES6+ (frontend)
- HTML5, CSS3 (frontend UI)
- Terraform (infrastructure)

### AWS Services
- Bedrock (Claude 4.5 Sonnet)
- S3 (storage)
- EventBridge (event routing)
- Lambda (serverless functions)
- EC2 (compute - standalone)
- ECS Fargate (compute - serverless)
- ECR (container registry)
- API Gateway (HTTP API)
- CloudFront (CDN)
- Route 53 (DNS)
- ACM (certificates)
- SES (email)
- IAM (security)
- CloudWatch (monitoring)
- SSM (remote commands)

### Third-Party Tools
- **pandoc**: PDF generation
- **uvx**: MCP server management
- **Strands AI Agents**: Agent framework
- **MCP Protocol**: Tool integration

### MCP Servers
- AWS Knowledge Server
- Diagram Generation Server
- AWS Pricing Server

---

## Conclusion

TRNDA provides a flexible, scalable architecture for automated AWS diagram analysis and cost calculation. With multiple deployment options and comprehensive monitoring, it can adapt to various organizational needs and workload patterns.

The architecture emphasizes:
- **Event-driven design** for scalability
- **Cost optimization** through serverless and right-sizing
- **Security** via IAM roles and encryption
- **Reliability** through CloudWatch monitoring
- **Flexibility** with multiple deployment options

For questions or support, refer to the README.md and individual deployment guides.

---

**End of Architecture Documentation**
