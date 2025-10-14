#!/usr/bin/env python3
"""
TRNDA - Trask Ručně Nakreslí, Dokončí AWS

Simple agent: image -> As-Is cost -> Well-Architected design -> cost comparison
Maximum 3-4 pages output.
"""

import os
import sys
import subprocess
import time
import tempfile
import shutil
from datetime import datetime
from strands import Agent
from strands.models import BedrockModel
from strands.agent.conversation_manager import SlidingWindowConversationManager
from strands_tools import image_reader
from strands.tools import tool
from mcp import stdio_client, StdioServerParameters
from mcp.client.streamable_http import streamablehttp_client
from strands.tools.mcp import MCPClient

# S3 Configuration
# Can be overridden via S3_BUCKET environment variable
DEFAULT_BUCKET = os.environ.get('S3_BUCKET', 'your-trnda-s3-bucket')
DEFAULT_REGION = "eu-central-1"

os.environ['BYPASS_TOOL_CONSENT'] = 'true'
os.environ["STRANDS_TOOL_CONSOLE_MODE"] = "enabled"
# AWS_PROFILE should be set by caller (CLI or environment)

# MCP Servers
aws_knowledge_mcp = MCPClient(
    lambda: streamablehttp_client("https://knowledge-mcp.global.api.aws")
)

aws_diagram_mcp = MCPClient(
    lambda: stdio_client(
        StdioServerParameters(
            command="uvx",
            args=["awslabs.aws-diagram-mcp-server"],
            env={
                "FASTMCP_LOG_LEVEL": "ERROR",
                "AWS_PROFILE": os.environ.get('AWS_PROFILE', 'default')
            }
        )
    )
)

aws_pricing_mcp = MCPClient(
    lambda: stdio_client(
        StdioServerParameters(
            command="uvx",
            args=["awslabs.aws-pricing-mcp-server@latest"],
            env={
                "AWS_REGION": "eu-central-1",
                "AWS_PROFILE": os.environ.get('AWS_PROFILE', 'default')
            }
        )
    )
)

# Bedrock Model with 1M context window
bedrock_model = BedrockModel(
    model_id="eu.anthropic.claude-sonnet-4-5-20250929-v1:0",
    region_name="eu-central-1",
    additional_request_fields={
        "anthropic_beta": ["context-1m-2025-08-07"]
    }
)


def get_s3_client(profile=None, region=None):
    """Get S3 client with proper credentials
    
    On EC2 with IAM role: uses instance profile automatically
    Locally: uses AWS_PROFILE environment variable or default profile
    """
    import boto3
    region = region or DEFAULT_REGION
    
    # Get profile from parameter or environment
    profile = profile or os.environ.get('AWS_PROFILE')
    
    # If profile is specified, use it; otherwise boto3 will use IAM role on EC2 or default credentials
    if profile:
        session = boto3.Session(profile_name=profile)
    else:
        session = boto3.Session()
    
    return session.client('s3', region_name=region)


def get_ses_client(profile=None, region=None):
    """Get SES client with proper credentials
    
    On EC2 with IAM role: uses instance profile automatically
    Locally: uses AWS_PROFILE environment variable or default profile
    """
    import boto3
    region = region or DEFAULT_REGION
    
    # Get profile from parameter or environment
    profile = profile or os.environ.get('AWS_PROFILE')
    
    # If profile is specified, use it; otherwise boto3 will use IAM role on EC2 or default credentials
    if profile:
        session = boto3.Session(profile_name=profile)
    else:
        session = boto3.Session()
    
    return session.client('ses', region_name=region)


def is_email(text: str) -> bool:
    """Check if text is an email address"""
    import re
    if not text:
        return False
    # Simple email regex
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(email_pattern, text.strip()))


def extract_email_from_text(text: str) -> str:
    """Extract email address from longer text
    
    Args:
        text: Text that may contain email address
        
    Returns:
        Extracted email or None if not found
    """
    import re
    if not text:
        return None
    
    # Find email pattern in text
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    match = re.search(email_pattern, text)
    
    if match:
        return match.group(0)
    return None


def send_report_email(pdf_path: str, recipient_email: str) -> bool:
    """Send report PDF via email using AWS SES
    
    Args:
        pdf_path: Path to PDF file
        recipient_email: Recipient email address (from --client)
        
    Returns:
        True if sent successfully, False otherwise
    """
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.mime.application import MIMEApplication
    from datetime import datetime
    
    SENDER = "trnda@ai.aws.thetrasklab.com"
    BCC_EMAIL = "mirdvorak@trask.cz"
    
    try:
        # Read PDF file
        with open(pdf_path, 'rb') as f:
            pdf_data = f.read()
        
        # Create message
        msg = MIMEMultipart()
        msg['Subject'] = 'TRNDA Report - AWS Architecture Design'
        msg['From'] = f'TRNDA Report <{SENDER}>'
        msg['To'] = recipient_email
        msg['Bcc'] = BCC_EMAIL
        
        # Email body
        body_text = f"""Hello,

Your AWS architecture report is ready and attached to this email.

Generated: {datetime.now().strftime("%d.%m.%Y %H:%M")}

---
Generated by TRNDA (Trask Ručně Nakreslí, Dokončí AWS)
Trask Solutions a.s.
"""
        
        # Attach body
        body = MIMEText(body_text, 'plain', 'utf-8')
        msg.attach(body)
        
        # Attach PDF
        pdf_attachment = MIMEApplication(pdf_data, _subtype='pdf')
        pdf_attachment.add_header('Content-Disposition', 'attachment', filename='trnda-report.pdf')
        msg.attach(pdf_attachment)
        
        # Send email
        ses = get_ses_client()
        
        print(f"[SES] Sending email to {recipient_email} (BCC: {BCC_EMAIL})")
        
        response = ses.send_raw_email(
            Source=SENDER,
            Destinations=[recipient_email, BCC_EMAIL],
            RawMessage={'Data': msg.as_string()}
        )
        
        print(f"[OK] Email sent successfully (MessageId: {response['MessageId']})")
        return True
        
    except Exception as e:
        print(f"[WARNING] Failed to send email: {e}")
        print(f"         Email notification skipped, but report was generated successfully")
        return False


