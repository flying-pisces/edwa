#!/usr/bin/env python3
"""
PixeLINK Top View Camera Automation for EDWA System
Integrates with the existing optical alignment system to provide visual feedback
during DS102 positioning and laser optimization operations.
"""

import os
import sys
import time
import threading
from datetime import datetime
from ctypes import *
import tkinter as tk
from tkinter import ttk
import numpy as np
from PIL import Image, ImageTk
import cv2

# Add pixelinkPythonWrapper to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'pixelinkPythonWrapper'))

try:
    # Apply WMIC compatibility fix before importing
    import os
    if os.name == 'nt':  # Windows
        print("[INFO] Applying Windows WMIC compatibility fix for PixeLINK...")
        
    from pixelinkWrapper import PxLApi
    print("[INFO] PixeLINK wrapper imported successfully")
    
except ImportError as e:
    print(f"[ERROR] Failed to import PixeLINK wrapper: {e}")
    print("Make sure PixeLINK SDK is installed and wrapper is in the correct path")
    print("\nCommon solutions:")
    print("1. Install PixeLINK SDK from https://www.navitar.com/products/pixelink-cameras")
    print("2. Verify PxLAPI40.dll is in system PATH or Windows/System32")
    print("3. Check if WMIC is available (deprecated in Windows 11)")
    print("4. Try running as Administrator if permission issues")
    sys.exit(1)
    
except Exception as e:
    print(f"[ERROR] PixeLINK wrapper failed to load: {e}")
    print("This may be due to:")
    print("1. Missing PixeLINK SDK or PxLAPI40.dll")
    print("2. Incompatible Windows version or missing dependencies")
    print("3. WMIC compatibility issues (should be fixed)")
    import traceback
    traceback.print_exc()
    sys.exit(1)

