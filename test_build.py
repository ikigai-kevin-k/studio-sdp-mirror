#!/usr/bin/env python3
"""
Test script to verify build process and module imports
This script helps debug shiv packaging issues
"""

import sys
import os
import importlib


def test_module_imports():
    """Test if all main modules can be imported successfully."""
    modules_to_test = ["main_sicbo", "main_vip", "main_speed", "main_baccarat"]

    print("Testing module imports...")
    print(f"Current working directory: {os.getcwd()}")
    print(f"Python path: {sys.path}")
    print()

    success_count = 0
    total_count = len(modules_to_test)

    for module_name in modules_to_test:
        try:
            module = importlib.import_module(module_name)
            print(f"✓ {module_name}: Successfully imported")

            # Check if main function exists
            if hasattr(module, "main"):
                print("  - main function found")
            else:
                print("  - WARNING: main function not found")

            success_count += 1

        except ImportError as e:
            print(f"✗ {module_name}: Import failed - {e}")
        except Exception as e:
            error_msg = str(e)
            if "No such file or directory" in error_msg and "/dev/ttyUSB" in error_msg:
                print(
                    f"⚠ {module_name}: Hardware device not available "
                    "(expected in test environment)"
                )
                success_count += 1  # Count as success for hardware-related errors
            else:
                print(f"✗ {module_name}: Unexpected error - {e}")

    print()
    print(
        f"Import test results: {success_count}/{total_count} modules imported successfully"
    )

    if success_count == total_count:
        print("All modules imported successfully! Build should work.")
        return True
    else:
        print("Some modules failed to import. Build may fail.")
        return False


def test_package_structure():
    """Test package structure and file existence."""
    print("\nTesting package structure...")

    required_files = [
        "main_sicbo.py",
        "main_vip.py",
        "main_speed.py",
        "main_baccarat.py",
        "__init__.py",
        "setup.py",
        "pyproject.toml",
    ]

    missing_files = []
    for file_name in required_files:
        if os.path.exists(file_name):
            print(f"✓ {file_name}: Found")
        else:
            print(f"✗ {file_name}: Missing")
            missing_files.append(file_name)

    if missing_files:
        print(f"\nMissing files: {missing_files}")
        return False
    else:
        print("\nAll required files found!")
        return True


if __name__ == "__main__":
    print("Studio SDP Roulette Build Test")
    print("=" * 40)

    # Test package structure
    structure_ok = test_package_structure()

    # Test module imports
    imports_ok = test_module_imports()

    print("\n" + "=" * 40)
    if structure_ok and imports_ok:
        print("✓ All tests passed! Ready for build.")
        sys.exit(0)
    else:
        print("✗ Some tests failed. Please fix issues before building.")
        sys.exit(1)
