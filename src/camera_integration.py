#!/usr/bin/env python3
"""
Camera Integration for EDWA Optical Alignment System
Integrates PixeLINK top view camera with DS102 positioning and laser optimization
"""

import os
import sys
import time
import threading
from datetime import datetime
from contextlib import contextmanager

# Import camera controller
from pixelink_camera import PixelinkCamera, capture_during_scan

class EDWACameraManager:
    """Camera Manager for EDWA System Integration"""
    
    def __init__(self, enable_camera=True):
        """Initialize camera manager with optional enable flag"""
        self.enable_camera = enable_camera
        self.camera = None
        self.is_initialized = False
        
        if self.enable_camera:
            try:
                self.camera = PixelinkCamera()
                self.initialize()
            except Exception as e:
                print(f"[WARNING] Camera initialization failed: {e}")
                self.enable_camera = False
                self.camera = None
    
    def initialize(self):
        """Initialize camera system"""
        if not self.enable_camera:
            print("[CAMERA] Camera disabled")
            return True
            
        try:
            print("[CAMERA] Initializing EDWA camera system...")
            
            if self.camera.initialize():
                self.is_initialized = True
                print("[CAMERA] EDWA camera system ready")
                return True
            else:
                print("[WARNING] Camera initialization failed, continuing without camera")
                self.enable_camera = False
                return False
                
        except Exception as e:
            print(f"[WARNING] Camera initialization error: {e}")
            self.enable_camera = False
            return False
    
    def capture_scan_images(self, scan_data, log_dir):
        """Capture images during brute force scanning"""
        if not self.enable_camera or not self.is_initialized:
            return []
            
        try:
            return capture_during_scan(self.camera, scan_data, log_dir)
        except Exception as e:
            print(f"[ERROR] Scan image capture failed: {e}")
            return []
    
    def capture_position_image(self, position_dict, log_dir, label="position"):
        """Capture image at specific DS102 position"""
        if not self.enable_camera or not self.is_initialized:
            return None
            
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Create camera subdirectory in log directory
            camera_dir = os.path.join(log_dir, "camera_captures")
            os.makedirs(camera_dir, exist_ok=True)
            
            # Temporarily change save directory
            original_save_dir = self.camera.save_directory
            self.camera.save_directory = camera_dir
            
            # Create descriptive filename
            pos_str = "_".join([f"{axis}{int(position_dict.get(axis, 0))}" for axis in ['X', 'Y', 'Z', 'U', 'V', 'W']])
            filename = f"{label}_{pos_str}_{timestamp}.jpg"
            
            filepath = self.camera.capture_image(filename)
            
            # Restore original save directory
            self.camera.save_directory = original_save_dir
            
            if filepath:
                print(f"[CAMERA] Position image captured: {os.path.basename(filepath)}")
            
            return filepath
            
        except Exception as e:
            print(f"[ERROR] Position image capture failed: {e}")
            return None
    
    def capture_optimization_sequence(self, log_dir, count=5, interval=1.0, label="optimization"):
        """Capture sequence during optimization process"""
        if not self.enable_camera or not self.is_initialized:
            return []
            
        try:
            # Create camera subdirectory
            camera_dir = os.path.join(log_dir, "camera_captures")
            os.makedirs(camera_dir, exist_ok=True)
            
            # Temporarily change save directory
            original_save_dir = self.camera.save_directory
            self.camera.save_directory = camera_dir
            
            # Capture sequence
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            prefix = f"{label}_{timestamp}"
            
            files = self.camera.capture_sequence(count=count, interval=interval, prefix=prefix)
            
            # Restore original save directory
            self.camera.save_directory = original_save_dir
            
            if files:
                print(f"[CAMERA] Optimization sequence captured: {len(files)} images")
            
            return files
            
        except Exception as e:
            print(f"[ERROR] Optimization sequence capture failed: {e}")
            return []
    
    @contextmanager
    def streaming_context(self):
        """Context manager for camera streaming"""
        if not self.enable_camera or not self.is_initialized:
            yield
            return
            
        try:
            was_streaming = self.camera.is_streaming
            if not was_streaming:
                self.camera.start_streaming()
            
            yield
            
        except Exception as e:
            print(f"[ERROR] Camera streaming context error: {e}")
        finally:
            if not was_streaming and self.camera.is_streaming:
                self.camera.stop_streaming()
    
    def cleanup(self):
        """Cleanup camera resources"""
        if self.camera:
            self.camera.cleanup()

