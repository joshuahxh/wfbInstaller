# Building Standalone Executables for wfbInstaller

This guide explains how to create standalone executables for Windows, macOS, and Linux that don't require Python or any dependencies to be pre-installed.

## Overview

Using PyInstaller, we can bundle the Python application and all its dependencies into a single executable file that works on any machine with the same OS.

## Requirements for Building

- Python 3.7 or later (to run the build)
- PyInstaller 6.1.0 (installed automatically by build script)
- The appropriate OS (Windows to build .exe, macOS to build macOS binary, Linux to build Linux binary)

## Building on Windows

### Step 1: Install Python (if not already installed)
Download from https://www.python.org/downloads/ and ensure "Add Python to PATH" is checked.

### Step 2: Run the Build Script
```bash
cd wfbInstaller
build.bat
```

### Step 3: Find the Executable
The built executable will be at: `dist\wfbinstaller.exe`

### Step 4: Test the Executable (Optional)
```bash
dist\wfbinstaller.exe --help
```

### Distributing on Windows
Simply share the `.exe` file. Windows users can:
1. Download the `.exe`
2. Run it directly (no installation needed)
3. Place it in a directory in their PATH for command-line access

**Note**: Some antivirus software may flag the executable. This is normal for PyInstaller binaries. You can sign the executable with a code signing certificate to prevent warnings.

---

## Building on macOS

### Step 1: Install Python (if not already installed)
```bash
# Using Homebrew (recommended)
brew install python3

# Or download from https://www.python.org/downloads/
```

### Step 2: Install libmtp (optional, for MTP support)
```bash
brew install libmtp
```

### Step 3: Run the Build Script
```bash
cd wfbInstaller
chmod +x build.sh
./build.sh
```

### Step 4: Find the Executable
The built executable will be at: `dist/wfbinstaller` (or `dist/wfbinstaller.app` for app bundle)

### Step 5: Test the Executable (Optional)
```bash
./dist/wfbinstaller --help
```

### Distributing on macOS
Simply share the executable file. macOS users can:
1. Download the executable
2. Make it executable: `chmod +x wfbinstaller`
3. Run it: `./wfbinstaller`

**Note**: On first run, macOS may show a security warning. Users can allow it in System Preferences > Security & Privacy.

---

## Building on Linux

### Step 1: Install Python and Dependencies
```bash
# Ubuntu/Debian
sudo apt-get install python3 python3-pip libmtp9 libusb-1.0-0

# Fedora/RHEL
sudo dnf install python3 python3-pip libmtp libusb

# Arch
sudo pacman -S python python-pip libmtp libusb
```

### Step 2: Run the Build Script
```bash
cd wfbInstaller
chmod +x build.sh
./build.sh
```

### Step 3: Find the Executable
The built executable will be at: `dist/wfbinstaller`

### Step 4: Test the Executable (Optional)
```bash
./dist/wfbinstaller --help
```

### Distributing on Linux
Simply share the executable file. Linux users can:
1. Download the executable
2. Make it executable: `chmod +x wfbinstaller`
3. Run it: `./wfbinstaller`

Or place in a system directory:
```bash
sudo cp wfbinstaller /usr/local/bin/
wfbinstaller  # Can now run from anywhere
```

---

## Cross-Platform Building

### Building All Platforms

If you have access to all three operating systems, you can build for all platforms:

**On Windows (in PowerShell):**
```powershell
cd wfbInstaller
.\build.bat
# Creates: dist\wfbinstaller.exe
```

**On macOS/Linux:**
```bash
cd wfbInstaller
./build.sh
# Creates: dist/wfbinstaller
```

Then share the appropriate executable for each platform.

### CI/CD Alternative

For automated building across platforms, consider using GitHub Actions:

```yaml
name: Build wfbInstaller

on: [push, pull_request]

jobs:
  build-windows:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: |
          pip install -r requirements-build.txt
          pyinstaller --onefile wfbinstaller.spec
      - uses: actions/upload-artifact@v4
        with:
          name: wfbinstaller-windows
          path: dist/wfbinstaller.exe

  build-macos:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: |
          brew install libmtp
          pip install -r requirements-build.txt
          pyinstaller --onefile wfbinstaller.spec
      - uses: actions/upload-artifact@v4
        with:
          name: wfbinstaller-macos
          path: dist/wfbinstaller

  build-linux:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: |
          sudo apt-get install libmtp9 libusb-1.0-0
          pip install -r requirements-build.txt
          pyinstaller --onefile wfbinstaller.spec
      - uses: actions/upload-artifact@v4
        with:
          name: wfbinstaller-linux
          path: dist/wfbinstaller
```

---

## Troubleshooting

### "PyInstaller not found"
Install PyInstaller:
```bash
pip install PyInstaller==6.1.0
```

### "libmtp not found" (macOS/Linux)
Make sure you've installed libmtp via your package manager:
```bash
# macOS
brew install libmtp

# Ubuntu/Debian
sudo apt-get install libmtp9 libusb-1.0-0

# Fedora
sudo dnf install libmtp libusb
```

### Antivirus False Positive (Windows)
PyInstaller-created binaries sometimes trigger antivirus software. Options:
1. Add to antivirus whitelist
2. Sign the executable with a code signing certificate
3. Disable the warning for that executable

### macOS Security Warning
On macOS, first-run executables may show a security warning. Users can:
1. Right-click the executable
2. Select "Open"
3. Click "Open" in the security dialog

Or bypass it with:
```bash
spctl --add-exec --label "wfbInstaller" ./wfbinstaller
```

### Linux Permission Denied
Ensure the binary is executable:
```bash
chmod +x ./dist/wfbinstaller
```

---

## File Sizes

Typical standalone executable sizes:

| Platform | Size | Notes |
|----------|------|-------|
| Windows (.exe) | ~30-50 MB | Includes Python runtime and all dependencies |
| macOS | ~30-50 MB | Can be distributed as standalone binary |
| Linux | ~30-50 MB | Can be distributed as standalone binary |

---

## Distribution

### Release on GitHub

Create releases with the built executables:

```bash
# Create a release
gh release create v1.0.0 \
  ./dist/wfbinstaller.exe#Windows \
  ./dist/wfbinstaller#macOS \
  ./dist/wfbinstaller#Linux
```

### Packaging

For better distribution, you can create archives:

```bash
# Windows
7z a wfbinstaller-windows.7z dist\wfbinstaller.exe

# macOS
tar -czf wfbinstaller-macos.tar.gz dist/wfbinstaller

# Linux
tar -czf wfbinstaller-linux.tar.gz dist/wfbinstaller
```

---

## Advanced Options

### Code Signing (macOS)
```bash
codesign --deep --force --verify --verbose --sign "Developer ID Application" dist/wfbinstaller
```

### UPX Compression (Optional)
Reduce binary size further (requires UPX installed):

Edit `wfbinstaller.spec`:
```python
exe = EXE(
    ...
    upx=True,  # Enable UPX compression
    ...
)
```

### Single Directory Distribution
For easier analysis/modification by users, create a directory instead:

```bash
pyinstaller --onedir --name wfbinstaller wfbinstaller.spec
```

This creates `dist/wfbinstaller/` directory with all files.

---

## Resources

- [PyInstaller Documentation](https://pyinstaller.org/)
- [PyInstaller Hooks](https://github.com/pyinstaller/pyinstaller-hooks-contrib/)
- [Code Signing Certificates](https://www.sectigo.com/)
