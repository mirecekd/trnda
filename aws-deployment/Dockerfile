# TRNDA Docker Image for ECS Fargate
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    pandoc \
    graphviz \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    texlive-latex-base \
    texlive-fonts-recommended \
    texlive-latex-extra \
    tesseract-ocr \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uvx (for MCP servers)
RUN pip install --no-cache-dir uv

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY trnda-agent.py .
COPY trnda-s3-handler.py .

# Create workdir for processing
RUN mkdir -p /tmp/aws-api-mcp/workdir

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV AWS_DEFAULT_REGION=eu-central-1

# Entry point
ENTRYPOINT ["python", "trnda-s3-handler.py"]
