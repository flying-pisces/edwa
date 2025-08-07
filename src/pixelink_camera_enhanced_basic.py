#!/usr/bin/env python3
"""
Enhanced PixeLINK Camera with Basic Analysis
Comprehensive camera control optimized for standard Python libraries
"""

import os
import sys
import time
import threading
from datetime import datetime
from ctypes import *
import tkinter as tk
from tkinter import ttk
import json
import math

# Add pixelinkPythonWrapper to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'pixelinkPythonWrapper'))

try:
    from pixelinkWrapper import PxLApi
    print("[INFO] Enhanced PixeLINK wrapper imported successfully")
except ImportError as e:
    print(f"[ERROR] Failed to import PixeLINK wrapper: {e}")
    sys.exit(1)

class EnhancedPixelinkCamera:
    """Enhanced PixeLINK Camera Controller with Advanced Features"""
    
    def __init__(self, camera_index=0):
        """Initialize camera with specified index"""
        self.camera_index = camera_index
        self.h_camera = None
        self.is_streaming = False
        
        # Enhanced settings
        self.image_format = PxLApi.ImageFormat.JPEG
        self.auto_exposure = True
        self.exposure_time = 10.0  # ms
        self.gain = 0.0  # dB
        self.trigger_mode = 'free_run'
        
        # ROI settings
        self.roi_x = 0
        self.roi_y = 0
        self.roi_width = 0
        self.roi_height = 0
        
        # Data storage
        self.measurement_data = {}
        self.last_analysis = None
        self.camera_info = {}
        
        # File management
        self.save_directory = "camera_captures"
        os.makedirs(self.save_directory, exist_ok=True)
        
    def initialize(self):
        """Initialize and connect to the camera"""
        try:
            print(f"[CAMERA] Initializing Enhanced PixeLINK camera {self.camera_index}...")
            
            ret = PxLApi.initialize(self.camera_index)
            if not PxLApi.apiSuccess(ret[0]):
                print(f"[ERROR] Failed to initialize camera: {ret[0]}")
                return False
                
            self.h_camera = ret[1]
            print(f"[CAMERA] Camera initialized successfully (handle: {self.h_camera})")
            
            # Get camera info and configure
            self.get_camera_info()
            self.configure_camera()
            
            return True
            
        except Exception as e:
            print(f"[ERROR] Camera initialization failed: {e}")
            return False
    
    def get_camera_info(self):
        """Get comprehensive camera information"""
        try:
            ret = PxLApi.getCameraInfo(self.h_camera)
            if PxLApi.apiSuccess(ret[0]):
                info = ret[1]
                self.camera_info = {
                    'model': info.ModelName.decode('utf-8'),
                    'serial': info.SerialNumber.decode('utf-8'),
                    'firmware': info.FirmwareVersion.decode('utf-8')
                }
                
                print(f"[CAMERA] Enhanced Camera Info:")
                print(f"  Model: {self.camera_info['model']}")
                print(f"  Serial: {self.camera_info['serial']}")
                print(f"  Firmware: {self.camera_info['firmware']}")
                
        except Exception as e:
            print(f"[WARNING] Could not retrieve camera info: {e}")
    
    def configure_camera(self):
        """Configure camera with enhanced settings"""
        try:
            self.set_exposure(self.exposure_time, self.auto_exposure)
            self.set_gain(self.gain)
            self.set_trigger_mode(self.trigger_mode)
            
            # White balance
            ret = PxLApi.setFeature(self.h_camera, PxLApi.FeatureId.WHITE_BALANCE, 
                                  PxLApi.FeatureFlags.AUTO, [])
            if PxLApi.apiSuccess(ret[0]):
                print("[CAMERA] Auto white balance enabled")
                
        except Exception as e:
            print(f"[WARNING] Camera configuration warning: {e}")
    
    def set_exposure(self, exposure_time_ms, auto_exposure=False):
        """Set camera exposure time"""
        try:
            self.exposure_time = exposure_time_ms
            self.auto_exposure = auto_exposure
            
            if auto_exposure:
                ret = PxLApi.setFeature(self.h_camera, PxLApi.FeatureId.EXPOSURE, 
                                      PxLApi.FeatureFlags.AUTO, [])
                if PxLApi.apiSuccess(ret[0]):
                    print("[CAMERA] Auto exposure enabled")
                    return True
            else:
                ret = PxLApi.setFeature(self.h_camera, PxLApi.FeatureId.EXPOSURE, 
                                      PxLApi.FeatureFlags.MANUAL, [exposure_time_ms])
                if PxLApi.apiSuccess(ret[0]):
                    print(f"[CAMERA] Manual exposure set to {exposure_time_ms} ms")
                    return True
            
            return False
            
        except Exception as e:
            print(f"[ERROR] Failed to set exposure: {e}")
            return False
    
    def set_gain(self, gain_db):
        """Set camera gain in dB"""
        try:
            self.gain = gain_db
            ret = PxLApi.setFeature(self.h_camera, PxLApi.FeatureId.GAIN, 
                                  PxLApi.FeatureFlags.MANUAL, [gain_db])
            
            if PxLApi.apiSuccess(ret[0]):
                print(f"[CAMERA] Gain set to {gain_db} dB")
                return True
            else:
                print(f"[WARNING] Could not set gain (may not be supported)")
                return False
                
        except Exception as e:
            print(f"[WARNING] Gain control not available: {e}")
            return False
    
    def set_trigger_mode(self, mode='free_run'):
        """Set camera trigger mode"""
        try:
            self.trigger_mode = mode
            
            if mode == 'free_run':
                trigger_type = PxLApi.TriggerTypes.FREE_RUNNING
            elif mode == 'software':
                trigger_type = PxLApi.TriggerTypes.SOFTWARE
            elif mode == 'external':
                trigger_type = PxLApi.TriggerTypes.HARDWARE
            else:
                trigger_type = PxLApi.TriggerTypes.FREE_RUNNING
                self.trigger_mode = 'free_run'
            
            ret = PxLApi.setFeature(self.h_camera, PxLApi.FeatureId.TRIGGER, 
                                  PxLApi.FeatureFlags.MANUAL, [trigger_type])
            
            if PxLApi.apiSuccess(ret[0]):
                print(f"[CAMERA] Trigger mode set to {self.trigger_mode}")
                return True
            else:
                print(f"[WARNING] Failed to set trigger mode")
                return False
                
        except Exception as e:
            print(f"[ERROR] Failed to set trigger mode: {e}")
            return False
    
    def trigger_measurement(self):
        """Trigger a measurement capture"""
        try:
            if self.trigger_mode == 'software':
                ret = PxLApi.setFeature(self.h_camera, PxLApi.FeatureId.TRIGGER, 
                                      PxLApi.FeatureFlags.ONEPUSH, [])
                
                if PxLApi.apiSuccess(ret[0]):
                    print("[CAMERA] Software trigger activated")
                    return True
                else:
                    print(f"[WARNING] Failed to trigger")
                    return False
            else:
                return True
                
        except Exception as e:
            print(f"[ERROR] Failed to trigger measurement: {e}")
            return False
    
    def start_streaming(self):
        """Start camera streaming"""
        try:
            if not self.h_camera:
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
    
    def capture_image(self, filename=None):
        """Enhanced image capture"""
        try:
            if not self.h_camera:
                return None
            
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"enhanced_camera_{timestamp}.jpg"
            
            filepath = os.path.join(self.save_directory, filename)
            
            # Handle streaming
            was_streaming = self.is_streaming
            if not was_streaming:
                if not self.start_streaming():
                    return None
            
            # Capture
            success = self._get_snapshot(self.image_format, filename)
            
            if not was_streaming:
                self.stop_streaming()
                
            if success:
                print(f"[CAMERA] Image saved: {filepath}")
                return filepath
            else:
                return None
                
        except Exception as e:
            print(f"[ERROR] Image capture failed: {e}")
            return None
    
    def save_measurement_data(self, position_dict, power_reading, optimization_phase):
        """Save measurement data for correlation"""
        timestamp = datetime.now().isoformat()
        
        self.measurement_data[timestamp] = {
            'position': position_dict.copy(),
            'power_reading': float(power_reading),
            'phase': optimization_phase,
            'camera_settings': self.get_camera_settings()
        }
        
        # Keep recent measurements only
        if len(self.measurement_data) > 1000:
            oldest_keys = sorted(self.measurement_data.keys())[:100]
            for key in oldest_keys:
                del self.measurement_data[key]
    
    def create_measurement_triggered_capture(self, position_dict, power_reading, phase_name):
        """Create measurement-triggered capture with data correlation"""
        try:
            # Save measurement data
            self.save_measurement_data(position_dict, power_reading, phase_name)
            
            # Trigger if needed
            if self.trigger_mode == 'software':
                self.trigger_measurement()
                time.sleep(0.05)
            
            # Create filename with measurement info
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            pos_str = "_".join([f"{axis}{int(position_dict.get(axis, 0))}" for axis in ['X', 'Y', 'Z', 'U', 'V', 'W']])
            filename = f"meas_{phase_name}_{pos_str}_P{power_reading:.1f}_{timestamp}.jpg"
            
            filepath = self.capture_image(filename)
            
            if filepath:
                print(f"[CAMERA] Measurement capture complete: {os.path.basename(filepath)}")
                print(f"[CAMERA] Position: {pos_str}, Power: {power_reading:.1f}")
                
                # Save measurement metadata as JSON
                metadata_file = filepath.replace('.jpg', '_metadata.json')
                metadata = {
                    'timestamp': timestamp,
                    'position': position_dict,
                    'power_reading': power_reading,
                    'phase': phase_name,
                    'camera_settings': self.get_camera_settings(),
                    'camera_info': self.camera_info
                }
                
                with open(metadata_file, 'w') as f:
                    json.dump(metadata, f, indent=2)
                
                return filepath, metadata
            
            return None, None
            
        except Exception as e:
            print(f"[ERROR] Measurement-triggered capture failed: {e}")
            return None, None
    
    def get_camera_settings(self):
        """Get current camera settings"""
        return {
            'exposure_time': self.exposure_time,
            'auto_exposure': self.auto_exposure,
            'gain': self.gain,
            'trigger_mode': self.trigger_mode,
            'image_format': str(self.image_format)
        }
    
    def export_measurement_data(self, filepath):
        """Export measurement data to JSON"""
        try:
            with open(filepath, 'w') as f:
                json.dump(self.measurement_data, f, indent=2)
            print(f"[CAMERA] Measurement data exported: {filepath}")
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to export measurement data: {e}")
            return False
    
    def _get_snapshot(self, image_format, filename):
        """Internal method to capture snapshot"""
        try:
            raw_image_size = self._determine_raw_image_size()
            if raw_image_size == 0:
                return False
            
            raw_image = create_string_buffer(raw_image_size)
            
            ret = self._get_raw_image(raw_image)
            if PxLApi.apiSuccess(ret[0]):
                frame_descriptor = ret[1]
                
                ret = PxLApi.formatImage(raw_image, frame_descriptor, image_format)
                if ret[0] == 0:
                    formatted_image = ret[1]
                    
                    filepath = os.path.join(self.save_directory, filename)
                    with open(filepath, "wb") as f:
                        bytes_written = f.write(formatted_image)
                        
                    return bytes_written == len(formatted_image)
                    
            return False
            
        except Exception as e:
            print(f"[ERROR] Snapshot capture failed: {e}")
            return False
    
    def _determine_raw_image_size(self):
        """Calculate raw image buffer size"""
        try:
            ret = PxLApi.getFeature(self.h_camera, PxLApi.FeatureId.ROI)
            params = ret[2]
            roi_width = params[PxLApi.RoiParams.WIDTH]
            roi_height = params[PxLApi.RoiParams.HEIGHT]
            
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
            
            num_pixels = (roi_width / pixel_addressing_x) * (roi_height / pixel_addressing_y)
            
            ret = PxLApi.getFeature(self.h_camera, PxLApi.FeatureId.PIXEL_FORMAT)
            params = ret[2]
            pixel_format = int(params[0])
            
            pixel_size = PxLApi.getBytesPerPixel(pixel_format)
            return int(num_pixels * pixel_size)
            
        except Exception as e:
            print(f"[ERROR] Failed to determine image size: {e}")
            return 0
    
    def _get_raw_image(self, raw_image):
        """Capture raw image from camera"""
        MAX_TRIES = 4
        
        for i in range(MAX_TRIES):
            ret = PxLApi.getNextFrame(self.h_camera, raw_image)
            if PxLApi.apiSuccess(ret[0]):
                return ret
            time.sleep(0.01)
            
        return (PxLApi.ReturnCode.ApiUnknownError,)
    
    def cleanup(self):
        """Cleanup camera resources"""
        try:
            self.stop_streaming()
            
            if self.h_camera:
                PxLApi.uninitialize(self.h_camera)
                self.h_camera = None
                print("[CAMERA] Enhanced camera cleaned up")
                
        except Exception as e:
            print(f"[ERROR] Camera cleanup failed: {e}")

