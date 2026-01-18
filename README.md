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

### Core Control System
- **Real-time motor speed control** with hardware integration
- **4 Controller Types:**
  - PI Controller (Proportional-Integral)
  - PID Controller (with derivative filtering and anti-windup)
  - Fuzzy Logic Controller (Mamdani inference)
  - ANFIS Controller (Adaptive Neuro-Fuzzy with REAL neural networks)

### Modern GUI (v2.2)
- **3 Professional Themes** (Modern Light, Modern Dark, Classic)
- **Smooth Animations** throughout the interface
- **Thread-Safe Operation** with Queue and Lock synchronization
- **6 Functional Tabs** (Control, Plot, Tuning, Performance, Settings, Logs)

### Advanced Plotting (NEW in v2.2!) 📊
- **Multi-Trace Plot Widget:**
  - 7 configurable traces (Target, Actual, Error, PWM, P term, I term, D term)
  - Toggle traces on/off with checkboxes
  - Real-time updates (10 Hz)
  - 30-second rolling window

- **Export Functionality:**
  - Save plots as PNG (300 DPI, publication quality)
  - Export data to CSV (Excel compatible)
  - Export data to JSON (structured format with metadata)
  - Export to MATLAB .m files (with plot commands)

- **FFT Analysis:**
  - Frequency domain analysis
  - Dominant frequency detection
  - Stability checking
  - Oscillation identification

- **Phase Portrait:**
  - Error vs Error Rate visualization
  - Convergence analysis
  - Trajectory plotting
  - Stability assessment

- **Controller Comparison:**
  - Side-by-side performance comparison
  - 4 subplots (Speed, Error, PWM, Metrics)
  - Record and replay multiple runs
  - Load/save recordings

### Educational Features (NEW in v2.2!) 📚
- **8 Comprehensive Topics:**
  - PI Controller
  - PID Controller
  - Fuzzy Logic Controller
  - ANFIS Controller
  - Anti-Windup Protection
  - Derivative Filtering
  - Performance Metrics
  - Ziegler-Nichols Tuning

- **Interactive Tutorial:**
  - 7-step guided walkthrough
  - Learn-by-doing approach
  - Beginner-friendly
  - Step-by-step navigation

- **Educational Panel:**
  - Quick reference buttons
  - One-click explanations
  - Context-aware tooltips
  - Full explanation dialogs

### Advanced Features
- **Auto-Tuning:** Relay feedback method (Åström-Hägglund)
- **Data Collection:** Real optimal control data (no heuristics)
- **Neural Network Training:** TensorFlow/Keras models
- **Performance Metrics:** Overshoot, settling time, steady-state error
- **Professional Logging:** Rotating file logs with multiple levels

## Troubleshooting

If you encounter any issues:

1. Ensure all hardware connections are correct
2. Check that the motor power supply is adequate
3. Verify that the IR sensor is properly aligned with the motor shaft
4. Run `sudo chmod a+rw /dev/gpiomem` if permission errors occur

## Educational Resources

This system is designed as a teaching tool for control theory and artificial intelligence concepts. For more information, see the "Educational Guide" tab in the application.
