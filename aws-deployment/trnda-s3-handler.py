#!/usr/bin/env python3
"""
TRNDA S3 Handler for ECS Fargate
Processes S3 upload events and runs TRNDA agent
"""

import os
import sys
import json
import boto3
import tempfile
import shutil
from datetime import datetime
from pathlib import Path

# Import the main TRNDA agent
sys.path.insert(0, '/app')

# Import directly from trnda-agent.py
import importlib.util
spec = importlib.util.spec_from_file_location("trnda_agent", "/app/trnda-agent.py")
trnda_agent_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trnda_agent_module)

# Get the functions we need
get_image_dimensions = trnda_agent_module.get_image_dimensions
compress_image_if_needed = trnda_agent_module.compress_image_if_needed
create_output_dir = trnda_agent_module.create_output_dir
build_system_prompt = trnda_agent_module.build_system_prompt
write_file = trnda_agent_module.write_file
convert_with_pandoc = trnda_agent_module.convert_with_pandoc


def get_s3_client():
    """Get S3 client with proper credentials"""
    return boto3.client('s3', region_name=os.environ.get('AWS_REGION', 'eu-central-1'))


def download_from_s3(bucket: str, key: str, local_path: str) -> str:
    """Download file from S3
    
    Args:
        bucket: S3 bucket name
        key: S3 object key
        local_path: Local path to save file
        
    Returns:
        Path to downloaded file
    """
    s3 = get_s3_client()
    print(f"[INFO] Downloading s3://{bucket}/{key} to {local_path}")
    
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    s3.download_file(bucket, key, local_path)
    
    print(f"[OK] Downloaded {local_path}")
    return local_path


def upload_to_s3(local_path: str, bucket: str, key: str):
    """Upload file to S3
    
    Args:
        local_path: Local file path
        bucket: S3 bucket name
        key: S3 object key
    """
    s3 = get_s3_client()
    print(f"[INFO] Uploading {local_path} to s3://{bucket}/{key}")
    
    s3.upload_file(local_path, bucket, key)
    print(f"[OK] Uploaded s3://{bucket}/{key}")


def upload_directory_to_s3(local_dir: str, bucket: str, s3_prefix: str):
    """Upload entire directory to S3
    
    Args:
        local_dir: Local directory path
        bucket: S3 bucket name
        s3_prefix: S3 prefix (folder)
    """
    s3 = get_s3_client()
    
    for root, dirs, files in os.walk(local_dir):
        for file in files:
            local_file = os.path.join(root, file)
            relative_path = os.path.relpath(local_file, local_dir)
            s3_key = f"{s3_prefix}/{relative_path}".replace('\\', '/')
            
            upload_to_s3(local_file, bucket, s3_key)


def extract_email_from_text(text: str) -> str:
    """Extract first email address from text using regex
    
    Args:
        text: Text that may contain an email address
        
    Returns:
        Email address if found, None otherwise
    """
    import re
    
    if not text:
        return None
    
    # Regex pattern for email addresses
    email_pattern = r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b'
    match = re.search(email_pattern, text)
    
    if match:
        return match.group(0)
    return None


def get_client_info_from_s3_metadata(bucket: str, key: str) -> tuple:
    """Get client information from S3 object metadata
    
    Args:
        bucket: S3 bucket name
        key: S3 object key
        
    Returns:
        Tuple of (client_info_text, extracted_email)
        Both can be None if not found
    """
    try:
        s3 = get_s3_client()
        response = s3.head_object(Bucket=bucket, Key=key)
        metadata = response.get('Metadata', {})
        
        # Try to get client-info from metadata
        client_info = metadata.get('client-info', '')
        
        if client_info:
            print(f"[INFO] Found client-info in S3 metadata: {client_info}")
            # Try to extract email from the client info
            extracted_email = extract_email_from_text(client_info)
            if extracted_email:
                print(f"[INFO] Extracted email from metadata: {extracted_email}")
            else:
                print(f"[INFO] No email found in metadata")
            return client_info, extracted_email
        
        return None, None
        
    except Exception as e:
        print(f"[WARNING] Could not read S3 metadata: {e}")
        return None, None


