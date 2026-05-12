# wfbinstaller

Cross-platform console installer for Garmin payloads built in Go.

## Behavior

- Detects a connected Garmin device before prompting for a URL or file.
- Accepts Watchface Builder URLs, ZIP files, PRG files, and SET files.
- Uses OpenMTP's Kalam Kernel through `github.com/ganeshrvel/go-mtpx` and `github.com/ganeshrvel/go-mtpfs` for MTP transfers.
- Falls back to the Windows Shell / PowerShell portable-device path when the Kalam upload path fails on Windows.

## Build prerequisites

- Install Go 1.22 or newer.
- Run `go mod tidy` once to resolve module dependencies.
- Install `libusb-1.0` development headers so `github.com/ganeshrvel/usb` can build.

Examples:

- macOS: `brew install pkg-config libusb`
- Ubuntu/Debian: install `pkg-config` and the `libusb-1.0` development package from apt
- Windows: install a Go-compatible C toolchain plus `libusb-1.0` development files; if the Kalam transfer path still fails at runtime, the app falls back to the PowerShell portable-device copy path

## Run

```powershell
go run .
go run . path\to\file.zip
go run . https://garmin.watchfacebuilder.com/watchface/xxxxx/
```