def is_s3_path(path: str) -> bool:
    """Check if path is an S3 path"""
    return path.startswith('s3://')


def parse_s3_path(s3_path: str) -> tuple:
    """Parse S3 path into bucket and key
    
    Args:
        s3_path: S3 path in format s3://bucket/key
        
    Returns:
        Tuple of (bucket, key)
    """
    if not s3_path.startswith('s3://'):
        raise ValueError(f"Invalid S3 path: {s3_path}")
    
    path = s3_path[5:]  # Remove 's3://'
    parts = path.split('/', 1)
    
    if len(parts) == 1:
        return parts[0], ''
    return parts[0], parts[1]


def download_from_s3(s3_path: str, local_path: str) -> str:
    """Download file from S3
    
    Args:
        s3_path: S3 path (s3://bucket/key)
        local_path: Local path to save file
        
    Returns:
        Path to downloaded file
    """
    bucket, key = parse_s3_path(s3_path)
    
    # Add input/ prefix if not present and key doesn't start with it
    if key and not key.startswith('input/') and not key.startswith('output/'):
        key = f"input/{key}"
    
    print(f"[S3] Downloading s3://{bucket}/{key}")
    
    try:
        s3 = get_s3_client()
        os.makedirs(os.path.dirname(local_path) if os.path.dirname(local_path) else '.', exist_ok=True)
        s3.download_file(bucket, key, local_path)
        print(f"[OK] Downloaded to {local_path}")
        return local_path
    except Exception as e:
        print(f"[ERROR] Failed to download from S3: {e}")
        raise


def upload_directory_to_s3(local_dir: str, s3_bucket: str, s3_prefix: str) -> list:
    """Upload entire directory to S3
    
    Args:
        local_dir: Local directory path
        s3_bucket: S3 bucket name
        s3_prefix: S3 prefix (folder)
        
    Returns:
        List of uploaded S3 keys
    """
    s3 = get_s3_client()
    
    print(f"[S3] Uploading results to s3://{s3_bucket}/{s3_prefix}/")
    
    uploaded_files = []
    
    for root, dirs, files in os.walk(local_dir):
        for file in files:
            local_file = os.path.join(root, file)
            relative_path = os.path.relpath(local_file, local_dir)
            s3_key = f"{s3_prefix}/{relative_path}".replace('\\', '/')
            
            try:
                s3.upload_file(local_file, s3_bucket, s3_key)
                print(f"[OK] Uploaded s3://{s3_bucket}/{s3_key}")
                uploaded_files.append(s3_key)
            except Exception as e:
                print(f"[ERROR] Failed to upload {s3_key}: {e}")
    
    return uploaded_files


def get_image_dimensions(image_path: str) -> tuple:
    """Get image dimensions and aspect ratio.
    
    Args:
        image_path: Path to the image
        
    Returns:
        Tuple of (width, height, aspect_ratio, is_portrait)
    """
    try:
        from PIL import Image
        img = Image.open(image_path)
        width, height = img.size
        aspect_ratio = width / height
        is_portrait = height > width
        
        print(f"[INFO] Image dimensions: {width}x{height}, aspect_ratio={aspect_ratio:.2f}, {'PORTRAIT' if is_portrait else 'LANDSCAPE'}")
        
        return width, height, aspect_ratio, is_portrait
    except Exception as e:
        print(f"[WARNING] Could not get image dimensions: {e}")
        return None, None, 1.0, False


