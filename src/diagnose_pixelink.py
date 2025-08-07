#!/usr/bin/env python3
"""
PixeLINK Diagnostic Script
Comprehensive diagnosis of PixeLINK installation and Python wrapper issues
"""

import os
import sys
import subprocess
import traceback
from pathlib import Path

def check_pixelink_sdk_installation():
    """Check if PixeLINK SDK is properly installed"""
    print("=== PixeLINK SDK Installation Check ===")
    
    # Check common installation paths
    sdk_paths = [
        r"C:\Program Files\PixeLINK",
        r"C:\Program Files (x86)\PixeLINK",
        os.path.expanduser("~\\AppData\\Local\\Programs\\PixeLINK")
    ]
    
    for path in sdk_paths:
        if os.path.exists(path):
            print(f"✓ Found PixeLINK installation at: {path}")
            
            # Check for key components
            dll_path = os.path.join(path, "bin", "PxLAPI40.dll")
            if os.path.exists(dll_path):
                print(f"✓ Found PxLAPI40.dll at: {dll_path}")
                return dll_path
            else:
                print(f"⚠ PxLAPI40.dll not found in {path}/bin/")
        else:
            print(f"✗ PixeLINK not found at: {path}")
    
    # Check if DLL is in system PATH
    try:
        import ctypes.util
        dll_path = ctypes.util.find_library("PxLAPI40")
        if dll_path:
            print(f"✓ PxLAPI40.dll found in system PATH: {dll_path}")
            return dll_path
        else:
            print("✗ PxLAPI40.dll not found in system PATH")
    except Exception as e:
        print(f"✗ Error checking system PATH: {e}")
    
    return None

def check_python_wrapper_structure():
    """Check if Python wrapper files are correctly structured"""
    print("\n=== Python Wrapper Structure Check ===")
    
    wrapper_dir = Path(__file__).parent / "pixelinkPythonWrapper"
    
    if not wrapper_dir.exists():
        print(f"✗ Wrapper directory not found: {wrapper_dir}")
        return False
    
    print(f"✓ Wrapper directory found: {wrapper_dir}")
    
    # Check key files
    required_files = [
        "pixelinkWrapper/__init__.py",
        "pixelinkWrapper/pixelink.py"
    ]
    
    all_found = True
    for file_path in required_files:
        full_path = wrapper_dir / file_path
        if full_path.exists():
            print(f"✓ Found: {file_path}")
        else:
            print(f"✗ Missing: {file_path}")
            all_found = False
    
    return all_found

def test_wrapper_import():
    """Test importing the wrapper step by step"""
    print("\n=== Wrapper Import Test ===")
    
    wrapper_dir = Path(__file__).parent / "pixelinkPythonWrapper"
    
    if str(wrapper_dir) not in sys.path:
        sys.path.insert(0, str(wrapper_dir))
        print(f"✓ Added to Python path: {wrapper_dir}")
    
    try:
        print("Testing pixelinkWrapper package import...")
        import pixelinkWrapper
        print("✓ pixelinkWrapper package imported successfully")
        
        print("Testing PxLApi class import...")
        from pixelinkWrapper import PxLApi
        print("✓ PxLApi class imported successfully")
        
        print("Testing PxLApi attributes...")
        if hasattr(PxLApi, '_Api'):
            print("✓ PxLApi._Api attribute exists")
        else:
            print("✗ PxLApi._Api attribute missing")
        
        return True
        
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"✗ Unexpected error during import: {e}")
        traceback.print_exc()
        return False

def test_dll_loading():
    """Test if the actual DLL can be loaded"""
    print("\n=== DLL Loading Test ===")
    
    try:
        from ctypes import WinDLL
        
        # Try to load the DLL directly
        try:
            dll = WinDLL("PxLAPI40.dll")
            print("✓ PxLAPI40.dll loaded successfully via WinDLL")
            return True
        except OSError as e:
            print(f"✗ Failed to load PxLAPI40.dll: {e}")
            
            # Try to find and load from specific path
            dll_path = check_pixelink_sdk_installation()
            if dll_path:
                try:
                    dll = WinDLL(dll_path)
                    print(f"✓ PxLAPI40.dll loaded from specific path: {dll_path}")
                    return True
                except OSError as e2:
                    print(f"✗ Failed to load from specific path: {e2}")
            
            return False
            
    except Exception as e:
        print(f"✗ DLL loading test failed: {e}")
        return False