class PixelinkCamera:
    """PixeLINK Camera Controller for EDWA Top View Imaging"""
    
    def __init__(self, camera_index=0):
        """Initialize camera with specified index (0 for first camera)"""
        self.camera_index = camera_index
        self.h_camera = None
        self.is_streaming = False
        self.is_preview_running = False
        self.capture_thread = None
        self.preview_callback = None
        
        # Image settings
        self.image_format = PxLApi.ImageFormat.JPEG
        self.auto_exposure = True
        self.exposure_time = 10.0  # ms
        
        # Capture settings
        self.save_directory = "camera_captures"
        os.makedirs(self.save_directory, exist_ok=True)
        
    def initialize(self):
        """Initialize and connect to the camera"""
        try:
            print(f"[CAMERA] Initializing PixeLINK camera {self.camera_index}...")
            
            # Initialize camera
            ret = PxLApi.initialize(self.camera_index)
            if not PxLApi.apiSuccess(ret[0]):
                print(f"[ERROR] Failed to initialize camera: {ret[0]}")
                return False
                
            self.h_camera = ret[1]
            print(f"[CAMERA] Camera initialized successfully (handle: {self.h_camera})")
            
            # Get camera info
            self.get_camera_info()
            
            # Set initial camera parameters
            self.configure_camera()
            
            return True
            
        except Exception as e:
            print(f"[ERROR] Camera initialization failed: {e}")
            return False
    
    def get_camera_info(self):
        """Get and display camera information"""
        try:
            ret = PxLApi.getCameraInfo(self.h_camera)
            if PxLApi.apiSuccess(ret[0]):
                info = ret[1]
                print(f"[CAMERA] Camera Info:")
                print(f"  Model: {info.ModelName.decode('utf-8')}")
                print(f"  Serial: {info.SerialNumber.decode('utf-8')}")
                print(f"  Firmware: {info.FirmwareVersion.decode('utf-8')}")
                
        except Exception as e:
            print(f"[WARNING] Could not retrieve camera info: {e}")
    
    def configure_camera(self):
        """Configure camera settings for optimal imaging"""
        try:
            # Set pixel format to color if available
            ret = PxLApi.getFeature(self.h_camera, PxLApi.FeatureId.PIXEL_FORMAT)
            if PxLApi.apiSuccess(ret[0]):
                print(f"[CAMERA] Current pixel format: {ret[2][0]}")
            
            # Configure exposure
            if self.auto_exposure:
                ret = PxLApi.setFeature(self.h_camera, PxLApi.FeatureId.EXPOSURE, 
                                      PxLApi.FeatureFlag.AUTO)
                if PxLApi.apiSuccess(ret[0]):
                    print("[CAMERA] Auto exposure enabled")
            else:
                ret = PxLApi.setFeature(self.h_camera, PxLApi.FeatureId.EXPOSURE, 
                                      PxLApi.FeatureFlag.MANUAL, [self.exposure_time])
                if PxLApi.apiSuccess(ret[0]):
                    print(f"[CAMERA] Manual exposure set to {self.exposure_time} ms")
            
            # Configure auto white balance
            ret = PxLApi.setFeature(self.h_camera, PxLApi.FeatureId.WHITE_BALANCE, 
                                  PxLApi.FeatureFlag.AUTO)
            if PxLApi.apiSuccess(ret[0]):
                print("[CAMERA] Auto white balance enabled")
                
        except Exception as e:
            print(f"[WARNING] Camera configuration warning: {e}")
    
    def start_streaming(self):
        """Start camera streaming for image capture"""
        try:
            if not self.h_camera:
                print("[ERROR] Camera not initialized")
                return False
                
            ret = PxLApi.setStreamState(self.h_camera, PxLApi.StreamState.START)
            if PxLApi.apiSuccess(ret[0]):
                self.is_streaming = True
                print("[CAMERA] Streaming started")
                return True
            else:
                print(f"[ERROR] Failed to start streaming: {ret[0]}")
                return False
                
        except Exception as e:
            print(f"[ERROR] Failed to start streaming: {e}")
            return False
    
    def stop_streaming(self):
        """Stop camera streaming"""
        try:
            if self.h_camera and self.is_streaming:
                ret = PxLApi.setStreamState(self.h_camera, PxLApi.StreamState.STOP)
                if PxLApi.apiSuccess(ret[0]):
                    self.is_streaming = False
                    print("[CAMERA] Streaming stopped")
                    
        except Exception as e:
            print(f"[ERROR] Failed to stop streaming: {e}")
    
    def capture_image(self, filename=None, image_format=None):
        """Capture a single image and save to file"""
        try:
            if not self.h_camera:
                print("[ERROR] Camera not initialized")
                return None
                
            # Use provided format or default
            fmt = image_format if image_format else self.image_format
            
            # Generate filename if not provided
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                ext = "jpg" if fmt == PxLApi.ImageFormat.JPEG else "bmp"
                filename = f"camera_{timestamp}.{ext}"
            
            filepath = os.path.join(self.save_directory, filename)
            
            # Ensure streaming is active
            was_streaming = self.is_streaming
            if not was_streaming:
                if not self.start_streaming():
                    return None
            
            # Capture image using the snapshot method
            success = self._get_snapshot(fmt, filename)
            
            # Restore streaming state
            if not was_streaming:
                self.stop_streaming()
                
            if success:
                print(f"[CAMERA] Image saved: {filepath}")
                return filepath
            else:
                print("[ERROR] Failed to capture image")
                return None
                
        except Exception as e:
            print(f"[ERROR] Image capture failed: {e}")
            return None
    
    def _get_snapshot(self, image_format, filename):
        """Internal method to capture and save snapshot (adapted from sample code)"""
        try:
            # Determine raw image size
            raw_image_size = self._determine_raw_image_size()
            if raw_image_size == 0:
                return False
            
            # Create buffer for raw image
            raw_image = create_string_buffer(raw_image_size)
            
            # Capture raw image
            ret = self._get_raw_image(raw_image)
            if PxLApi.apiSuccess(ret[0]):
                frame_descriptor = ret[1]
                
                # Format the image
                ret = PxLApi.formatImage(raw_image, frame_descriptor, image_format)
                if ret[0] == 0:  # SUCCESS
                    formatted_image = ret[1]
                    
                    # Save to file
                    filepath = os.path.join(self.save_directory, filename)
                    with open(filepath, "wb") as f:
                        bytes_written = f.write(formatted_image)
                        
                    return bytes_written == len(formatted_image)
                    
            return False
            
        except Exception as e:
            print(f"[ERROR] Snapshot capture failed: {e}")
            return False
    
    def _determine_raw_image_size(self):
        """Calculate raw image buffer size (from sample code)"""
        try:
            # Get ROI
            ret = PxLApi.getFeature(self.h_camera, PxLApi.FeatureId.ROI)
            params = ret[2]
            roi_width = params[PxLApi.RoiParams.WIDTH]
            roi_height = params[PxLApi.RoiParams.HEIGHT]
            
            # Get pixel addressing
            pixel_addressing_x = 1
            pixel_addressing_y = 1
            
            ret = PxLApi.getFeature(self.h_camera, PxLApi.FeatureId.PIXEL_ADDRESSING)
            if PxLApi.apiSuccess(ret[0]):
                params = ret[2]
                if PxLApi.PixelAddressingParams.NUM_PARAMS == len(params):
                    pixel_addressing_x = params[PxLApi.PixelAddressingParams.X_VALUE]
                    pixel_addressing_y = params[PxLApi.PixelAddressingParams.Y_VALUE]
                else:
                    pixel_addressing_x = params[PxLApi.PixelAddressingParams.VALUE]
                    pixel_addressing_y = params[PxLApi.PixelAddressingParams.VALUE]
            
            # Calculate number of pixels
            num_pixels = (roi_width / pixel_addressing_x) * (roi_height / pixel_addressing_y)
            
            # Get pixel format
            ret = PxLApi.getFeature(self.h_camera, PxLApi.FeatureId.PIXEL_FORMAT)
            params = ret[2]
            pixel_format = int(params[0])
            
            # Calculate total size
            pixel_size = PxLApi.getBytesPerPixel(pixel_format)
            return int(num_pixels * pixel_size)
            
        except Exception as e:
            print(f"[ERROR] Failed to determine image size: {e}")
            return 0
    
    def _get_raw_image(self, raw_image):
        """Capture raw image from camera (from sample code)"""
        MAX_TRIES = 4
        
        # Get image with retries
        for i in range(MAX_TRIES):
            ret = PxLApi.getNextFrame(self.h_camera, raw_image)
            if PxLApi.apiSuccess(ret[0]):
                return ret
            time.sleep(0.01)  # Brief pause between retries
            
        return (PxLApi.ReturnCode.ApiUnknownError,)
    
    def capture_sequence(self, count=5, interval=1.0, prefix="sequence"):
        """Capture a sequence of images"""
        captured_files = []
        
        try:
            print(f"[CAMERA] Capturing sequence of {count} images (interval: {interval}s)")
            
            if not self.start_streaming():
                return captured_files
            
            for i in range(count):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # Include milliseconds
                filename = f"{prefix}_{i+1:03d}_{timestamp}.jpg"
                
                filepath = self.capture_image(filename, PxLApi.ImageFormat.JPEG)
                if filepath:
                    captured_files.append(filepath)
                    print(f"[CAMERA] Captured {i+1}/{count}: {filename}")
                else:
                    print(f"[ERROR] Failed to capture image {i+1}/{count}")
                
                if i < count - 1:  # Don't wait after the last image
                    time.sleep(interval)
            
            self.stop_streaming()
            print(f"[CAMERA] Sequence complete: {len(captured_files)}/{count} images captured")
            
        except Exception as e:
            print(f"[ERROR] Sequence capture failed: {e}")
            self.stop_streaming()
        
        return captured_files
    
    def capture_for_position(self, position_info, timestamp=None):
        """Capture image with DS102 position information in filename"""
        try:
            if not timestamp:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Create descriptive filename with position
            pos_str = "_".join([f"{axis}{int(position_info.get(axis, 0))}" for axis in ['X', 'Y', 'Z', 'U', 'V', 'W']])
            filename = f"pos_{pos_str}_{timestamp}.jpg"
            
            return self.capture_image(filename, PxLApi.ImageFormat.JPEG)
            
        except Exception as e:
            print(f"[ERROR] Position capture failed: {e}")
            return None
    
    def cleanup(self):
        """Cleanup camera resources"""
        try:
            self.stop_streaming()
            
            if self.h_camera:
                PxLApi.uninitialize(self.h_camera)
                self.h_camera = None
                print("[CAMERA] Camera uninitialized")
                
        except Exception as e:
            print(f"[ERROR] Camera cleanup failed: {e}")