def compress_image_if_needed(image_path: str, max_size_mb: float = 4.0) -> str:
    """Compress image if it exceeds max size.
    
    Args:
        image_path: Path to the image
        max_size_mb: Maximum size in MB (default 4.0 to be safe under 5MB limit)
        
    Returns:
        Path to compressed image (or original if no compression needed)
    """
    try:
        from PIL import Image
        import io
        
        # Check current size
        current_size_mb = os.path.getsize(image_path) / (1024 * 1024)
        
        if current_size_mb <= max_size_mb:
            return image_path
        
        print(f"[INFO] Image is {current_size_mb:.1f}MB, compressing to under {max_size_mb}MB...")
        
        # Open image
        img = Image.open(image_path)
        
        # Convert RGBA to RGB if needed
        if img.mode == 'RGBA':
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])
            img = background
        elif img.mode not in ('RGB', 'L'):
            img = img.convert('RGB')
        
        # Create compressed version
        compressed_path = image_path.rsplit('.', 1)[0] + '_compressed.jpg'
        
        # Start with quality 85 and reduce if needed
        quality = 85
        while quality > 20:
            buffer = io.BytesIO()
            img.save(buffer, format='JPEG', quality=quality, optimize=True)
            size_mb = len(buffer.getvalue()) / (1024 * 1024)
            
            if size_mb <= max_size_mb:
                with open(compressed_path, 'wb') as f:
                    f.write(buffer.getvalue())
                print(f"[OK] Compressed to {size_mb:.1f}MB (quality={quality})")
                return compressed_path
            
            quality -= 5
        
        # If still too large, resize
        print("[INFO] Quality reduction not enough, resizing...")
        max_dimension = 2048
        img.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
        
        quality = 85
        while quality > 20:
            buffer = io.BytesIO()
            img.save(buffer, format='JPEG', quality=quality, optimize=True)
            size_mb = len(buffer.getvalue()) / (1024 * 1024)
            
            if size_mb <= max_size_mb:
                with open(compressed_path, 'wb') as f:
                    f.write(buffer.getvalue())
                print(f"[OK] Resized and compressed to {size_mb:.1f}MB (quality={quality})")
                return compressed_path
            
            quality -= 5
        
        # Last resort - save whatever we have
        img.save(compressed_path, format='JPEG', quality=20, optimize=True)
        final_size_mb = os.path.getsize(compressed_path) / (1024 * 1024)
        print(f"[WARNING] Best effort compression: {final_size_mb:.1f}MB")
        return compressed_path
        
    except Exception as e:
        print(f"[WARNING] Could not compress image: {e}")
        return image_path


@tool
def write_file(filepath: str, content: str) -> str:
    """Write content to a file.
    
    Args:
        filepath: Path to the file to write
        content: Content to write to the file
        
    Returns:
        Success message
    """
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return f"Successfully written to {filepath}"
    except Exception as e:
        return f"Error writing file: {e}"


@tool
def convert_with_pandoc(input_file: str, output_format: str) -> str:
    """Convert markdown file to PDF using pandoc with better spacing.
    
    Args:
        input_file: Path to markdown file
        output_format: Must be 'pdf'
        
    Returns:
        Success message
    """
    try:
        if output_format != 'pdf':
            return f"Error: format must be 'pdf', got '{output_format}'"
        
        output_file = input_file.replace('.md', f'.{output_format}')
        
        # Get directory of the markdown file
        working_dir = os.path.dirname(os.path.abspath(input_file))
        input_basename = os.path.basename(input_file)
        output_basename = os.path.basename(output_file)
        
        # Run pandoc from the directory where the markdown file is
        # This ensures relative image paths work correctly
        cmd = ['pandoc', input_basename, '-o', output_basename]
        
        # Add better spacing for PDF
        if output_format == 'pdf':
            # Create header file for fancy footer
            header_path = os.path.join(working_dir, 'header.tex')
            with open(header_path, 'w') as f:
                f.write(r'''\usepackage{fancyhdr}
\pagestyle{fancy}
\fancyhf{}
\fancyfoot[L]{Trask Solutions a.s.}
\fancyfoot[C]{\thepage}
\fancyfoot[R]{TRNDA report v0.5}
\renewcommand{\headrulewidth}{0pt}
\renewcommand{\footrulewidth}{0.4pt}
''')
            
            cmd.extend([
                '-V', 'geometry:margin=2cm',
                '-V', 'linestretch=1.1',
                '-V', 'fontsize=10pt',
                '-H', 'header.tex'
            ])
        
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True,
            cwd=working_dir
        )
        
        if result.returncode == 0:
            return f"Successfully converted to {output_file}"
        else:
            return f"Error: {result.stderr}"
            
    except Exception as e:
        return f"Error running pandoc: {e}"


