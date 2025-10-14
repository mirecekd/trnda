#!/bin/bash
# Fix SSM shell path issue on running EC2 instance
# SSM expects /usr/bin/sh but Ubuntu 24.04 has /bin/sh

INSTANCE_ID="i-04203940846876baf"
PROFILE="k-dava"
REGION="eu-central-1"

echo "=== Fixing SSM Shell Path Issue ==="
echo "Instance: $INSTANCE_ID"
echo ""

# Send SSM command to create symlink
COMMAND_ID=$(aws ssm send-command \
    --instance-ids "$INSTANCE_ID" \
    --document-name "AWS-RunShellScript" \
    --comment "Fix SSM shell path - create /usr/bin/sh symlink" \
    --parameters 'commands=["if [ ! -e /usr/bin/sh ]; then sudo ln -s /bin/sh /usr/bin/sh && echo \"Symlink created successfully\"; else echo \"Symlink already exists\"; fi"]' \
    --profile "$PROFILE" \
    --region "$REGION" \
    --output text \
    --query 'Command.CommandId')

echo "SSM Command sent: $COMMAND_ID"
echo ""
echo "Waiting for command to complete..."
sleep 5

# Check command status
aws ssm get-command-invocation \
    --command-id "$COMMAND_ID" \
    --instance-id "$INSTANCE_ID" \
    --profile "$PROFILE" \
    --region "$REGION" \
    --output text \
    --query '[Status,StandardOutputContent,StandardErrorContent]'

echo ""
echo "=== Done ==="
echo ""
echo "Now you can test the original TRNDA command:"
echo "aws s3 cp samples/sample1.jpg s3://tr-sw-trnda-diagrams/input/ --profile $PROFILE"
