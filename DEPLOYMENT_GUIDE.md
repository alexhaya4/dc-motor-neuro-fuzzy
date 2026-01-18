# Deployment Guide - Push to Raspberry Pi via SSH

## 🚀 Complete Guide to Deploy DC Motor Control System to Raspberry Pi

---

## Prerequisites

### On Your Development PC (Windows)

1. **SSH Client** (Built into Windows 10/11)
   - Open PowerShell or Command Prompt
   - Test: `ssh --version`

2. **Git** (Optional but recommended)
   - Download from: https://git-scm.com/download/win
   - Or use existing Git installation

3. **Your Project Files**
   - Location: `d:\dc-motor-neuro-fuzzy\`

### On Raspberry Pi

1. **SSH Enabled**
   - Enable via `sudo raspi-config` → Interface Options → SSH → Enable
   - Or create empty file `ssh` on boot partition

2. **Network Connection**
   - Connected to same network as your PC
   - Know the Pi's IP address

3. **Python 3.7+**
   - Usually pre-installed on Raspberry Pi OS

---

## Method 1: SCP (Secure Copy) - Recommended for First Deploy

### Step 1: Find Your Raspberry Pi's IP Address

**On Raspberry Pi:**
```bash
hostname -I
# Example output: 192.168.1.100
```

**Or from your PC (if you know the hostname):**
```bash
ping raspberrypi.local
```

### Step 2: Transfer Files Using SCP

**Open PowerShell/Command Prompt on your Windows PC:**

```powershell
# Navigate to your project directory
cd d:\dc-motor-neuro-fuzzy

# Option A: Transfer entire directory (RECOMMENDED)
scp -r d:\dc-motor-neuro-fuzzy pi@192.168.1.100:/home/pi/

# Option B: Transfer to specific location
scp -r d:\dc-motor-neuro-fuzzy pi@192.168.1.100:/home/pi/motor-control

# You'll be prompted for password (default is "raspberry")
```

**What this does:**
- `scp` = Secure Copy Protocol
- `-r` = Recursive (copies entire directory)
- `pi@192.168.1.100` = Username@IP_address
- `:/home/pi/` = Destination directory on Pi

### Step 3: Connect and Verify

```bash
# SSH into Raspberry Pi
ssh pi@192.168.1.100

# Navigate to project
cd dc-motor-neuro-fuzzy

# List files
ls -la

# You should see all your files!
```

---

## Method 2: RSYNC - Best for Updates

**Advantages:**
- Only transfers changed files (faster)
- Can exclude unnecessary files
- Preserves permissions

### Initial Setup

**Install rsync on Windows (if not already installed):**
- Usually included with Git for Windows
- Or install via WSL (Windows Subsystem for Linux)

### Sync Command

```powershell
# From your project directory
cd d:\dc-motor-neuro-fuzzy

