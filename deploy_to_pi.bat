@echo off
REM Run the checked transfer script from WSL.
wsl.exe --cd "%~dp0." --exec bash ./deploy_to_pi.sh "%~1"
exit /b %errorlevel%
