import tkinter as tk
from tkinter import ttk, messagebox
import serial
import time
import numpy as np
import os
import datetime
from PIL import Image, ImageTk
import xmlrpc.client

DUT_SERIAL_PORT = 'COM3'
CAMERA_SERIAL_PORT = 'COM5'
BAUDRATE = 38400

def get_rayci_proxy():
    server_url = "http://localhost:8080/"
    return xmlrpc.client.ServerProxy(server_url)

def capture_bmp(rayci, filename):
    try:
        result = rayci.RayCi.LiveMode.Measurement.newSingle()
        rayci.RayCi.LiveMode.TwoD.View.exportView(0, filename)
        print(f"Saved image to {filename}")
    except Exception as e:
        print(f"RayCi image capture failed: {e}")

def get_positions_for_axes(port, axes):
    positions = {}
    try:
        ser = serial.Serial(port, baudrate=BAUDRATE, timeout=0.5)
        for axis in axes:
            try:
                ser.reset_input_buffer()
                ser.reset_output_buffer()
                cmd = f'AXI{axis}:POS?\r'
                ser.write(cmd.encode('ascii'))
                time.sleep(0.1)
                resp = ser.readline().decode('ascii').strip()
                if resp:
                    try:
                        positions[axis] = str(int(float(resp)))
                    except ValueError:
                        positions[axis] = resp
                else:
                    positions[axis] = 'NA'
            except Exception:
                positions[axis] = 'NA'
        ser.close()
    except Exception:
        for axis in axes:
            positions[axis] = 'NA'
    return positions

def move_axis_to(ser, axis, pos):
    try:
        cmd = f'AXI{axis}:GOABS {int(round(float(pos)))}\r'
        ser.write(cmd.encode('ascii'))
        while True:
            ser.write(f'AXI{axis}:MOTION?\r'.encode('ascii'))
            resp = ser.readline().decode('ascii').strip()
            if resp == '0':
                break
            time.sleep(0.05)
    except Exception as e:
        print(f"Error moving axis {axis}: {e}")

class DualStageScanGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("DS102 Multi-Axis Scan & RayCi Image Capture")
        self.geometry("1550x750")
        self.dut_axes = ['X', 'Y', 'Z', 'U', 'V', 'W']
        self.camera_axes = ['X', 'Y']
        self.entries = {}
        self.check_vars = {}

        self.dut_origin = get_positions_for_axes(DUT_SERIAL_PORT, self.dut_axes)
        self.camera_origin = get_positions_for_axes(CAMERA_SERIAL_PORT, self.camera_axes)

        # --- DUT Umbrella Group (smaller) ---
        self.dut_frame = tk.LabelFrame(self, text="DUT (COM3)", font=("Arial", 13, "bold"), bg="#ccc", bd=3, relief="groove")
        self.dut_frame.place(x=20, y=20, width=480, height=240)

        header = ["Axis", "Enable", "Origin", "Start (pulse)", "Stop (pulse)", "Step (count)"]
        for i, label in enumerate(header):
            tk.Label(self.dut_frame, text=label, font=('Arial', 10, 'bold'), bg="#ccc").grid(row=0, column=i, padx=5, pady=2)

        self.entries['DUT'] = {}
        self.check_vars['DUT'] = {}
        for i, axis in enumerate(self.dut_axes):
            tk.Label(self.dut_frame, text=axis, bg="#ccc").grid(row=i+1, column=0)
            self.check_vars['DUT'][axis] = tk.BooleanVar(value=False)
            cb = tk.Checkbutton(self.dut_frame, variable=self.check_vars['DUT'][axis], bg="#ccc")
            cb.grid(row=i+1, column=1)
            self.entries['DUT'][axis] = {}
            val = self.dut_origin[axis]
            ent = tk.Entry(self.dut_frame, width=9, fg="black", readonlybackground="#ccc")
            ent.grid(row=i+1, column=2)
            ent.insert(0, str(val))
            ent.config(state="readonly")
            self.entries['DUT'][axis]['origin'] = ent
            for j, name in enumerate(['start', 'stop', 'step']):
                ent2 = tk.Entry(self.dut_frame, width=9)
                ent2.grid(row=i+1, column=3+j)
                self.entries['DUT'][axis][name] = ent2

        # --- Camera Umbrella Group (same layout as DUT) ---
        self.camera_frame = tk.LabelFrame(self, text="Camera (COM5)", font=("Arial", 13, "bold"), bg="#bbb", bd=3, relief="groove")
        self.camera_frame.place(x=20, y=280, width=480, height=120)

        for i, label in enumerate(header):
            tk.Label(self.camera_frame, text=label, font=('Arial', 10, 'bold'), bg="#bbb").grid(row=0, column=i, padx=5, pady=2)

        self.entries['CAMERA'] = {}
        self.check_vars['CAMERA'] = {}
        for i, axis in enumerate(self.camera_axes):
            tk.Label(self.camera_frame, text=axis, bg="#bbb").grid(row=i+1, column=0)
            self.check_vars['CAMERA'][axis] = tk.BooleanVar(value=False)
            cb = tk.Checkbutton(self.camera_frame, variable=self.check_vars['CAMERA'][axis], bg="#bbb")
            cb.grid(row=i+1, column=1)
            self.entries['CAMERA'][axis] = {}
            val = self.camera_origin[axis]
            ent = tk.Entry(self.camera_frame, width=9, fg="black", readonlybackground="#bbb")
            ent.grid(row=i+1, column=2)
            ent.insert(0, str(val))
            ent.config(state="readonly")
            self.entries['CAMERA'][axis]['origin'] = ent
            for j, name in enumerate(['start', 'stop', 'step']):
                ent2 = tk.Entry(self.camera_frame, width=9)
                ent2.grid(row=i+1, column=3+j)
                self.entries['CAMERA'][axis][name] = ent2

        self.unitset_btn = tk.Button(self, text="Unit Set", command=self.open_unitset)
        self.unitset_btn.place(x=60, y=550, width=120, height=36)
        self.start_btn = tk.Button(self, text="Start Scan", command=self.start_scan)
        self.start_btn.place(x=220, y=550, width=120, height=36)

        self.progress_label = tk.Label(self, text="", font=('Arial', 12, 'bold'), fg="blue")
        self.progress_label.place(x=370, y=550, width=370, height=36)

        self.image_panel = tk.Label(self, text="Scan image preview here", width=632, height=504, bg="#EEE", anchor='center', relief="sunken")
        self.image_panel.place(x=600, y=20, width=632, height=504)

    def open_unitset(self):
        messagebox.showinfo("Unit Set", "Unit Set dialog logic not yet implemented for dual-stage.")

    def show_scan_image(self, image_path):
        try:
            im = Image.open(image_path)
            photo = ImageTk.PhotoImage(im)
            self.image_panel.configure(image=photo, text="")
            self.image_panel.image = photo
        except Exception as e:
            self.image_panel.configure(text="(Image failed to load)")

    def start_scan(self):
        dut_enabled = any(self.check_vars['DUT'][ax].get() for ax in self.dut_axes)
        cam_enabled = any(self.check_vars['CAMERA'][ax].get() for ax in self.camera_axes)
        if dut_enabled and cam_enabled:
            messagebox.showerror("Scan Error", "Please enable axes for ONLY ONE group (either DUT or Camera) at a time.")
            return
        if not dut_enabled and not cam_enabled:
            messagebox.showwarning("No Axis Selected", "Please enable at least one axis in either group.")
            return

        if dut_enabled:
            stage = 'DUT'
            port = DUT_SERIAL_PORT
            axes = self.dut_axes
            origin = self.dut_origin
            log_group = "DUT"
        else:
            stage = 'CAMERA'
            port = CAMERA_SERIAL_PORT
            axes = self.camera_axes
            origin = self.camera_origin
            log_group = "camera"

        scan_params = {}
        for ax in axes:
            if self.check_vars[stage][ax].get():
                try:
                    start = float(self.entries[stage][ax]['start'].get())
                    stop = float(self.entries[stage][ax]['stop'].get())
                    step = int(float(self.entries[stage][ax]['step'].get()))
                    if step < 2:
                        messagebox.showerror("Input Error", f"Step (count) for {ax} must be integer ≥2.")
                        return
                    scan_params[ax] = np.linspace(start, stop, step)
                except Exception:
                    messagebox.showerror("Input Error", f"Invalid range/step for {ax}")
                    return
            else:
                origin_val = origin[ax]
                if origin_val == 'NA':
                    messagebox.showerror("Axis Error", f"Origin value not available for {ax}")
                    return
                scan_params[ax] = np.array([float(origin_val)])

        if stage == 'DUT':
            other_axes = self.camera_axes
            other_origin = self.camera_origin
            other_port = CAMERA_SERIAL_PORT
        else:
            other_axes = self.dut_axes
            other_origin = self.dut_origin
            other_port = DUT_SERIAL_PORT

        other_positions = {ax: float(other_origin[ax]) if other_origin[ax] != 'NA' else 0.0 for ax in other_axes}

        log_root = os.path.join(os.getcwd(), "log", log_group)
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
        log_dir = os.path.join(log_root, timestamp)
        os.makedirs(log_dir, exist_ok=True)

        grids = [scan_params[ax] for ax in axes]
        positions = np.array(np.meshgrid(*grids, indexing='ij')).reshape(len(axes), -1).T

        try:
            ser1 = serial.Serial(port, baudrate=BAUDRATE, timeout=0.5)
            ser2 = serial.Serial(other_port, baudrate=BAUDRATE, timeout=0.5)
            origin_pulses1 = {ax: float(origin[ax]) if origin[ax] != 'NA' else 0.0 for ax in axes}
            origin_pulses2 = {ax: float(other_origin[ax]) if other_origin[ax] != 'NA' else 0.0 for ax in other_axes}
            total = len(positions)

            rayci = get_rayci_proxy()

            for idx, pos in enumerate(positions):
                for ax, val in zip(axes, pos):
                    move_axis_to(ser1, ax, val)
                for ax in other_axes:
                    move_axis_to(ser2, ax, other_positions[ax])

                pos_strs = [f"{ax.lower()}_{int(round(val))}" for ax, val in zip(axes, pos)]
                filename = os.path.join(log_dir, '_'.join(pos_strs) + '.bmp')

                # Now: Real RayCi image saved for preview and disk!
                if rayci:
                    capture_bmp(rayci, filename)
                else:
                    self.progress_label.config(text="RayCi not available; skipping image capture.")

                self.progress_label.config(text=f"Iteration {idx+1} of {total}")
                self.show_scan_image(filename)
                self.update()

            for ax in axes:
                move_axis_to(ser1, ax, origin_pulses1[ax])
            for ax in other_axes:
                move_axis_to(ser2, ax, origin_pulses2[ax])
            ser1.close()
            ser2.close()
            messagebox.showinfo("Scan Completed", "Scan complete and all axes returned to origin.")
        except Exception as e:
            messagebox.showerror("Serial Error", str(e))

if __name__ == "__main__":
    app = DualStageScanGUI()
    app.mainloop()
