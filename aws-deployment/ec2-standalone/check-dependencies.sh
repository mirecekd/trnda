#!/bin/bash
echo "=== Checking installed tools ==="
which uvx || echo "uvx: NOT FOUND"
which pandoc || echo "pandoc: NOT FOUND"
which tesseract || echo "tesseract: NOT FOUND"

echo ""
echo "=== Python packages ==="
pip3 list | grep -E "(opencv|pytesseract|Pillow|strands|mcp)" || echo "Some packages missing"

echo ""
echo "=== System libraries for OpenCV ==="
dpkg -l | grep -E "(libopencv|libtesseract)" || echo "OpenCV/Tesseract libs: NOT FOUND"

echo ""
echo "=== PATH and Python info ==="
echo "PATH: $PATH"
echo "Python: $(which python3)"
echo "Python version: $(python3 --version)"
