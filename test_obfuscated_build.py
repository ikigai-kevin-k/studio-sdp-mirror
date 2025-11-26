#!/usr/bin/env python3
"""
Test script for obfuscated SDP Roulette executables
This script validates that obfuscated code can be imported and basic functionality works
"""

import sys
import os
import zipimport
import subprocess
from pathlib import Path


class ObfuscatedCodeTester:
    """Test obfuscated code functionality"""
    
    def __init__(self, executable_path: str):
        self.executable_path = Path(executable_path)
        self.test_results = {}
    
    def test_zipapp_structure(self) -> bool:
        """Test if the zipapp file has correct structure"""
        try:
            if not self.executable_path.exists():
                print(f"❌ Executable not found: {self.executable_path}")
                return False
            
            # Test zipapp import
            z = zipimport.zipimporter(str(self.executable_path))
            print(f"✅ Zipapp structure valid: {self.executable_path}")
            
            # List contents
            try:
                contents = z.get_data("__main__.py")
                print(f"✅ Found __main__.py in zipapp")
            except:
                print("⚠️  No __main__.py found (this might be normal)")
            
            return True
            
        except Exception as e:
            print(f"❌ Zipapp structure test failed: {e}")
            return False
    
    def test_executable_import(self) -> bool:
        """Test if the executable can be imported"""
        try:
            # Add executable to Python path
            sys.path.insert(0, str(self.executable_path.parent))
            
            # Try to import the module
            module_name = self.executable_path.stem.replace("sdp-", "main_")
            
            # Use zipimport to load from zipapp
            z = zipimport.zipimporter(str(self.executable_path))
            
            # Try to load the main module
            try:
                module = z.load_module(module_name)
                print(f"✅ Successfully imported {module_name} from zipapp")
                
                # Check if main function exists
                if hasattr(module, 'main'):
                    print(f"✅ Found main() function in {module_name}")
                else:
                    print(f"⚠️  No main() function found in {module_name}")
                
                return True
                
            except Exception as e:
                print(f"❌ Failed to import {module_name}: {e}")
                return False
                
        except Exception as e:
            print(f"❌ Import test failed: {e}")
            return False
    
    def test_executable_execution(self) -> bool:
        """Test if the executable can be executed (dry run)"""
        try:
            # Test with --help or --version flag if available
            result = subprocess.run(
                [sys.executable, str(self.executable_path), "--help"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                print(f"✅ Executable runs successfully: {self.executable_path}")
                return True
            else:
                # Try without arguments (might exit immediately)
                result = subprocess.run(
                    [sys.executable, str(self.executable_path)],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if result.returncode in [0, 1]:  # 1 might be normal for missing config
                    print(f"✅ Executable executes (exit code {result.returncode}): {self.executable_path}")
                    return True
                else:
                    print(f"⚠️  Executable exits with code {result.returncode}: {self.executable_path}")
                    return False
                    
        except subprocess.TimeoutExpired:
            print(f"⚠️  Executable execution timed out: {self.executable_path}")
            return False
        except Exception as e:
            print(f"❌ Execution test failed: {e}")
            return False
    
    def run_all_tests(self) -> dict:
        """Run all tests and return results"""
        print(f"🧪 Testing obfuscated executable: {self.executable_path}")
        print("=" * 60)
        
        tests = [
            ("Zipapp Structure", self.test_zipapp_structure),
            ("Module Import", self.test_executable_import),
            ("Execution Test", self.test_executable_execution)
        ]
        
        results = {}
        for test_name, test_func in tests:
            print(f"\n🔍 Running {test_name} test...")
            try:
                result = test_func()
                results[test_name] = result
                if result:
                    print(f"✅ {test_name} test passed")
                else:
                    print(f"❌ {test_name} test failed")
            except Exception as e:
                print(f"❌ {test_name} test error: {e}")
                results[test_name] = False
        
        return results


def test_all_executables():
    """Test all obfuscated executables"""
    executables = [
        "sdp-vip.pyz",
        "sdp-speed.pyz", 
        "sdp-sicbo.pyz",
        "sdp-baccarat.pyz"
    ]
    
    print("🧪 Testing All Obfuscated SDP Roulette Executables")
    print("=" * 60)
    
    all_results = {}
    overall_success = True
    
    for exe_name in executables:
        exe_path = Path(exe_name)
        
        if not exe_path.exists():
            print(f"⚠️  Executable not found: {exe_name}")
            all_results[exe_name] = {"error": "File not found"}
            overall_success = False
            continue
        
        tester = ObfuscatedCodeTester(exe_path)
        results = tester.run_all_tests()
        all_results[exe_name] = results
        
        # Check if all tests passed for this executable
        exe_success = all(results.values())
        if not exe_success:
            overall_success = False
        
        print(f"\n📊 Results for {exe_name}:")
        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"  {test_name}: {status}")
        
        print("-" * 40)
    
    # Summary
    print("\n📋 Overall Test Summary:")
    print("=" * 60)
    
    for exe_name, results in all_results.items():
        if "error" in results:
            print(f"{exe_name}: ❌ ERROR - {results['error']}")
        else:
            passed = sum(1 for r in results.values() if r)
            total = len(results)
            status = "✅ PASS" if passed == total else "❌ FAIL"
            print(f"{exe_name}: {status} ({passed}/{total} tests passed)")
    
    print(f"\n🎯 Overall Result: {'✅ ALL TESTS PASSED' if overall_success else '❌ SOME TESTS FAILED'}")
    
    return overall_success


def main():
    """Main function"""
    if len(sys.argv) > 1:
        # Test specific executable
        exe_path = sys.argv[1]
        tester = ObfuscatedCodeTester(exe_path)
        results = tester.run_all_tests()
        
        success = all(results.values())
        print(f"\n🎯 Test Result: {'✅ PASSED' if success else '❌ FAILED'}")
        sys.exit(0 if success else 1)
    else:
        # Test all executables
        success = test_all_executables()
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
