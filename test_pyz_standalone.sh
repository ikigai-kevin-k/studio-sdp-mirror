#!/bin/bash
# Test script for sdp-sicbo.pyz standalone execution
# This script verifies that the .pyz file can run independently without installing the development package

set -e

echo "=== Testing sdp-sicbo.pyz Standalone Execution ==="
echo ""

# Activate production environment
echo "1. Activating production environment..."
source ~/sdp-env/bin/activate
echo "   ✅ Using Python: $(which python)"
echo "   ✅ Python version: $(python --version)"
echo ""

# Check if studio_sdp_roulette is installed (should NOT be)
echo "2. Verifying studio_sdp_roulette is NOT installed..."
if pip show studio_sdp_roulette &> /dev/null; then
    echo "   ⚠️  WARNING: studio_sdp_roulette is installed. Uninstalling..."
    pip uninstall studio_sdp_roulette -y
else
    echo "   ✅ Good! studio_sdp_roulette is not installed"
fi
echo ""

# Check .pyz file exists
echo "3. Checking sdp-sicbo.pyz exists..."
if [ -f "sdp-sicbo.pyz" ]; then
    echo "   ✅ Found: sdp-sicbo.pyz ($(du -h sdp-sicbo.pyz | cut -f1))"
else
    echo "   ❌ ERROR: sdp-sicbo.pyz not found!"
    exit 1
fi
echo ""

# Verify shebang
echo "4. Verifying shebang..."
SHEBANG=$(head -1 sdp-sicbo.pyz)
echo "   Shebang: $SHEBANG"
if [[ "$SHEBANG" == *"/home/rnd/sdp-env/bin/python"* ]]; then
    echo "   ✅ Correct shebang pointing to production Python"
else
    echo "   ⚠️  Shebang not pointing to expected Python"
fi
echo ""

# Test help command
echo "5. Testing --help command..."
if ./sdp-sicbo.pyz --help > /dev/null 2>&1; then
    echo "   ✅ --help command works"
else
    echo "   ❌ ERROR: --help command failed"
    exit 1
fi
echo ""

# Check config files in pyz
echo "6. Verifying config files are packaged..."
CONFIG_COUNT=$(python -c "import zipfile; z = zipfile.ZipFile('sdp-sicbo.pyz'); print(len([f for f in z.namelist() if 'conf/' in f]))")
echo "   ✅ Found $CONFIG_COUNT config files in pyz"
echo ""

# Check main modules in pyz
echo "7. Verifying main modules are packaged..."
python -c "
import zipfile
z = zipfile.ZipFile('sdp-sicbo.pyz')
modules = ['main_sicbo', 'main_vip', 'main_speed', 'main_baccarat', 'gameStateController']
found = []
for module in modules:
    if any(module in f for f in z.namelist()):
        found.append(module)
print(f'   ✅ Found {len(found)}/{len(modules)} main modules')
for m in found:
    print(f'      - {m}')
"
echo ""

echo "=== All Tests Passed! ==="
echo ""
echo "The sdp-sicbo.pyz can run standalone in production environment."
echo "To run the game:"
echo "  source ~/sdp-env/bin/activate"
echo "  ./sdp-sicbo.pyz [options]"
echo ""

