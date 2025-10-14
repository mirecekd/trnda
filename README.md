# TRNDA - Trask Ručně Nakreslí, Dokončí AWS

**TRNDA** is an AI agent for converting hand-drawn architectures into AWS designs with cost calculations.

## What TRNDA Does

**Simple workflow:**

1. **Analyzes** hand-drawn architecture
2. **As-Is** -> diagram + cost calculation (3 scenarios)
3. **Well-Architected** -> improvements list + diagram + cost calculation (3 scenarios)
4. **Comparison** -> As-Is vs. Well-Architected (% differences)
5. **Export** -> design.md + design.pdf
6. **Email** -> Optional PDF delivery via SES (when client email provided)

## Requirements

- **Python 3.10+**
- **pandoc** (for PDF export)
- **uvx** (for MCP servers)
- **AWS credentials** (Bedrock + S3 + SES access)
- **AWS Profile** configured (or use environment variables)
- **S3 Bucket** - Configure via environment variable or code

```bash
pip install -r requirements.txt
```

## Configuration

### S3 Bucket Configuration

**Option 1: Environment Variable (Recommended)**
```bash
export S3_BUCKET=your-trnda-s3-bucket
export AWS_PROFILE=your-profile

python trnda-cli.py diagram.jpg
```

**Option 2: Modify Code**
Edit `trnda-agent.py` and change:
```python
DEFAULT_BUCKET = os.environ.get('S3_BUCKET', 'your-trnda-s3-bucket')
```
to your actual bucket name.

**Note:** The default placeholder `your-trnda-s3-bucket` will not work until you configure a real bucket name.

## Usage

### Local CLI (Recommended)

The CLI supports both local files and S3 paths.

```bash
# Local file
python trnda-cli.py diagram.jpg

# S3 path (full)
python trnda-cli.py s3://your-trnda-s3-bucket/input/diagram.jpg

# S3 path (short - auto-downloads from input/)
python trnda-cli.py diagram.jpg  # If exists in S3, downloads automatically

# With client name
python trnda-cli.py diagram.jpg --client "ACME Corporation"

# With email notification (sends PDF via SES - email is auto-detected from client name)
python trnda-cli.py diagram.jpg --client "jan@acme.com"

# With client info that includes email
python trnda-cli.py diagram.jpg --client "Project ABC, contact: jan@acme.com"

# Multiple images
python trnda-cli.py image1.jpg image2.jpg --client "Client A"

# Examples:
python trnda-cli.py samples/sample1.jpg
python trnda-cli.py sample1.jpg --client "jan@acme.com"  # Downloads from S3 + sends email
```

**Email Notifications:**
- Detects email in `--client` parameter
- Sends PDF report via AWS SES
- FROM: trnda@ai.aws.thetrasklab.com
- Requires SES email verification (sender and recipient emails must be verified in SES)

### S3 Integration

**S3 Bucket Structure:**
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

**How S3 Works:**
1. CLI detects S3 paths or checks if file exists in S3
2. Downloads from `s3://your-trnda-s3-bucket/input/`
3. Processes locally
4. Uploads results to `s3://your-trnda-s3-bucket/output/YYYYMMDDHHMMSS/`

### Original Script (Still Works)

```bash
# Basic usage
python trnda-agent.py <path_to_image>

# With client name
python trnda-agent.py <path_to_image> "Client Name"

# Examples:
python trnda-agent.py samples/sample1.jpg
python trnda-agent.py samples/sample1.jpg "ACME Corporation"
```

### AWS Deployment (Production)

For production use with EventBridge triggers and ECS Fargate:

```bash
# See aws-deployment/README.md for full deployment guide
cd aws-deployment
# Follow deployment instructions
```

**Benefits of AWS deployment:**
- Automatic processing on S3 upload
- EventBridge trigger (ObjectCreated in input/)
- Lambda starts ECS Fargate task
- No execution time limits
- Scalable (parallel processing)
- CloudWatch monitoring
- Cost: ~$3-5 per diagram + $0.15 ECS

**S3 Metadata Support:**

When uploading to S3 for automated processing, you can include client information and email in object metadata:

```bash
# Upload with metadata containing client info and email
aws s3 cp diagram.jpg s3://bucket/input/diagram.jpg \
  --metadata client-info="Project ABC for ACME Corp, contact: jan.novak@acme.com"

# Or just email
aws s3 cp diagram.jpg s3://bucket/input/diagram.jpg \
  --metadata client-info="jan.novak@acme.com"

# Or just project info (no email)
aws s3 cp diagram.jpg s3://bucket/input/diagram.jpg \
  --metadata client-info="Internal testing project"
```

**How it works:**
1. Upload image to S3 with `client-info` metadata
2. EventBridge triggers Lambda (EC2 deployment) or ECS (Fargate deployment)
3. Handler reads the metadata automatically
4. Full text appears in report header: `**Analysis is made for:** Project ABC for ACME Corp, contact: jan.novak@acme.com`
5. If email is detected in the text, report PDF is automatically sent via SES
6. Results saved to `s3://bucket/output/YYYYMMDDHHMMSS/`

**Two deployment options:**

