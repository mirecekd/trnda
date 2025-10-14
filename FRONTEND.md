# TRNDA Frontend - Super Simple Upload

One password, Lambda checks it, uploads to S3. That's it!

## Quick Start

```bash
cd aws-deployment/terraform
terraform init
terraform apply
```

Access at **HTTPS** URL in output (via CloudFront).  
Password: Configure in `terraform.tfvars` (see Deployment section)

## Architecture

```
HTML Page --> API Gateway --> Lambda --> S3
(password)     (CORS)        (check    (upload)
                             password)
```

**Components:**
- S3 Static Website (hosting HTML/CSS/JS)
- CloudFront CDN (HTTPS + global distribution)
- Lambda Function (password check + S3 upload)
- API Gateway (HTTPS API with CORS)

**Password:** Configured in terraform.tfvars and set as Lambda environment variable

**Cost:** ~$1-2/month (CloudFront + S3 + Lambda/API free tier)

## How It Works

1. Enter your configured password
2. Select/take photo
3. Rotate if needed
4. Add client info (optional)
5. Upload → Lambda checks password → uploads to S3

**No AWS credentials in JavaScript!** Only password sent to Lambda.

## Files

```
frontend/
├── index.html           # Page with password input
├── app.js               # JavaScript (template)
├── styles.css           # Styling
├── app-local.js         # Local testing
├── test-local.sh        # Test server
├── lambda/
│   └── upload.py        # Lambda (20 lines!)
└── aws-deployment/
    └── terraform/
        ├── main.tf
        ├── variables.tf
        ├── outputs.tf
        ├── terraform.tfvars.example
        └── templates/
            └── app.js.tpl
```

## Deployment

### 1. Create terraform.tfvars (REQUIRED)

```bash
cd aws-deployment/terraform
cp terraform.tfvars.example terraform.tfvars
```

**Edit terraform.tfvars and set your values:**
```hcl
upload_password = "YourSecurePasswordHere"

# Optional: Custom domain
# custom_domain = "trnda.ai.aws.thetrasklab.com"
# acm_certificate_arn = "arn:aws:acm:us-east-1:ACCOUNT:certificate/CERT_ID"
```

**Important:** 
- `terraform.tfvars` is in `.gitignore` and won't be committed to Git
- Custom domain requires ACM certificate in **us-east-1** region (CloudFront requirement)
- DNS CNAME record must point to CloudFront domain

### 2. Deploy

```bash
terraform init
terraform apply
```

Terraform creates everything and outputs website URL.

## Local Testing

```bash
./test-local.sh
```

Opens at http://localhost:8000 (simulated upload).

## Password Configuration

**Password is stored in `terraform.tfvars` (NOT in Git):**

1. Copy example: `cp terraform.tfvars.example terraform.tfvars`
2. Edit `terraform.tfvars` and set `upload_password`
3. Deploy: `terraform apply`

Lambda reads password from environment variable set by Terraform.

**Default in example:** `YourSecurePassword123`  
**Location:** `aws-deployment/terraform/terraform.tfvars` (protected by .gitignore)

## Usage

1. Enter password (set in terraform.tfvars)
2. Take/select photo
3. Rotate if needed (90° per click)
4. Add client info (optional, max 1900 chars)
5. Upload

Processing: 10-15 minutes
Report sent if email provided.

## What Gets Created

- S3 bucket: `trnda-frontend`
- CloudFront Distribution (HTTPS with CDN)
- Lambda: `trnda-upload`
- API Gateway: HTTPS API
- IAM role: Lambda execution + S3 upload permissions

## Cost

~$1-2/month:
- CloudFront: ~$1/month
- S3: ~$0.02
- Lambda: Free tier
- API Gateway: Free tier

## Security

- Password checked in Lambda (not visible in source)
- Lambda has only S3 upload permissions
- HTTPS via API Gateway
- No AWS credentials in browser

## Troubleshooting

### Wrong password
- Check your password in `terraform.tfvars`
- Case sensitive!

- Access key: Embedded in app.js

## Cleanup

```bash
cd aws-deployment/terraform
terraform destroy
```

**Note:** Manually delete IAM access key if needed.

## Version

**Frontend Version:** fe-v0.2
