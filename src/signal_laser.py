import pyvisa

# Initialize VISA resource manager
rm = pyvisa.ResourceManager()

# Connect to HP8164A via GPIB
instr = rm.open_resource('GPIB0::20::INSTR')

# Optional: Set timeout and termination characters
instr.timeout = 5000  # in ms
instr.write_termination = '\n'
instr.read_termination = '\n'

# Identify the instrument
idn = instr.query('*IDN?')
print("Instrument ID:", idn)

# Example: Turn on laser output (slot dependent — assuming channel 1)
instr.write(":SOUR1:POW:STAT ON")  # Turn ON laser output
instr.write(":SOUR1:POW 0.0")      # Set power to 0.0 dBm

# Query power setting
power = instr.query(":SOUR1:POW?")
print("Current Laser Power (dBm):", power)

# Clean up
instr.close()