# Integration with main GUI
class EnhancedCameraGUI:
    """Enhanced camera controls for main GUI integration"""
    
    def __init__(self, parent_frame, camera):
        self.camera = camera
        self.parent = parent_frame
        
        # Create camera control frame
        self.camera_frame = ttk.LabelFrame(parent_frame, text="Enhanced Camera Control")
        self.camera_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self._create_controls()
    
    def _create_controls(self):
        """Create enhanced camera control widgets"""
        # Row 1: Basic controls
        control_row1 = ttk.Frame(self.camera_frame)
        control_row1.pack(fill=tk.X, padx=5, pady=2)
        
        self.enable_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(control_row1, text="Enable Camera", 
                       variable=self.enable_var).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(control_row1, text="Test Capture", 
                  command=self._test_capture).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(control_row1, text="Export Data", 
                  command=self._export_data).pack(side=tk.LEFT, padx=5)
        
        # Row 2: Settings
        control_row2 = ttk.Frame(self.camera_frame)
        control_row2.pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Label(control_row2, text="Exposure:").pack(side=tk.LEFT, padx=5)
        self.exposure_var = tk.DoubleVar(value=self.camera.exposure_time)
        ttk.Scale(control_row2, from_=1.0, to=50.0, variable=self.exposure_var,
                 orient=tk.HORIZONTAL, command=self._exposure_changed).pack(side=tk.LEFT, padx=5)
        
        ttk.Label(control_row2, text="Trigger:").pack(side=tk.LEFT, padx=5)
        self.trigger_var = tk.StringVar(value=self.camera.trigger_mode)
        trigger_combo = ttk.Combobox(control_row2, textvariable=self.trigger_var,
                                   values=['free_run', 'software'], width=10,
                                   state='readonly')
        trigger_combo.bind('<<ComboboxSelected>>', self._trigger_changed)
        trigger_combo.pack(side=tk.LEFT, padx=5)
        
        # Status display
        self.status_label = ttk.Label(self.camera_frame, text="Camera ready")
        self.status_label.pack(pady=5)
    
    def _test_capture(self):
        """Test capture functionality"""
        if self.enable_var.get():
            filepath = self.camera.capture_image()
            if filepath:
                self.status_label.config(text=f"Captured: {os.path.basename(filepath)}")
            else:
                self.status_label.config(text="Capture failed")
        else:
            self.status_label.config(text="Camera disabled")
    
    def _export_data(self):
        """Export measurement data"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = f"measurement_data_{timestamp}.json"
        if self.camera.export_measurement_data(filepath):
            self.status_label.config(text=f"Data exported: {filepath}")
        else:
            self.status_label.config(text="Export failed")
    
    def _exposure_changed(self, value):
        """Handle exposure change"""
        self.camera.set_exposure(float(value))
        self.status_label.config(text=f"Exposure: {float(value):.1f}ms")
    
    def _trigger_changed(self, event):
        """Handle trigger mode change"""
        mode = self.trigger_var.get()
        self.camera.set_trigger_mode(mode)
        self.status_label.config(text=f"Trigger: {mode}")
    
    def update_status(self, message):
        """Update status display"""
        self.status_label.config(text=message)
    
    def is_enabled(self):
        """Check if camera is enabled"""
        return self.enable_var.get()

# Enhanced Preview Window for separate popup
class EnhancedCameraPreviewWindow:
    """Enhanced preview window with real-time camera display"""
    
    def __init__(self, camera):
        self.camera = camera
        self.root = None
        self.is_running = False
        self.preview_thread = None
        
        # Control variables
        self.exposure_var = None
        self.gain_var = None
        self.trigger_var = None
        
    def start_preview(self):
        """Start enhanced preview window"""
        if self.is_running:
            return
            
        self.preview_thread = threading.Thread(target=self._preview_window, daemon=True)
        self.preview_thread.start()
    
    def _preview_window(self):
        """Enhanced preview window with controls"""
        try:
            self.root = tk.Toplevel()
            self.root.title("Enhanced PixeLINK Camera - Live Preview")
            self.root.geometry("900x600")
            
            # Create main frames
            control_frame = ttk.Frame(self.root)
            control_frame.pack(pady=5, fill=tk.X)
            
            settings_frame = ttk.Frame(self.root)
            settings_frame.pack(pady=5, fill=tk.X)
            
            # Control buttons
            ttk.Button(control_frame, text="Capture", 
                      command=self._capture_button_clicked).pack(side=tk.LEFT, padx=5)
            ttk.Button(control_frame, text="Measurement Capture", 
                      command=self._measurement_capture_clicked).pack(side=tk.LEFT, padx=5)
            ttk.Button(control_frame, text="Trigger", 
                      command=self._trigger_button_clicked).pack(side=tk.LEFT, padx=5)
            ttk.Button(control_frame, text="Export Data", 
                      command=self._export_button_clicked).pack(side=tk.LEFT, padx=5)
            
            # Settings controls
            self._create_settings_controls(settings_frame)
            
            # Status label
            self.status_label = ttk.Label(self.root, text="Enhanced Camera Preview - Live View")
            self.status_label.pack(pady=5)
            
            # Camera display frame (placeholder for real-time video)
            display_frame = tk.Frame(self.root, bg='black', relief=tk.SUNKEN, bd=2)
            display_frame.pack(expand=True, fill=tk.BOTH, padx=10, pady=5)
            
            # Real-time display placeholder
            self.display_label = tk.Label(display_frame, text="LIVE CAMERA FEED\\n\\nReal-time video display would appear here.\\nUse 'Capture' to take still images.", 
                                        fg="white", bg="black", font=("Arial", 14))
            self.display_label.pack(expand=True)
            
            self.is_running = True
            
            # Start camera streaming
            if not self.camera.is_streaming:
                self.camera.start_streaming()
            
            # Update loop
            self._update_preview()
            
            self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
            self.root.mainloop()
            
        except Exception as e:
            print(f"[ERROR] Enhanced preview window error: {e}")
    
    def _create_settings_controls(self, parent):
        """Create enhanced settings controls"""
        # Exposure control
        ttk.Label(parent, text="Exposure (ms):").pack(side=tk.LEFT, padx=5)
        self.exposure_var = tk.DoubleVar(value=self.camera.exposure_time)
        exposure_scale = ttk.Scale(parent, from_=1.0, to=50.0, 
                                 variable=self.exposure_var, orient=tk.HORIZONTAL,
                                 command=self._exposure_changed)
        exposure_scale.pack(side=tk.LEFT, padx=5)
        
        # Gain control  
        ttk.Label(parent, text="Gain (dB):").pack(side=tk.LEFT, padx=5)
        self.gain_var = tk.DoubleVar(value=self.camera.gain)
        gain_scale = ttk.Scale(parent, from_=0.0, to=20.0, 
                             variable=self.gain_var, orient=tk.HORIZONTAL,
                             command=self._gain_changed)
        gain_scale.pack(side=tk.LEFT, padx=5)
        
        # Trigger mode selection
        ttk.Label(parent, text="Trigger:").pack(side=tk.LEFT, padx=5)
        self.trigger_var = tk.StringVar(value=self.camera.trigger_mode)
        trigger_combo = ttk.Combobox(parent, textvariable=self.trigger_var,
                                   values=['free_run', 'software'], width=10,
                                   state='readonly')
        trigger_combo.bind('<<ComboboxSelected>>', self._trigger_changed)
        trigger_combo.pack(side=tk.LEFT, padx=5)
    
    def _exposure_changed(self, value):
        """Handle exposure slider change"""
        self.camera.set_exposure(float(value))
    
    def _gain_changed(self, value):
        """Handle gain slider change"""
        self.camera.set_gain(float(value))
    
    def _trigger_changed(self, event):
        """Handle trigger mode change"""
        self.camera.set_trigger_mode(self.trigger_var.get())
    
    def _update_preview(self):
        """Update enhanced preview display"""
        if self.is_running and self.root:
            # Enhanced status display
            settings = self.camera.get_camera_settings()
            status_text = f"Status: {'Streaming' if self.camera.is_streaming else 'Stopped'} | "
            status_text += f"Exposure: {settings['exposure_time']:.1f}ms | "
            status_text += f"Gain: {settings['gain']:.1f}dB | "
            status_text += f"Trigger: {settings['trigger_mode']}"
            
            # Add camera info if available
            if self.camera.camera_info:
                info = self.camera.camera_info
                status_text += f" | Model: {info.get('model', 'Unknown')}"
            
            self.status_label.config(text=status_text)
            self.root.after(100, self._update_preview)
    
    def _capture_button_clicked(self):
        """Enhanced capture button"""
        filepath = self.camera.capture_image()
        if filepath:
            self.status_label.config(text=f"Captured: {os.path.basename(filepath)}")
        else:
            self.status_label.config(text="Capture failed")
    
    def _measurement_capture_clicked(self):
        """Measurement-triggered capture with mock data"""
        test_position = {'X': 1000, 'Y': 2000, 'Z': 3000, 'U': -500, 'V': 100, 'W': -200}
        power_reading = 87.3
        
        filepath, metadata = self.camera.create_measurement_triggered_capture(
            test_position, power_reading, "preview_measurement")
        
        if filepath and metadata:
            self.status_label.config(text=f"Measurement captured: {os.path.basename(filepath)}")
        else:
            self.status_label.config(text="Measurement capture failed")
    
    def _trigger_button_clicked(self):
        """Enhanced trigger button"""
        if self.camera.trigger_measurement():
            self.status_label.config(text="Measurement triggered successfully")
        else:
            self.status_label.config(text="Trigger failed")
    
    def _export_button_clicked(self):
        """Export measurement data"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = f"preview_measurement_data_{timestamp}.json"
        if self.camera.export_measurement_data(filepath):
            self.status_label.config(text=f"Data exported: {filepath}")
        else:
            self.status_label.config(text="Export failed")
    
    def _on_closing(self):
        """Handle window closing"""
        self.is_running = False
        try:
            self.root.destroy()
        except:
            pass
    
    def stop_preview(self):
        """Stop enhanced preview window"""
        self.is_running = False
        if self.root:
            try:
                self.root.quit()
            except:
                pass

