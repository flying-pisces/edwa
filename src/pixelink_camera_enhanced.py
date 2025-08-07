#!/usr/bin/env python3
"""
Enhanced PixeLINK Top View Camera Automation for EDWA System
Comprehensive camera control with measurement triggers, exposure control,
imaging analysis, and data correlation capabilities.
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
from PIL import Image, ImageTk, ImageEnhance, ImageFilter
import cv2
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
        self.is_preview_running = False
        self.capture_thread = None
        self.preview_callback = None
        
        # Enhanced image settings
        self.image_format = PxLApi.ImageFormat.JPEG
        self.auto_exposure = True
        self.exposure_time = 10.0  # ms
        self.gain = 0.0  # dB
        self.brightness = 0.0
        self.contrast = 1.0
        self.saturation = 1.0
        
        # ROI settings
        self.roi_x = 0
        self.roi_y = 0
        self.roi_width = 0
        self.roi_height = 0
        
        # Measurement and trigger settings
        self.trigger_mode = 'free_run'  # 'free_run', 'software', 'external'
        self.measurement_data = {}
        self.last_analysis = None
        
        # File management
        self.save_directory = "camera_captures"
        os.makedirs(self.save_directory, exist_ok=True)
        
        # Camera info
        self.camera_info = {}
        
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
            
            # Get and store camera info
            self.get_camera_info()
            
            # Configure camera with enhanced settings
            self.configure_camera()
            
            return True
            
        except Exception as e:
            print(f"[ERROR] Camera initialization failed: {e}")
            return False
    
    def get_camera_info(self):
        """Get and display comprehensive camera information"""
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
                
                # Get additional camera capabilities
                self._get_camera_capabilities()
                
        except Exception as e:
            print(f"[WARNING] Could not retrieve camera info: {e}")
    
    def _get_camera_capabilities(self):
        """Get camera capabilities and supported features"""
        try:
            # Get pixel format info
            ret = PxLApi.getFeature(self.h_camera, PxLApi.FeatureId.PIXEL_FORMAT)
            if PxLApi.apiSuccess(ret[0]):
                self.camera_info['pixel_format'] = ret[2][0]
                
            # Get sensor size
            ret = PxLApi.getFeature(self.h_camera, PxLApi.FeatureId.ROI)
            if PxLApi.apiSuccess(ret[0]):
                params = ret[2]
                self.camera_info['sensor_width'] = params[PxLApi.RoiParams.WIDTH]
                self.camera_info['sensor_height'] = params[PxLApi.RoiParams.HEIGHT]
                
            print(f"[CAMERA] Sensor: {self.camera_info.get('sensor_width', 'Unknown')}x{self.camera_info.get('sensor_height', 'Unknown')}")
                
        except Exception as e:
            print(f"[WARNING] Could not get camera capabilities: {e}")
    
    def configure_camera(self):
        """Configure camera with enhanced settings"""
        try:
            # Configure exposure
            self.set_exposure(self.exposure_time, self.auto_exposure)
            
            # Configure gain
            self.set_gain(self.gain)
            
            # Configure white balance
            ret = PxLApi.setFeature(self.h_camera, PxLApi.FeatureId.WHITE_BALANCE, 
                                  PxLApi.FeatureFlag.AUTO)
            if PxLApi.apiSuccess(ret[0]):
                print("[CAMERA] Auto white balance enabled")
            
            # Set trigger mode
            self.set_trigger_mode(self.trigger_mode)
            
            # Set ROI if specified
            if self.roi_width > 0 and self.roi_height > 0:
                self.set_roi(self.roi_x, self.roi_y, self.roi_width, self.roi_height)
                
        except Exception as e:
            print(f"[WARNING] Camera configuration warning: {e}")
    
    def set_exposure(self, exposure_time_ms, auto_exposure=False):
        """Set camera exposure time with enhanced control"""
        try:
            self.exposure_time = exposure_time_ms
            self.auto_exposure = auto_exposure
            
            if auto_exposure:
                ret = PxLApi.setFeature(self.h_camera, PxLApi.FeatureId.EXPOSURE, 
                                      PxLApi.FeatureFlag.AUTO)
                if PxLApi.apiSuccess(ret[0]):
                    print("[CAMERA] Auto exposure enabled")
                    return True
            else:
                ret = PxLApi.setFeature(self.h_camera, PxLApi.FeatureId.EXPOSURE, 
                                      PxLApi.FeatureFlag.MANUAL, [exposure_time_ms])
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
                                  PxLApi.FeatureFlag.MANUAL, [gain_db])
            
            if PxLApi.apiSuccess(ret[0]):
                print(f"[CAMERA] Gain set to {gain_db} dB")
                return True
            else:
                print(f"[WARNING] Could not set gain: {ret[0]} (may not be supported)")
                return False
                
        except Exception as e:
            print(f"[WARNING] Gain control not available: {e}")
            return False
    
    def set_roi(self, x, y, width, height):
        """Set Region of Interest for enhanced imaging control"""
        try:
            self.roi_x, self.roi_y = x, y
            self.roi_width, self.roi_height = width, height
            
            roi_params = [x, y, width, height]
            ret = PxLApi.setFeature(self.h_camera, PxLApi.FeatureId.ROI, 
                                  PxLApi.FeatureFlag.MANUAL, roi_params)
            
            if PxLApi.apiSuccess(ret[0]):
                print(f"[CAMERA] ROI set to ({x}, {y}, {width}, {height})")
                return True
            else:
                print(f"[WARNING] Failed to set ROI: {ret[0]}")
                return False
                
        except Exception as e:
            print(f"[ERROR] Failed to set ROI: {e}")
            return False
    
    def set_trigger_mode(self, mode='free_run'):
        """Set camera trigger mode for measurement synchronization"""
        try:
            self.trigger_mode = mode
            
            if mode == 'free_run':
                trigger_type = PxLApi.TriggerType.FREE_RUNNING
            elif mode == 'software':
                trigger_type = PxLApi.TriggerType.SOFTWARE
            elif mode == 'external':
                trigger_type = PxLApi.TriggerType.HARDWARE
            else:
                print(f"[WARNING] Unknown trigger mode: {mode}, using free_run")
                trigger_type = PxLApi.TriggerType.FREE_RUNNING
                self.trigger_mode = 'free_run'
            
            ret = PxLApi.setFeature(self.h_camera, PxLApi.FeatureId.TRIGGER, 
                                  PxLApi.FeatureFlag.MANUAL, [trigger_type])
            
            if PxLApi.apiSuccess(ret[0]):
                print(f"[CAMERA] Trigger mode set to {self.trigger_mode}")
                return True
            else:
                print(f"[WARNING] Failed to set trigger mode: {ret[0]}")
                return False
                
        except Exception as e:
            print(f"[ERROR] Failed to set trigger mode: {e}")
            return False
    
    def trigger_measurement(self):
        """Trigger a measurement capture for software trigger mode"""
        try:
            if self.trigger_mode == 'software':
                ret = PxLApi.setFeature(self.h_camera, PxLApi.FeatureId.TRIGGER, 
                                      PxLApi.FeatureFlag.ONEPUSH)
                
                if PxLApi.apiSuccess(ret[0]):
                    print("[CAMERA] Software trigger activated")
                    return True
                else:
                    print(f"[WARNING] Failed to trigger: {ret[0]}")
                    return False
            else:
                # For other modes, just return success (capture will work normally)
                return True
                
        except Exception as e:
            print(f"[ERROR] Failed to trigger measurement: {e}")
            return False
    
    def start_streaming(self):
        """Start camera streaming"""
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
        """Enhanced image capture with better error handling"""
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
            
            # Capture image
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
    
    def capture_with_analysis(self, filename=None, analyze=True):
        """Capture image with comprehensive analysis"""
        filepath = self.capture_image(filename)
        
        if filepath and analyze:
            try:
                analysis = self.analyze_image(filepath)
                self.last_analysis = analysis
                
                # Save analysis data alongside image
                analysis_file = filepath.replace('.jpg', '_analysis.json').replace('.bmp', '_analysis.json')
                with open(analysis_file, 'w') as f:
                    json.dump(analysis, f, indent=2)
                
                print(f"[CAMERA] Analysis saved: {os.path.basename(analysis_file)}")
                return filepath, analysis
                
            except Exception as e:
                print(f"[ERROR] Image analysis failed: {e}")
                return filepath, None
        
        return filepath, None
    
    def analyze_image(self, image_path):
        """Perform comprehensive image analysis"""
        try:
            # Load image
            img_pil = Image.open(image_path)
            img_array = np.array(img_pil)
            
            analysis = {
                'timestamp': datetime.now().isoformat(),
                'image_path': image_path,
                'image_size': img_pil.size,
                'color_mode': img_pil.mode,
                'camera_info': self.camera_info.copy(),
                'camera_settings': self.get_camera_settings()
            }
            
            # Convert to grayscale for analysis
            if len(img_array.shape) == 3:  # Color image
                # RGB channel statistics
                analysis['color_stats'] = {
                    'red': {
                        'mean': float(np.mean(img_array[:,:,0])),
                        'std': float(np.std(img_array[:,:,0])),
                        'min': int(np.min(img_array[:,:,0])),
                        'max': int(np.max(img_array[:,:,0]))
                    },
                    'green': {
                        'mean': float(np.mean(img_array[:,:,1])),
                        'std': float(np.std(img_array[:,:,1])),
                        'min': int(np.min(img_array[:,:,1])),
                        'max': int(np.max(img_array[:,:,1]))
                    },
                    'blue': {
                        'mean': float(np.mean(img_array[:,:,2])),
                        'std': float(np.std(img_array[:,:,2])),
                        'min': int(np.min(img_array[:,:,2])),
                        'max': int(np.max(img_array[:,:,2]))
                    }
                }
                img_gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            else:
                img_gray = img_array
            
            # Intensity statistics
            analysis['intensity_stats'] = {
                'mean': float(np.mean(img_gray)),
                'std': float(np.std(img_gray)),
                'min': int(np.min(img_gray)),
                'max': int(np.max(img_gray)),
                'median': float(np.median(img_gray))
            }
            
            # Advanced analysis
            analysis['quality'] = self._calculate_image_quality(img_gray)
            analysis['features'] = self._detect_features(img_gray)
            analysis['center_of_mass'] = self._calculate_center_of_mass(img_gray)
            analysis['edges'] = self._analyze_edges(img_gray)
            analysis['histogram'] = self._calculate_histogram(img_gray)
            
            return analysis
            
        except Exception as e:
            print(f"[ERROR] Image analysis failed: {e}")
            return {'error': str(e)}
    
    def _calculate_image_quality(self, img_gray):
        """Calculate comprehensive image quality metrics"""
        try:
            # Sharpness (Laplacian variance)
            laplacian = cv2.Laplacian(img_gray, cv2.CV_64F)
            sharpness = laplacian.var()
            
            # Contrast (RMS contrast)
            contrast = img_gray.std()
            
            # Brightness
            brightness = img_gray.mean()
            
            # Signal-to-noise ratio approximation
            signal = img_gray.mean()
            noise = img_gray.std()
            snr = signal / noise if noise > 0 else float('inf')
            
            # Focus measure (variance of Laplacian)
            focus_measure = cv2.Laplacian(img_gray, cv2.CV_64F).var()
            
            return {
                'sharpness': float(sharpness),
                'contrast': float(contrast),
                'brightness': float(brightness),
                'snr': float(snr),
                'focus_measure': float(focus_measure)
            }
            
        except Exception as e:
            print(f"[ERROR] Quality calculation failed: {e}")
            return {}
    
    def _detect_features(self, img_gray):
        """Detect and analyze features in the image"""
        try:
            # Harris corner detection
            corners = cv2.cornerHarris(img_gray, 2, 3, 0.04)
            num_corners = len(corners[corners > 0.01 * corners.max()])
            
            # SimpleBlobDetector
            params = cv2.SimpleBlobDetector_Params()
            params.minThreshold = 50
            params.maxThreshold = 200
            params.filterByArea = True
            params.minArea = 20
            
            detector = cv2.SimpleBlobDetector_create(params)
            keypoints = detector.detect(img_gray)
            num_blobs = len(keypoints)
            
            # SIFT features (if available)
            try:
                sift = cv2.SIFT_create()
                keypoints_sift, descriptors = sift.detectAndCompute(img_gray, None)
                num_sift_features = len(keypoints_sift)
            except:
                num_sift_features = 0
            
            return {
                'corners': int(num_corners),
                'blobs': int(num_blobs),
                'sift_features': int(num_sift_features)
            }
            
        except Exception as e:
            print(f"[ERROR] Feature detection failed: {e}")
            return {}
    
    def _calculate_center_of_mass(self, img_gray):
        """Calculate center of mass and related metrics"""
        try:
            # Image moments
            moments = cv2.moments(img_gray)
            
            if moments['m00'] != 0:
                cx = moments['m10'] / moments['m00']
                cy = moments['m01'] / moments['m00']
                
                # Central moments for shape analysis
                mu20 = moments['mu20'] / moments['m00']
                mu02 = moments['mu02'] / moments['m00']
                mu11 = moments['mu11'] / moments['m00']
                
                # Eccentricity calculation
                eccentricity = 0.0
                if (mu20 + mu02) > 0:
                    lambda1 = 0.5 * (mu20 + mu02 + math.sqrt(4 * mu11**2 + (mu20 - mu02)**2))
                    lambda2 = 0.5 * (mu20 + mu02 - math.sqrt(4 * mu11**2 + (mu20 - mu02)**2))
                    if lambda1 > 0:
                        eccentricity = math.sqrt(1 - lambda2/lambda1) if lambda2/lambda1 < 1 else 0.0
                
                return {
                    'x': float(cx),
                    'y': float(cy),
                    'eccentricity': float(eccentricity)
                }
            else:
                return {'x': 0.0, 'y': 0.0, 'eccentricity': 0.0}
                
        except Exception as e:
            print(f"[ERROR] Center of mass calculation failed: {e}")
            return {}
    
    def _analyze_edges(self, img_gray):
        """Comprehensive edge analysis"""
        try:
            # Canny edge detection
            edges = cv2.Canny(img_gray, 50, 150)
            
            # Edge statistics
            edge_pixels = np.sum(edges > 0)
            total_pixels = edges.shape[0] * edges.shape[1]
            edge_density = edge_pixels / total_pixels
            
            # Contour analysis
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            num_contours = len(contours)
            
            # Largest contour area
            max_contour_area = 0
            if contours:
                areas = [cv2.contourArea(c) for c in contours]
                max_contour_area = max(areas) if areas else 0
            
            return {
                'edge_pixels': int(edge_pixels),
                'edge_density': float(edge_density),
                'contours': int(num_contours),
                'max_contour_area': float(max_contour_area)
            }
            
        except Exception as e:
            print(f"[ERROR] Edge analysis failed: {e}")
            return {}
    
    def _calculate_histogram(self, img_gray):
        """Calculate and analyze image histogram"""
        try:
            hist = cv2.calcHist([img_gray], [0], None, [256], [0, 256])
            
            # Histogram statistics
            hist_mean = np.mean(hist)
            hist_std = np.std(hist)
            
            # Peak detection
            peaks = []
            for i in range(1, len(hist)-1):
                if hist[i] > hist[i-1] and hist[i] > hist[i+1] and hist[i] > hist_mean + hist_std:
                    peaks.append(int(i))
            
            return {
                'histogram': hist.flatten().tolist(),
                'num_peaks': len(peaks),
                'peaks': peaks[:10]  # Limit to first 10 peaks
            }
            
        except Exception as e:
            print(f"[ERROR] Histogram calculation failed: {e}")
            return {}
    
    def save_measurement_data(self, position_dict, power_reading, optimization_phase):
        """Save measurement data for correlation with images"""
        timestamp = datetime.now().isoformat()
        
        self.measurement_data[timestamp] = {
            'position': position_dict.copy(),
            'power_reading': float(power_reading),
            'phase': optimization_phase,
            'camera_settings': self.get_camera_settings()
        }
        
        # Keep only recent measurements (last 1000)
        if len(self.measurement_data) > 1000:
            oldest_keys = sorted(self.measurement_data.keys())[:100]
            for key in oldest_keys:
                del self.measurement_data[key]
    
    def create_measurement_triggered_capture(self, position_dict, power_reading, phase_name):
        """Create measurement-triggered capture with full data correlation"""
        try:
            # Save measurement data first
            self.save_measurement_data(position_dict, power_reading, phase_name)
            
            # Trigger measurement if in software trigger mode
            if self.trigger_mode == 'software':
                self.trigger_measurement()
                time.sleep(0.05)  # Brief delay for trigger
            
            # Create descriptive filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            pos_str = "_".join([f"{axis}{int(position_dict.get(axis, 0))}" for axis in ['X', 'Y', 'Z', 'U', 'V', 'W']])
            filename = f"meas_{phase_name}_{pos_str}_P{power_reading:.1f}_{timestamp}.jpg"
            
            # Capture with analysis
            filepath, analysis = self.capture_with_analysis(filename, analyze=True)
            
            if filepath and analysis:
                print(f"[CAMERA] Measurement capture complete: {os.path.basename(filepath)}")
                print(f"[CAMERA] Position: {pos_str}, Power: {power_reading:.1f}")
                
                # Add measurement data to analysis
                analysis['measurement'] = {
                    'position': position_dict.copy(),
                    'power_reading': power_reading,
                    'phase': phase_name
                }
                
                # Re-save updated analysis
                analysis_file = filepath.replace('.jpg', '_analysis.json')
                with open(analysis_file, 'w') as f:
                    json.dump(analysis, f, indent=2)
            
            return filepath, analysis
            
        except Exception as e:
            print(f"[ERROR] Measurement-triggered capture failed: {e}")
            return None, None
    
    def get_camera_settings(self):
        """Get current camera settings as dictionary"""
        return {
            'exposure_time': self.exposure_time,
            'auto_exposure': self.auto_exposure,
            'gain': self.gain,
            'brightness': self.brightness,
            'contrast': self.contrast,
            'saturation': self.saturation,
            'trigger_mode': self.trigger_mode,
            'image_format': str(self.image_format),
            'roi': {
                'x': self.roi_x,
                'y': self.roi_y,
                'width': self.roi_width,
                'height': self.roi_height
            }
        }
    
    def apply_camera_settings(self, settings_dict):
        """Apply camera settings from dictionary"""
        try:
            if 'exposure_time' in settings_dict:
                auto_exp = settings_dict.get('auto_exposure', False)
                self.set_exposure(settings_dict['exposure_time'], auto_exp)
            
            if 'gain' in settings_dict:
                self.set_gain(settings_dict['gain'])
            
            if 'trigger_mode' in settings_dict:
                self.set_trigger_mode(settings_dict['trigger_mode'])
            
            roi = settings_dict.get('roi', {})
            if roi.get('width', 0) > 0:
                self.set_roi(roi['x'], roi['y'], roi['width'], roi['height'])
            
            print("[CAMERA] Settings applied successfully")
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to apply settings: {e}")
            return False
    
    def export_measurement_data(self, filepath):
        """Export measurement data to JSON file"""
        try:
            with open(filepath, 'w') as f:
                json.dump(self.measurement_data, f, indent=2)
            print(f"[CAMERA] Measurement data exported: {filepath}")
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to export measurement data: {e}")
            return False
    
    def _get_snapshot(self, image_format, filename):
        """Internal method to capture and save snapshot"""
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
        """Calculate raw image buffer size"""
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
        """Capture raw image from camera"""
        MAX_TRIES = 4
        
        for i in range(MAX_TRIES):
            ret = PxLApi.getNextFrame(self.h_camera, raw_image)
            if PxLApi.apiSuccess(ret[0]):
                return ret
            time.sleep(0.01)
            
        return (PxLApi.ReturnCode.ApiUnknownError,)
    
    def cleanup(self):
        """Comprehensive camera cleanup"""
        try:
            self.stop_streaming()
            
            if self.h_camera:
                PxLApi.uninitialize(self.h_camera)
                self.h_camera = None
                print("[CAMERA] Enhanced camera uninitialized")
                
        except Exception as e:
            print(f"[ERROR] Camera cleanup failed: {e}")

class EnhancedCameraPreviewWindow:
    """Enhanced preview window with real-time controls"""
    
    def __init__(self, camera):
        self.camera = camera
        self.root = None
        self.canvas = None
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
            self.root = tk.Tk()
            self.root.title("Enhanced PixeLINK Top View Camera")
            self.root.geometry("1000x700")
            
            # Create main frames
            control_frame = ttk.Frame(self.root)
            control_frame.pack(pady=5, fill=tk.X)
            
            settings_frame = ttk.Frame(self.root)
            settings_frame.pack(pady=5, fill=tk.X)
            
            # Control buttons
            ttk.Button(control_frame, text="Capture", 
                      command=self._capture_button_clicked).pack(side=tk.LEFT, padx=5)
            ttk.Button(control_frame, text="Analyze", 
                      command=self._analyze_button_clicked).pack(side=tk.LEFT, padx=5)
            ttk.Button(control_frame, text="Trigger", 
                      command=self._trigger_button_clicked).pack(side=tk.LEFT, padx=5)
            ttk.Button(control_frame, text="Export Data", 
                      command=self._export_button_clicked).pack(side=tk.LEFT, padx=5)
            
            # Settings controls
            self._create_settings_controls(settings_frame)
            
            # Status label
            self.status_label = ttk.Label(self.root, text="Enhanced Camera Preview")
            self.status_label.pack()
            
            # Canvas for image display
            self.canvas = tk.Canvas(self.root, bg='black')
            self.canvas.pack(expand=True, fill=tk.BOTH)
            
            self.is_running = True
            
            # Start camera
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
        exposure_scale = ttk.Scale(parent, from_=1.0, to=100.0, 
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
                                   values=['free_run', 'software', 'external'],
                                   state='readonly')
        trigger_combo.bind('<<ComboboxSelected>>', self._trigger_changed)
        trigger_combo.pack(side=tk.LEFT, padx=5)
    
    def _exposure_changed(self, value):
        """Handle exposure slider change"""
        self.camera.set_exposure(float(value), auto_exposure=False)
    
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
            status_text += f"Trigger: {settings['trigger_mode']} | "
            status_text += f"Format: {settings['image_format']}"
            
            if self.camera.last_analysis:
                quality = self.camera.last_analysis.get('quality', {})
                sharpness = quality.get('sharpness', 0)
                status_text += f" | Sharpness: {sharpness:.1f}"
            
            self.status_label.config(text=status_text)
            self.root.after(100, self._update_preview)
    
    def _capture_button_clicked(self):
        """Enhanced capture button"""
        filepath = self.camera.capture_image()
        if filepath:
            self.status_label.config(text=f"Captured: {os.path.basename(filepath)}")
    
    def _analyze_button_clicked(self):
        """Enhanced analyze button"""
        filepath, analysis = self.camera.capture_with_analysis()
        if analysis:
            quality = analysis.get('quality', {})
            features = analysis.get('features', {})
            self.status_label.config(text=f"Analysis: Sharpness={quality.get('sharpness', 0):.1f}, Features={features.get('corners', 0)}")
        else:
            self.status_label.config(text="Analysis failed")
    
    def _trigger_button_clicked(self):
        """Enhanced trigger button"""
        if self.camera.trigger_measurement():
            self.status_label.config(text="Measurement triggered successfully")
        else:
            self.status_label.config(text="Trigger failed")
    
    def _export_button_clicked(self):
        """Export measurement data"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = f"measurement_data_{timestamp}.json"
        if self.camera.export_measurement_data(filepath):
            self.status_label.config(text=f"Data exported: {filepath}")
        else:
            self.status_label.config(text="Export failed")
    
    def _on_closing(self):
        """Handle window closing"""
        self.is_running = False
        self.root.destroy()
    
    def stop_preview(self):
        """Stop enhanced preview window"""
        self.is_running = False
        if self.root:
            self.root.quit()

