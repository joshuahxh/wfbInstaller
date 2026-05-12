package main

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"runtime"
	"sort"
	"strings"
	"time"

	"github.com/ganeshrvel/go-mtpfs/fs"
	"github.com/ganeshrvel/go-mtpfs/mtp"
	mtpx "github.com/ganeshrvel/go-mtpx"
	"github.com/ganeshrvel/usb"
)

type deviceTransport string

const (
	transportMTP             deviceTransport = "mtp"
	transportFilesystem      deviceTransport = "filesystem"
	transportWindowsPortable deviceTransport = "windows-portable"
)

type deviceInfo struct {
	Index              int
	Name               string
	Manufacturer       string
	BusLocation        string
	Transport          deviceTransport
	DevicePattern      string
	PreferredStorageID uint32
	ShellPathSegments  []string
}

type portableDeviceRecord struct {
	Name     string   `json:"name"`
	Segments []string `json:"segments"`
}

func (a *app) discoverDevices() []deviceInfo {
	devices := make([]deviceInfo, 0)
	devices = append(devices, a.scanMTPDevices()...)
	devices = append(devices, a.scanFilesystemDevices()...)

	if runtime.GOOS == "windows" {
		devices = a.mergePortableFallbacks(devices, a.scanWindowsPortableDevices())
	}

	devices = uniqueDevices(devices)
	sort.SliceStable(devices, func(i, j int) bool {
		leftRank := transportRank(devices[i].Transport)
		rightRank := transportRank(devices[j].Transport)
		if leftRank != rightRank {
			return leftRank < rightRank
		}
		return strings.ToLower(devices[i].Name) < strings.ToLower(devices[j].Name)
	})

	for index := range devices {
		devices[index].Index = index + 1
	}

	return devices
}

func transportRank(transport deviceTransport) int {
	switch transport {
	case transportFilesystem:
		return 0
	case transportMTP:
		return 1
	case transportWindowsPortable:
		return 2
	default:
		return 99
	}
}

func uniqueDevices(devices []deviceInfo) []deviceInfo {
	seen := make(map[string]int)
	result := make([]deviceInfo, 0, len(devices))

	for _, device := range devices {
		key := strings.ToLower(string(device.Transport) + "|" + device.Name + "|" + device.BusLocation)
		if existingIndex, ok := seen[key]; ok {
			if len(result[existingIndex].ShellPathSegments) == 0 && len(device.ShellPathSegments) > 0 {
				result[existingIndex].ShellPathSegments = append([]string(nil), device.ShellPathSegments...)
			}
			continue
		}

		seen[key] = len(result)
		result = append(result, device)
	}

	return result
}

func (a *app) scanMTPDevices() []deviceInfo {
	ctx := usb.NewContext()
	defer ctx.Exit()

	candidates, err := mtp.FindDevices(ctx)
	if err != nil {
		a.logger.Printf("MTP scan failed: %v", err)
		return nil
	}

	devices := make([]deviceInfo, 0)
	for _, candidate := range candidates {
		device, err := inspectMTPDevice(candidate)
		if err != nil {
			continue
		}
		devices = append(devices, *device)
	}

	return devices
}

func inspectMTPDevice(candidate *mtp.Device) (*deviceInfo, error) {
	defer candidate.Done()

	if err := candidate.Open(); err != nil {
		return nil, err
	}
	defer candidate.Close()

	deviceID, err := candidate.ID()
	if err != nil {
		return nil, err
	}

	usbInfo, _ := candidate.GetUsbInfo()

	if err := candidate.Configure(); err != nil {
		return nil, err
	}

	storageIDs, err := fs.SelectStorages(candidate, ".*")
	if err != nil {
		return nil, err
	}

	preferredStorageID := uint32(0)
	for _, storageID := range storageIDs {
		if hasGarminRoot(candidate, storageID) {
			preferredStorageID = storageID
			break
		}
	}

	name, manufacturer := formatMTPName(usbInfo, deviceID)
	if !looksLikeGarmin(name, manufacturer, deviceID, preferredStorageID != 0) {
		return nil, errors.New("not a Garmin device")
	}

	return &deviceInfo{
		Name:               name,
		Manufacturer:       manufacturer,
		BusLocation:        deviceID,
		Transport:          transportMTP,
		DevicePattern:      "^" + regexp.QuoteMeta(deviceID) + "$",
		PreferredStorageID: preferredStorageID,
	}, nil
}

