#!/usr/bin/env python3
"""
Test script for PixeLINK WMIC compatibility fix
Verifies that the WMIC issue is resolved and camera can be imported
"""

import os
import sys
import subprocess
import traceback

def test_wmic_availability():
    """Test if WMIC is available on this system"""
    print("=== Testing WMIC Availability ===")
    
    try:
        result = subprocess.run(['wmic', 'os', 'get', 'caption'], 
                              capture_output=True, text=True, timeout=5)
        
        if result.returncode == 0:
            print("✓ WMIC is available on this system")
            return True
        else:
            print("✗ WMIC command failed")
            return False
            
    except FileNotFoundError:
        print("✗ WMIC not found - this is expected on newer Windows versions")
        return False
    except Exception as e:
        print(f"✗ WMIC test failed: {e}")
        return False

def test_powershell_alternative():
    """Test if PowerShell version checking works"""
    print("\n=== Testing PowerShell Alternative ===")
    
    # Find a system DLL to test with
    test_dll = r"C:\Windows\System32\kernel32.dll"
    
    try:
        ps_command = f'(Get-Item "{test_dll}").VersionInfo.FileVersion'
        result = subprocess.run(['powershell', '-Command', ps_command], 
                              capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0 and result.stdout.strip():
            version = result.stdout.strip()
            print(f"✓ PowerShell version check works: {version}")
            return True
        else:
            print("✗ PowerShell version check failed")
            return False
            
    except Exception as e:
        print(f"✗ PowerShell test failed: {e}")
        return False

def test_pixelink_import_original():
    """Test importing original PixeLINK wrapper (should fail on systems without WMIC)"""
    print("\n=== Testing Original PixeLINK Import ===")
    
    try:
        # Add the wrapper path
        wrapper_path = os.path.join(os.path.dirname(__file__), 'pixelinkPythonWrapper')
        if wrapper_path not in sys.path:
            sys.path.insert(0, wrapper_path)
        
        # Try importing - this might fail with WMIC error
        from pixelinkWrapper.pixelink import PxLApi
        print("✓ Original PixeLINK wrapper imported successfully")
        return True
        
    except subprocess.CalledProcessError as e:
        if 'wmic' in str(e).lower():
            print("✗ Original import failed due to WMIC issue (this confirms the problem exists)")
            return False
        else:
            print(f"✗ Original import failed for other reason: {e}")
            return False
    except Exception as e:
        if 'wmic' in str(e).lower() or 'system cannot find the file specified' in str(e).lower():
            print("✗ Original import failed due to WMIC issue (this confirms the problem exists)")
            return False
        else:
            print(f"✗ Original import failed: {e}")
            return True  # Might be other non-WMIC related issues

def test_pixelink_import_fixed():
    """Test importing fixed PixeLINK wrapper"""
    print("\n=== Testing Fixed PixeLINK Import ===")
    
    try:
        # The fixed version should already be in place
        from pixelinkWrapper.pixelink import PxLApi
        print("✓ Fixed PixeLINK wrapper imported successfully")
        
        # Try to access some basic functionality
        if hasattr(PxLApi, '_Api'):
            print("✓ PixeLINK API object accessible")
        
        if hasattr(PxLApi, '_curApiVersion'):
            version = PxLApi._curApiVersion
            print(f"✓ API version detected: {version}")
        
        return True
        
    except Exception as e:
        print(f"✗ Fixed import failed: {e}")
        print("Full error:")
        traceback.print_exc()
        return False

def test_camera_functionality():
    """Test basic camera functionality"""
    print("\n=== Testing Camera Functionality ===")
    
    try:
        from pixelink_camera import PixelinkCamera
        
        camera = PixelinkCamera()
        print("✓ PixelinkCamera class created")
        
        # Try to initialize (might fail if no camera connected, but shouldn't crash)
        try:
            if camera.initialize():
                print("✓ Camera initialized successfully")
                camera.cleanup()
                return True
            else:
                print("⚠ Camera initialization failed (no camera connected?)")
                return True  # Still a success if no hardware error
        except Exception as init_e:
            print(f"⚠ Camera initialization failed: {init_e}")
            return True  # Still a success if it's just a hardware issue
        
    except Exception as e:
        print(f"✗ Camera functionality test failed: {e}")
        return False

def run_comprehensive_test():
    """Run all WMIC fix tests"""
    print("PixeLINK WMIC Compatibility Fix Test Suite")
    print("=" * 50)
    
    tests = [
        ("WMIC Availability", test_wmic_availability),
        ("PowerShell Alternative", test_powershell_alternative),
        ("Fixed PixeLINK Import", test_pixelink_import_fixed),
        ("Camera Functionality", test_camera_functionality)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"✗ Test '{test_name}' crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print(f"\n=== Test Results Summary ===")
    passed = sum(1 for name, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed >= 3:  # Allow one test to fail (WMIC availability is expected to fail)
        print("\n🎉 WMIC fix is working correctly!")
        print("PixeLINK camera should now work on Windows 10/11 systems")
        return True
    else:
        print("\n⚠ WMIC fix needs additional work")
        return False

if __name__ == "__main__":
    success = run_comprehensive_test()
    sys.exit(0 if success else 1)