import serial
from vimba import Vimba
import cv2
import os

# ---- 1. Read Stage Positions ----
ser = serial.Serial('COM3', baudrate=38400, timeout=0.5)

def get_axis_position(axis):
    cmd = f'AXI{axis}:POS?\r'
    ser.write(cmd.encode('ascii'))
    resp = ser.readline().decode('ascii').strip()
    print(f"Axis {axis} position: {resp}")
    return resp

x_pos = get_axis_position('X')
y_pos = get_axis_position('Y')
z_pos = get_axis_position('Z')
u_pos = get_axis_position('U')
v_pos = get_axis_position('V')
w_pos = get_axis_position('W')
ser.close()