func formatMTPName(usbInfo *mtp.UsbDeviceInfo, deviceID string) (string, string) {
	manufacturer := "Garmin"
	product := ""

	if usbInfo != nil {
		if strings.TrimSpace(usbInfo.Manufacturer) != "" {
			manufacturer = strings.TrimSpace(usbInfo.Manufacturer)
		}
		product = strings.TrimSpace(usbInfo.Product)
	}

	parts := make([]string, 0, 2)
	if manufacturer != "" {
		parts = append(parts, manufacturer)
	}
	if product != "" && !strings.EqualFold(product, manufacturer) {
		parts = append(parts, product)
	}

	name := strings.TrimSpace(strings.Join(parts, " "))
	if name == "" {
		name = strings.TrimSpace(deviceID)
	}
	if name == "" {
		name = "Garmin MTP Device"
	}

	return name, manufacturer
}

func looksLikeGarmin(name string, manufacturer string, deviceID string, hasGarminFolder bool) bool {
	if hasGarminFolder {
		return true
	}

	combined := strings.ToLower(name + " " + manufacturer + " " + deviceID)
	return strings.Contains(combined, "garmin")
}

func hasGarminRoot(device *mtp.Device, storageID uint32) bool {
	_, err := mtpx.GetObjectFromPath(device, storageID, "/GARMIN")
	return err == nil
}

func (a *app) scanFilesystemDevices() []deviceInfo {
	devices := make([]deviceInfo, 0)

	if runtime.GOOS == "windows" {
		for letter := 'A'; letter <= 'Z'; letter++ {
			drive := fmt.Sprintf("%c:\\", letter)
			garminPath := filepath.Join(drive, "GARMIN")
			if _, err := os.Stat(garminPath); err == nil {
				devices = append(devices, deviceInfo{
					Name:         fmt.Sprintf("Garmin (%s)", drive),
					Manufacturer: "Garmin",
					BusLocation:  garminPath,
					Transport:    transportFilesystem,
				})
			}
		}
		return devices
	}

	mountPoints := []string{"/media", "/mnt", "/run/media", "/Volumes"}
	for _, mountPoint := range mountPoints {
		entries, err := os.ReadDir(mountPoint)
		if err != nil {
			continue
		}

		for _, entry := range entries {
			if !entry.IsDir() {
				continue
			}

			root := filepath.Join(mountPoint, entry.Name())
			if garminRoot, ok := resolveFilesystemGarminRoot(root); ok {
				devices = append(devices, deviceInfo{
					Name:         displayNameForMount(root),
					Manufacturer: "Garmin",
					BusLocation:  garminRoot,
					Transport:    transportFilesystem,
				})
				continue
			}

			nestedEntries, err := os.ReadDir(root)
			if err != nil {
				continue
			}

			for _, nestedEntry := range nestedEntries {
				if !nestedEntry.IsDir() {
					continue
				}

				nestedRoot := filepath.Join(root, nestedEntry.Name())
				if garminRoot, ok := resolveFilesystemGarminRoot(nestedRoot); ok {
					devices = append(devices, deviceInfo{
						Name:         displayNameForMount(nestedRoot),
						Manufacturer: "Garmin",
						BusLocation:  garminRoot,
						Transport:    transportFilesystem,
					})
				}
			}
		}
	}

	return devices
}

func resolveFilesystemGarminRoot(root string) (string, bool) {
	if strings.EqualFold(filepath.Base(root), "GARMIN") {
		if info, err := os.Stat(root); err == nil && info.IsDir() {
			return root, true
		}
	}

	garminChild := filepath.Join(root, "GARMIN")
	if info, err := os.Stat(garminChild); err == nil && info.IsDir() {
		return garminChild, true
	}

	return "", false
}

func displayNameForMount(root string) string {
	base := filepath.Base(root)
	if strings.EqualFold(base, "GARMIN") {
		parent := filepath.Base(filepath.Dir(root))
		if parent != "." && parent != string(filepath.Separator) && parent != "" {
			return parent
		}
	}
	return base
}

