#!/bin/bash

# TRNDA Image Upload Script
# Uploads image to S3 with optional client-info metadata

# Usage:
#   ./img-upload.sh <image-file>
#   ./img-upload.sh <image-file> "client info with email"
#
# Examples:
#   ./img-upload.sh samples/sample1.jpg
#   ./img-upload.sh samples/sample1.jpg "jan.novak@acme.com"
#   ./img-upload.sh diagram.jpg "Project ABC, contact: jan.novak@acme.com"

if [ $# -eq 0 ]; then
    echo "Error: No image file specified"
    echo "Usage: $0 <image-file> [client-info]"
    exit 1
fi

IMAGE_FILE="$1"
CLIENT_INFO="$2"
BUCKET="tr-sw-trnda-diagrams"
PROFILE="k-dava"

if [ ! -f "$IMAGE_FILE" ]; then
    echo "Error: File not found: $IMAGE_FILE"
    exit 1
fi

# Build S3 command
if [ -n "$CLIENT_INFO" ]; then
    echo "Uploading with client-info: $CLIENT_INFO"
    aws s3 cp "$IMAGE_FILE" "s3://$BUCKET/input/" \
        --metadata "{\"client-info\":\"$CLIENT_INFO\"}" \
        --profile "$PROFILE"
else
    echo "Uploading without client-info"
    aws s3 cp "$IMAGE_FILE" "s3://$BUCKET/input/" \
        --profile "$PROFILE"
fi

if [ $? -eq 0 ]; then
    echo "Upload successful!"
    echo "S3 path: s3://$BUCKET/input/$(basename "$IMAGE_FILE")"
else
    echo "Upload failed!"
    exit 1
fi