def build_system_prompt():
    """Simple system prompt - max 3-4 pages output."""
    # Use consistent height-based sizing for all images (no adaptive sizing)
    input_image_size = r"height=0.7\textheight,keepaspectratio"
    
    return rf"""You are an AWS Solutions Architect. Create a CONCISE report (MAX 3-4 PAGES).

AVAILABLE TOOLS:
- image_reader: Analyze images
- AWS Diagram MCP: Generate AWS diagrams
- AWS Pricing MCP: Calculate costs
- write_file: Save content to files
- convert_with_pandoc: Convert markdown to PDF

WORKFLOW:

1. Use image_reader to analyze the hand-drawn diagram
2. Generate As-Is diagram (aws_diagram MCP)
3. Calculate As-Is costs (aws_pricing MCP) - 3 scenarios
4. Design Well-Architected version (LIST improvements only)
5. Generate Well-Architected diagram (aws_diagram MCP)
6. Calculate Well-Architected costs (aws_pricing MCP) - 3 scenarios
7. Compare costs (show percentage differences)
8. Use write_file to save markdown report to design.md

MARKDOWN TEMPLATE:

```markdown
# AWS Architecture Design - [Name]

**Analysis is made for:** [CLIENT_NAME - ONLY IF PROVIDED]
**Generated by:** TRNDA (Trask Ručně Nakreslí, Dokončí AWS)
**Date:** [Current date]  
**Region:** eu-central-1

---

## Original Hand-Drawn Design

**Original input diagram:**

\begin{{{{center}}}}
\includegraphics[{input_image_size}]{{{{diagram_input.png}}}}
\end{{{{center}}}}

\newpage

## 1. As-Is Architecture

**Components:** 

[List in bullet points]

&nbsp;

**As-Is Notes:**

[Include any notes, comments, or requirements found in the hand-drawn diagram in bullet points]

&nbsp;

**Monthly Costs:**

| Scenario | Cost |
|----------|------|
| Low | $XXX |
| Medium | $YYY |
| High | $ZZZ |

### Cost Breakdown (Low Scenario):

[Details in bullet points]

### Cost Breakdown (Medium Scenario):

[Details in bullet points]

### Cost Breakdown (High Scenario):

[Details in bullet points]

\newpage

**As-Is Architecture Diagram:**

\begin{{{{center}}}}
\includegraphics[height=0.7\textheight,keepaspectratio]{{{{generated-diagrams/diagram_as_is.png}}}}
\end{{{{center}}}}

\newpage

## 2. Well-Architected Design

**Improvements:**
[List in bullet points]

&nbsp;

**Monthly Costs:**

| Scenario | As-Is | Well-Architected | Difference |
|----------|-------|------------------|------------|
| Low | $XXX | $AAA | +$BBB (+X%) |
| Medium | $YYY | $CCC | +$DDD (+Y%) |
| High | $ZZZ | $EEE | +$FFF (+Z%) |

**Key Benefits:**
[List in bullet points]

\newpage

**Well-Architected Design Diagram:**

\begin{{{{center}}}}
\includegraphics[height=0.7\textheight,keepaspectratio]{{{{generated-diagrams/diagram_well_architected.png}}}}
\end{{{{center}}}}

```

CRITICAL REQUIREMENTS:
- MAX 3-4 pages total
- NO verbose descriptions  
- NO UTF-8 special characters (no checkmarks, no emojis, no fancy bullets)
- You MUST use write_file tool to save the markdown
- You MUST use convert_with_pandoc tool to create PDF
- Region: eu-central-1
- Do NOT just print the content - SAVE IT using write_file tool!"""


def calculate_complete_cost(input_tokens: int, output_tokens: int, runtime_minutes: float = 15.0) -> dict:
    """Calculate complete AWS costs for TRNDA report generation.
    
    Args:
        input_tokens: Number of input tokens used
        output_tokens: Number of output tokens used
        runtime_minutes: Estimated runtime in minutes (default 15 min)
        
    Returns:
        Dictionary with cost breakdown
    """
    # Bedrock Claude 4.5 Sonnet pricing (eu-central-1)
    # Input: $3 per 1M tokens, Output: $15 per 1M tokens
    bedrock_input_cost = (input_tokens / 1_000_000) * 3.0
    bedrock_output_cost = (output_tokens / 1_000_000) * 15.0
    bedrock_total = bedrock_input_cost + bedrock_output_cost
    
    # ECS Fargate pricing (eu-central-1) - 2 vCPU, 4 GB RAM
    # vCPU: $0.04656 per vCPU per hour
    # Memory: $0.00511 per GB per hour
    vcpu_cost_per_hour = 0.04656 * 2  # 2 vCPU
    memory_cost_per_hour = 0.00511 * 4  # 4 GB
    ecs_cost_per_hour = vcpu_cost_per_hour + memory_cost_per_hour
    ecs_total = ecs_cost_per_hour * (runtime_minutes / 60.0)
    
    # S3 costs (minimal for this use case)
    # Storage: $0.023 per GB/month (assume 10 MB output = 0.01 GB)
    # PUT requests: $0.005 per 1000 requests (assume 5 PUT requests)
    # GET requests: $0.0004 per 1000 requests (assume 5 GET requests)
    s3_storage = 0.023 * 0.01 / 30  # Daily cost for 10 MB
    s3_put = 0.005 * (5 / 1000)
    s3_get = 0.0004 * (5 / 1000)
    s3_total = s3_storage + s3_put + s3_get
    
    # Total cost
    total = bedrock_total + ecs_total + s3_total
    
    return {
        'bedrock': bedrock_total,
        'bedrock_input': bedrock_input_cost,
        'bedrock_output': bedrock_output_cost,
        'ecs': ecs_total,
        'ecs_vcpu': vcpu_cost_per_hour * (runtime_minutes / 60.0),
        'ecs_memory': memory_cost_per_hour * (runtime_minutes / 60.0),
        's3': s3_total,
        's3_storage': s3_storage,
        's3_put': s3_put,
        's3_get': s3_get,
        'total': total,
        'runtime_minutes': runtime_minutes
    }


