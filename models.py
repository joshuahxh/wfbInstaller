from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class InstallResult:
    success: bool
    message: str
    error: Optional[Exception] = None


@dataclass
class DeviceInfo:
    index: int
    name: str
    manufacturer: str
    vendor_id: int
    product_id: int
    bus_location: str
    # How to talk to this device:
    #   "filesystem"       - bus_location is a real filesystem path (drive letter
    #                        on Windows, mount point on Linux/macOS); use shutil.
    #   "windows-portable" - device is exposed through the Windows Shell namespace
    #                        as an MTP "Portable Device" with no drive letter; use
    #                        PowerShell + Shell.Application to navigate and copy.
    transport: str = "filesystem"
    # For "windows-portable" only: ordered Shell breadcrumb from "This PC" down
    # to and including the "GARMIN" folder. e.g. ["fenix 6 Pro", "Internal Storage", "GARMIN"].
    shell_path_segments: List[str] = field(default_factory=list)


@dataclass
class FileInfo:
    path: str
    extension: str
    size_bytes: int
    is_temporary: bool
