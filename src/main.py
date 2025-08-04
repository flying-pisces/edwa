# main.py

import pyvisa
import serial
import time
import os
import csv
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.colors as mcolors
from scipy.interpolate import griddata
from PIL import Image
import requests
import json
import webbrowser

# Hardware setup
PUMP1_ADDRESS = "USB0::0x1313::0x804F::M01093719::0::INSTR"
PUMP2_ADDRESS = "USB0::0x1313::0x804F::M00859480::0::INSTR"  # Adjust as needed
SIGNAL_ADDRESS = "GPIB0::20::INSTR"
POWER_METER_ADDRESS = "TCPIP0::100.65.16.193::inst0::INSTR"
STAGE_PORT = "COM3"
BAUDRATE = 38400
AXES = ['X', 'Y', 'Z', 'U', 'V', 'W']
AXIS_COLORS = {'X': 'red', 'Y': 'green', 'Z': 'blue', 'U': 'cyan', 'V': 'magenta', 'W': 'black'}
SLEEP_TIME = 0.2
INITIAL_STEP = 100
MIN_STEP = 10
INDEX_MATCHING = 0  # Set to 0 since power meter readings are already matched

# Pump laser setup
def setup_pump(inst, current_amps):
    inst.write("*RST")
    inst.write("OUTP:STAT ON")
    inst.write("SOUR:FUNC:MODE CURR")
    inst.write("SOUR:CURR:LIM:AMPL 0.08")
    inst.write(f"SOUR:CURR:LEV:IMM:AMPL {current_amps:.4f}")

# Signal laser setup
def setup_signal(instr, power_dbm):
    instr.write(":SOUR1:POW:STAT ON")
    instr.write(f":SOUR1:POW {power_dbm:.2f}")

# Stage control
def move_stage(ser, axis, pulses):
    cmd = f"{axis}{pulses:+d}\r\n".encode()
    ser.write(cmd)
    time.sleep(SLEEP_TIME)

def get_axis_position(ser, axis):
    """Read current position of an axis"""
    try:
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        cmd = f'AXI{axis}:POS?\r'
        ser.write(cmd.encode('ascii'))
        time.sleep(0.1)
        resp = ser.readline().decode('ascii').strip()
        if resp:
            return int(float(resp))
        return 0
    except Exception as e:
        print(f"Error reading position for axis {axis}: {e}")
        return 0

def move_axis_to(ser, axis, pos):
    """Move axis to absolute position"""
    try:
        cmd = f'AXI{axis}:GOABS {int(round(float(pos)))}\r'
        ser.write(cmd.encode('ascii'))
        # Wait for motion to complete
        while True:
            ser.write(f'AXI{axis}:MOTION?\r'.encode('ascii'))
            resp = ser.readline().decode('ascii').strip()
            if resp == '0':
                break
            time.sleep(0.05)
    except Exception as e:
        print(f"Error moving axis {axis}: {e}")

def get_all_positions(ser):
    """Get positions of all axes"""
    positions = {}
    for axis in AXES:
        positions[axis] = get_axis_position(ser, axis)
    return positions

# Power meter - updated to use channel 1 with debugging
def read_power(inst, debug=False):
    try:
        # Try multiple SCPI commands to find the correct one
        commands_to_try = [
            "READ1:pow?",  # Current command
            "READ:ch1:pow?",  # Alternative format
            "meas1:pow?",  # Measurement command
            "fetch1:pow?",  # Fetch command
            ":read1:pow?",  # With leading colon
            "read:pow? (@1)",  # Channel syntax
        ]
        
        raw_reading = None
        successful_command = None
        
        for cmd in commands_to_try:
            try:
                if debug:
                    print(f"[DEBUG] Trying command: {cmd}")
                inst.write(cmd)
                raw_reading = float(inst.read())
                successful_command = cmd
                break
            except Exception as cmd_error:
                if debug:
                    print(f"[DEBUG] Command {cmd} failed: {cmd_error}")
                continue
        
        if raw_reading is None:
            print(f"[ERROR] All power reading commands failed")
            return None
            
        # Apply INDEX_MATCHING offset (investigate if this is correct)
        adjusted_reading = INDEX_MATCHING + raw_reading
        
        if debug:
            print(f"[DEBUG] Successful command: {successful_command}")
            print(f"[DEBUG] Raw reading: {raw_reading:.6f} dBm")
            print(f"[DEBUG] INDEX_MATCHING offset: {INDEX_MATCHING}")
            print(f"[DEBUG] Final reading: {adjusted_reading:.6f} dBm")
            
        return adjusted_reading
        
    except Exception as e:
        print(f"[ERROR] Power read failed: {e}")
        return None

