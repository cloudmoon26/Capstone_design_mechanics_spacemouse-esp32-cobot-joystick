# Capstone_design_mechanics_spacemouse-esp32-cobot-joystick
ESP32 reads 6-DoF SpaceMouse over UART and streams commands to a PC/Python controller for real-time cobot jogging (OLED/buttons/battery included).

dcp3_spacemouse.ino: Spacemouse coordinate extraction code

test.py: dcp3 Python code

<img src ="circuit.png" width = "300">
circuit.png: This is a circuit diagram, but the spacemouse is not included. The spacemouse's TX (green) is connected to GPIO16, RX (orange) is connected to GPIO17, VCC (red) is connected to 3.3V, and GND (black) is connected to GND.