def save_cost_breakdown(output_dir: str, cost_breakdown: dict, usage, start_datetime, end_datetime, elapsed_str) -> None:
    """Save detailed cost breakdown to cost.md file.
    
    Args:
        output_dir: Output directory path
        cost_breakdown: Cost breakdown dictionary
        usage: Token usage object
        start_datetime: Start time as datetime object
        end_datetime: End time as datetime object
        elapsed_str: Elapsed time as formatted string (MM:SS)
    """
    cost_file = os.path.join(output_dir, 'cost.md')
    
    content = f"""# TRNDA Generation Cost Breakdown

**Generated:** {datetime.now().strftime("%B %d, %Y at %H:%M:%S")}  
**Region:** eu-central-1  
**Runtime:** {elapsed_str} (MM:SS)

---

## Execution Timeline

| Event | Time |
|-------|------|
| Start | {start_datetime.strftime("%H:%M:%S")} |
| End | {end_datetime.strftime("%H:%M:%S")} |
| **Duration** | **{elapsed_str}** |

---

## Summary

| Component | Cost (USD) |
|-----------|------------|
| **Bedrock (Claude 4.5 Sonnet)** | **${cost_breakdown['bedrock']:.4f}** |
| **ECS Fargate Compute** | **${cost_breakdown['ecs']:.4f}** |
| **S3 Storage & Transfer** | **${cost_breakdown['s3']:.6f}** |
| **TOTAL** | **${cost_breakdown['total']:.4f}** |

---

## Detailed Breakdown

### 1. Amazon Bedrock - Claude 4.5 Sonnet

**Model:** `eu.anthropic.claude-sonnet-4-5-20250929-v1:0`  
**Region:** eu-central-1

| Metric | Usage | Rate | Cost |
|--------|-------|------|------|
| Input tokens | {usage.input_tokens:,} | $3.00 per 1M | ${cost_breakdown['bedrock_input']:.4f} |
| Output tokens | {usage.output_tokens:,} | $15.00 per 1M | ${cost_breakdown['bedrock_output']:.4f} |
| **Bedrock Total** | **{usage.input_tokens + usage.output_tokens:,}** | | **${cost_breakdown['bedrock']:.4f}** |

### 2. Amazon ECS Fargate

**Configuration:** 2 vCPU, 4 GB RAM  
**Runtime:** ~{cost_breakdown['runtime_minutes']:.1f} minutes

| Resource | Usage | Rate (per hour) | Cost |
|----------|-------|-----------------|------|
| vCPU (2x) | {cost_breakdown['runtime_minutes']:.1f} min | $0.04656/vCPU | ${cost_breakdown['ecs_vcpu']:.4f} |
| Memory (4 GB) | {cost_breakdown['runtime_minutes']:.1f} min | $0.00511/GB | ${cost_breakdown['ecs_memory']:.4f} |
| **ECS Total** | | | **${cost_breakdown['ecs']:.4f}** |

### 3. Amazon S3

**Usage:** Input image upload, output files storage

| Operation | Volume | Rate | Cost |
|-----------|--------|------|------|
| Storage (daily) | ~10 MB | $0.023/GB/month | ${cost_breakdown['s3_storage']:.6f} |
| PUT requests | ~5 requests | $0.005/1000 | ${cost_breakdown['s3_put']:.6f} |
| GET requests | ~5 requests | $0.0004/1000 | ${cost_breakdown['s3_get']:.6f} |
| **S3 Total** | | | **${cost_breakdown['s3']:.6f}** |

---

## Cost Optimization Notes

### Current Configuration
- **ECS:** 2 vCPU, 4 GB RAM - optimal for typical workloads
- **Runtime:** ~{cost_breakdown['runtime_minutes']:.0f} minutes average
- **Bedrock:** Claude 4.5 Sonnet with 1M context window

### Optimization Opportunities
1. **Reduce token usage:**
   - Optimize prompts and system instructions
   - Use smaller context windows where possible
   - Cache frequently used prompts

2. **Adjust ECS resources:**
   - Consider 1 vCPU, 2 GB for smaller diagrams
   - Current: 2 vCPU, 4 GB is good for complex diagrams

3. **Batch processing:**
   - Process multiple diagrams in one session
   - Amortize ECS startup costs

### Monthly Cost Estimates

Assuming 100 reports per month:

| Volume | Bedrock | ECS | S3 | **Total** |
|--------|---------|-----|----|-----------| 
| 10 reports | ${cost_breakdown['bedrock'] * 10:.2f} | ${cost_breakdown['ecs'] * 10:.2f} | ${cost_breakdown['s3'] * 10:.2f} | **${cost_breakdown['total'] * 10:.2f}** |
| 50 reports | ${cost_breakdown['bedrock'] * 50:.2f} | ${cost_breakdown['ecs'] * 50:.2f} | ${cost_breakdown['s3'] * 50:.2f} | **${cost_breakdown['total'] * 50:.2f}** |
| 100 reports | ${cost_breakdown['bedrock'] * 100:.2f} | ${cost_breakdown['ecs'] * 100:.2f} | ${cost_breakdown['s3'] * 100:.2f} | **${cost_breakdown['total'] * 100:.2f}** |
| 200 reports | ${cost_breakdown['bedrock'] * 200:.2f} | ${cost_breakdown['ecs'] * 200:.2f} | ${cost_breakdown['s3'] * 200:.2f} | **${cost_breakdown['total'] * 200:.2f}** |

---

## Pricing References

- **Bedrock Pricing:** https://aws.amazon.com/bedrock/pricing/
- **ECS Fargate Pricing:** https://aws.amazon.com/fargate/pricing/
- **S3 Pricing:** https://aws.amazon.com/s3/pricing/

**Note:** Prices are for eu-central-1 region and subject to change. Always verify current pricing.
"""
    
    try:
        with open(cost_file, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"[OK] Cost breakdown saved to {cost_file}")
    except Exception as e:
        print(f"[WARNING] Could not save cost breakdown: {e}")


