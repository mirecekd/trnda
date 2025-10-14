#!/bin/bash

# TRNDA Frontend - Local Testing Script
# This script starts a simple HTTP server for local testing

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== TRNDA Frontend - Local Testing ===${NC}"
echo ""

# Get WSL2 IP address
WSL_IP=$(hostname -I | awk '{print $1}')

# Check if Python is available
if command -v python3 &> /dev/null; then
    echo -e "${YELLOW}Starting Python HTTP server on port 8000...${NC}"
    echo ""
    echo -e "${GREEN}Local access:${NC}"
    echo "  http://localhost:8000"
    echo ""
    echo -e "${GREEN}Network access (from other devices):${NC}"
    echo "  http://${WSL_IP}:8000"
    echo ""
    echo -e "${YELLOW}Note: S3 upload will NOT work without Cognito configuration${NC}"
    echo -e "${YELLOW}But you can test the UI, camera, rotation, and form validation${NC}"
    echo ""
    echo -e "${YELLOW}Camera capture will work on mobile devices when accessed via network IP${NC}"
    echo ""
    echo "Press Ctrl+C to stop the server"
    echo ""
    echo -e "${YELLOW}Note: Serving index-local.html as index.html for testing${NC}"
    echo ""
    # Create symlink for testing
    ln -sf index-local.html index.html 2>/dev/null || true
    python3 -m http.server 8000 --bind 0.0.0.0
elif command -v python &> /dev/null; then
    echo -e "${YELLOW}Starting Python HTTP server on port 8000...${NC}"
    echo ""
    echo -e "${GREEN}Local access:${NC}"
    echo "  http://localhost:8000"
    echo ""
    echo -e "${GREEN}Network access (from other devices):${NC}"
    echo "  http://${WSL_IP}:8000"
    echo ""
    echo -e "${YELLOW}Note: S3 upload will NOT work without Cognito configuration${NC}"
    echo -e "${YELLOW}But you can test the UI, camera, rotation, and form validation${NC}"
    echo ""
    echo -e "${YELLOW}Camera capture will work on mobile devices when accessed via network IP${NC}"
    echo ""
    echo "Press Ctrl+C to stop the server"
    echo ""
    python -m SimpleHTTPServer 8000
else
    echo "Python is not installed. Please install Python or use another HTTP server."
    echo ""
    echo "Alternative options:"
    echo "1. Install Python: sudo apt install python3"
    echo "2. Use Node.js: npx http-server -p 8000"
    echo "3. Use PHP: php -S localhost:8000"
    exit 1
fi