# Sync to Pi (excludes unnecessary files)
rsync -avz --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' --exclude='logs/*' --exclude='models/*' . pi@192.168.1.100:/home/pi/dc-motor-neuro-fuzzy/

# Breakdown:
#   -a = archive mode (preserves permissions)
#   -v = verbose (shows progress)
#   -z = compress during transfer
#   --exclude = skip these files/folders
#   . = current directory
```

**Create a sync script for convenience:**

**`sync_to_pi.bat`** (Windows batch file):
```batch
@echo off
echo Syncing DC Motor Control to Raspberry Pi...

set PI_IP=192.168.1.100
set PI_USER=pi
set PROJECT_DIR=d:\dc-motor-neuro-fuzzy
set PI_DIR=/home/pi/dc-motor-neuro-fuzzy

rsync -avz --exclude=".git" --exclude="__pycache__" --exclude="*.pyc" --exclude="logs/*" --exclude="models/*.keras" %PROJECT_DIR%\ %PI_USER%@%PI_IP%:%PI_DIR%/

echo.
echo Sync complete!
echo Connect with: ssh %PI_USER%@%PI_IP%
pause
```

**Usage:**
```powershell
# Just double-click sync_to_pi.bat
# Or run from command prompt:
.\sync_to_pi.bat
```

---

## Method 3: Git (Best for Version Control)

### Initial Setup on Raspberry Pi

**SSH into your Pi:**
```bash
ssh pi@192.168.1.100
```

**Option A: Clone from GitHub/GitLab (if you have a remote repo)**
```bash
cd /home/pi
git clone https://github.com/yourusername/dc-motor-neuro-fuzzy.git
cd dc-motor-neuro-fuzzy
```

**Option B: Clone from your PC (local network)**
```bash
# On your PC (in Git Bash or WSL):
cd d:\dc-motor-neuro-fuzzy
git init
git add .
git commit -m "Initial commit"

# Start a simple Git server
git daemon --base-path=. --export-all --reuseaddr --informative-errors --verbose

# On Raspberry Pi:
git clone git://192.168.1.50:9418/dc-motor-neuro-fuzzy
```

### Updating with Git

**After making changes on your PC:**

```bash
# On PC:
cd d:\dc-motor-neuro-fuzzy
git add .
git commit -m "Added advanced features"
git push origin main

# On Raspberry Pi:
cd /home/pi/dc-motor-neuro-fuzzy
git pull origin main
```

---

## Method 4: WinSCP (GUI Tool) - Easiest for Beginners

### Download and Install WinSCP

1. Download from: https://winscp.net/eng/download.php
2. Install with default settings

### Connect to Raspberry Pi

1. **Open WinSCP**
2. **New Session:**
   - File protocol: `SCP`
   - Host name: `192.168.1.100` (your Pi's IP)
   - Port: `22`
   - User name: `pi`
   - Password: `raspberry` (or your password)
3. **Click "Login"**

### Transfer Files

1. **Left panel** = Your PC (`d:\dc-motor-neuro-fuzzy`)
2. **Right panel** = Raspberry Pi (`/home/pi/`)
3. **Drag and drop** entire folder from left to right

### Advantages
- ✅ Visual interface
- ✅ Drag-and-drop
- ✅ Built-in text editor
- ✅ Can sync directories
- ✅ Shows transfer progress

---

## Post-Deployment Setup

### Step 1: SSH into Raspberry Pi

```bash
ssh pi@192.168.1.100
```

### Step 2: Navigate to Project

```bash
cd dc-motor-neuro-fuzzy
```

### Step 3: Install Dependencies

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install system dependencies
sudo apt install -y python3-pip python3-dev python3-venv libatlas-base-dev

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install project dependencies
pip install -r requirements.txt

# Note: TensorFlow on Pi may need special version
pip install tensorflow==2.15.0  # or tensorflow-lite for better performance
```

**If you get errors with TensorFlow:**
```bash
# Use TensorFlow Lite (optimized for Pi)
pip install tflite-runtime
```

### Step 4: Configure GPIO Permissions

```bash
# Add user to gpio group
sudo usermod -a -G gpio pi

# Set GPIO permissions
sudo chmod a+rw /dev/gpiomem

# Reboot to apply
sudo reboot
```

### Step 5: Test Installation

**After reboot, SSH back in:**
```bash
ssh pi@192.168.1.100
cd dc-motor-neuro-fuzzy
source venv/bin/activate

# Run tests
python -m pytest tests/ -v

# Test GPIO (basic)
python -c "import RPi.GPIO as GPIO; print('GPIO OK')"

# Test controllers
python -c "from conventional_controllers import PIDController; print('Controllers OK')"
```

### Step 6: Run the Application

```bash
# Activate environment
source venv/bin/activate

# Run main GUI
python modern_motor_gui.py

# Or run integration example
python integration_example.py
```

---

## Quick Deployment Script (All-in-One)

**Create `deploy_to_pi.bat`** on your Windows PC:

```batch
@echo off
echo ========================================
echo  DC Motor Control - Deploy to Pi
echo ========================================
echo.

REM Configuration
set PI_IP=192.168.1.100
set PI_USER=pi
set PROJECT_DIR=d:\dc-motor-neuro-fuzzy
set PI_DIR=/home/pi/dc-motor-neuro-fuzzy

echo Step 1: Syncing files to Raspberry Pi...
rsync -avz --progress --exclude=".git" --exclude="__pycache__" --exclude="*.pyc" --exclude="logs/*" --exclude="venv/*" %PROJECT_DIR%\ %PI_USER%@%PI_IP%:%PI_DIR%/

if errorlevel 1 (
    echo ERROR: File sync failed!
    pause
    exit /b 1
)

echo.
echo Step 2: Installing dependencies on Pi...
ssh %PI_USER%@%PI_IP% "cd %PI_DIR% && source venv/bin/activate 2>/dev/null || python3 -m venv venv && source venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt"

if errorlevel 1 (
    echo WARNING: Dependency installation may have issues
    echo Please check manually
)

echo.
echo ========================================
echo  Deployment Complete!
echo ========================================
echo.
echo To connect: ssh %PI_USER%@%PI_IP%
echo To run: cd %PI_DIR% ^&^& source venv/bin/activate ^&^& python modern_motor_gui.py
echo.
pause
```

**Usage:**
```powershell
.\deploy_to_pi.bat
```

---

## Troubleshooting

### Problem 1: "Permission Denied" during SCP

**Solution:**
```bash
# On Raspberry Pi:
sudo chmod 755 /home/pi
mkdir -p /home/pi/dc-motor-neuro-fuzzy
```

### Problem 2: SSH Connection Refused

**Solution:**
```bash
# On Raspberry Pi (connect monitor/keyboard):
sudo systemctl enable ssh
sudo systemctl start ssh
sudo systemctl status ssh
```

### Problem 3: Large Files Taking Forever

**Solution - Exclude unnecessary files:**
```powershell
# Don't transfer logs, models, cache
rsync -avz --exclude="logs/*" --exclude="models/*.keras" --exclude="__pycache__" . pi@IP:/path/
```

### Problem 4: TensorFlow Won't Install on Pi

**Solution - Use TensorFlow Lite:**
```bash
# Remove full TensorFlow from requirements.txt
# Install TF Lite instead
pip install tflite-runtime

# Modify anfis_controller.py to use TF Lite
```

### Problem 5: GUI Won't Start (No Display)

**Solution - Enable X11 Forwarding:**
```bash
# From your PC:
ssh -X pi@192.168.1.100

# Or use VNC:
# On Pi:
sudo raspi-config
# -> Interface Options -> VNC -> Enable

# From PC:
# Install RealVNC Viewer
# Connect to Pi's IP
```

### Problem 6: "ModuleNotFoundError"

**Solution:**
```bash
# Make sure virtual environment is activated
source venv/bin/activate

# Verify installation
pip list

# Reinstall if needed
pip install -r requirements.txt
```

---

## Best Practices

### 1. Use Version Control
```bash
# Before deploying:
git add .
git commit -m "Ready for deployment"
git push

# Easier to rollback if needed
```

### 2. Test Locally First
```bash
# On your PC:
pytest tests/ -v

# Only deploy if tests pass
```

### 3. Keep Backups
```bash
# On Raspberry Pi (before update):
cd /home/pi
tar -czf dc-motor-backup-$(date +%Y%m%d).tar.gz dc-motor-neuro-fuzzy/
```

### 4. Use Deployment Script
- Automates the process
- Reduces errors
- Saves time

### 5. Exclude Unnecessary Files
```bash
# Don't transfer:
# - .git directory
# - __pycache__
# - logs/*
# - Large model files (upload separately)
```

---

## Advanced: Continuous Deployment

### Using GitHub Actions (if you have a repo)

**`.github/workflows/deploy.yml`**:
```yaml
name: Deploy to Raspberry Pi

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2

    - name: Deploy to Pi
      uses: appleboy/scp-action@master
      with:
        host: ${{ secrets.PI_HOST }}
        username: ${{ secrets.PI_USER }}
        password: ${{ secrets.PI_PASSWORD }}
        source: "."
        target: "/home/pi/dc-motor-neuro-fuzzy"
```

---

## Quick Reference Commands

```bash
# === TRANSFER FILES ===
# SCP (entire directory)
scp -r d:\dc-motor-neuro-fuzzy pi@IP:/home/pi/

# RSYNC (sync changes only)
rsync -avz --exclude=".git" . pi@IP:/home/pi/dc-motor-neuro-fuzzy/

# === CONNECT ===
# SSH
ssh pi@IP

# SSH with X11 forwarding (for GUI)
ssh -X pi@IP

# === ON RASPBERRY PI ===
# Navigate
cd dc-motor-neuro-fuzzy

# Activate environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run application
python modern_motor_gui.py

# Run tests
pytest tests/ -v

# Check GPIO
python -c "import RPi.GPIO as GPIO; print('OK')"

# === UPDATE ===
# Pull latest from Git
git pull origin main

# Or sync from PC
rsync -avz . pi@IP:/home/pi/dc-motor-neuro-fuzzy/
```

---

## Example: Complete First Deployment

```powershell
# === ON YOUR WINDOWS PC ===

# 1. Open PowerShell
cd d:\dc-motor-neuro-fuzzy

# 2. Find Pi's IP (example: 192.168.1.100)
ping raspberrypi.local

# 3. Transfer files
scp -r . pi@192.168.1.100:/home/pi/dc-motor-neuro-fuzzy

# Enter password when prompted

# 4. Connect to Pi
ssh pi@192.168.1.100
```

```bash
# === NOW ON RASPBERRY PI ===

# 5. Navigate to project
cd dc-motor-neuro-fuzzy

# 6. Setup environment
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 7. Configure GPIO
sudo usermod -a -G gpio pi
sudo chmod a+rw /dev/gpiomem

# 8. Test
python -c "from conventional_controllers import PIDController; print('Success!')"

# 9. Run application
python integration_example.py

# Done! 🎉
```

---

## Summary

### Recommended Method for Most Users

**Initial Deployment:**
1. Use **SCP** for first transfer
2. Use **WinSCP** if you prefer GUI

**Updates:**
1. Use **RSYNC** for fast syncing
2. Use **Git** if you have version control

**Production:**
1. Use **deployment script** (deploy_to_pi.bat)
2. Automates everything
3. One-click deployment

---

## Need Help?

**Common Commands:**
```bash
# Test connection
ping 192.168.1.100

# Test SSH
ssh pi@192.168.1.100 echo "Connection OK"

# Check disk space on Pi
ssh pi@192.168.1.100 df -h

# View Pi system info
ssh pi@192.168.1.100 cat /etc/os-release
```

**Resources:**
- Raspberry Pi Documentation: https://www.raspberrypi.org/documentation/
- SSH Tutorial: https://www.raspberrypi.org/documentation/remote-access/ssh/
- WinSCP: https://winscp.net/

---

**Happy Deploying!** 🚀

For questions, check the [README.md](README.md) or project documentation.