func (a *app) scanWindowsPortableDevices() []deviceInfo {
	if runtime.GOOS != "windows" {
		return nil
	}

	script := `$ErrorActionPreference = 'Continue'
$shell = New-Object -ComObject Shell.Application
$computer = $shell.Namespace(17)
$results = @()

function Find-GarminPath($folder, $segments) {
    foreach ($item in $folder.Items()) {
        if ($item.IsFolder -and $item.Name -ieq 'GARMIN') {
            return @($segments + @('GARMIN'))
        }
    }
    foreach ($item in $folder.Items()) {
        if (-not $item.IsFolder) { continue }
        try {
            $sub = $item.GetFolder()
            foreach ($child in $sub.Items()) {
                if ($child.IsFolder -and $child.Name -ieq 'GARMIN') {
                    return @($segments + @($item.Name, 'GARMIN'))
                }
            }
        } catch {}
    }
    return $null
}

foreach ($device in $computer.Items()) {
    if (-not $device.IsFolder) { continue }
    if ($device.Path -match '^[A-Za-z]:\\?$') { continue }
    try {
        $folder = $device.GetFolder()
        $path = Find-GarminPath $folder @($device.Name)
        if ($path) {
            $results += [pscustomobject]@{
                name = $device.Name
                segments = $path
            }
        }
    } catch {}
}

if ($results.Count -eq 0) {
    Write-Output '[]'
} else {
    $results | ConvertTo-Json -Compress -Depth 4
}`

	exitCode, stdout, stderr, err := runPowerShell(script, 30*time.Second)
	if err != nil {
		a.logger.Printf("Portable-device scan failed: %v", err)
		return nil
	}
	if exitCode != 0 {
		a.logger.Printf("Portable-device scan exit=%d: %s", exitCode, strings.TrimSpace(stderr))
		return nil
	}

	stdout = strings.TrimSpace(stdout)
	if stdout == "" || stdout == "[]" {
		return nil
	}

	var records []portableDeviceRecord
	if strings.HasPrefix(stdout, "{") {
		var record portableDeviceRecord
		if err := json.Unmarshal([]byte(stdout), &record); err != nil {
			a.logger.Printf("Portable-device JSON parse failed: %v", err)
			return nil
		}
		records = append(records, record)
	} else {
		if err := json.Unmarshal([]byte(stdout), &records); err != nil {
			if trimmed := strings.TrimSpace(stderr); trimmed != "" {
				a.logger.Printf("Portable-device scan stderr: %s", trimmed)
			}
			a.logger.Printf("Portable-device JSON parse failed: %v", err)
			return nil
		}
	}

	devices := make([]deviceInfo, 0, len(records))
	for _, record := range records {
		if len(record.Segments) == 0 {
			continue
		}
		devices = append(devices, deviceInfo{
			Name:              record.Name,
			Manufacturer:      "Garmin",
			BusLocation:       strings.Join(record.Segments, ` \ `),
			Transport:         transportWindowsPortable,
			ShellPathSegments: append([]string(nil), record.Segments...),
		})
	}

	return devices
}

func (a *app) mergePortableFallbacks(existing []deviceInfo, portable []deviceInfo) []deviceInfo {
	for _, portableDevice := range portable {
		matched := false
		for index := range existing {
			if strings.EqualFold(existing[index].Name, portableDevice.Name) {
				if len(existing[index].ShellPathSegments) == 0 {
					existing[index].ShellPathSegments = append([]string(nil), portableDevice.ShellPathSegments...)
				}
				matched = true
				break
			}
		}

		if !matched {
			existing = append(existing, portableDevice)
		}
	}

	return existing
}

func (a *app) uploadTargets(device deviceInfo, targets []installTarget) error {
	switch device.Transport {
	case transportFilesystem:
		return a.uploadFilesystemTargets(device, targets)
	case transportMTP:
		err := a.uploadMTPTargets(device, targets)
		if err == nil {
			return nil
		}

		if runtime.GOOS == "windows" && len(device.ShellPathSegments) > 0 {
			a.logger.Printf("Kalam Kernel upload failed: %v", err)
			a.logger.Println("Falling back to Windows Shell copy...")
			return a.uploadWindowsPortableTargets(device, targets)
		}

		return err
	case transportWindowsPortable:
		return a.uploadWindowsPortableTargets(device, targets)
	default:
		return fmt.Errorf("unsupported device transport: %s", device.Transport)
	}
}

func (a *app) uploadFilesystemTargets(device deviceInfo, targets []installTarget) error {
	for _, target := range targets {
		destination := target.filesystemDestination(device.BusLocation)
		if err := os.MkdirAll(filepath.Dir(destination), 0o755); err != nil {
			return err
		}

		if _, err := os.Stat(destination); err == nil {
			if err := os.Remove(destination); err != nil {
				return err
			}
		}

		a.logger.Printf("Uploading %s...", target.DisplayFileName)
		if err := copyFile(target.SourcePath, destination); err != nil {
			return err
		}

		a.logger.Printf("Installed %s.", target.DisplayFileName)
	}

	return nil
}

