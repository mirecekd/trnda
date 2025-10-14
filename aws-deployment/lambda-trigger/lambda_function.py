"""
Lambda Trigger for TRNDA ECS Fargate Tasks
Triggered by S3 uploads (via EventBridge), starts ECS Fargate task
"""

import json
import boto3
import os

ecs_client = boto3.client('ecs')

# Environment variables set by Terraform/CloudFormation
ECS_CLUSTER = os.environ['ECS_CLUSTER_NAME']
TASK_DEFINITION = os.environ['TASK_DEFINITION_ARN']
SUBNET_IDS = os.environ['SUBNET_IDS'].split(',')
SECURITY_GROUP_IDS = os.environ['SECURITY_GROUP_IDS'].split(',')
CONTAINER_NAME = os.environ.get('CONTAINER_NAME', 'trnda-container')


def lambda_handler(event, context):
    """
    Lambda handler triggered by S3 upload via EventBridge
    
    Args:
        event: EventBridge event with S3 details
        context: Lambda context
        
    Returns:
        Response with task ARN
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
    
    # Skip if file is in output/ folder (to avoid processing our own outputs)
    if key.startswith('output/'):
        print(f"SKIP: File in output folder: {key}")
        return {
            'statusCode': 200,
            'body': json.dumps(f'Skipped output file: {key}')
        }
    
    print(f"Processing: s3://{bucket}/{key}")
    
    # Prepare event data for ECS task
    trnda_event = json.dumps({
        'detail': {
            'bucket': {'name': bucket},
            'object': {'key': key}
        }
    })
    
    # Start ECS Fargate task
    try:
        response = ecs_client.run_task(
            cluster=ECS_CLUSTER,
            taskDefinition=TASK_DEFINITION,
            launchType='FARGATE',
            networkConfiguration={
                'awsvpcConfiguration': {
                    'subnets': SUBNET_IDS,
                    'securityGroups': SECURITY_GROUP_IDS,
                    'assignPublicIp': 'ENABLED'  # Needed for MCP servers to reach internet
                }
            },
            overrides={
                'containerOverrides': [
                    {
                        'name': CONTAINER_NAME,
                        'environment': [
                            {
                                'name': 'TRNDA_EVENT',
                                'value': trnda_event
                            }
                        ]
                    }
                ]
            },
            tags=[
                {'key': 'Source', 'value': 'TRNDA-Lambda-Trigger'},
                {'key': 'S3Bucket', 'value': bucket},
                {'key': 'S3Key', 'value': key}
            ]
        )
        
        task_arn = response['tasks'][0]['taskArn']
        print(f"Started ECS task: {task_arn}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'ECS task started',
                'taskArn': task_arn,
                's3Bucket': bucket,
                's3Key': key
            })
        }
        
    except Exception as e:
        print(f"ERROR starting ECS task: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps(f'Failed to start ECS task: {str(e)}')
        }