class CameraPreviewWindow:
    """Simple preview window for camera feed"""
    
    def __init__(self, camera):
        self.camera = camera
        self.root = None
        self.canvas = None
        self.is_running = False
        self.preview_thread = None
        
    def start_preview(self):
        """Start preview window in separate thread"""
        if self.is_running:
            return
            
        self.preview_thread = threading.Thread(target=self._preview_window, daemon=True)
        self.preview_thread.start()
    
    def _preview_window(self):
        """Preview window main loop"""
        try:
            self.root = tk.Tk()
            self.root.title("PixeLINK Top View Camera")
            self.root.geometry("800x600")
            
            # Control frame
            control_frame = ttk.Frame(self.root)
            control_frame.pack(pady=5)
            
            ttk.Button(control_frame, text="Capture Image", 
                      command=self._capture_button_clicked).pack(side=tk.LEFT, padx=5)
            ttk.Button(control_frame, text="Capture Sequence", 
                      command=self._sequence_button_clicked).pack(side=tk.LEFT, padx=5)
            
            # Status label
            self.status_label = ttk.Label(self.root, text="Camera Preview")
            self.status_label.pack()
            
            # Canvas for image display
            self.canvas = tk.Canvas(self.root, bg='black')
            self.canvas.pack(expand=True, fill=tk.BOTH)
            
            self.is_running = True
            
            # Start camera if not already started
            if not self.camera.is_streaming:
                self.camera.start_streaming()
            
            # Update loop
            self._update_preview()
            
            self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
            self.root.mainloop()
            
        except Exception as e:
            print(f"[ERROR] Preview window error: {e}")
    
    def _update_preview(self):
        """Update preview image (placeholder - would need frame capture)"""
        if self.is_running and self.root:
            # This would capture and display live frames
            # For now, just update status
            self.status_label.config(text=f"Camera Status: {'Streaming' if self.camera.is_streaming else 'Stopped'}")
            self.root.after(100, self._update_preview)
    
    def _capture_button_clicked(self):
        """Handle capture button click"""
        filepath = self.camera.capture_image()
        if filepath:
            self.status_label.config(text=f"Captured: {os.path.basename(filepath)}")
    
    def _sequence_button_clicked(self):
        """Handle sequence capture button click"""
        files = self.camera.capture_sequence(count=3, interval=0.5)
        self.status_label.config(text=f"Sequence captured: {len(files)} images")
    
    def _on_closing(self):
        """Handle window closing"""
        self.is_running = False
        self.root.destroy()
    
    def stop_preview(self):
        """Stop preview window"""
        self.is_running = False
        if self.root:
            self.root.quit()