### EC2 Standalone Deployment
- EventBridge → Lambda → SSM → EC2 instance
- Single t4g.medium instance runs TRNDA CLI
- Lower cost for occasional use
- Simple architecture, easy to debug
- See [aws-deployment/ec2-standalone/README.md](aws-deployment/ec2-standalone/README.md)

### ECS Fargate Deployment
- EventBridge → Lambda → ECS Fargate task
- Serverless, scales automatically
- No server management
- Higher cost per execution but no idle costs
- See [aws-deployment/README.md](aws-deployment/README.md)

See deployment guides for complete setup instructions.

### Image Requirements

- **Format:** JPG, JPEG, PNG
- **Max size:** Will be auto-compressed if > 5MB
- **Orientation:** Provide in correct orientation (no auto-rotation)

## Output (in English, max 3-4 pages)

```
output_YYYYMMDDHHMMSS/          # or s3://bucket/output/YYYYMMDDHHMMSS/
├── design.md                   # Complete report (Markdown)
├── design.pdf                  # PDF version with footer
├── cost.md                     # Detailed cost breakdown
├── diagram_input.png           # Original input (compressed if needed)
└── generated-diagrams/
    ├── diagram_as_is.png              # As-Is diagram (landscape)
    └── diagram_well_architected.png   # Well-Architected diagram (landscape)
```

### PDF Features

- **Professional footer:** "Trask Solutions a.s." | page number | "TRNDA report v0.5"
- **Optimal formatting:** 2cm margins, 10pt font, 1.1 line stretch
- **Page breaks:** Each section on separate pages

## Report Structure (SHORT)

```markdown
# AWS Architecture Design - [Name]

## 1. As-Is Architecture
- Components list
- Diagram
- Cost table (Low/Medium/High)

## 2. Well-Architected Design
- Improvements list (NO details)
- Diagram  
- Cost table (Low/Medium/High)
- Comparison with As-Is (%)
- Key benefits
```

**Everything in English, maximum 3-4 pages!**

## Architecture & Components

### Core Components

#### 1. **trnda-agent.py** (Core Processing Engine)
- **Purpose:** Core business logic for architecture analysis
- **Input:** Local file path or S3 path
- **Output:** Local folder or S3 with design.md, design.pdf, cost.md
- **S3:** Yes - auto-detects and handles S3 paths
- **Email:** Yes - sends PDF via SES when email detected
- **Used by:** Both CLI and S3 handler

#### 2. **trnda-cli.py** (Local CLI Wrapper)
- **Purpose:** Command-line interface with S3 support
- **Input:** Local image files or S3 paths
- **Output:** Local output folders or S3
- **S3:** Yes - supports both local and S3 operations
- **Use case:** Development, testing, manual processing, local S3 uploads

#### 3. **trnda-s3-handler.py** (AWS ECS Handler)
- **Purpose:** EventBridge-triggered processing on ECS
- **Flow:**
  1. Receives EventBridge event (S3 ObjectCreated)
  2. Downloads image from S3
  3. Calls `process_image_standalone()` from trnda-agent.py
  4. Uploads results back to S3
- **S3:** Yes - handles EventBridge event processing
- **Use case:** Production AWS deployment (ECS Fargate)

### Deployment Models

```
┌─────────────────────────────────────────────────────────────┐
│ LOCAL DEPLOYMENT (with S3 support)                          │
├─────────────────────────────────────────────────────────────┤
│ User → trnda-cli.py                                         │
│          ↓                                                  │
│      trnda-agent.py:                                        │
│      - Detects S3 path or checks S3                         │
│      - Downloads from S3 if needed                          │
│      - Processes locally                                    │
│      - Uploads to S3 if S3 path                             │
│      - Sends email if email provided                        │
│          ↓                                                  │
│      Local output/ or s3://bucket/output/timestamp/         │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ EC2 STANDALONE DEPLOYMENT                                   │
├─────────────────────────────────────────────────────────────┤
│ S3 upload → EventBridge → Lambda → SSM → EC2                │
│   (with        (trigger)    (reads      (sends  (t4g.medium)│
│  metadata)                   metadata)  command)            │
│                                              ↓              │
│                                    trnda-cli.py:            │
│                                    - Reads S3 with metadata │
│                                    - Calls trnda-agent.py   │
│                                    - Sends email if found   │
│                                    - Uploads to S3          │
│                                              ↓              │
│                                s3://bucket/output/timestamp/│
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ ECS FARGATE DEPLOYMENT (Serverless)                         │
├─────────────────────────────────────────────────────────────┤
│ S3 upload → EventBridge → Lambda → ECS Fargate Task         │
│   (with        (trigger)    (starts    (2 vCPU, 4GB)        │
│  metadata)                   task)                          │
│                                              ↓              │
│                              trnda-s3-handler.py:           │
│                              1. Parse EventBridge event     │
│                              2. Read S3 metadata            │
│                              3. Download from S3            │
│                              4. Call trnda-agent.py         │
│                              5. Send email if found         │
│                              6. Upload to S3                │
│                                              ↓              │
│                                s3://bucket/output/timestamp/│
└─────────────────────────────────────────────────────────────┘
```

