# TRNDA Backend - API Reference for Frontend

## Overview

TRNDA backend runs on AWS infrastructure and processes hand-drawn AWS diagrams using Claude 4.5 Sonnet.

**Supported deployment variants:**
- EC2 Standalone (production)
- ECS Fargate (scalable variant)

---

## S3 API - Diagram Upload

### Endpoint
```
S3 Bucket: your-trnda-s3-bucket
Region: eu-central-1
```

### Upload with AWS CLI

```bash
aws s3 cp diagram.jpg s3://your-trnda-s3-bucket/input/ \
    --metadata '{"client-info":"Client Name or Email"}' \
    --profile your-profile
```

### Upload with boto3 (Python)

```python
import boto3

s3 = boto3.client('s3', region_name='eu-central-1')

s3.upload_file(
    'diagram.jpg',
    'your-trnda-s3-bucket',
    'input/diagram.jpg',
    ExtraArgs={
        'Metadata': {
            'client-info': 'client@example.com'  # Optional
        }
    }
)
```

### Upload with JavaScript (AWS SDK v3)

```javascript
import { S3Client, PutObjectCommand } from "@aws-sdk/client-s3";
import { readFileSync } from 'fs';

const s3Client = new S3Client({ region: "eu-central-1" });

const fileContent = readFileSync('diagram.jpg');

await s3Client.send(new PutObjectCommand({
  Bucket: "your-trnda-s3-bucket",
  Key: "input/diagram.jpg",
  Body: fileContent,
  Metadata: {
    'client-info': 'client@example.com'  // Optional
  }
}));
```

---

## Custom Metadata

### client-info metadata

**Purpose:** Client/project identification for which the diagram is created

**Format:**
- Email: `client@example.com`
- Name: `Company Name`
- Project ID: `project-12345`

**Limitations:**
- Maximum size: **~1900 characters** (safe limit)
- AWS limit for all custom metadata: 2 KB
- If you exceed the limit: AWS returns `MetadataTooLarge` error

**Example:**
```bash
--metadata '{"client-info":"client@example.com"}'
```

**Email automatically triggers report sending:**
- If `client-info` is a valid email, the report will be automatically sent
- CC: mirdvorak@trask.cz
- From: trnda@ai.aws.thetrasklab.com

---

## Pipeline Flow

```
1. Upload to S3 (input/ folder)
   ↓
2. EventBridge trigger
   ↓
3. Lambda starts processing
   ↓
4. EC2/ECS processes diagram (10-15 min)
   ↓
5. Output to S3 (output/ folder)
   ↓
6. Email with report (if client-info is email)
```

---

## Output Files

After processing completes, files are created in `s3://your-trnda-s3-bucket/output/{timestamp}/`:

### Files:

1. **design.pdf** - Main output report (3-4 pages)
   - As-Is architecture
   - Well-Architected design
   - Cost comparison (3 scenarios)

2. **design.md** - Markdown version of the report

3. **cost.md** - Detailed cost breakdown