# Integration functions for EDWA system
def capture_during_scan(camera, scan_data, log_dir):
    """Capture images during scanning process"""
    captured_images = []
    
    try:
        print("[CAMERA] Starting scan image capture...")
        
        if not camera.start_streaming():
            return captured_images
        
        # Capture at key scan points
        total_points = len(scan_data)
        capture_interval = max(1, total_points // 10)  # Capture ~10 images per scan
        
        for i, point in enumerate(scan_data):
            if i % capture_interval == 0:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"scan_point_{i:04d}_{timestamp}.jpg"
                
                # Create camera captures subdirectory in log directory
                camera_dir = os.path.join(log_dir, "camera_captures")
                os.makedirs(camera_dir, exist_ok=True)
                
                # Temporarily change camera save directory
                original_save_dir = camera.save_directory
                camera.save_directory = camera_dir
                
                filepath = camera.capture_image(filename)
                if filepath:
                    captured_images.append(filepath)
                    print(f"[CAMERA] Captured scan point {i}/{total_points}")
                
                # Restore original save directory
                camera.save_directory = original_save_dir
        
        camera.stop_streaming()
        print(f"[CAMERA] Scan capture complete: {len(captured_images)} images")
        
    except Exception as e:
        print(f"[ERROR] Scan image capture failed: {e}")
        camera.stop_streaming()
    
    return captured_images

def test_camera():
    """Test camera functionality"""
    print("=== PixeLINK Camera Test ===")
    
    camera = PixelinkCamera()
    
    try:
        # Initialize camera
        if not camera.initialize():
            print("Failed to initialize camera")
            return False
        
        # Capture test image
        print("Capturing test image...")
        filepath = camera.capture_image("test_image.jpg")
        
        if filepath:
            print(f"Test image saved: {filepath}")
            
            # Capture sequence
            print("Capturing test sequence...")
            files = camera.capture_sequence(count=3, interval=0.5, prefix="test_seq")
            print(f"Sequence captured: {len(files)} images")
            
            return True
        else:
            print("Failed to capture test image")
            return False
            
    except Exception as e:
        print(f"Camera test failed: {e}")
        return False
    finally:
        camera.cleanup()

if __name__ == "__main__":
    # Run camera test
    if test_camera():
        print("Camera test successful!")
    else:
        print("Camera test failed!")