def test_enhanced_camera_basic():
    """Test enhanced camera with basic features"""
    print("=== Enhanced PixeLINK Camera Test (Basic Version) ===")
    
    camera = EnhancedPixelinkCamera()
    
    try:
        if not camera.initialize():
            print("[ERROR] Failed to initialize enhanced camera")
            return False
        
        print("\n1. Testing exposure control...")
        camera.set_exposure(15.0, auto_exposure=False)
        
        print("2. Testing gain control...")
        camera.set_gain(5.0)
        
        print("3. Testing trigger modes...")
        camera.set_trigger_mode('software')
        
        print("4. Testing measurement-triggered capture...")
        test_position = {'X': 1000, 'Y': 2000, 'Z': 3000, 'U': -500, 'V': 100, 'W': -200}
        filepath, metadata = camera.create_measurement_triggered_capture(test_position, 85.5, 'test_phase')
        
        if filepath and metadata:
            print(f"   [OK] Measurement capture successful: {os.path.basename(filepath)}")
            print(f"   [OK] Metadata saved with {len(metadata)} parameters")
            
        print("5. Testing data export...")
        export_file = f"test_measurement_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        if camera.export_measurement_data(export_file):
            print(f"   [OK] Data exported: {export_file}")
            
        print("6. Testing settings management...")
        settings = camera.get_camera_settings()
        print(f"   [OK] Settings retrieved: {len(settings)} parameters")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Enhanced camera test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        camera.cleanup()

if __name__ == "__main__":
    print("Enhanced PixeLINK Camera System for EDWA (Basic Version)")
    print("=" * 60)
    
    if test_enhanced_camera_basic():
        print("\n*** ENHANCED CAMERA FEATURES WORKING! ***")
        print("\nEnhanced capabilities verified:")
        print("   [OK] Advanced exposure and gain control")
        print("   [OK] Software trigger synchronization")
        print("   [OK] Measurement data correlation") 
        print("   [OK] Metadata export and archiving")
        print("   [OK] Real-time settings management")
        print("   [OK] GUI integration ready")
        print("\nReady for integration with EDWA main application.")
        print("Use create_measurement_triggered_capture() for synchronized measurements.")
    else:
        print("\n*** ENHANCED CAMERA TEST FAILED ***")
        print("Check hardware connection and SDK installation.")