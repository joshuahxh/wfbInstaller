#!/bin/bash

# Build script for wfbInstaller on macOS and Linux
# This creates standalone executables for your platform

set -e

echo "========================================"
echo "wfbInstaller - Build Script"
echo "========================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed"
    echo "Please install Python 3.7+ first"
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python version: $PYTHON_VERSION"
echo ""

# Detect OS
OS=$(uname -s)
if [[ "$OS" == "Darwin" ]]; then
    echo "Detected: macOS"
    PLATFORM="macos"
elif [[ "$OS" == "Linux" ]]; then
    echo "Detected: Linux"
    PLATFORM="linux"
else
    echo "Unsupported OS: $OS"
    exit 1
fi

echo ""
echo "Installing build dependencies..."
pip3 install -q -r requirements-build.txt

echo ""
echo "Building standalone executable for $PLATFORM..."

if [[ "$PLATFORM" == "macos" ]]; then
    pyinstaller --onefile --console --name wfbinstaller wfbinstaller.spec
    if [ $? -eq 0 ]; then
        echo ""
        echo "========================================"
        echo "Build completed successfully!"
        echo "========================================"
        echo ""
        echo "Output: dist/wfbinstaller (or dist/wfbinstaller.app)"
        echo ""
        echo "macOS users can run:"
        echo "  ./dist/wfbinstaller"
        echo ""
        echo "Or distribute the executable to other macOS users."
        echo ""
    else
        echo "ERROR: Build failed"
        exit 1
    fi
else
    # Linux build
    pyinstaller --onefile --console --name wfbinstaller wfbinstaller.spec
    if [ $? -eq 0 ]; then
        # Make executable
        chmod +x dist/wfbinstaller

        echo ""
        echo "========================================"
        echo "Build completed successfully!"
        echo "========================================"
        echo ""
        echo "Output: dist/wfbinstaller"
        echo ""
        echo "Linux users can run:"
        echo "  ./dist/wfbinstaller"
        echo ""
        echo "Or distribute the executable to other Linux users."
        echo ""
    else
        echo "ERROR: Build failed"
        exit 1
    fi
fi