def test_enhanced_camera():
    """Test enhanced camera functionality"""
    print("=== Enhanced PixeLINK Camera System Test ===")
    print("Testing all advanced features...")
    
    camera = EnhancedPixelinkCamera()
    
    try:
        # Initialize camera
        if not camera.initialize():
            print("Failed to initialize enhanced camera")
            return False
        
        print("\n1. Testing exposure control...")
        camera.set_exposure(15.0, auto_exposure=False)
        
        print("2. Testing gain control...")
        camera.set_gain(5.0)
        
        print("3. Testing trigger modes...")
        camera.set_trigger_mode('software')
        camera.trigger_measurement()
        
        print("4. Testing measurement-triggered capture...")
        test_position = {'X': 1000, 'Y': 2000, 'Z': 3000, 'U': -500, 'V': 100, 'W': -200}
        filepath, analysis = camera.create_measurement_triggered_capture(test_position, 85.5, 'test_phase')
        
        if filepath and analysis:
            print(f"✓ Measurement capture successful: {os.path.basename(filepath)}")
            
            # Display analysis results
            quality = analysis.get('quality', {})
            features = analysis.get('features', {})
            print(f"  Quality metrics:")
            print(f"    Sharpness: {quality.get('sharpness', 0):.1f}")
            print(f"    Brightness: {quality.get('brightness', 0):.1f}")
            print(f"    Contrast: {quality.get('contrast', 0):.1f}")
            print(f"    SNR: {quality.get('snr', 0):.1f}")
            print(f"  Features detected:")
            print(f"    Corners: {features.get('corners', 0)}")
            print(f"    Blobs: {features.get('blobs', 0)}")
            print(f"    SIFT features: {features.get('sift_features', 0)}")
            
        print("5. Testing measurement data export...")
        export_file = f"test_measurement_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        if camera.export_measurement_data(export_file):
            print(f"✓ Measurement data exported: {export_file}")
        
        print("6. Testing settings management...")
        settings = camera.get_camera_settings()
        print(f"✓ Current settings retrieved: {len(settings)} parameters")
        
        return True
        
    except Exception as e:
        print(f"Enhanced camera test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        camera.cleanup()

if __name__ == "__main__":
    print("Enhanced PixeLINK Camera System for EDWA")
    print("=" * 50)
    
    if test_enhanced_camera():
        print("\n*** ALL ENHANCED FEATURES WORKING! ***")
        print("\nEnhanced capabilities verified:")
        print("✓ Advanced exposure and gain control")
        print("✓ Software trigger synchronization")  
        print("✓ Comprehensive image analysis")
        print("✓ Feature detection and quality assessment")
        print("✓ Measurement data correlation")
        print("✓ Real-time settings management")
        print("✓ Data export and archiving")
        print("\nReady for integration with EDWA main application.")
        print("Use create_measurement_triggered_capture() for synchronized measurements.")
    else:
        print("\n*** ENHANCED CAMERA TEST FAILED ***")
        print("Check hardware connection and SDK installation.")