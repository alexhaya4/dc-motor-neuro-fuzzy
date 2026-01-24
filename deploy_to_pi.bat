@echo off
REM Deployment script for DC Motor Control System to Raspberry Pi (Windows)
REM Usage: deploy_to_pi.bat

set PI_USER=wajeru
set PI_IP=192.168.100.106
set PI_DIR=DC-Control_v1.0

echo.
echo ========================================
echo Deploying DC Motor Control System to Raspberry Pi
echo ========================================
echo Target: %PI_USER%@%PI_IP%
echo Directory: ~/%PI_DIR%
echo.

REM Test connection
echo Testing SSH connection...
ssh -o ConnectTimeout=5 %PI_USER%@%PI_IP% "echo Connection successful" >nul 2>&1
if errorlevel 1 (
    echo ERROR: Cannot connect to Raspberry Pi
    echo Please check:
    echo   1. IP address is correct: %PI_IP%
    echo   2. Raspberry Pi is powered on and connected
    echo   3. SSH is enabled on the Pi
    pause
    exit /b 1
)
echo Connection successful!
echo.

REM Create directory
echo Creating directory on Raspberry Pi...
ssh %PI_USER%@%PI_IP% "mkdir -p %PI_DIR%"
echo.

REM Transfer files using SCP
echo Transferring files (this may take a minute)...
echo.

REM Copy all Python files
scp *.py %PI_USER%@%PI_IP%:%PI_DIR%/

REM Copy configuration and documentation
scp requirements.txt .env.example .gitignore %PI_USER%@%PI_IP%:%PI_DIR%/
scp *.md %PI_USER%@%PI_IP%:%PI_DIR%/
scp LICENSE %PI_USER%@%PI_IP%:%PI_DIR%/

REM Copy directories
scp -r tests %PI_USER%@%PI_IP%:%PI_DIR%/
scp -r .github %PI_USER%@%PI_IP%:%PI_DIR%/

REM Copy icon if exists
scp icon.png %PI_USER%@%PI_IP%:%PI_DIR%/ 2>nul

echo.
echo Files transferred successfully!
echo.

REM Rename to include space
echo Renaming directory to 'DC-Control v1.0'...
ssh %PI_USER%@%PI_IP% "mv %PI_DIR% 'DC-Control v1.0' 2>/dev/null || true"
set PI_DIR=DC-Control v1.0
echo.

REM Setup instructions
echo ========================================
echo Deployment Complete!
echo ========================================
echo.
echo Next steps on Raspberry Pi:
echo.
echo 1. SSH into your Pi:
echo    ssh %PI_USER%@%PI_IP%
echo.
echo 2. Navigate to project:
echo    cd "%PI_DIR%"
echo.
echo 3. Install dependencies:
echo    pip3 install -r requirements.txt
echo.
echo 4. Update TensorFlow (recommended):
echo    pip3 install --upgrade tensorflow
echo.
echo 5. Generate model checksums (if you have models):
echo    python3 -c "from nn_models import compute_file_checksum, save_checksum; import os; [save_checksum(f'models/{f}', compute_file_checksum(f'models/{f}')) for f in os.listdir('models') if f.endswith('.h5')]"
echo.
echo 6. Run tests:
echo    pytest tests/ -v
echo.
echo 7. Run the application:
echo    python3 modern_motor_gui.py
echo.
pause
