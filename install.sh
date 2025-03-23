#!/bin/bash

echo "Installing DC Motor Neuro-Fuzzy Control System..."

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
    echo "Virtual environment created."
else
    echo "Virtual environment already exists."
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install required packages
echo "Installing required packages..."
pip install numpy scipy scikit-fuzzy tensorflow matplotlib PyQt5

# Check if GPIO library is accessible
python3 -c "import RPi.GPIO" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Installing RPi.GPIO..."
    pip install RPi.GPIO
fi

# Create models directory if it doesn't exist
if [ ! -d "models" ]; then
    echo "Creating models directory..."
    mkdir models
fi

# Create logs directory if it doesn't exist
if [ ! -d "logs" ]; then
    echo "Creating logs directory..."
    mkdir logs
fi

# Make main script executable
chmod +x dc_motor_gui.py

echo "Installation complete!"
echo "You can now run the application with: ./run.sh"
