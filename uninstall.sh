#!/bin/bash

echo "Uninstalling DC Motor Neuro-Fuzzy Control System..."

# Stop any running instances
pkill -f dc_motor_gui.py

# Remove desktop shortcut
rm -f ~/Desktop/DCMotorControl.desktop

# Clean up virtual environment and generated files
read -p "Do you want to remove all files including saved models and logs? (y/n): " confirm
if [[ $confirm == [yY] || $confirm == [yY][eE][sS] ]]; then
    echo "Removing all files..."
    rm -rf venv models logs
    rm -f *.png
    echo "Files removed. The code files and scripts are still present."
else
    echo "Keeping saved files. Only removing configuration."
fi

echo "Uninstallation complete!"
