#!/bin/bash
# Deploy script for sdp-speed.pyz
# This script creates a complete deployment package with all necessary files

set -e

echo "=== SDP Speed Deployment Script ==="
echo ""

# Configuration
PYZ_FILE="sdp-speed.pyz"
DEPLOY_DIR="/home/rnd/git/sdp"
SOURCE_DIR="/home/rnd/studio-sdp-roulette"

# Check if PYZ file exists
if [ ! -f "$PYZ_FILE" ]; then
    echo "❌ Error: $PYZ_FILE not found in current directory"
    echo "Please run this script from the project root directory"
    exit 1
fi

echo "1. Preparing deployment directory: $DEPLOY_DIR"
mkdir -p "$DEPLOY_DIR"
echo "   ✅ Directory ready"
echo ""

echo "2. Copying executable..."
cp "$PYZ_FILE" "$DEPLOY_DIR/"
echo "   ✅ $PYZ_FILE copied to $DEPLOY_DIR"
echo ""

echo "3. Copying configuration files..."
cp -r conf "$DEPLOY_DIR/"
echo "   ✅ Configuration files copied"
echo ""

echo "4. Setting permissions..."
chmod +x "$DEPLOY_DIR/$PYZ_FILE"
echo "   ✅ Executable permissions set"
echo ""

echo "5. Verifying deployment..."
cd "$DEPLOY_DIR"
if [ -f "$PYZ_FILE" ] && [ -d "conf" ] && [ -f "conf/sr_dev.json" ]; then
    echo "   ✅ Deployment verification successful"
    echo ""
    echo "=== Deployment Summary ==="
    echo "Deployment location: $DEPLOY_DIR"
    echo "Files deployed:"
    ls -lh "$DEPLOY_DIR" | awk '{print "  - " $9 " (" $5 ")"}'
    echo ""
    echo "To run the application:"
    echo "  cd $DEPLOY_DIR"
    echo "  ./$PYZ_FILE"
    echo ""
    echo "To test:"
    echo "  cd $DEPLOY_DIR && ./$PYZ_FILE --help"
else
    echo "   ❌ Deployment verification failed"
    exit 1
fi