# Global camera manager instance
_camera_manager = None

def get_camera_manager(enable_camera=True):
    """Get global camera manager instance"""
    global _camera_manager
    if _camera_manager is None:
        _camera_manager = EDWACameraManager(enable_camera=enable_camera)
    return _camera_manager

def initialize_camera_system(enable_camera=True):
    """Initialize camera system for EDWA"""
    return get_camera_manager(enable_camera=enable_camera).initialize()

def capture_scan_start_image(position_dict, log_dir):
    """Capture image at scan start position"""
    camera_mgr = get_camera_manager()
    return camera_mgr.capture_position_image(position_dict, log_dir, "scan_start")

def capture_scan_optimum_image(position_dict, log_dir):
    """Capture image at scan optimum position"""
    camera_mgr = get_camera_manager()
    return camera_mgr.capture_position_image(position_dict, log_dir, "scan_optimum")

def capture_hillclimb_start_image(position_dict, log_dir):
    """Capture image at hill climbing start position"""
    camera_mgr = get_camera_manager()
    return camera_mgr.capture_position_image(position_dict, log_dir, "hillclimb_start")

def capture_hillclimb_optimum_image(position_dict, log_dir):
    """Capture image at hill climbing optimum position"""
    camera_mgr = get_camera_manager()
    return camera_mgr.capture_position_image(position_dict, log_dir, "hillclimb_optimum")

def capture_scan_images_during_process(scan_data, log_dir):
    """Capture images during scanning process"""
    camera_mgr = get_camera_manager()
    return camera_mgr.capture_scan_images(scan_data, log_dir)

def capture_optimization_sequence(log_dir, count=5, interval=1.0):
    """Capture optimization sequence"""
    camera_mgr = get_camera_manager()
    return camera_mgr.capture_optimization_sequence(log_dir, count=count, interval=interval)

def cleanup_camera_system():
    """Cleanup camera system"""
    global _camera_manager
    if _camera_manager:
        _camera_manager.cleanup()
        _camera_manager = None

# Context manager for camera operations
@contextmanager
def camera_streaming():
    """Context manager for camera streaming operations"""
    camera_mgr = get_camera_manager()
    with camera_mgr.streaming_context():
        yield

# Integration helper functions
def add_camera_to_scan_results(scan_data, log_dir):
    """Add camera images to scan results if enabled"""
    try:
        camera_mgr = get_camera_manager()
        if not camera_mgr.enable_camera:
            return
        
        # Capture images at key scan points
        images = capture_scan_images_during_process(scan_data, log_dir)
        
        if images:
            print(f"[CAMERA] Added {len(images)} images to scan results")
        
    except Exception as e:
        print(f"[WARNING] Camera integration error during scan: {e}")

def add_camera_to_optimization_results(position_dict, log_dir, phase="optimization"):
    """Add camera image to optimization results"""
    try:
        camera_mgr = get_camera_manager()
        if not camera_mgr.enable_camera:
            return None
        
        return camera_mgr.capture_position_image(position_dict, log_dir, phase)
        
    except Exception as e:
        print(f"[WARNING] Camera integration error during {phase}: {e}")
        return None

if __name__ == "__main__":
    # Test camera integration
    print("=== EDWA Camera Integration Test ===")
    
    # Initialize camera system
    if initialize_camera_system(enable_camera=True):
        print("Camera system initialized successfully")
        
        # Test position capture
        test_position = {'X': 1000, 'Y': 2000, 'Z': 3000, 'U': -1000, 'V': 0, 'W': 500}
        test_log_dir = "test_camera_log"
        os.makedirs(test_log_dir, exist_ok=True)
        
        # Test various capture functions
        with camera_streaming():
            capture_scan_start_image(test_position, test_log_dir)
            time.sleep(0.5)
            capture_scan_optimum_image(test_position, test_log_dir)
            time.sleep(0.5)
            capture_optimization_sequence(test_log_dir, count=3, interval=0.5)
        
        print("Camera integration test completed")
        
        # Cleanup
        cleanup_camera_system()
    else:
        print("Camera system initialization failed")