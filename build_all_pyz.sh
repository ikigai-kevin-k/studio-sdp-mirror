#!/bin/bash
# Build all SDP game executables using shiv
# This script packages all game controllers into standalone .pyz files

set -e

echo "=== Building All SDP Game Executables ==="
echo ""

# Activate production environment
echo "1. Activating production environment..."
source ~/sdp-env/bin/activate
echo "   ✅ Using Python: $(which python)"
echo "   ✅ Python version: $(python --version)"
echo ""

# Navigate to project directory
cd "$(dirname "$0")"
PROJECT_DIR=$(pwd)
echo "2. Project directory: $PROJECT_DIR"
echo ""

# Clean up old .pyz files
echo "3. Cleaning up old .pyz files..."
rm -f sdp-*.pyz
echo "   ✅ Cleaned"
echo ""

# Set Python interpreter path
PYTHON_PATH="/home/rnd/sdp-env/bin/python"

# Build SicBo
echo "4. Building SicBo game executable..."
shiv --compressed --compile-pyc \
     --python "$PYTHON_PATH" \
     --output-file sdp-sicbo.pyz \
     --entry-point main_sicbo:main \
     . 2>&1 | tail -5
if [ -f "sdp-sicbo.pyz" ]; then
    echo "   ✅ sdp-sicbo.pyz built successfully ($(du -h sdp-sicbo.pyz | cut -f1))"
else
    echo "   ❌ Failed to build sdp-sicbo.pyz"
    exit 1
fi
echo ""

# Build VIP Roulette
echo "5. Building VIP Roulette executable..."
shiv --compressed --compile-pyc \
     --python "$PYTHON_PATH" \
     --output-file sdp-vip.pyz \
     --entry-point main_vip:main \
     . 2>&1 | tail -5
if [ -f "sdp-vip.pyz" ]; then
    echo "   ✅ sdp-vip.pyz built successfully ($(du -h sdp-vip.pyz | cut -f1))"
else
    echo "   ❌ Failed to build sdp-vip.pyz"
    exit 1
fi
echo ""

# Build Speed Roulette
echo "6. Building Speed Roulette executable..."
shiv --compressed --compile-pyc \
     --python "$PYTHON_PATH" \
     --output-file sdp-speed.pyz \
     --entry-point main_speed:main \
     . 2>&1 | tail -5
if [ -f "sdp-speed.pyz" ]; then
    echo "   ✅ sdp-speed.pyz built successfully ($(du -h sdp-speed.pyz | cut -f1))"
else
    echo "   ❌ Failed to build sdp-speed.pyz"
    exit 1
fi
echo ""

# Build Baccarat
echo "7. Building Baccarat executable..."
shiv --compressed --compile-pyc \
     --python "$PYTHON_PATH" \
     --output-file sdp-baccarat.pyz \
     --entry-point main_baccarat:main \
     . 2>&1 | tail -5
if [ -f "sdp-baccarat.pyz" ]; then
    echo "   ✅ sdp-baccarat.pyz built successfully ($(du -h sdp-baccarat.pyz | cut -f1))"
else
    echo "   ❌ Failed to build sdp-baccarat.pyz"
    exit 1
fi
echo ""

# Verify all executables
echo "8. Verifying all executables..."
ALL_GOOD=true
for pyz in sdp-sicbo.pyz sdp-vip.pyz sdp-speed.pyz sdp-baccarat.pyz; do
    if [ -f "$pyz" ]; then
        if ./"$pyz" --help > /dev/null 2>&1; then
            echo "   ✅ $pyz: OK"
        else
            echo "   ❌ $pyz: Failed to run"
            ALL_GOOD=false
        fi
    else
        echo "   ❌ $pyz: Not found"
        ALL_GOOD=false
    fi
done
echo ""

# Create bundle
if [ "$ALL_GOOD" = true ]; then
    echo "9. Creating sdp.zip bundle..."
    zip sdp.zip sdp-*.pyz
    echo "   ✅ sdp.zip created ($(du -h sdp.zip | cut -f1))"
    echo ""
    
    echo "=== Build Summary ==="
    echo "All executables built successfully!"
    echo ""
    echo "Files created:"
    ls -lh sdp-*.pyz sdp.zip | awk '{print "  - " $9 " (" $5 ")"}'
    echo ""
    echo "To test individual executables:"
    echo "  ./sdp-sicbo.pyz --help"
    echo "  ./sdp-vip.pyz --help"
    echo "  ./sdp-speed.pyz --help"
    echo "  ./sdp-baccarat.pyz --help"
    echo ""
    echo "To deploy: Copy sdp.zip to target server and unzip"
else
    echo "❌ Some builds failed. Please check the errors above."
    exit 1
fi

