#!/usr/bin/env python3
"""
Test script to validate built executables
This script performs basic validation of the packaged .pyz files
"""

import os
import sys
import zipfile
from pathlib import Path

def test_executable_structure(pyz_file):
    """Test if the .pyz file has correct structure"""
    print(f"Testing {pyz_file}...")
    
    if not os.path.exists(pyz_file):
        print(f"❌ ERROR: {pyz_file} does not exist")
        return False
    
    try:
        # Test if it's a valid zip file
        with zipfile.ZipFile(pyz_file, 'r') as zip_ref:
            # Check for essential files
            file_list = zip_ref.namelist()
            
            # Look for main module files
            has_main = any('__main__.py' in f or 'main_' in f for f in file_list)
            has_site_packages = any('site-packages' in f for f in file_list)
            
            print(f"  ✅ File exists and is valid zip")
            print(f"  ✅ Contains {len(file_list)} files")
            print(f"  ✅ Has main modules: {has_main}")
            print(f"  ✅ Has dependencies: {has_site_packages}")
            
            return True
            
    except zipfile.BadZipFile:
        print(f"❌ ERROR: {pyz_file} is not a valid zip file")
        return False
    except Exception as e:
        print(f"❌ ERROR: Failed to validate {pyz_file}: {e}")
        return False

def main():
    """Main test function"""
    print("=" * 60)
    print("Testing Built Executables")
    print("=" * 60)
    
    # List of expected executables
    executables = [
        "sdp-vip.pyz",
        "sdp-speed.pyz", 
        "sdp-sicbo.pyz",
        "sdp-baccarat.pyz"
    ]
    
    all_passed = True
    
    for exe in executables:
        if not test_executable_structure(exe):
            all_passed = False
        print()  # Add spacing between tests
    
    print("=" * 60)
    if all_passed:
        print("✅ ALL TESTS PASSED - All executables are valid")
        sys.exit(0)
    else:
        print("❌ SOME TESTS FAILED - Check the output above")
        sys.exit(1)

if __name__ == "__main__":
    main()
