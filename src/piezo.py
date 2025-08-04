import os
import csv
import time
import serial
import pyvisa
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path  # ✅ Fix for line 46
from datetime import datetime
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import Matern, WhiteKernel, ConstantKernel
import tkinter as tk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


# Constants
PIEZO_PORT = "COM6"
KEYSIGHT_IP = "TCPIP0::100.65.16.193::inst0::INSTR"
INITIAL_STEP = 1000  # in nm (10 µm)
MIN_STEP = 10  # in nm
AXES = ['X', 'Y', 'Z']
AXIS_COLORS = {'X': 'red', 'Y': 'green', 'Z': 'blue'}
PNG_SAVE_INTERVAL = 1800  # 30 minutes
INDEX_MATCHING = 35

# Read Keysight optical power
def read_power(inst):
    try:
        inst.write("READ3:POW?")
        flag = INDEX_MATCHING + float(inst.read())
        return flag
    except Exception as e:
        print(f"[ERROR] Keysight read failed: {e}")
        return None

# Move piezo axis
def move_piezo(ser, axis, value):
    cmd = f"{axis}{value:+d}\r\n".encode()
    ser.write(cmd)
    time.sleep(0.05)

# Load DS102 final position
def load_ds102_final():
    try:
        logs = sorted(Path("log").glob("ds102_opt_log_*.csv"), reverse=True)
        if not logs:
            raise FileNotFoundError("No DS102 log file found.")
        with open(logs[0], "r") as f:
            lines = f.readlines()
            for i, line in enumerate(lines):
                if "Final Position" in line:
                    values = list(map(int, lines[i+1].split(",")[1:4]))
                    return dict(zip(AXES, values))
    except Exception as e:
        print(f"[WARN] Failed to load DS102 position: {e}")
    return dict((a, 0) for a in AXES)

# Fit surrogate model
def fit_gp_model(X, y):
    kernel = C(1.0, (1e-3, 1e3)) * Matern(nu=2.5) + WhiteKernel()
    gp = GaussianProcessRegressor(kernel=kernel, normalize_y=True, n_restarts_optimizer=5)
    gp.fit(X, y)
    return gp

# GUI Application
class PiezoOptimizerApp:
    def __init__(self, root):
        self.root = root
        root.title("Piezo XYZ Optimizer")

        # Init plot
        self.fig, self.ax = plt.subplots(figsize=(10, 5))
        self.canvas = FigureCanvasTkAgg(self.fig, master=root)
        self.canvas.get_tk_widget().pack()
        self.label = tk.Label(root, text="Initializing...", font=("Arial", 12))
        self.label.pack(pady=5)

        # Data holders
        self.iterations = []
        self.powers = []
        self.colors = []
        self.positions = []
        self.step_size = INITIAL_STEP
        self.position = load_ds102_final()
        self.iteration = 0
        self.last_save_time = time.time()

        # Start optimizer
        root.after(100, self.start_optimization)

    def update_plot(self):
        self.ax.clear()
        self.ax.set_title(f"Piezo Optimization: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.ax.set_xlabel("Iteration")
        self.ax.set_ylabel("Power (dBm)")
        self.ax.grid(True)
        for ax in AXES:
            self.ax.plot([], [], color=AXIS_COLORS[ax], label=ax)
        self.ax.legend()
        self.ax.scatter(self.iterations, self.powers, c=self.colors)
        self.canvas.draw()

        # Intermediate PNG
        if time.time() - self.last_save_time > PNG_SAVE_INTERVAL:
            self.last_save_time = time.time()
            self.fig.savefig(f"log/piezo_plot_intermediate_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")

    def start_optimization(self):
        try:
            os.makedirs("log", exist_ok=True)
            rm = pyvisa.ResourceManager()
            self.inst = rm.open_resource(KEYSIGHT_IP)
            self.inst.timeout = 2000
            self.label.config(text=f"[INFO] Connected to Keysight: {self.inst.query('*IDN?').strip()}")

            self.ser = serial.Serial(PIEZO_PORT, baudrate=9600, timeout=1)
            time.sleep(1)
            self.ser.reset_input_buffer()

            self.optimize_loop()

        except Exception as e:
            self.label.config(text=f"[ERROR] {e}")

    def optimize_loop(self):
        max_power = -np.inf
        recent_powers = []

        while self.step_size >= MIN_STEP:
            improved = False
            for axis in AXES:
                for direction in [+1, -1]:
                    move_piezo(self.ser, axis, direction * self.step_size)
                    power = read_power(self.inst)
                    if power is None:
                        continue

                    pos = self.position.copy()
                    pos[axis] += direction * self.step_size
                    self.positions.append(pos.copy())
                    self.iterations.append(self.iteration)
                    self.colors.append(AXIS_COLORS[axis])
                    self.powers.append(power)
                    recent_powers.append(power)
                    if len(recent_powers) > 10:
                        recent_powers.pop(0)

                    self.update_plot()
                    self.iteration += 1

                    # Check for improvement
                    if power > max_power + 0.02:
                        self.position[axis] += direction * self.step_size
                        max_power = power
                        improved = True
                    else:
                        move_piezo(self.ser, axis, -direction * self.step_size)  # revert

            if not improved:
                filtered = uniform_filter1d(self.powers[-10:], size=5)
                if np.std(filtered) < 0.01:  # Stability threshold
                    break
                self.step_size //= 2

        # Fit GP model for final overlay (not shown here for brevity)
        self.save_results()

    def save_results(self):
        final_idx = np.argmax(self.powers)
        final_power = self.powers[final_idx]
        final_pos = self.positions[final_idx]
        self.ax.scatter(self.iterations[final_idx], final_power, s=100, c='yellow', edgecolors='black', label='Best')
        self.ax.legend()
        self.canvas.draw()

        self.label.config(
            text=f"[DONE] Max Power: {final_power:.4f} dBm\nFinal Pos: {final_pos}"
        )

        # Save log
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        with open(f"log/piezo_opt_log_{ts}.csv", "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Iteration", "Power", "Axis", "X", "Y", "Z"])
            for i, (p, c, pos) in enumerate(zip(self.powers, self.colors, self.positions)):
                axis = [a for a, clr in AXIS_COLORS.items() if clr == c][0]
                writer.writerow([i, p, axis, pos['X'], pos['Y'], pos['Z']])
        self.fig.savefig(f"log/piezo_final_plot_{ts}.png")

# Run GUI
if __name__ == "__main__":
    root = tk.Tk()
    app = PiezoOptimizerApp(root)
    root.mainloop()