## Cost Tracking & Monitoring

### Automatic Cost Tracking (v0.5+)

TRNDA automatically tracks and reports complete AWS costs:

**Console Output:**
```
TOKEN USAGE STATISTICS:
Input tokens:  747,147
Output tokens: 8,292
Total tokens:  755,439
Bedrock cost:   $2.3659

COMPLETE AWS COST BREAKDOWN:
Runtime:               02:57 (2.95 min)
Bedrock (Claude 4.5):  $2.3659
ECS Fargate compute:   $0.0305
S3 storage & transfer: $0.0000
TOTAL COST FOR REPORT GENERATION: $2.3964
```

**Generated Files:**
- **cost.md** - Detailed breakdown with timeline, component costs, optimization tips
- **design.md/PDF** - Runtime + total cost in header

### Cost Breakdown

#### Bedrock (Claude 4.5 Sonnet)
- Input: $3.00 per 1M tokens
- Output: $15.00 per 1M tokens
- Typical: ~500K input, ~5K output = ~$1.58

#### ECS Fargate (2 vCPU, 4 GB RAM)
- vCPU: $0.04656 per vCPU/hour
- Memory: $0.00511 per GB/hour
- Typical: ~3 min runtime = ~$0.01

#### EC2 t4g.medium (24/7 deployment)
- Fixed: ~$30/month (regardless of usage)
- Per report: Depends on volume

#### S3 Storage & Transfer
- Minimal (<$0.01 per report)

**Typical cost per report: ~$1.60** (varies by backend technology and diagram complexity)

**Note:** ECS Fargate costs ~$1.60/report, EC2 deployment costs ~$30/month + ~$1.58/report for Bedrock

## Frontend - Web Upload Interface

TRNDA includes a password-protected web interface for uploading diagrams.

### Features

- Password-protected access
- Camera capture on mobile devices
- Image rotation (90° per click)
- Client info metadata (max 1900 ASCII characters)
- Direct upload to S3
- HTTPS via CloudFront
- Serverless (S3 + Lambda + API Gateway + CloudFront)

### Architecture

```
Web Browser → CloudFront (HTTPS) → API Gateway → Lambda → S3
(password)    (CDN)                 (auth)        (upload)  (diagrams)
```

### Deployment

```bash
cd frontend/aws-deployment/terraform

# 1. Configure (copy example and set your values)
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars - set AWS profile, bucket names, password

# 2. Deploy
terraform init
terraform apply
```

**Output:** HTTPS URL via CloudFront

**Cost:** ~$1-2/month (CloudFront + S3, Lambda/API free tier)

### Configuration

All sensitive data is stored in `terraform/terraform.tfvars` (not committed to Git):
- AWS profile
- S3 bucket names
- Upload password

See `FRONTEND.md` for complete documentation.

## Technical Details

- **Model:** Claude 4.5 Sonnet + 1M context window
- **Framework:** Strands AI Agents
- **MCP Servers:** AWS Knowledge + Diagram + Pricing
- **Region:** eu-central-1
- **S3 Bucket:** your-trnda-s3-bucket (configure in code or Terraform)
- **Authentication:** AWS credentials (local) or IAM role (ECS)
- **SES Sender:** trnda@ai.aws.thetrasklab.com
- **Version:** v0.5

### Model Configuration

```python
bedrock_model = BedrockModel(
    model_id="eu.anthropic.claude-sonnet-4-5-20250929-v1:0",
    region_name="eu-central-1",
    additional_model_request_fields={
        "anthropic_beta": ["context-1m-2025-08-07"]  # 1M context
    }
)
```

## Cost Calculation

Agent calculates costs for **6 scenarios total**:
- **As-Is:** Low/Medium/High load
- **Well-Architected:** Low/Medium/High load
- **Comparison:** % differences between As-Is and Well-Architected

## Important Notes

- **Output in English** - professional documentation
- **Maximum 3-4 pages** - concise and to the point
- **Single-shot** - everything in one run
- **No verbose descriptions** - just component lists, diagrams, costs
- **S3 Support** - Both CLI and agent support S3 operations
- **Email Notifications** - Automatic PDF delivery when email provided

## Troubleshooting

### Pandoc error
```bash
# Linux
sudo apt-get install pandoc

# macOS
brew install pandoc
```

### AWS credentials
```bash
# Configure AWS credentials
aws configure

# Or use environment variables:
export AWS_PROFILE=your-profile
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
```

### MCP servers
```bash
uvx --version  # Verify installation
```

### S3 access
```bash
# Verify bucket access
aws s3 ls s3://your-trnda-s3-bucket/

# Upload test
aws s3 cp samples/sample1.jpg s3://your-trnda-s3-bucket/input/
```

### SES email verification
```bash
# Verify sender email
aws ses verify-email-identity --email-address trnda@ai.aws.thetrasklab.com --region eu-central-1

# Verify recipient email (for testing)
aws ses verify-email-identity --email-address your-email@example.com --region eu-central-1
```

---

**TRNDA** = **T**rask **R**učně **N**akreslí, **D**okončí **A**WS
