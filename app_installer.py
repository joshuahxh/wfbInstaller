import os

from device_service import DeviceService
from download_service import DownloadService
from file_handler import FileHandler
from logger import Logger
from models import InstallResult


class AppInstaller:
    def __init__(self, logger: Logger):
        self.logger = logger
        self.device_service = DeviceService(logger)
        self.file_handler = FileHandler(logger)
        self.download_service = DownloadService(logger)

    def install(self, input_str: str) -> InstallResult:
        """Install an app from a file or URL"""
        input_str = input_str.strip()

        if not input_str:
            return InstallResult(
                success=False,
                message="No input provided"
            )

        file_path = input_str

        # Download if URL
        if file_path.startswith('https://') or file_path.startswith('http://'):
            download_info = self.download_service.download_file(file_path)
            if download_info is None:
                return InstallResult(
                    success=False,
                    message="Download failed"
                )
            file_path = download_info.path

        # Validate file
        file_info = self.file_handler.validate_and_prepare_file(file_path)
        if file_info is None:
            if os.path.exists(file_path) and file_path.endswith('.zip'):
                # Clean up if it was a download
                self.file_handler.cleanup_temporary_download(file_path)
            return InstallResult(
                success=False,
                message="Invalid file"
            )

        # Process based on file type
        ext = file_info.extension.lower()

        if ext == '.zip':
            return self._process_zip_file(file_info)
        elif ext == '.prg':
            return self._process_prg_file(file_info)
        elif ext == '.set':
            return self._process_set_file(file_info)
        else:
            return InstallResult(
                success=False,
                message="Unsupported file type"
            )

    def _process_zip_file(self, file_info) -> InstallResult:
        """Process a zip file"""
        extracted_files = self.file_handler.extract_prg_from_zip(file_info.path)

        if not extracted_files:
            # Clean up download if it was temporary
            if file_info.is_temporary:
                self.file_handler.cleanup_temporary_download(file_info.path)
            return InstallResult(
                success=False,
                message="No installable files in zip"
            )

        try:
            success_count = 0

            for file_item in extracted_files:
                app_name = os.path.splitext(os.path.basename(file_item.path))[0]
                result = self.device_service.upload_file(file_item.path, app_name)

                if not result.success:
                    self.logger.error(f"Failed to install {app_name}: {result.message}")
                else:
                    success_count += 1

            message = f"Installation completed: {success_count}/{len(extracted_files)} files installed"

            return InstallResult(
                success=success_count > 0,
                message=message
            )

        finally:
            self.file_handler.cleanup_temporary_files(extracted_files)
            if file_info.is_temporary:
                self.file_handler.cleanup_temporary_download(file_info.path)

    def _process_prg_file(self, file_info) -> InstallResult:
        """Process a .prg file"""
        app_name = os.path.splitext(os.path.basename(file_info.path))[0]
        result = self.device_service.upload_file(file_info.path, app_name)

        if file_info.is_temporary:
            self.file_handler.cleanup_temporary_download(file_info.path)

        return result

    def _process_set_file(self, file_info) -> InstallResult:
        """Process a .set file"""
        setting_name = os.path.splitext(os.path.basename(file_info.path))[0]
        result = self.device_service.upload_file(file_info.path, setting_name)

        if file_info.is_temporary:
            self.file_handler.cleanup_temporary_download(file_info.path)

        return result

    def select_device(self) -> None:
        """Interactively select a device"""
        while True:
            devices = self.device_service.get_available_devices()

            if not devices:
                self.logger.warn("No Garmin device found.")
                self.logger.info("Please connect your Garmin device via USB and press Enter to retry (Ctrl+C to exit)...")
                input()
                continue

            self.logger.info("Available devices:")
            for device in devices:
                self.logger.info(f"  {device.index}: {device.name} ({device.manufacturer})")

            # Try auto-select if only one Garmin device
            if self.device_service.try_auto_select_garmin():
                break

            self.logger.info("Enter the device number to select (or press Enter to refresh):")
            user_input = input().strip()

            if not user_input:
                continue

            try:
                selected_index = int(user_input)
                if self.device_service.select_device(selected_index):
                    break
            except ValueError:
                pass

            self.logger.error("Invalid selection. Please try again.")
