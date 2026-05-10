@echo off
REM Build script for wfbInstaller on Windows
REM This creates a standalone .exe file for Windows

echo ========================================
echo wfbInstaller - Windows Build Script
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.7+ from https://www.python.org
    pause
    exit /b 1
)

echo Installing build dependencies...
pip install -q -r requirements-build.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo Building standalone Windows executable...
pyinstaller --onefile --console --name wfbinstaller wfbinstaller.spec

if errorlevel 1 (
    echo ERROR: Build failed
    pause
    exit /b 1
)

echo.
echo ========================================
echo Build completed successfully!
echo ========================================
echo.
echo Output: dist\wfbinstaller.exe
echo.
echo You can now distribute this .exe file to Windows users.
echo They can run it directly without installing Python or dependencies.
echo.
pause
