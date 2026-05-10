from dataclasses import dataclass
from typing import Optional


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


@dataclass
class FileInfo:
    path: str
    extension: str
    size_bytes: int
    is_temporary: bool
