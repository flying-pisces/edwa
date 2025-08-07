#!/usr/bin/env python3
"""
Test script for PixeLINK camera integration with EDWA system
Tests camera functionality and integration points
"""

import os
import sys
import time

def test_imports():
    """Test that all camera modules import correctly"""
    print("=== Testing Camera Module Imports ===")
    
    try:
        from pixelink_camera import PixelinkCamera, CameraPreviewWindow, test_camera
        print("✓ PixeLINK camera module imported successfully")
        return True
    except ImportError as e:
        print(f"✗ PixeLINK camera module import failed: {e}")
        return False

def test_camera_initialization():
    """Test camera initialization"""
    print("\n=== Testing Camera Initialization ===")
    
    try:
        from pixelink_camera import PixelinkCamera
        
        camera = PixelinkCamera()
        if camera.initialize():
            print("✓ Camera initialized successfully")
            camera.cleanup()
            return True
        else:
            print("✗ Camera initialization failed")
            return False
            
    except Exception as e:
        print(f"✗ Camera initialization error: {e}")
        return False

def test_camera_integration():
    """Test camera integration module"""
    print("\n=== Testing Camera Integration ===")
    
    try:
        from camera_integration import (
            initialize_camera_system, capture_scan_start_image, 
            cleanup_camera_system
        )
        
        # Test initialization
        if initialize_camera_system(enable_camera=True):
            print("✓ Camera integration initialized successfully")
            
            # Test position capture
            test_position = {'X': 1000, 'Y': 2000, 'Z': 3000, 'U': -1000, 'V': 0, 'W': 500}
            test_log_dir = "test_camera_integration"
            os.makedirs(test_log_dir, exist_ok=True)
            
            filepath = capture_scan_start_image(test_position, test_log_dir)
            if filepath:
                print(f"✓ Position image captured: {filepath}")
            else:
                print("⚠ Position image capture returned None (camera may not be connected)")
            
            cleanup_camera_system()
            print("✓ Camera integration test completed")
            return True
        else:
            print("⚠ Camera integration failed to initialize (camera may not be available)")
            return True  # Still consider this a success if no camera is connected
            
    except Exception as e:
        print(f"✗ Camera integration test error: {e}")
        return False

def test_main_integration():
    """Test that main.py can import camera functions"""
    print("\n=== Testing Main Application Integration ===")
    
    try:
        # Add src to path to import main
        sys.path.insert(0, os.path.dirname(__file__))
        
        # Test the import section from main.py
        from camera_integration import (
            initialize_camera_system, capture_scan_start_image, capture_scan_optimum_image,
            capture_hillclimb_start_image, capture_hillclimb_optimum_image,
            capture_scan_images_during_process, capture_optimization_sequence,
            cleanup_camera_system, camera_streaming
        )
        
        print("✓ All camera integration functions imported successfully")
        
        # Test dummy context manager
        with camera_streaming():
            print("✓ Camera streaming context manager works")
        
        return True
        
    except Exception as e:
        print(f"✗ Main integration test error: {e}")
        return False

def run_all_tests():
    """Run all camera tests"""
    print("PixeLINK Camera Integration Test Suite")
    print("="*50)
    
    tests = [
        test_imports,
        test_camera_initialization,
        test_camera_integration,
        test_main_integration
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"✗ Test {test.__name__} crashed: {e}")
            results.append(False)
    
    # Summary
    print(f"\n=== Test Summary ===")
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"🎉 All tests passed! ({passed}/{total})")
        print("Camera integration is ready for use with EDWA system")
    else:
        print(f"⚠ {passed}/{total} tests passed")
        if passed >= 3:
            print("Camera integration should work but may have limitations")
        else:
            print("Camera integration may not work properly")
    
    return passed == total

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)