func (a *app) uploadMTPTargets(device deviceInfo, targets []installTarget) error {
	mtpDevice, err := openSelectedMTPDevice(device)
	if err != nil {
		return err
	}
	defer mtpDevice.Close()
	defer mtpDevice.Done()

	storageID, err := pickStorageID(mtpDevice, device.PreferredStorageID)
	if err != nil {
		return err
	}

	progressCb := func(_ *mtpx.ProgressInfo, callbackErr error) error {
		return callbackErr
	}

	for _, target := range targets {
		if err := func() error {
			stagedPath, cleanup, err := stageTargetFile(target)
			if cleanup != nil {
				defer cleanup()
			}
			if err != nil {
				return err
			}

			a.logger.Printf("Uploading %s...", target.DisplayFileName)
			_, _, _, err = mtpx.UploadFiles(
				mtpDevice,
				storageID,
				[]string{stagedPath},
				target.mtpDestinationDir(),
				false,
				nil,
				progressCb,
			)
			if err != nil {
				return err
			}

			a.logger.Printf("Installed %s.", target.DisplayFileName)
			return nil
		}(); err != nil {
			return err
		}
	}

	return nil
}

func openSelectedMTPDevice(device deviceInfo) (*mtp.Device, error) {
	mtpDevice, err := mtp.SelectDeviceWithDebugging(device.DevicePattern, false)
	if err != nil {
		return nil, err
	}

	if err := mtpDevice.Configure(); err != nil {
		mtpDevice.Close()
		mtpDevice.Done()
		return nil, err
	}

	return mtpDevice, nil
}

func pickStorageID(device *mtp.Device, preferredStorageID uint32) (uint32, error) {
	storageIDs, err := fs.SelectStorages(device, ".*")
	if err != nil {
		return 0, err
	}

	if len(storageIDs) == 0 {
		return 0, errors.New("no MTP storage found")
	}

	if preferredStorageID != 0 {
		for _, storageID := range storageIDs {
			if storageID == preferredStorageID {
				return storageID, nil
			}
		}
	}

	for _, storageID := range storageIDs {
		if hasGarminRoot(device, storageID) {
			return storageID, nil
		}
	}

	return storageIDs[0], nil
}

func stageTargetFile(target installTarget) (string, func(), error) {
	tempDir, err := os.MkdirTemp("", "wfbinstaller_stage_*")
	if err != nil {
		return "", nil, err
	}

	destination := filepath.Join(tempDir, target.DesiredFileName)
	if err := copyFile(target.SourcePath, destination); err != nil {
		_ = os.RemoveAll(tempDir)
		return "", nil, err
	}

	cleanup := func() {
		_ = os.RemoveAll(tempDir)
	}

	return destination, cleanup, nil
}

func (a *app) uploadWindowsPortableTargets(device deviceInfo, targets []installTarget) error {
	if runtime.GOOS != "windows" {
		return errors.New("Windows Shell fallback is only available on Windows")
	}
	if len(device.ShellPathSegments) == 0 {
		return errors.New("device Shell path is missing")
	}

	for _, target := range targets {
		if err := func() error {
			stagedPath, cleanup, err := stageTargetFile(target)
			if cleanup != nil {
				defer cleanup()
			}
			if err != nil {
				return err
			}

			a.logger.Printf("Uploading %s...", target.DisplayFileName)
			if err := copyToWindowsPortableDevice(device, target, stagedPath); err != nil {
				return err
			}

			a.logger.Printf("Installed %s.", target.DisplayFileName)
			return nil
		}(); err != nil {
			return err
		}
	}

	return nil
}

