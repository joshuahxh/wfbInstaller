import json
import os
import shutil
import subprocess
import tempfile
from typing import List, Optional, Tuple

from logger import Logger
from models import DeviceInfo, InstallResult


class DeviceService:
    def __init__(self, logger: Logger):
        self.logger = logger
        self.device: Optional[DeviceInfo] = None

    # ── Detection ────────────────────────────────────────────────────────

    def get_available_devices(self) -> List[DeviceInfo]:
        """
        Collect Garmin devices from every backend available on this OS.

        Order tried, results merged:
          1. libmtp (Linux/macOS only — python-libmtp has no Windows wheel)
          2. Filesystem scan (drive letters on Windows, mount points elsewhere)
          3. Windows Shell namespace scan via PowerShell (covers MTP-only mode
             where the watch shows up in "This PC" without a drive letter)
        """
        devices: List[DeviceInfo] = []

        # 1. libmtp
        try:
            import mtp  # type: ignore
            device_list = mtp.MTP.get_devices()
            for device in device_list:
                if "Garmin" in (device.get("manufacturer", "") or ""):
                    devices.append(DeviceInfo(
                        index=0,
                        name=device.get("name", "Unknown"),
                        manufacturer="Garmin",
                        vendor_id=device.get("vendor_id", 0),
                        product_id=device.get("product_id", 0),
                        bus_location=device.get("bus_location", ""),
                        transport="filesystem",
                    ))
        except ImportError:
            self.logger.debug("libmtp not available on this platform")
        except Exception as e:
            self.logger.debug(f"libmtp scan failed: {str(e)}")

        # 2. Filesystem scan
        devices.extend(self._scan_filesystem_devices())

        # 3. Windows Shell namespace (MTP via Portable Devices)
        if os.name == "nt":
            existing_names = {d.name.lower() for d in devices}
            for d in self._scan_windows_portable_devices():
                if d.name.lower() not in existing_names:
                    devices.append(d)

        # Renumber for the interactive picker.
        for i, d in enumerate(devices, start=1):
            d.index = i

        return devices

    def _scan_filesystem_devices(self) -> List[DeviceInfo]:
        """Scan for Garmin devices exposed as a regular filesystem path."""
        devices: List[DeviceInfo] = []

        if os.name == "nt":
            import string
            for letter in string.ascii_uppercase:
                drive = f"{letter}:\\"
                garmin_path = os.path.join(drive, "GARMIN")
                try:
                    if os.path.exists(garmin_path):
                        devices.append(DeviceInfo(
                            index=0,
                            name=f"Garmin ({drive})",
                            manufacturer="Garmin",
                            vendor_id=0,
                            product_id=0,
                            bus_location=drive,
                            transport="filesystem",
                        ))
                except (PermissionError, OSError):
                    continue
        else:
            mount_points = ["/media", "/mnt", "/run/media"]
            for base_path in mount_points:
                if not os.path.exists(base_path):
                    continue
                try:
                    for entry in os.listdir(base_path):
                        full_path = os.path.join(base_path, entry)
                        if os.path.isdir(full_path):
                            garmin_path = os.path.join(full_path, "GARMIN")
                            if os.path.exists(garmin_path):
                                devices.append(DeviceInfo(
                                    index=0,
                                    name=entry,
                                    manufacturer="Garmin",
                                    vendor_id=0,
                                    product_id=0,
                                    bus_location=full_path,
                                    transport="filesystem",
                                ))
                except PermissionError:
                    self.logger.debug(f"Permission denied accessing {base_path}")
                    continue

        return devices

    def _scan_windows_portable_devices(self) -> List[DeviceInfo]:
        """
        Walk the Windows Shell namespace ("This PC", CSIDL 17) looking for any
        portable device that contains a top-level GARMIN folder — either
        directly, or one storage-folder layer down (e.g. "Internal Storage").
        """
        if os.name != "nt":
            return []

        script = r"""
$ErrorActionPreference = 'Continue'
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
    # Skip plain drive letters - they're already covered by the filesystem scan.
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
}
"""
        code, stdout, stderr = self._run_powershell(script, timeout=30)
        if code != 0:
            self.logger.debug(f"Portable-device scan exit={code}: {stderr.strip()}")
            return []

        output = stdout.strip()
        if not output:
            return []

        try:
            raw = json.loads(output)
        except json.JSONDecodeError as e:
            self.logger.debug(f"JSON parse failed for portable scan: {e}; raw={output[:200]!r}")
            return []

        if isinstance(raw, dict):
            raw = [raw]

        devices: List[DeviceInfo] = []
        for item in raw:
            segments = item.get("segments") or []
            if not segments:
                continue
            devices.append(DeviceInfo(
                index=0,
                name=item.get("name", "Portable Garmin"),
                manufacturer="Garmin",
                vendor_id=0,
                product_id=0,
                bus_location=" \\ ".join(segments),
                transport="windows-portable",
                shell_path_segments=list(segments),
            ))

        return devices

    # ── Selection ────────────────────────────────────────────────────────

    def select_device(self, index: int) -> bool:
        devices = self.get_available_devices()
        if index < 1 or index > len(devices):
            self.logger.error(f"Invalid device index: {index}")
            return False
        self.device = devices[index - 1]
        self.logger.info(f"Selected device: {self.device.name}")
        return True

    def try_auto_select_garmin(self) -> bool:
        devices = self.get_available_devices()
        if len(devices) == 1 and devices[0].manufacturer == "Garmin":
            self.device = devices[0]
            self.logger.info(f"Auto-selected device: {self.device.name}")
            return True
        return False

    def is_connected(self) -> bool:
        return self.device is not None

    # ── Upload ───────────────────────────────────────────────────────────

    def upload_file(self, source_file: str, app_name: str) -> InstallResult:
        if self.device is None:
            return InstallResult(False, "No device selected")
        if not os.path.exists(source_file):
            return InstallResult(False, f"Source file not found: {source_file}")

        if self.device.transport == "windows-portable":
            return self._upload_windows_portable(source_file, app_name)
        return self._upload_filesystem(source_file, app_name)

    def _upload_filesystem(self, source_file: str, app_name: str) -> InstallResult:
        try:
            dest_path = self._determine_destination_path(app_name, source_file)
            dest_file = os.path.join(self.device.bus_location, dest_path)

            dest_dir = os.path.dirname(dest_file)
            os.makedirs(dest_dir, exist_ok=True)

            if os.path.exists(dest_file):
                self.logger.info(f"Removing existing file: {dest_file}")
                os.remove(dest_file)

            self.logger.info(f"Uploading {os.path.basename(source_file)}...")
            shutil.copy2(source_file, dest_file)

            self.logger.info("Upload completed successfully")
            return InstallResult(
                success=True,
                message=f"Successfully installed {os.path.basename(dest_file)}",
            )
        except Exception as e:
            self.logger.error(f"Upload failed: {str(e)}")
            return InstallResult(
                success=False,
                message=f"Failed to upload file: {str(e)}",
                error=e,
            )

    def _upload_windows_portable(self, source_file: str, app_name: str) -> InstallResult:
        if not self.device.shell_path_segments:
            return InstallResult(False, "Device Shell path is missing — re-scan and try again.")

        src_ext = os.path.splitext(source_file)[1].lower()
        if src_ext == ".set":
            sub_dirs = ["Apps", "Settings"]
            target_name = f"{app_name}.SET"
        else:
            sub_dirs = ["Apps"]
            # Preserve the source extension so .prg ends up as .prg on the watch.
            target_name = f"{app_name}{src_ext or '.prg'}"

        # The Shell path's first segment is the device name; the rest is the
        # path through any storage folders and ends with "GARMIN".
        device_name = self.device.shell_path_segments[0]
        segments_after_device = list(self.device.shell_path_segments[1:]) + sub_dirs

        # Shell.CopyHere always uses the source file's own basename. Stage the
        # source as target_name in a temp dir, then copy that.
        tmpdir = tempfile.mkdtemp(prefix="wfbinstaller_")
        staged = os.path.join(tmpdir, target_name)
        try:
            shutil.copy2(source_file, staged)
            self.logger.info(f"Uploading {target_name} to {self.device.name}...")
            device_target = "\\".join([device_name] + segments_after_device + [target_name])
            self.logger.debug(f"Target path on device: {device_target}")
            return self._do_portable_copy(device_name, segments_after_device, staged)
        finally:
            try:
                if os.path.isfile(staged):
                    os.remove(staged)
                os.rmdir(tmpdir)
            except OSError:
                pass

    def _do_portable_copy(
        self,
        device_name: str,
        segments_after_device: List[str],
        local_path: str,
    ) -> InstallResult:
        def esc(s: str) -> str:
            # PowerShell single-quoted strings escape ' as ''.
            return s.replace("'", "''")

        seg_literal = ", ".join(f"'{esc(s)}'" for s in segments_after_device)
        script = f"""
$ErrorActionPreference = 'Stop'
$DEVICE_NAME = '{esc(device_name)}'
$PATH_SEGMENTS = @({seg_literal})
$SOURCE_FILE = '{esc(local_path)}'

$shell = New-Object -ComObject Shell.Application
$computer = $shell.Namespace(17)

$device = $null
foreach ($item in $computer.Items()) {{
    if ($item.IsFolder -and $item.Name -eq $DEVICE_NAME) {{ $device = $item; break }}
}}
if (-not $device) {{ throw "Device not found: $DEVICE_NAME" }}

$folder = $device.GetFolder()
foreach ($segment in $PATH_SEGMENTS) {{
    $next = $null
    foreach ($child in $folder.Items()) {{
        if ($child.IsFolder -and $child.Name -ieq $segment) {{ $next = $child; break }}
    }}
    if (-not $next) {{
        try {{
            $folder.NewFolder($segment) | Out-Null
            Start-Sleep -Milliseconds 800
            foreach ($child in $folder.Items()) {{
                if ($child.IsFolder -and $child.Name -ieq $segment) {{ $next = $child; break }}
            }}
        }} catch {{}}
    }}
    if (-not $next) {{ throw ("Folder not found and could not be created: " + $segment) }}
    $folder = $next.GetFolder()
}}

$sourceFull = (Resolve-Path -LiteralPath $SOURCE_FILE).Path
$sourceDir  = Split-Path -Parent $sourceFull
$sourceName = Split-Path -Leaf   $sourceFull
$sourceFolder = $shell.Namespace($sourceDir)
$sourceItem = $sourceFolder.ParseName($sourceName)
if (-not $sourceItem) {{ throw "Source not accessible: $sourceFull" }}

$alreadyExisted = $false
if ($folder.ParseName($sourceName)) {{ $alreadyExisted = $true }}

# FOF_SILENT (0x4) + FOF_NOCONFIRMATION (0x10) + FOF_NOERRORUI (0x400) + FOF_NOCONFIRMMKDIR (0x200)
$folder.CopyHere($sourceItem, 0x614)

$elapsedMs = 0
$timeoutMs = 120000
$seen = $false
while ($elapsedMs -lt $timeoutMs) {{
    Start-Sleep -Milliseconds 500
    $elapsedMs += 500
    if ($folder.ParseName($sourceName)) {{ $seen = $true; break }}
}}
if (-not $seen) {{ throw "Copy did not complete within 120 seconds" }}

# Small grace period for MTP to flush, longer if we were overwriting.
if ($alreadyExisted) {{ Start-Sleep -Seconds 3 }} else {{ Start-Sleep -Milliseconds 500 }}
Write-Output 'OK'
"""

        try:
            code, stdout, stderr = self._run_powershell(script, timeout=180)
        except subprocess.TimeoutExpired:
            return InstallResult(False, "PowerShell upload timed out")
        except Exception as e:
            return InstallResult(False, f"PowerShell upload failed: {e}", error=e)

        if code != 0 or stdout.strip().splitlines()[-1:] != ["OK"]:
            msg = (stderr or stdout).strip() or "Unknown PowerShell error"
            self.logger.debug(f"Upload PS exit={code} stdout={stdout!r} stderr={stderr!r}")
            return InstallResult(False, f"Upload failed: {msg}")

        self.logger.info("Upload completed successfully")
        return InstallResult(
            success=True,
            message=f"Successfully installed {os.path.basename(local_path)}",
        )

    # ── Helpers ──────────────────────────────────────────────────────────

    def _run_powershell(self, script: str, timeout: int = 30) -> Tuple[int, str, str]:
        """
        Run a PowerShell script via stdin, avoiding command-line escaping
        and ExecutionPolicy issues. Returns (returncode, stdout, stderr).
        """
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", "-"],
            input=script,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return result.returncode, result.stdout, result.stderr

    def _determine_destination_path(self, app_name: str, source_file: str) -> str:
        ext = os.path.splitext(source_file)[1].lower()
        if ext == ".set":
            return os.path.join("GARMIN", "Apps", "Settings", f"{app_name}.SET")
        return os.path.join("GARMIN", "Apps", f"{app_name}.prg")