def read_power_web_interface():
    """Read power from Keysight web interface for comparison"""
    try:
        # Try to get data from the web interface
        url = "http://100.65.16.193/pm/index.html?page=ch1"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            # This is a basic approach - the actual API endpoint might be different
            # We might need to find the AJAX/API endpoint that returns the power value
            print(f"[DEBUG] Web interface accessible at: {url}")
            return url
        else:
            print(f"[DEBUG] Web interface not accessible: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"[DEBUG] Cannot access web interface: {e}")
        return None

def compare_power_readings(inst, debug=True):
    """Compare SCPI reading with web interface"""
    print("\n" + "="*60)
    print("POWER READING COMPARISON")
    print("="*60)
    
    # Get SCPI reading
    scpi_reading = read_power(inst, debug=True)
    
    # Try to access web interface
    web_url = read_power_web_interface()
    
    print(f"\nSCPI Reading: {scpi_reading:.1f} dBm" if scpi_reading else "SCPI Reading: FAILED")
    
    if web_url:
        print(f"Web Interface: {web_url}")
        print("Please manually compare the web interface value with the SCPI reading above.")
        
        # Try to open web browser for manual comparison
        try:
            webbrowser.open(web_url)
            print("Web interface opened in browser for manual verification.")
        except:
            print("Could not open web browser automatically.")
    else:
        print("Web Interface: NOT ACCESSIBLE")
    
    print("="*60)
    return scpi_reading

# Optimization
def random_walk(inst, ser, position, iterations, step_size):
    history = []
    for _ in range(iterations):
        axis = np.random.choice(AXES)
        direction = np.random.choice([-1, 1])
        move_stage(ser, axis, direction * step_size)
        power = read_power(inst)
        if power is not None:
            position[axis] += direction * step_size
            history.append((axis, position.copy(), power))
        else:
            move_stage(ser, axis, -direction * step_size)
    return history

def hill_climb(inst, ser, position, step_size):
    improved = True
    history = []
    base_power = read_power(inst)
    while improved and step_size >= MIN_STEP:
        improved = False
        for axis in AXES:
            for direction in [1, -1]:
                move_stage(ser, axis, direction * step_size)
                power = read_power(inst)
                if power is not None and power > base_power:
                    position[axis] += direction * step_size
                    history.append((axis, position.copy(), power))
                    improved = True
                    base_power = power
                else:
                    move_stage(ser, axis, -direction * step_size)
        if not improved:
            step_size = step_size // 2
    return history

def systematic_scan(inst, ser, scan_params, origin_positions):
    """Perform systematic scan based on selected axes and parameters"""
    history = []
    
    # Create meshgrid for all enabled axes
    axes = list(scan_params.keys())
    grids = [scan_params[ax] for ax in axes]
    positions = np.array(np.meshgrid(*grids, indexing='ij')).reshape(len(axes), -1).T
    
    total_positions = len(positions)
    
    for idx, pos in enumerate(positions):
        # Move to scan position
        current_pos = origin_positions.copy()
        for ax, val in zip(axes, pos):
            move_axis_to(ser, ax, val)
            current_pos[ax] = val
        
        # Read power with debugging
        power = read_power(inst, debug=True)
        if power is not None:
            history.append((axes[0], current_pos, power))
        
        # Update progress (this would be called from GUI)
        print(f"Scan progress: {idx+1}/{total_positions}")
    
    # Return to origin
    for ax in axes:
        move_axis_to(ser, ax, origin_positions[ax])
    
    return history

def brute_force_3d_scan(inst, ser, scan_params, origin_positions, progress_callback=None):
    """Perform brute force 3D scanning for DS102"""
    scan_data = []
    axes = list(scan_params.keys())
    
    if not axes:
        return scan_data
    
    # Create full 3D grid for enabled axes
    grids = [scan_params[ax] for ax in axes]
    
    if len(axes) == 1:
        # 1D scan
        positions = [(pos,) for pos in grids[0]]
    elif len(axes) == 2:
        # 2D scan
        X, Y = np.meshgrid(grids[0], grids[1], indexing='ij')
        positions = [(x, y) for x, y in zip(X.ravel(), Y.ravel())]
    elif len(axes) >= 3:
        # 3D+ scan
        meshgrids = np.meshgrid(*grids[:3], indexing='ij')
        positions = list(zip(*[grid.ravel() for grid in meshgrids]))
    
    total_positions = len(positions)
    
    for idx, pos in enumerate(positions):
        # Move to scan position
        current_pos = origin_positions.copy()
        for i, ax in enumerate(axes[:len(pos)]):
            move_axis_to(ser, ax, pos[i])
            current_pos[ax] = pos[i]
        
        # Read power with debugging
        power = read_power(inst, debug=True)
        if power is not None:
            # Store position and power data
            scan_point = {
                'position': current_pos.copy(),
                'power': power,
                'index': idx
            }
            scan_data.append(scan_point)
        
        # Progress callback
        if progress_callback:
            progress_callback(idx + 1, total_positions)
    
    # Return to origin
    for ax in axes:
        move_axis_to(ser, ax, origin_positions[ax])
    
    return scan_data

def generate_heatmaps(scan_data, axes, timestamp, log_dir):
    """Generate 1D/2D/3D heatmaps from scan data"""
    if not scan_data or not axes:
        return
    
    # Extract data
    positions = np.array([[point['position'][ax] for ax in axes] for point in scan_data])
    powers = np.array([point['power'] for point in scan_data])
    
    # Find peak power and position for title
    max_idx = np.argmax(powers)
    peak_power = powers[max_idx]
    peak_positions = {ax: positions[max_idx][i] for i, ax in enumerate(axes)}
    
    # Format all XYZUVW positions for title
    all_axes = ['X', 'Y', 'Z', 'U', 'V', 'W']
    position_str = ', '.join([f"{ax}:{peak_positions.get(ax, 0):.0f}" for ax in all_axes])
    
    if len(axes) == 1:
        # 1D plot
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(positions[:, 0], powers, 'b-o', markersize=4)
        ax.set_xlabel(f'{axes[0]} Position')
        ax.set_ylabel('Power (dBm)')
        ax.set_title(f'1D Scan - {axes[0]} vs Power\nPeak: {peak_power:.1f} dBm at [{position_str}]')
        ax.grid(True)
        plt.tight_layout()
        plt.savefig(os.path.join(log_dir, f'heatmap_1D_{timestamp}.png'), dpi=300, bbox_inches='tight')
        plt.close()
        
    elif len(axes) == 2:
        # 2D heatmap
        fig, ax = plt.subplots(figsize=(10, 8))
        
        # Create regular grid for interpolation
        x_unique = np.unique(positions[:, 0])
        y_unique = np.unique(positions[:, 1])
        X, Y = np.meshgrid(x_unique, y_unique)
        
        # Interpolate power values to grid
        Z = griddata(positions[:, :2], powers, (X, Y), method='cubic', fill_value=np.nan)
        
        # Create heatmap
        im = ax.imshow(Z, extent=[x_unique.min(), x_unique.max(), y_unique.min(), y_unique.max()],
                      origin='lower', cmap='viridis', aspect='auto')
        
        # Add colorbar
        cbar = plt.colorbar(im, ax=ax)
        cbar.set_label('Power (dBm)')
        
        # Labels and title
        ax.set_xlabel(f'{axes[0]} Position')
        ax.set_ylabel(f'{axes[1]} Position')
        ax.set_title(f'2D Heatmap - {axes[0]} vs {axes[1]} vs Power\nPeak: {peak_power:.1f} dBm at [{position_str}]')
        
        # Add scatter points
        ax.scatter(positions[:, 0], positions[:, 1], c=powers, s=20, cmap='viridis', alpha=0.7, edgecolors='white', linewidth=0.5)
        
        plt.tight_layout()
        plt.savefig(os.path.join(log_dir, f'heatmap_2D_{timestamp}.png'), dpi=300, bbox_inches='tight')
        plt.close()
        
    elif len(axes) >= 3:
        # 3D volumetric visualization
        fig = plt.figure(figsize=(12, 10))
        ax = fig.add_subplot(111, projection='3d')
        
        # 3D scatter plot with color mapping
        scatter = ax.scatter(positions[:, 0], positions[:, 1], positions[:, 2], 
                           c=powers, cmap='viridis', s=50, alpha=0.8)
        
        # Colorbar
        cbar = plt.colorbar(scatter, ax=ax, shrink=0.8)
        cbar.set_label('Power (dBm)')
        
        # Labels and title
        ax.set_xlabel(f'{axes[0]} Position')
        ax.set_ylabel(f'{axes[1]} Position')
        ax.set_zlabel(f'{axes[2]} Position')
        ax.set_title(f'3D Volumetric Scan - {axes[0]} vs {axes[1]} vs {axes[2]} vs Power\nPeak: {peak_power:.1f} dBm at [{position_str}]')
        
        plt.tight_layout()
        plt.savefig(os.path.join(log_dir, f'heatmap_3D_{timestamp}.png'), dpi=300, bbox_inches='tight')
        plt.close()
        
        # Also create 2D projections
        for i in range(3):
            for j in range(i+1, 3):
                fig, ax = plt.subplots(figsize=(8, 6))
                scatter = ax.scatter(positions[:, i], positions[:, j], c=powers, cmap='viridis', s=30, alpha=0.8)
                cbar = plt.colorbar(scatter, ax=ax)
                cbar.set_label('Power (dBm)')
                ax.set_xlabel(f'{axes[i]} Position')
                ax.set_ylabel(f'{axes[j]} Position')
                ax.set_title(f'2D Projection: {axes[i]} vs {axes[j]} vs Power\nPeak: {peak_power:.1f} dBm at [{position_str}]')
                ax.grid(True, alpha=0.3)
                plt.tight_layout()
                plt.savefig(os.path.join(log_dir, f'projection_{axes[i]}_{axes[j]}_{timestamp}.png'), dpi=300, bbox_inches='tight')
                plt.close()
    
    print(f"Heatmaps saved to {log_dir}")

# GUI Application
class OptimizerApp:
    def __init__(self, root):
        self.root = root
        root.title("Integrated Laser + DS102 Optimizer")
        root.geometry("1200x800")
        
        # Variables
        self.pump1_current = tk.DoubleVar(value=50)
        self.pump2_current = tk.DoubleVar(value=50)
        self.signal_power = tk.DoubleVar(value=0.0)
        # Remove scan_mode variable as we now use separate buttons
        
        # Axis configuration
        self.axis_enabled = {}
        self.axis_entries = {}
        self.current_positions = {}
        
        # Initialize axis variables
        for axis in AXES:
            self.axis_enabled[axis] = tk.BooleanVar(value=False)
            self.axis_entries[axis] = {}
            self.current_positions[axis] = 0
        
        self.setup_ui()
        
        # Data storage
        self.iterations, self.powers, self.colors, self.positions = [], [], [], []
        
        # Read initial positions
        self.read_current_positions()
    
    def setup_ui(self):
        # Main frame
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Left panel for controls
        control_frame = tk.Frame(main_frame)
        control_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        
        # Laser controls
        laser_frame = tk.LabelFrame(control_frame, text="Laser Controls", font=("Arial", 12, "bold"))
        laser_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(laser_frame, text="Pump 1 Current (mA):").pack()
        tk.Scale(laser_frame, variable=self.pump1_current, from_=0, to=80, orient='horizontal').pack(fill=tk.X)
        
        tk.Label(laser_frame, text="Pump 2 Current (mA):").pack()
        tk.Scale(laser_frame, variable=self.pump2_current, from_=0, to=80, orient='horizontal').pack(fill=tk.X)
        
        tk.Label(laser_frame, text="Signal Laser Power (dBm):").pack()
        tk.Scale(laser_frame, variable=self.signal_power, from_=-20, to=10, resolution=0.1, orient='horizontal').pack(fill=tk.X)
        
        # Scan mode selection - Remove radio buttons, will use separate buttons instead
        
        # DS102 Axis Configuration
        self.setup_axis_config(control_frame)
        
        # Control buttons
        button_frame = tk.Frame(control_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        tk.Button(button_frame, text="Read Positions", command=self.read_current_positions).pack(side=tk.LEFT, padx=(0, 5))
        tk.Button(button_frame, text="Scan", command=self.run_brute_force_scan, bg="lightblue").pack(side=tk.LEFT, padx=(0, 5))
        tk.Button(button_frame, text="ClimbHill", command=self.run_climb_hill, bg="lightgreen").pack(side=tk.LEFT)
        
        # Status
        self.status = tk.Label(control_frame, text="Ready.", font=("Arial", 12), fg="blue")
        self.status.pack(pady=10)
        
        # Right panel for plot
        plot_frame = tk.Frame(main_frame)
        plot_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        self.fig, self.ax = plt.subplots(figsize=(8, 6))
        self.canvas = FigureCanvasTkAgg(self.fig, master=plot_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    def setup_axis_config(self, parent):
        """Setup DS102 axis configuration UI"""
        axis_frame = tk.LabelFrame(parent, text="DS102 Axis Configuration", font=("Arial", 12, "bold"))
        axis_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Headers
        headers = ["Axis", "Enable", "Current", "Start", "Stop", "Steps"]
        for i, header in enumerate(headers):
            tk.Label(axis_frame, text=header, font=("Arial", 10, "bold")).grid(row=0, column=i, padx=2, pady=2)
        
        # Axis rows
        for i, axis in enumerate(AXES):
            row = i + 1
            
            # Axis label
            tk.Label(axis_frame, text=axis).grid(row=row, column=0, padx=2, pady=2)
            
            # Enable checkbox
            tk.Checkbutton(axis_frame, variable=self.axis_enabled[axis]).grid(row=row, column=1, padx=2, pady=2)
            
            # Current position (read-only)
            current_entry = tk.Entry(axis_frame, width=8, state="readonly")
            current_entry.grid(row=row, column=2, padx=2, pady=2)
            self.axis_entries[axis]['current'] = current_entry
            
            # Start position
            start_entry = tk.Entry(axis_frame, width=8)
            start_entry.grid(row=row, column=3, padx=2, pady=2)
            self.axis_entries[axis]['start'] = start_entry
            
            # Stop position
            stop_entry = tk.Entry(axis_frame, width=8)
            stop_entry.grid(row=row, column=4, padx=2, pady=2)
            self.axis_entries[axis]['stop'] = stop_entry
            
            # Steps
            steps_entry = tk.Entry(axis_frame, width=8)
            steps_entry.insert(0, "10")  # Default value
            steps_entry.grid(row=row, column=5, padx=2, pady=2)
            self.axis_entries[axis]['steps'] = steps_entry
    
    def read_current_positions(self):
        """Read current positions from DS102"""
        try:
            self.status.config(text="Reading DS102 positions...")
            self.root.update()
            
            ser = serial.Serial(STAGE_PORT, baudrate=BAUDRATE, timeout=0.5)
            positions = get_all_positions(ser)
            ser.close()
            
            # Update UI
            for axis in AXES:
                self.current_positions[axis] = positions[axis]
                entry = self.axis_entries[axis]['current']
                entry.config(state="normal")
                entry.delete(0, tk.END)
                entry.insert(0, str(positions[axis]))
                entry.config(state="readonly")
                
                # Set default start/stop values if empty
                if not self.axis_entries[axis]['start'].get():
                    self.axis_entries[axis]['start'].insert(0, str(positions[axis] - 1000))
                if not self.axis_entries[axis]['stop'].get():
                    self.axis_entries[axis]['stop'].insert(0, str(positions[axis] + 1000))
            
            self.status.config(text="Positions read successfully.")
            
        except Exception as e:
            self.status.config(text=f"Error reading positions: {e}")
            messagebox.showerror("Error", f"Failed to read DS102 positions: {e}")

    def debug_power_reading(self):
        """Debug power meter readings and compare with web interface"""
        try:
            self.status.config(text="Debugging power meter readings...")
            self.root.update()
            
            # Initialize power meter
            rm = pyvisa.ResourceManager()
            pwr = rm.open_resource(POWER_METER_ADDRESS)
            pwr.timeout = 5000
            
            # Get instrument info
            try:
                idn = pwr.query("*IDN?")
                print(f"\n[DEBUG] Instrument ID: {idn.strip()}")
            except:
                print("\n[DEBUG] Could not get instrument ID")
            
            # Compare readings
            compare_power_readings(pwr, debug=True)
            
            # Show multiple readings for consistency
            print("\n[DEBUG] Taking 5 consecutive readings:")
            readings = []
            for i in range(5):
                reading = read_power(pwr, debug=False)
                if reading is not None:
                    readings.append(reading)
                    print(f"Reading {i+1}: {reading:.1f} dBm")
                time.sleep(0.5)
            
            if readings:
                avg_reading = np.mean(readings)
                std_reading = np.std(readings)
                print(f"\nAverage: {avg_reading:.1f} dBm")
                print(f"Std Dev: {std_reading:.1f} dBm")
                
                self.status.config(text=f"Debug complete. Avg: {avg_reading:.1f} dBm, StdDev: {std_reading:.1f} dBm")
            else:
                self.status.config(text="Debug failed - no valid readings")
            
            pwr.close()
            
        except Exception as e:
            self.status.config(text=f"Debug error: {e}")
            messagebox.showerror("Debug Error", f"Power meter debug failed: {e}")
            print(f"[ERROR] Debug failed: {e}")

    def update_plot(self, iteration, power, axis, position):
        self.iterations.append(iteration)
        self.powers.append(power)
        self.colors.append(AXIS_COLORS[axis])
        self.positions.append(position.copy())
        self.ax.clear()
        self.ax.set_title("Power vs Iteration")
        self.ax.scatter(self.iterations, self.powers, c=self.colors)
        self.ax.grid(True)
        self.canvas.draw()

    def get_scan_parameters(self):
        """Get scan parameters for enabled axes"""
        scan_params = {}
        enabled_axes = []
        
        for axis in AXES:
            if self.axis_enabled[axis].get():
                try:
                    start = float(self.axis_entries[axis]['start'].get())
                    stop = float(self.axis_entries[axis]['stop'].get())
                    steps = int(self.axis_entries[axis]['steps'].get())
                    
                    if steps < 2:
                        raise ValueError(f"Steps for {axis} must be >= 2")
                    
                    scan_params[axis] = np.linspace(start, stop, steps)
                    enabled_axes.append(axis)
                    
                except ValueError as e:
                    messagebox.showerror("Input Error", f"Invalid parameters for axis {axis}: {e}")
                    return None, None
        
        return scan_params, enabled_axes
    
    def run_brute_force_scan(self):
        """Run brute force 3D scanning"""
        try:
            self.status.config(text="Initializing brute force scan...")
            self.root.update()
            
            # Get scan parameters
            scan_params, enabled_axes = self.get_scan_parameters()
            if scan_params is None or not enabled_axes:
                messagebox.showwarning("No Axes Selected", "Please enable at least one axis for scanning.")
                return
            
            # Initialize instruments
            rm = pyvisa.ResourceManager()
            p1 = rm.open_resource(PUMP1_ADDRESS)
            p2 = rm.open_resource(PUMP2_ADDRESS)
            sgl = rm.open_resource(SIGNAL_ADDRESS)
            pwr = rm.open_resource(POWER_METER_ADDRESS)
            ser = serial.Serial(STAGE_PORT, baudrate=BAUDRATE, timeout=1)
            ser.reset_input_buffer()
            
            # Setup lasers
            setup_pump(p1, self.pump1_current.get() / 1000)
            setup_pump(p2, self.pump2_current.get() / 1000)
            setup_signal(sgl, self.signal_power.get())
            
            # Get origin positions
            origin_positions = get_all_positions(ser)
            
            self.status.config(text=f"Scanning {len(enabled_axes)}D grid on axes: {', '.join(enabled_axes)}")
            self.root.update()
            
            # Clear previous data
            self.iterations, self.powers, self.colors, self.positions = [], [], [], []
            
            # Progress callback
            def update_progress(current, total):
                self.status.config(text=f"Scanning: {current}/{total} ({100*current/total:.1f}%)")
                self.root.update()
            
            # Perform brute force scan
            scan_data = brute_force_3d_scan(pwr, ser, scan_params, origin_positions, update_progress)
            
            # Process data for plotting
            for i, point in enumerate(scan_data):
                self.update_plot(i, point['power'], enabled_axes[0], point['position'])
            
            # Generate and save heatmaps
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_dir = os.path.join("log", f"scan_{timestamp}")
            os.makedirs(log_dir, exist_ok=True)
            
            generate_heatmaps(scan_data, enabled_axes, timestamp, log_dir)
            
            # Save scan data
            self.save_scan_results(scan_data, enabled_axes, timestamp, log_dir)
            
            # Display results
            if scan_data:
                best_point = max(scan_data, key=lambda x: x['power'])
                best_power = best_point['power']
                best_pos = best_point['position']
                pos_str = ', '.join([f"{a}:{best_pos[a]:.0f}" for a in AXES])
                self.status.config(text=f"Scan Complete! Max: {best_power:.1f} dBm @ {pos_str}")
            else:
                self.status.config(text="Scan completed - no data collected")
            
            # Cleanup
            p1.write("OUTP:STAT OFF")
            p2.write("OUTP:STAT OFF")
            sgl.write(":SOUR1:POW:STAT OFF")
            p1.close(); p2.close(); sgl.close(); pwr.close(); ser.close()
            
        except Exception as e:
            self.status.config(text=f"[ERROR] {e}")
            messagebox.showerror("Error", f"Brute force scan failed: {e}")
            print(e)
    
    def run_climb_hill(self):
        """Run hill climbing optimization (random walk + hill climb)"""
        try:
            self.status.config(text="Initializing hill climb...")
            self.root.update()

            # Initialize instruments
            rm = pyvisa.ResourceManager()
            p1 = rm.open_resource(PUMP1_ADDRESS)
            p2 = rm.open_resource(PUMP2_ADDRESS)
            sgl = rm.open_resource(SIGNAL_ADDRESS)
            pwr = rm.open_resource(POWER_METER_ADDRESS)
            ser = serial.Serial(STAGE_PORT, baudrate=BAUDRATE, timeout=1)
            ser.reset_input_buffer()

            # Setup lasers
            setup_pump(p1, self.pump1_current.get() / 1000)
            setup_pump(p2, self.pump2_current.get() / 1000)
            setup_signal(sgl, self.signal_power.get())

            # Get origin positions
            origin_positions = get_all_positions(ser)
            
            # Clear previous data
            self.iterations, self.powers, self.colors, self.positions = [], [], [], []
            
            self.status.config(text="Running hill climb optimization...")
            self.root.update()
            
            i = 0
            position = origin_positions.copy()
            
            # Random walk first
            self.status.config(text="Phase 1: Random walk exploration...")
            self.root.update()
            for axis, pos, pwrval in random_walk(pwr, ser, position, 20, INITIAL_STEP):
                self.update_plot(i, pwrval, axis, pos)
                i += 1
                self.root.update()
                
            # Then hill climb
            self.status.config(text="Phase 2: Hill climb optimization...")
            self.root.update()
            for axis, pos, pwrval in hill_climb(pwr, ser, position, INITIAL_STEP):
                self.update_plot(i, pwrval, axis, pos)
                i += 1
                self.root.update()

            # Return to origin
            self.status.config(text="Returning to origin positions...")
            self.root.update()
            for ax in AXES:
                move_axis_to(ser, ax, origin_positions[ax])

            # Display results
            if self.powers:
                max_idx = np.argmax(self.powers)
                best = self.powers[max_idx]
                pos_str = ', '.join([f"{a}:{self.positions[max_idx][a]:.0f}" for a in AXES])
                self.status.config(text=f"Hill climb complete! Max: {best:.1f} dBm @ {pos_str}")
            else:
                self.status.config(text="Hill climb completed - no data collected")

            self.save_results()

            # Cleanup
            p1.write("OUTP:STAT OFF")
            p2.write("OUTP:STAT OFF")
            sgl.write(":SOUR1:POW:STAT OFF")
            p1.close(); p2.close(); sgl.close(); pwr.close(); ser.close()

        except Exception as e:
            self.status.config(text=f"[ERROR] {e}")
            messagebox.showerror("Error", f"Hill climb failed: {e}")
            print(e)

    def save_results(self):
        """Save hill climb results"""
        os.makedirs("log", exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        with open(f"log/climb_hill_{ts}.csv", "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Iteration", "Power (dBm)", "Axis"] + AXES)
            for i, (pwr, color, pos) in enumerate(zip(self.powers, self.colors, self.positions)):
                # Find axis from color
                axis = [a for a, c in AXIS_COLORS.items() if c == color][0] if color in AXIS_COLORS.values() else 'Unknown'
                writer.writerow([i, pwr, axis] + [pos[a] for a in AXES])
        self.fig.savefig(f"log/climb_hill_plot_{ts}.png")
        print(f"[INFO] Hill climb results saved to log/climb_hill_{ts}.*")
    
    def save_scan_results(self, scan_data, enabled_axes, timestamp, log_dir):
        """Save brute force scan results"""
        with open(os.path.join(log_dir, f"scan_data_{timestamp}.csv"), "w", newline="") as f:
            writer = csv.writer(f)
            header = ["Index", "Power (dBm)"] + [f"{ax}_Position" for ax in AXES]
            writer.writerow(header)
            
            for point in scan_data:
                row = [point['index'], point['power']] + [point['position'][ax] for ax in AXES]
                writer.writerow(row)
        
        # Save current plot
        self.fig.savefig(os.path.join(log_dir, f"scan_plot_{timestamp}.png"))
        
        print(f"[INFO] Scan results saved to {log_dir}")

# Launch GUI
if __name__ == "__main__":
    root = tk.Tk()
    app = OptimizerApp(root)
    root.mainloop()