func copyToWindowsPortableDevice(device deviceInfo, target installTarget, stagedPath string) error {
	deviceName := device.ShellPathSegments[0]
	segmentsAfterDevice := append([]string(nil), device.ShellPathSegments[1:]...)
	if target.Extension == ".set" {
		segmentsAfterDevice = append(segmentsAfterDevice, "Apps", "Settings")
	} else {
		segmentsAfterDevice = append(segmentsAfterDevice, "Apps")
	}

	segmentLiteralParts := make([]string, 0, len(segmentsAfterDevice))
	for _, segment := range segmentsAfterDevice {
		segmentLiteralParts = append(segmentLiteralParts, fmt.Sprintf("'%s'", psEscape(segment)))
	}

	script := fmt.Sprintf(`$ErrorActionPreference = 'Stop'
$DEVICE_NAME = '%s'
$PATH_SEGMENTS = @(%s)
$SOURCE_FILE = '%s'

$shell = New-Object -ComObject Shell.Application
$computer = $shell.Namespace(17)

$device = $null
foreach ($item in $computer.Items()) {
    if ($item.IsFolder -and $item.Name -eq $DEVICE_NAME) { $device = $item; break }
}
if (-not $device) { throw "Device not found: $DEVICE_NAME" }

$folder = $device.GetFolder()
foreach ($segment in $PATH_SEGMENTS) {
    $next = $null
    foreach ($child in $folder.Items()) {
        if ($child.IsFolder -and $child.Name -ieq $segment) { $next = $child; break }
    }
    if (-not $next) {
        try {
            $folder.NewFolder($segment) | Out-Null
            Start-Sleep -Milliseconds 800
            foreach ($child in $folder.Items()) {
                if ($child.IsFolder -and $child.Name -ieq $segment) { $next = $child; break }
            }
        } catch {}
    }
    if (-not $next) { throw ("Folder not found and could not be created: " + $segment) }
    $folder = $next.GetFolder()
}

$sourceFull = (Resolve-Path -LiteralPath $SOURCE_FILE).Path
$sourceDir = Split-Path -Parent $sourceFull
$sourceName = Split-Path -Leaf $sourceFull
$sourceFolder = $shell.Namespace($sourceDir)
$sourceItem = $sourceFolder.ParseName($sourceName)
if (-not $sourceItem) { throw "Source not accessible: $sourceFull" }

$alreadyExisted = $false
if ($folder.ParseName($sourceName)) { $alreadyExisted = $true }

$folder.CopyHere($sourceItem, 0x614)

$elapsedMs = 0
$timeoutMs = 120000
$seen = $false
while ($elapsedMs -lt $timeoutMs) {
    Start-Sleep -Milliseconds 500
    $elapsedMs += 500
    if ($folder.ParseName($sourceName)) { $seen = $true; break }
}
if (-not $seen) { throw 'Copy did not complete within 120 seconds' }

if ($alreadyExisted) { Start-Sleep -Seconds 3 } else { Start-Sleep -Milliseconds 500 }
Write-Output 'OK'
`, psEscape(deviceName), strings.Join(segmentLiteralParts, ", "), psEscape(stagedPath))

	exitCode, stdout, stderr, err := runPowerShell(script, 3*time.Minute)
	if err != nil {
		if errors.Is(err, context.DeadlineExceeded) {
			return errors.New("PowerShell upload timed out")
		}
		return fmt.Errorf("PowerShell upload failed: %w", err)
	}

	if exitCode != 0 || strings.TrimSpace(stdout) == "" || !strings.HasSuffix(strings.TrimSpace(stdout), "OK") {
		message := strings.TrimSpace(stderr)
		if message == "" {
			message = strings.TrimSpace(stdout)
		}
		if message == "" {
			message = "unknown PowerShell error"
		}
		return fmt.Errorf("upload failed: %s", message)
	}

	return nil
}

func runPowerShell(script string, timeout time.Duration) (int, string, string, error) {
	executable, err := resolvePowerShellExecutable()
	if err != nil {
		return 0, "", "", err
	}

	ctx, cancel := context.WithTimeout(context.Background(), timeout)
	defer cancel()

	command := exec.CommandContext(ctx, executable, "-NoProfile", "-NonInteractive", "-Command", "-")
	command.Stdin = strings.NewReader(script)

	var stdout bytes.Buffer
	var stderr bytes.Buffer
	command.Stdout = &stdout
	command.Stderr = &stderr

	err = command.Run()
	if ctx.Err() != nil {
		return 0, stdout.String(), stderr.String(), ctx.Err()
	}

	exitCode := 0
	if err != nil {
		var exitError *exec.ExitError
		if errors.As(err, &exitError) {
			exitCode = exitError.ExitCode()
		} else {
			return 0, stdout.String(), stderr.String(), err
		}
	}

	return exitCode, stdout.String(), stderr.String(), nil
}

func resolvePowerShellExecutable() (string, error) {
	for _, candidate := range []string{"powershell.exe", "powershell", "pwsh.exe", "pwsh"} {
		if path, err := exec.LookPath(candidate); err == nil {
			return path, nil
		}
	}
	return "", errors.New("PowerShell executable not found")
}

func psEscape(value string) string {
	return strings.ReplaceAll(value, "'", "''")
}

func copyFile(source string, destination string) error {
	input, err := os.Open(source)
	if err != nil {
		return err
	}
	defer input.Close()

	info, err := input.Stat()
	if err != nil {
		return err
	}

	output, err := os.OpenFile(destination, os.O_CREATE|os.O_WRONLY|os.O_TRUNC, info.Mode())
	if err != nil {
		return err
	}

	if _, err := io.Copy(output, input); err != nil {
		output.Close()
		return err
	}

	return output.Close()
}