def check_dependencies():
    """Check for required dependencies"""
    print("\n=== Dependencies Check ===")
    
    # Check Python version
    python_version = sys.version_info
    print(f"Python version: {python_version.major}.{python_version.minor}.{python_version.micro}")
    
    if python_version.major == 3 and python_version.minor >= 6:
        print("✓ Python version is compatible")
    else:
        print("⚠ Python version may be too old")
    
    # Check required modules
    required_modules = ['ctypes', 'subprocess', 'os']
    for module in required_modules:
        try:
            __import__(module)
            print(f"✓ {module} module available")
        except ImportError:
            print(f"✗ {module} module missing")

def check_system_info():
    """Check system information"""
    print("\n=== System Information ===")
    
    print(f"OS: {os.name}")
    print(f"Platform: {sys.platform}")
    
    if os.name == 'nt':  # Windows
        try:
            # Check Windows version
            result = subprocess.run(['systeminfo'], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'OS Name' in line or 'OS Version' in line:
                        print(line.strip())
        except Exception as e:
            print(f"Could not get detailed system info: {e}")

def suggest_solutions():
    """Provide troubleshooting suggestions"""
    print("\n=== Troubleshooting Suggestions ===")
    
    print("If you're experiencing issues, try these solutions in order:")
    print()
    print("1. **Install PixeLINK SDK**")
    print("   - Download from: https://www.navitar.com/products/pixelink-cameras")
    print("   - Run installer as Administrator")
    print("   - Restart computer after installation")
    print()
    print("2. **Check DLL Accessibility**")
    print("   - Verify PxLAPI40.dll exists in C:\\Program Files\\PixeLINK\\bin\\")
    print("   - Add PixeLINK\\bin to system PATH environment variable")
    print("   - Or copy PxLAPI40.dll to Windows\\System32\\")
    print()
    print("3. **Run as Administrator**")
    print("   - Right-click command prompt/IDE and 'Run as Administrator'")
    print("   - This can resolve permission issues")
    print()
    print("4. **Check Python Architecture**")
    print("   - Ensure Python (32/64-bit) matches PixeLINK SDK architecture")
    print("   - Most installations use 64-bit")
    print()
    print("5. **Windows Compatibility**")
    print("   - Ensure Windows 10/11 compatibility mode if needed")
    print("   - Install Visual C++ Redistributables")

def run_comprehensive_diagnosis():
    """Run all diagnostic checks"""
    print("PixeLINK Comprehensive Diagnostic Tool")
    print("=" * 50)
    
    checks = [
        ("SDK Installation", check_pixelink_sdk_installation),
        ("Wrapper Structure", check_python_wrapper_structure), 
        ("Dependencies", check_dependencies),
        ("System Info", check_system_info),
        ("DLL Loading", test_dll_loading),
        ("Wrapper Import", test_wrapper_import)
    ]
    
    results = {}
    
    for check_name, check_func in checks:
        try:
            if check_func == check_pixelink_sdk_installation or check_func == check_system_info:
                # These return None/info, not boolean
                check_func()
                results[check_name] = True
            else:
                result = check_func()
                results[check_name] = result
        except Exception as e:
            print(f"✗ {check_name} check failed: {e}")
            results[check_name] = False
    
    # Summary
    print(f"\n=== Diagnostic Summary ===")
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for check_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {check_name}")
    
    print(f"\nOverall: {passed}/{total} checks passed")
    
    if passed < total:
        suggest_solutions()
    
    if passed >= 4:  # Most checks passed
        print("\n🎉 PixeLINK should work - try running the camera test again")
    else:
        print("\n⚠ Multiple issues detected - follow troubleshooting suggestions")
    
    return passed >= 4

if __name__ == "__main__":
    run_comprehensive_diagnosis()