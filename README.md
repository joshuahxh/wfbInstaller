# wfbInstaller

A cross-platform Garmin watchface installer.

Wiki & FAQ: https://joshuahxh.github.io/wfbInstaller/ ([docs source](docs/index.md))

Supports direct MTP communication through OpenMTP's Kalam Kernel (`go-mtpx` / `go-mtpfs`) plus standard filesystem-based device access.

## Features

- Cross-platform executables for Windows, Linux, macOS Apple Silicon, and macOS Intel
- Install watchface packages (`.zip`, `.prg`, `.set`)
- Download and install directly from Watchface Builder URLs
- Detect connected Garmin devices before prompting for the payload
- Interactive device selection when more than one Garmin device is connected
- Windows Shell fallback for MTP-only Garmin devices that appear in `This PC` without a drive letter
- Filesystem fallback for mounted devices on Windows, Linux, and macOS

## Downloads

Download the matching executable from GitHub Actions artifacts or a release when one is published:

- Windows: `wfbInstaller-windows.exe`
- Linux x64: `wfbInstaller-linux-amd64`
- macOS Apple Silicon: `wfbInstaller-macos-arm64`
- macOS Intel: `wfbInstaller-macos-intel`

No Python is required.

## Requirements

### Windows

- 64-bit Windows 10/11
- Garmin device connected via USB
- MTP and mass-storage devices are both supported
- Modern Garmin watches that appear in `This PC` as a Portable Device with no drive letter are handled through the Windows Shell fallback
- Older Garmin devices that mount as a normal drive letter are handled through filesystem copy

### Linux

- x64 Linux
- Garmin device connected via USB
- `libusb-1.0` may be required for direct MTP access
- If direct MTP access is unavailable, mounted devices under `/media`, `/mnt`, or `/run/media` are supported

### macOS

- Apple Silicon or Intel macOS
- Garmin device connected via USB
- `libusb` may be required for direct MTP access
- Mounted devices under `/Volumes` are supported through filesystem copy

## Usage

### Interactive Mode

Run the executable with no arguments. The installer checks for a connected Garmin device first, then prompts for the URL or file to install.

```powershell
.\wfbInstaller-windows.exe
./wfbInstaller-linux-amd64
./wfbInstaller-macos-arm64
```

### Command Line

```powershell
# Install from a zip file
.\wfbInstaller-windows.exe mystyle.zip

# Install from a PRG file
./wfbInstaller-linux-amd64 mystyle.prg

# Install from a settings file
./wfbInstaller-macos-intel mystyle.set

# Download and install directly from a URL
./wfbInstaller-macos-arm64 https://garmin.watchfacebuilder.com/watchface/12345/
```

## Build From Source

### Prerequisites

- Go 1.22 or newer
- `pkg-config`
- `libusb-1.0` development files

Examples:

- macOS: `brew install pkg-config libusb`
- Ubuntu/Debian: `sudo apt-get install pkg-config libusb-1.0-0-dev`
- Windows: use MSYS2 with MinGW-w64 and `libusb`

### Build

```powershell
go mod tidy
go build -trimpath -o dist/wfbInstaller .
```

The GitHub Actions workflow builds these binaries automatically:

- Windows x64
- Linux x64
- macOS Apple Silicon
- macOS Intel

## Troubleshooting

### Device not detected

- Reconnect the watch and run the installer again
- On Windows, MTP-only Garmin devices should appear in `This PC` even without a drive letter
- On Linux and macOS, make sure the watch is either mounted or accessible over MTP

### Linux permissions

If USB access is blocked, add a Garmin udev rule:

```bash
sudo tee /etc/udev/rules.d/51-garmin.rules >/dev/null <<'EOF'
SUBSYSTEMS=="usb", ATTRS{idVendor}=="091e", MODE="0666"
EOF
sudo udevadm control --reload-rules
sudo udevadm trigger
```

### Missing `libusb`

If the executable reports a missing `libusb` dependency on Linux or macOS, install the runtime package for your platform and run the installer again.

## Repository

https://github.com/joshuahxh/wfbInstaller