import boto3
import base64
import json
import os
from datetime import datetime

s3 = boto3.client('s3')

# Configuration from environment variables (set by Terraform)
PASSWORD = os.environ.get('UPLOAD_PASSWORD')
BUCKET = os.environ.get('BUCKET_NAME')

def lambda_handler(event, context):
    # CORS headers
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'POST,OPTIONS'
    }
    
    # Get path
    path = event.get('rawPath', event.get('path', ''))
    method = event.get('requestContext', {}).get('http', {}).get('method', '')
    
    # Handle OPTIONS request
    if method == 'OPTIONS':
        return {'statusCode': 200, 'headers': headers, 'body': ''}
    
    # Parse body
    try:
        body = json.loads(event.get('body', '{}'))
        password = body.get('password', '')
    except:
        return {'statusCode': 400, 'headers': headers, 
                'body': json.dumps({'error': 'Invalid JSON'})}
    
    # Handle /auth endpoint
    if path.endswith('/auth'):
        if password == PASSWORD:
            return {'statusCode': 200, 'headers': headers,
                    'body': json.dumps({'authenticated': True})}
        else:
            return {'statusCode': 401, 'headers': headers,
                    'body': json.dumps({'error': 'Wrong password'})}
    
    # Handle /upload endpoint
    if path.endswith('/upload'):
        # Verify password
        if password != PASSWORD:
            return {'statusCode': 401, 'headers': headers,
                    'body': json.dumps({'error': 'Wrong password'})}
        
        try:
            image_base64 = body.get('image', '')
            client_info = body.get('clientInfo', '')
            
            if not image_base64:
                return {'statusCode': 400, 'headers': headers,
                        'body': json.dumps({'error': 'No image'})}
            
            # Decode and upload
            image_data = base64.b64decode(image_base64)
            timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
            key = f'input/diagram-{timestamp}.jpg'
            
            params = {
                'Bucket': BUCKET,
                'Key': key,
                'Body': image_data,
                'ContentType': 'image/jpeg'
            }
            
            if client_info:
                client_info_ascii = client_info.encode('ascii', 'ignore').decode('ascii')
                params['Metadata'] = {'client-info': client_info_ascii[:1900]}
            
            s3.put_object(**params)
            
            return {'statusCode': 200, 'headers': headers,
                    'body': json.dumps({'success': True, 'key': key})}
        
        except Exception as e:
            print(f'Error: {str(e)}')
            return {'statusCode': 500, 'headers': headers,
                    'body': json.dumps({'error': str(e)})}
    
    return {'statusCode': 404, 'headers': headers, 
            'body': json.dumps({'error': 'Not found'})}
