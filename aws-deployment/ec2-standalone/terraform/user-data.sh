#!/bin/bash
set -e

# Log everything
exec > >(tee /var/log/user-data.log)
exec 2>&1

echo "=== TRNDA EC2 Bootstrap Started ==="
echo "Timestamp: $(date)"

# Fix SSM shell path (SSM expects /usr/bin/sh but Ubuntu has /bin/sh)
echo "Creating shell symlink for SSM compatibility..."
if [ ! -e /usr/bin/sh ]; then
    ln -s /bin/sh /usr/bin/sh
fi

# Update system
echo "Updating system packages..."
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get upgrade -y

# Install dependencies
echo "Installing system dependencies..."
apt-get install -y \
    python3-pip \
    python3-venv \
    git \
    unzip \
    curl \
    jq \
    pandoc \
    texlive-xetex \
    texlive-fonts-recommended \
    texlive-plain-generic \
    tesseract-ocr \
    libopencv-dev \
    python3-opencv \
    graphviz \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \


# Install AWS CLI v2 (not available in Ubuntu 24.04 apt repos)
echo "Installing AWS CLI v2..."
curl "https://awscli.amazonaws.com/awscli-exe-linux-aarch64.zip" -o "awscliv2.zip"
unzip -q awscliv2.zip
./aws/install
rm -rf aws awscliv2.zip

# Clone TRNDA repository
echo "Cloning TRNDA repository..."
cd /home/ubuntu

if [ ! -d "trnda" ]; then
    sudo -u ubuntu git clone https://github.com/mirecekd/trnda.git
    cd trnda
    sudo -u ubuntu git checkout main
else
    echo "TRNDA directory already exists, pulling latest changes..."
    cd trnda
    sudo -u ubuntu git pull origin main
fi

# Install Python dependencies
echo "Installing Python dependencies..."
sudo -u ubuntu pip3 install --break-system-packages -r requirements.txt

# Install UV (which includes uvx) for MCP servers
echo "Installing UV package manager..."
sudo -u ubuntu bash -c 'curl -LsSf https://astral.sh/uv/install.sh | sh'

# Add .local/bin to PATH for pip-installed packages and uvx
echo "Configuring PATH..."
sudo -u ubuntu bash -c 'echo "export PATH=\"\$HOME/.local/bin:\$PATH\"" >> ~/.bashrc'
sudo -u ubuntu bash -c 'echo "export PATH=\"\$HOME/.cargo/bin:\$PATH\"" >> ~/.bashrc'

# Set proper permissions
echo "Setting permissions..."
chown -R ubuntu:ubuntu /home/ubuntu/trnda

# Create logs directory
sudo -u ubuntu mkdir -p /home/ubuntu/trnda/logs

# Create AWS config for boto3
echo "Creating AWS configuration..."
sudo -u ubuntu mkdir -p /home/ubuntu/.aws

# Create .aws/config
cat > /home/ubuntu/.aws/config << 'EOF'
[profile default]
region = eu-central-1
output = json
EOF

# Create .aws/credentials (using EC2 instance metadata)
cat > /home/ubuntu/.aws/credentials << 'EOF'
[default]
credential_source = Ec2InstanceMetadata
region = eu-central-1
output = json
EOF

chown -R ubuntu:ubuntu /home/ubuntu/.aws
chmod 600 /home/ubuntu/.aws/credentials
chmod 644 /home/ubuntu/.aws/config

# Set TRNDA environment variables in .bashrc
echo "Setting TRNDA environment variables..."
sudo -u ubuntu bash -c 'echo "# TRNDA Configuration" >> ~/.bashrc'
sudo -u ubuntu bash -c 'echo "export S3_BUCKET=${s3_bucket_name}" >> ~/.bashrc'
sudo -u ubuntu bash -c 'echo "export AWS_DEFAULT_REGION=eu-central-1" >> ~/.bashrc'

# Install SSM Agent (should be pre-installed on Ubuntu 24.04, but make sure)
echo "Checking SSM Agent..."
if ! systemctl is-active --quiet amazon-ssm-agent; then
    echo "Starting SSM Agent..."
    systemctl enable amazon-ssm-agent
    systemctl start amazon-ssm-agent
fi

# Create a simple health check script
cat > /home/ubuntu/trnda/health-check.sh << 'EOF'
#!/bin/bash
# Simple health check for TRNDA
echo "TRNDA Health Check - $(date)"
echo "Python version: $(python3 --version)"
echo "AWS CLI version: $(aws --version)"
echo "Git status:"
cd /home/ubuntu/trnda && git status
echo "Python packages:"
pip3 list | grep -E "(strands|boto3|Pillow)"
echo "Health check complete"
EOF

chmod +x /home/ubuntu/trnda/health-check.sh
chown ubuntu:ubuntu /home/ubuntu/trnda/health-check.sh

echo "=== TRNDA EC2 Bootstrap Completed ==="
echo "Timestamp: $(date)"
echo "You can now use SSM to run commands on this instance"
echo "Test with: sudo -u ubuntu /home/ubuntu/trnda/health-check.sh"
