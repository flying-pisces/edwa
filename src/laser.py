import pyvisa
import time

VISA_ADDRESS = "USB0::0x1313::0x804F::M01093719::0::INSTR"

rm = pyvisa.ResourceManager()
inst = rm.open_resource(VISA_ADDRESS)

# Optional: Print IDN string
print("IDN:", inst.query("*IDN?"))

# Reset the device
inst.write("*RST")

# Enable LD output
inst.write("OUTP:STAT ON")

# Set laser diode current mode
inst.write("SOUR:FUNC:MODE CURR")

# Set current limit to 80 mA
inst.write("SOUR:CURR:LIM:AMPL 0.08")

# Set current setpoint to 50 mA
inst.write("SOUR:CURR:LEV:IMM:AMPL 0.05")

# Wait a moment for stabilization
time.sleep(1)

# Query actual LD current
ld_current = inst.query("SENS3:CURR:DC:DATA?")
print(f"LD current: {float(ld_current)*1000:.2f} mA")

# Turn off LD output when done
inst.write("OUTP:STAT OFF")

# Close connection
inst.close()