def process_s3_event(event: dict):
    """Process S3 event and run TRNDA
    
    Args:
        event: S3 event data (EventBridge or direct S3 notification)
    """
    print("=" * 70)
    print("TRNDA S3 Handler - ECS Fargate")
    print("=" * 70)
    
    # Parse event (can be EventBridge or direct S3 notification)
    if 'detail' in event:  # EventBridge format
        bucket = event['detail']['bucket']['name']
        key = event['detail']['object']['key']
    elif 'Records' in event:  # Direct S3 notification
        bucket = event['Records'][0]['s3']['bucket']['name']
        key = event['Records'][0]['s3']['object']['key']
    else:
        raise ValueError("Unknown event format")
    
    print(f"Bucket: {bucket}")
    print(f"Key: {key}")
    
    # Validate file extension
    if not key.lower().endswith(('.jpg', '.jpeg', '.png')):
        print(f"[SKIP] Not an image file: {key}")
        return
    
    # Get client info from S3 metadata
    client_info, extracted_email = get_client_info_from_s3_metadata(bucket, key)
    
    print(f"Client info: {client_info or 'Not specified'}")
    if extracted_email:
        print(f"Email for report: {extracted_email}")
    
    # Create temporary working directory
    with tempfile.TemporaryDirectory() as temp_dir:
        # Download image from S3
        filename = os.path.basename(key)
        local_image = os.path.join(temp_dir, filename)
        download_from_s3(bucket, key, local_image)
        
        # Run TRNDA agent by calling main processing logic directly
        print("=" * 70)
        print("[START] Running TRNDA agent...")
        print("=" * 70)
        
        # We'll call the trnda-agent.py's main logic by importing its core functions
        # and recreating the process
        # Pass client_info as client_name - it will be displayed in report header
        # If extracted_email exists, it will be used for sending the report
        output_dir = trnda_agent_module.process_image_standalone(
            local_image, 
            client_name=client_info,
            recipient_email=extracted_email
        )
        
        print("=" * 70)
        print(f"[COMPLETED] Output: {output_dir}")
        print("=" * 70)
        
        # Upload results back to S3
        # Structure: output/YYYYMMDDHHMMSS/design.pdf, etc.
        timestamp = os.path.basename(output_dir).replace('output_', '')
        s3_output_prefix = f"output/{timestamp}"
        
        print(f"[INFO] Uploading results to s3://{bucket}/{s3_output_prefix}/")
        upload_directory_to_s3(output_dir, bucket, s3_output_prefix)
        
        print("=" * 70)
        print(f"[SUCCESS] Results uploaded to: s3://{bucket}/{s3_output_prefix}/")
        print("   - design.md")
        print("   - design.pdf")
        print("   - generated-diagrams/diagram_as_is.png")
        print("   - generated-diagrams/diagram_well_architected.png")
        print("=" * 70)
        
        # Generate presigned URL for PDF
        try:
            pdf_key = f"{s3_output_prefix}/design.pdf"
            s3 = get_s3_client()
            pdf_url = s3.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucket, 'Key': pdf_key},
                ExpiresIn=86400  # 24 hours
            )
            print(f"[INFO] PDF URL (valid 24h): {pdf_url}")
        except Exception as e:
            print(f"[WARNING] Could not generate presigned URL: {e}")


def main():
    """Main entry point for ECS Fargate task"""
    
    # Get event data from environment variable
    event_json = os.environ.get('TRNDA_EVENT')
    
    if not event_json:
        print("[ERROR] TRNDA_EVENT environment variable not set")
        sys.exit(1)
    
    try:
        event = json.loads(event_json)
        process_s3_event(event)
        print("[EXIT] Success")
        sys.exit(0)
    except Exception as e:
        print(f"[ERROR] Failed to process event: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
