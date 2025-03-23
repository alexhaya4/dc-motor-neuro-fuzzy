# Neuro-Fuzzy DC Motor Control System

This educational system demonstrates the application of Neuro-Fuzzy control techniques for DC motor speed control. The system allows comparison between conventional controllers (PI, PID) and adaptive Neuro-Fuzzy controllers.

## Installation

To install the system, simply run:
This will set up a Python virtual environment and install all required dependencies.

## Running the Application

There are two ways to run the application:

1. **Using the desktop shortcut:**  
   Double-click the "DC Motor Control" icon on your desktop.

2. **Using the command line:**
## Hardware Requirements

- Raspberry Pi (3 or 4 recommended)
- L298N motor driver
- 12V DC motor
- IR reflective sensor
- Appropriate power supply for the motor

## Hardware Connections

- Connect motor driver inputs IN1 and IN2 to GPIO pins 17 and 18
- Connect motor driver enable pin ENA to GPIO pin 12
- Connect IR sensor output to GPIO pin 23

## Features

- Real-time motor speed control
- Multiple controller types (PI, PID, ANFIS)
- Data logging and analysis
- Neural network training
- Performance visualization

## Troubleshooting

If you encounter any issues:

1. Ensure all hardware connections are correct
2. Check that the motor power supply is adequate
3. Verify that the IR sensor is properly aligned with the motor shaft
4. Run `sudo chmod a+rw /dev/gpiomem` if permission errors occur

## Educational Resources

This system is designed as a teaching tool for control theory and artificial intelligence concepts. For more information, see the "Educational Guide" tab in the application.
