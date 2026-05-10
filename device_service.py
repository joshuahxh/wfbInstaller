import os
import shutil
from typing import List, Optional

from logger import Logger
from models import DeviceInfo, FileInfo, InstallResult


class DeviceService:
    def __init__(self, logger: Logger):
        self.logger = logger
        self.device: Optional[DeviceInfo] = None

    def get_available_devices(self) -> List[DeviceInfo]:
        """
        Get available Garmin devices via libmtp or filesystem scanning.
        Falls back to filesystem scanning if libmtp is unavailable.
        """
        devices = []
        index = 1

        try:
            # Try using libmtp if available (Linux/macOS with proper libraries)
            import mtp
            device_list = mtp.MTP.get_devices()

            for device in device_list:
                if "Garmin" in (device.get("manufacturer", "") or ""):
                    devices.append(DeviceInfo(
                        index=index,
                        name=device.get("name", "Unknown"),
                        manufacturer="Garmin",
                        vendor_id=device.get("vendor_id", 0),
                        product_id=device.get("product_id", 0),
                        bus_location=device.get("bus_location", "")
                    ))
                    index += 1
        except (ImportError, Exception) as e:
            self.logger.debug(f"libmtp not available: {str(e)}")
            # Fallback to filesystem scanning
            devices.extend(self._scan_filesystem_devices())

        return devices

    def _scan_filesystem_devices(self) -> List[DeviceInfo]:
        """Scan filesystem for Garmin devices"""
        devices = []
        index = 1

        if os.name == 'nt':
            import string
            for letter in string.ascii_uppercase:
                drive = f"{letter}:\\"
                garmin_path = os.path.join(drive, "GARMIN")
                try:
                    if os.path.exists(garmin_path):
                        devices.append(DeviceInfo(
                            index=index,
                            name=f"Garmin ({drive})",
                            manufacturer="Garmin",
                            vendor_id=0,
                            product_id=0,
                            bus_location=drive
                        ))
                        index += 1
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
                                    index=index,
                                    name=entry,
                                    manufacturer="Garmin",
                                    vendor_id=0,
                                    product_id=0,
                                    bus_location=full_path
                                ))
                                index += 1
                except PermissionError:
                    self.logger.debug(f"Permission denied accessing {base_path}")
                    continue

        return devices

    def select_device(self, index: int) -> bool:
        """Select a device by index"""
        devices = self.get_available_devices()

        if index < 1 or index > len(devices):
            self.logger.error(f"Invalid device index: {index}")
            return False

        self.device = devices[index - 1]
        self.logger.info(f"Selected device: {self.device.name}")
        return True

    def try_auto_select_garmin(self) -> bool:
        """Auto-select if only one Garmin device is available"""
        devices = self.get_available_devices()

        if len(devices) == 1 and devices[0].manufacturer == "Garmin":
            self.device = devices[0]
            self.logger.info(f"Auto-selected device: {self.device.name}")
            return True

        return False

    def is_connected(self) -> bool:
        """Check if a device is selected"""
        return self.device is not None

    def upload_file(self, source_file: str, app_name: str) -> InstallResult:
        """Upload a file to the connected device"""
        if self.device is None:
            return InstallResult(
                success=False,
                message="No device selected"
            )

        if not os.path.exists(source_file):
            return InstallResult(
                success=False,
                message=f"Source file not found: {source_file}"
            )

        try:
            dest_path = self._determine_destination_path(app_name, source_file)
            dest_file = os.path.join(self.device.bus_location, dest_path)

            # Create destination directory
            dest_dir = os.path.dirname(dest_file)
            os.makedirs(dest_dir, exist_ok=True)

            # Remove existing file
            if os.path.exists(dest_file):
                self.logger.info(f"Removing existing file: {dest_file}")
                os.remove(dest_file)

            # Copy file
            self.logger.info(f"Uploading {os.path.basename(source_file)}...")
            shutil.copy2(source_file, dest_file)

            self.logger.info("Upload completed successfully")
            return InstallResult(
                success=True,
                message=f"Successfully installed {os.path.basename(dest_file)}"
            )

        except Exception as e:
            self.logger.error(f"Upload failed: {str(e)}")
            return InstallResult(
                success=False,
                message=f"Failed to upload file: {str(e)}",
                error=e
            )

    def _determine_destination_path(self, app_name: str, source_file: str) -> str:
        """Determine the destination path based on file type"""
        ext = os.path.splitext(source_file)[1].lower()

        if ext == ".set":
            return os.path.join("GARMIN", "Apps", "Settings", f"{app_name}.SET")

        return os.path.join("GARMIN", "Apps", f"{app_name}.prg")
