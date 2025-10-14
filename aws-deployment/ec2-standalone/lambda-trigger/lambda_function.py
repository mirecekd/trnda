"""
Lambda Function - TRNDA SSM Trigger
Triggered by S3 upload via EventBridge, runs SSM command on EC2
"""

import json
import boto3
import os

ssm = boto3.client('ssm')
s3 = boto3.client('s3')

# Environment variables from Terraform
INSTANCE_ID = os.environ['INSTANCE_ID']
WORKING_DIR = os.environ['WORKING_DIRECTORY']
S3_BUCKET = os.environ['S3_BUCKET']


def get_client_info_from_metadata(bucket, key):
    """
    Get client info from S3 object metadata
    
    Args:
        bucket: S3 bucket name
        key: S3 object key
        
    Returns:
        Client info string or None
    """
    try:
        response = s3.head_object(Bucket=bucket, Key=key)
        metadata = response.get('Metadata', {})
        client_info = metadata.get('client-info', '')
        
        if client_info:
            print(f"Found client-info in metadata: {client_info}")
            return client_info
        
        return None
        
    except Exception as e:
        print(f"WARNING: Could not read metadata: {e}")
        return None


def lambda_handler(event, context):
    """
    Lambda handler triggered by S3 upload via EventBridge
    
    Args:
        event: EventBridge event with S3 details
        context: Lambda context
        
    Returns:
        Response with SSM command ID
    """
    
    print(f"Received event: {json.dumps(event)}")
    
    # Extract S3 information from EventBridge event
    try:
        bucket = event['detail']['bucket']['name']
        key = event['detail']['object']['key']
    except KeyError as e:
        print(f"ERROR: Invalid event structure: {e}")
        return {
            'statusCode': 400,
            'body': json.dumps(f'Invalid event structure: {e}')
        }
    
    # Validate file extension
    if not key.lower().endswith(('.jpg', '.jpeg', '.png')):
        print(f"SKIP: Not an image file: {key}")
        return {
            'statusCode': 200,
            'body': json.dumps(f'Skipped non-image file: {key}')
        }
    
    # Skip if file is in output/ folder
    if key.startswith('output/'):
        print(f"SKIP: File in output folder: {key}")
        return {
            'statusCode': 200,
            'body': json.dumps(f'Skipped output file: {key}')
        }
    
    print(f"Processing: s3://{bucket}/{key}")
    
    # Get client info from S3 metadata
    client_info = get_client_info_from_metadata(bucket, key)
    
    # Construct S3 path
    s3_path = f"s3://{bucket}/{key}"
    
    # Build CLI command with proper escaping for nested bash -c
    if client_info:
        # Escape for nested bash -c: replace " with \"
        escaped_client_info = client_info.replace('"', '\\"')
        cli_command = f'python3 trnda-cli.py \\"{s3_path}\\" --client \\"{escaped_client_info}\\"'
    else:
        cli_command = f'python3 trnda-cli.py \\"{s3_path}\\"'
    
    # SSM Run Command
    try:
        response = ssm.send_command(
            InstanceIds=[INSTANCE_ID],
            DocumentName='AWS-RunShellScript',
            Comment=f'TRNDA processing: {key}',
            Parameters={
                'commands': [
                    f'#!/bin/bash',
                    f'cd {WORKING_DIR}',
                    # Set PATH to include .local/bin and .cargo/bin for uvx and pip-installed tools
                    f'export PATH="/home/ubuntu/.local/bin:/home/ubuntu/.cargo/bin:$PATH"',
                    # Set S3_BUCKET environment variable
                    f'export S3_BUCKET="{S3_BUCKET}"',
                    f'sudo -u ubuntu -E bash -c "export PATH=/home/ubuntu/.local/bin:/home/ubuntu/.cargo/bin:$PATH && export S3_BUCKET={S3_BUCKET} && cd {WORKING_DIR} && {cli_command} 2>&1 | tee logs/trnda-{context.aws_request_id}.log"'
                ],
                'workingDirectory': [WORKING_DIR],
                'executionTimeout': ['3600']  # 1 hour timeout
            },
            CloudWatchOutputConfig={
                'CloudWatchLogGroupName': f'/aws/ssm/trnda',
                'CloudWatchOutputEnabled': True
            }
        )
        
        command_id = response['Command']['CommandId']
        print(f"SSM Command sent: {command_id}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'SSM command sent successfully',
                'commandId': command_id,
                's3Bucket': bucket,
                's3Key': key,
                'instanceId': INSTANCE_ID
            })
        }
        
    except Exception as e:
        print(f"ERROR sending SSM command: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Failed to send SSM command',
                'message': str(e),
                's3Bucket': bucket,
                's3Key': key
            })
        }