def create_output_dir():
    """Create timestamped output directory."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    output_dir = f"output_{timestamp}"
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(f"{output_dir}/generated-diagrams", exist_ok=True)
    return output_dir


def process_image_standalone(image_path: str, client_name: str = None, recipient_email: str = None) -> str:
    """Standalone function for processing images - used by CLI and S3 handler.
    
    Supports both local paths and S3 paths (s3://bucket/key or just filename).
    For S3 paths, downloads input, processes locally, and uploads output.
    
    Args:
        image_path: Local path, S3 URI (s3://bucket/key), or short name (sample1.jpg)
        client_name: Optional client/project name (displayed in report header)
        recipient_email: Optional email address for sending report (overrides auto-detection from client_name)
        
    Returns:
        Output location (local directory or S3 path)
    """
    # Store original sys.argv
    original_argv = sys.argv.copy()
    
    # Detect S3 path and handle accordingly
    is_s3 = is_s3_path(image_path)
    
    # If just a filename without path, treat as S3
    if not is_s3 and not os.path.exists(image_path) and '/' not in image_path:
        # Short name like "sample1.jpg" -> convert to S3 path
        image_path = f"s3://{DEFAULT_BUCKET}/input/{image_path}"
        is_s3 = True
        print(f"[INFO] Treating as S3 path: {image_path}")
    
    # Handle S3 path
    if is_s3:
        print("=" * 70)
        print("S3 MODE: Downloading from S3, processing, uploading results")
        print("=" * 70)
        
        # Parse S3 path
        s3_bucket, s3_key = parse_s3_path(image_path)
        
        # Create temporary directory for S3 download/processing
        with tempfile.TemporaryDirectory() as temp_dir:
            # Download from S3
            filename = os.path.basename(s3_key) if s3_key else 'image.jpg'
            local_image = os.path.join(temp_dir, filename)
            
            try:
                download_from_s3(image_path, local_image)
            except Exception as e:
                raise FileNotFoundError(f"Failed to download from S3: {e}")
            
            # Process locally (reuse rest of the function)
            output_dir = _process_image_local(local_image, client_name, recipient_email)
            
            # Determine S3 output path - always just output/timestamp
            timestamp = os.path.basename(output_dir).replace('output_', '')
            s3_output_prefix = f"output/{timestamp}"
            
            # Upload results to S3
            print()
            print("=" * 70)
            print("[S3] Uploading results to S3...")
            print("=" * 70)
            uploaded_files = upload_directory_to_s3(output_dir, s3_bucket, s3_output_prefix)
            
            print()
            print("=" * 70)
            print(f"[SUCCESS] Results uploaded to S3")
            print("=" * 70)
            print(f"S3 Location: s3://{s3_bucket}/{s3_output_prefix}/")
            print()
            print("Files uploaded:")
            for file_key in uploaded_files:
                print(f"  - {file_key}")
            print("=" * 70)
            
            return f"s3://{s3_bucket}/{s3_output_prefix}/"
    
    # Local file processing
    # Temporarily set sys.argv for main()
    sys.argv = ['trnda-agent.py', image_path]
    if client_name:
        sys.argv.append(client_name)
    
    try:
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")
        
        output_dir = _process_image_local(image_path, client_name)
        return output_dir
        
    finally:
        # Restore original sys.argv
        sys.argv = original_argv


def _process_image_local(image_path: str, client_name: str = None, recipient_email: str = None) -> str:
    """Internal function to process image locally.
    
    Args:
        image_path: Local path to image
        client_name: Optional client name
        recipient_email: Optional email address for sending report
        
    Returns:
        Local output directory path
    """
    # Get image dimensions for adaptive sizing
    width, height, aspect_ratio, is_portrait = get_image_dimensions(image_path)
    
    # Compress image if needed (Bedrock has 5MB limit)
    # Use 3.5 MB max to have safe buffer for base64 encoding overhead
    processed_image_path = compress_image_if_needed(image_path, max_size_mb=3.5)
    
    output_dir = create_output_dir()
    
    # Copy image to output directory
    try:
        input_img_dest = f"{output_dir}/diagram_input.png"
        shutil.copy2(processed_image_path, input_img_dest)
        print(f"[OK] Input image copied to {input_img_dest}")
    except Exception as e:
        print(f"[WARNING] Could not copy input image: {e}")
    
    print("=" * 70)
    print("TRNDA - Trask Ručně Nakreslí, Dokončí AWS")
    print("=" * 70)
    print(f"Output: {output_dir}")
    print(f"Image: {processed_image_path}")
    print(f"Model: Claude 4.5 Sonnet (1M context)")
    print("=" * 70)
    print()
    
    with aws_knowledge_mcp, aws_diagram_mcp, aws_pricing_mcp:
        tools = (
            aws_knowledge_mcp.list_tools_sync() +
            aws_diagram_mcp.list_tools_sync() +
            aws_pricing_mcp.list_tools_sync()
        )
        
        print(f"[OK] Loaded {len(tools)} MCP tools")
        
        # Add custom tools
        all_tools = tools + [image_reader, write_file, convert_with_pandoc]
        
        agent = Agent(
            model=bedrock_model,
            system_prompt=build_system_prompt(),
            tools=all_tools,
            conversation_manager=SlidingWindowConversationManager()
        )
        
        print("[OK] Agent initialized")
        print("[START] Processing...")
        print()
        
        # Start timing
        start_time = time.time()
        start_datetime = datetime.now()
        
        # Get absolute path to output directory
        abs_output_dir = os.path.abspath(output_dir)
        
        # Build client name instruction
        client_instruction = f"\nCLIENT/PROJECT NAME: {client_name}\n- INCLUDE in header: **Analysis is made for:** {client_name}" if client_name else "\nCLIENT/PROJECT NAME: NOT PROVIDED\n- SKIP the 'Analysis is made for:' line in header"
        
        # Get current date
        current_date = datetime.now().strftime("%B %d, %Y")
        
        prompt = f"""Create AWS architecture report (MAX 3-4 pages):

IMAGE: {input_img_dest}
OUTPUT DIR: {abs_output_dir}
INPUT IMAGE: {input_img_dest} (ALREADY SAVED){client_instruction}
CURRENT DATE: {current_date} - USE THIS EXACT DATE in the report header

CRITICAL - DIAGRAM PATHS (must match markdown template):
- Input diagram (already saved): {abs_output_dir}/diagram_input.png
- As-Is diagram: {abs_output_dir}/generated-diagrams/diagram_as_is.png
- Well-Architected diagram: {abs_output_dir}/generated-diagrams/diagram_well_architected.png
- Markdown file: {abs_output_dir}/design.md

IMPORTANT: Diagramy MUSÍ být uloženy do generated-diagrams/ podsložky!

STEPS:
1. Use image_reader: analyze {abs_output_dir}/diagram_input.png - LOOK FOR ANY notes, comments, requirements
2. Generate As-Is diagram -> SAVE TO: {abs_output_dir}/generated-diagrams/diagram_as_is.png
   - IMPORTANT: Use EXACT number of resources from image (if image shows 1 EC2, use 1 EC2, even if it makes no sense)
   - As-Is means EXACTLY as drawn, no additions
3. Calculate As-Is costs (low/medium/high)
4. Design Well-Architected (list improvements only)
5. Generate Well-Architected diagram -> SAVE TO: {abs_output_dir}/generated-diagrams/diagram_well_architected.png
6. Calculate Well-Architected costs (low/medium/high)
7. Compare costs (% differences)
8. Use write_file: save markdown to {abs_output_dir}/design.md
   - Include "Original Hand-Drawn Design" with diagram_input.png
   - Include "As-Is Notes" with any notes found

AS-IS COST EXAMPLE SCENARIOS (assume based on predicted traffic/size/app):
- LOW: 1 Availability Zone, 1 EC2 Graviton (t4g.micro - ARM-based, cheapest), 1 RDS Single-AZ Graviton (db.t4g.micro)
- MEDIUM: 1 AZ, 2 EC2 instances (t3.micro - x86), 1 RDS Single-AZ (db.t3.micro)
- HIGH: 1 AZ, 4 EC2 instances (t3.small - x86), 1 RDS Single-AZ (db.t3.small - larger instance)

IMPORTANT:
- Keep report SHORT (3-4 pages max)
- NO UTF-8 special fancy characters (like icons)
- MUST include diagram_input.png in markdown (it's already saved!)
- If any service is unclear, choose a reasonable AWS service
- MUST use write_file to save design.md (NO PDF generation, just markdown!)
- Region: eu-central-1"""
        
        try:
            response = agent(prompt=prompt)
            
            # End timing
            end_time = time.time()
            end_datetime = datetime.now()
            
            # Calculate elapsed time
            elapsed_seconds = end_time - start_time
            elapsed_minutes = int(elapsed_seconds // 60)
            elapsed_secs = int(elapsed_seconds % 60)
            elapsed_str = f"{elapsed_minutes:02d}:{elapsed_secs:02d}"
            runtime_minutes = elapsed_seconds / 60.0
            
            print()
            print("=" * 70)
            print("[COMPLETED] Report generation finished")
            print("=" * 70)
            print(f"Runtime: {elapsed_str} (MM:SS)")
            print("=" * 70)
            
            # Calculate and log complete costs - tokeny jsou v response.metrics.accumulated_usage
            cost_breakdown = None
            
            # Get usage from metrics.accumulated_usage (not response.usage)
            usage_data = None
            if hasattr(response, 'metrics') and hasattr(response.metrics, 'accumulated_usage'):
                acc_usage = response.metrics.accumulated_usage
                # Create usage object with expected attributes
                class Usage:
                    def __init__(self, input_tokens, output_tokens):
                        self.input_tokens = input_tokens
                        self.output_tokens = output_tokens
                
                usage_data = Usage(
                    acc_usage.get('inputTokens', 0),
                    acc_usage.get('outputTokens', 0)
                )
            
            if usage_data:
                print()
                print("TOKEN USAGE STATISTICS:")
                print("-" * 70)
                
                # Input tokens
                print(f"Input tokens:  {usage_data.input_tokens:,}")
                
                # Output tokens
                print(f"Output tokens: {usage_data.output_tokens:,}")
                
                # Total tokens
                total_tokens = usage_data.input_tokens + usage_data.output_tokens
                print(f"Total tokens:  {total_tokens:,}")
                
                # Cost estimation (approximate for Claude Sonnet 4.5)
                # Input: $3 per 1M tokens, Output: $15 per 1M tokens
                input_cost = (usage_data.input_tokens / 1_000_000) * 3.0
                output_cost = (usage_data.output_tokens / 1_000_000) * 15.0
                bedrock_cost = input_cost + output_cost
                print(f"Bedrock cost:   ${bedrock_cost:.4f}")
                
                # Calculate complete AWS costs using actual runtime
                cost_breakdown = calculate_complete_cost(usage_data.input_tokens, usage_data.output_tokens, runtime_minutes)
                
                print()
                print("COMPLETE AWS COST BREAKDOWN:")
                print("-" * 70)
                print(f"Runtime:               {elapsed_str} ({runtime_minutes:.2f} min)")
                print(f"Bedrock (Claude 4.5):  ${cost_breakdown['bedrock']:.4f}")
                print(f"ECS Fargate compute:   ${cost_breakdown['ecs']:.4f}")
                print(f"S3 storage & transfer: ${cost_breakdown['s3']:.4f}")
                print(f"{'─' * 70}")
                print(f"TOTAL COST FOR REPORT GENERATION: ${cost_breakdown['total']:.4f}")
                print("-" * 70)
                
                # Save cost breakdown to file
                save_cost_breakdown(abs_output_dir, cost_breakdown, usage_data, start_datetime, end_datetime, elapsed_str)
                
                print("-" * 70)
            
            # POST-PROCESSING: Add runtime info and generate PDF
            print()
            print("[POST-PROCESSING] Adding runtime info and generating PDF...")
            try:
                design_md_path = os.path.join(abs_output_dir, 'design.md')
                if os.path.exists(design_md_path):
                    with open(design_md_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Find the header section and add runtime info after "Region:"
                    lines = content.split('\n')
                    new_lines = []
                    for i, line in enumerate(lines):
                        new_lines.append(line)
                        if line.startswith('**Region:**'):
                            # Add runtime info after Region line
                            new_lines.append(f'**Generation time:** {elapsed_str} (MM:SS)  ')
                            if cost_breakdown:
                                new_lines.append(f'**Total cost for report generation:** ${cost_breakdown["total"]:.4f}')
                            else:
                                new_lines.append(f'**Total cost for report generation:** N/A (usage data not available)')
                    
                    # Write back
                    with open(design_md_path, 'w', encoding='utf-8') as f:
                        f.write('\n'.join(new_lines))
                    
                    print(f"[OK] Added runtime info to design.md")
                    
                    # Create header.tex for pandoc
                    header_tex_path = os.path.join(abs_output_dir, 'header.tex')
                    with open(header_tex_path, 'w') as f:
                        f.write(r'''\usepackage{graphicx}
\usepackage{fancyhdr}
\pagestyle{fancy}
\fancyhf{}
\fancyfoot[L]{Trask Solutions a.s.}
\fancyfoot[C]{\thepage}
\fancyfoot[R]{TRNDA report v0.5}
\renewcommand{\headrulewidth}{0pt}
\renewcommand{\footrulewidth}{0.4pt}
''')
                    
                    # Generate PDF with updated markdown
                    print(f"[START] Generating PDF...")
                    try:
                        result = subprocess.run(
                            ['pandoc', 'design.md', '-o', 'design.pdf',
                             '-V', 'geometry:margin=2cm',
                             '-V', 'linestretch=1.1',
                             '-V', 'fontsize=10pt',
                             '-H', 'header.tex'],
                            capture_output=True,
                            text=True,
                            cwd=abs_output_dir
                        )
                        if result.returncode == 0:
                            print(f"[OK] PDF generated successfully: {abs_output_dir}/design.pdf")
                            
                            # Determine email address for sending report
                            # Priority 1: Use recipient_email if provided
                            # Priority 2: Check if client_name is a clean email address
                            # Priority 3: Try to extract email from client_name text
                            email_to_send = recipient_email
                            if not email_to_send and client_name:
                                if is_email(client_name):
                                    # Clean email address
                                    email_to_send = client_name
                                else:
                                    # Try to extract email from longer text
                                    extracted = extract_email_from_text(client_name)
                                    if extracted:
                                        email_to_send = extracted
                                        print(f"[INFO] Extracted email from client info: {email_to_send}")
                            
                            if email_to_send:
                                print()
                                print("=" * 70)
                                print(f"[EMAIL] Sending report to: {email_to_send}")
                                print("=" * 70)
                                pdf_path = os.path.join(abs_output_dir, 'design.pdf')
                                send_report_email(pdf_path, email_to_send)
                                print("=" * 70)
                        else:
                            print(f"[ERROR] PDF generation failed: {result.stderr}")
                    except Exception as e:
                        print(f"[ERROR] Could not generate PDF: {e}")
                else:
                    print(f"[WARNING] design.md not found, skipping PDF generation")
            except Exception as e:
                print(f"[ERROR] Post-processing failed: {e}")
                import traceback
                traceback.print_exc()
            
            return output_dir
            
        except Exception as e:
            raise


def main():
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
    else:
        image_path = "samples/mirek_art1.jpg"
        print(f"[WARNING] Using default: {image_path}")
    
    # Optional second argument for client/project name
    client_name = sys.argv[2] if len(sys.argv) > 2 else None
    
    try:
        output_dir = process_image_standalone(image_path, client_name)
        print(f"Check {output_dir}/ for files:")
        print(f"   - design.md")
        print(f"   - design.pdf")
        print(f"   - generated-diagrams/diagram_as_is.png")
        print(f"   - generated-diagrams/diagram_well_architected.png")
        print("=" * 70)
        
    except FileNotFoundError as e:
        print(f"[ERROR] {e}")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
