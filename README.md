# wfbInstaller

A cross-platform Garmin watchface installer.

📖 **Wiki & FAQ:** https://joshuahxh.github.io/wfbInstaller/ ([edit on GitHub](docs/index.md))

Supports both direct MTP (Media Transfer Protocol) communication via libmtp and standard filesystem-based device access.

## Features

- MTP protocol support via libmtp (optional)
- Cross-platform compatibility (Windows, Linux, macOS)
- Install watchface packages (.zip, .prg, .set files)
- Download watchfaces directly from URLs
- Interactive device selection
- Comprehensive error handling and logging
- Debug mode for troubleshooting

## Requirements

### Windows
- Python 3.7 or later
- Garmin device connected via USB
- **Note**: Windows versions require the Garmin device to be mounted as a drive (standard USB Mass Storage mode, not MTP-only mode)

### Linux
- Python 3.7 or later
- libmtp9 (optional - for direct MTP support)
- libusb-1.0-0 (optional - for direct MTP support)
- Garmin device connected via USB with MTP enabled
- **Note**: If libmtp not installed, device must be mounted at `/media`, `/mnt`, or `/run/media`

### macOS
- Python 3.7 or later
- libmtp (optional - via Homebrew for direct MTP support)
- Garmin device connected via USB with MTP enabled
- **Note**: If libmtp not installed, device must be mounted as a volume

## Installation

### Option 1: Standalone Executable (Easiest for End Users)

**No installation needed!** Download a pre-built executable for your OS:
- **Windows**: Download `wfbinstaller.exe` 
- **macOS**: Download `wfbinstaller`
- **Linux**: Download `wfbinstaller`

Just download and run - no Python or dependencies required!

See [Releases](https://github.com/joshuahxh/wfbInstaller/releases) for pre-built executables.

### Option 2: Python Installation (For Development)

#### Windows
```bash
pip install -r requirements.txt
```

#### Linux
```bash
sudo apt-get install libmtp9 libusb-1.0-0
pip install -r requirements.txt
```

#### macOS
```bash
brew install libmtp
pip install -r requirements.txt
```

### Option 3: Build Your Own Executable

To create standalone executables for your platform:

**Windows:**
```bash
build.bat
# Output: dist\wfbinstaller.exe
```

**macOS/Linux:**
```bash
chmod +x build.sh
./build.sh
# Output: dist/wfbinstaller
```

See [BUILDING.md](BUILDING.md) for detailed build instructions.

## Usage

### Interactive Mode
```bash
python main.py
# or
chmod +x main.py
./main.py
```

### Command Line
```bash
# Install from zip file
python main.py mystyle.zip

# Install from prg file
python main.py mystyle.prg

# Install from settings file
python main.py mystyle.set

# Download and install from URL
python main.py https://garmin.watchfacebuilder.com/watchface/12345/
```

### Debug Mode
```bash
python main.py --debug mystyle.zip
# or
python main.py -d mystyle.zip
```

## Project Structure

- `main.py` - Entry point and CLI handling
- `models.py` - Data structures
- `logger.py` - Logging interface and console implementation
- `device_service.py` - Garmin device detection and file upload via MTP
- `file_handler.py` - Zip extraction and file validation
- `download_service.py` - HTTP download handling
- `app_installer.py` - Main orchestration logic
- `requirements.txt` - Python dependencies

## Troubleshooting

### Device not detected
```bash
python main.py --debug
```

### Permission denied (Linux)
```bash
# Add udev rules for Garmin devices
sudo nano /etc/udev/rules.d/51-garmin.rules

# Add:
SUBSYSTEMS=="usb", ATTRS{idVendor}=="091e", MODE="0666"

# Reload rules
sudo udevadm control --reload-rules
```

### Module import errors
```bash
# Reinstall dependencies
pip install --upgrade -r requirements.txt
```

## Device Connection Modes

### USB Mass Storage (Recommended for Windows)
- Standard USB drive mount mode
- Works on Windows without additional drivers
- Device appears as a drive letter (e.g., D:\)
- Supported by wfbInstaller on all platforms

### MTP Mode
- Media Transfer Protocol mode
- Requires libmtp library on macOS/Linux
- Can work on Windows with proper drivers

### Which Mode Should You Use?

**Windows**: USB Mass Storage (device shows as drive)
**macOS/Linux**: Either mode works (libmtp for direct access, filesystem for mounted volumes)

## Notes

- Ensure your Garmin device is properly connected before running the installer
- On Windows, the device should appear as a drive or mounted volume
- Some Garmin devices may require toggling USB mode in settings
- Temporary files are automatically cleaned up
- Use `-d` or `--debug` flag for troubleshooting connection issues

## Platform Support

- Windows 10/11
- Ubuntu 18.04+
- Fedora 30+
- Debian 10+
- macOS 10.14+

## Development

### Run with debug output
```bash
python main.py --debug
```

### Testing dependencies
```bash
pip install pytest pytest-cov
pytest -v
```

## License

See LICENSE file in the root directory.

## Repository

https://github.com/joshuahxh/wfbInstaller
