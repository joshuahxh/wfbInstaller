import os
import tempfile
import zipfile
from typing import List, Optional

from logger import Logger
from models import FileInfo


class FileHandler:
    def __init__(self, logger: Logger):
        self.logger = logger

    def validate_and_prepare_file(self, file_path: str) -> Optional[FileInfo]:
        """Validate a file and return its info"""
        if not os.path.exists(file_path):
            self.logger.error(f"File not found: {file_path}")
            return None

        _, ext = os.path.splitext(file_path)
        ext = ext.lower()

        if not self._is_valid_file_type(ext):
            self.logger.error(f"Invalid file type: {ext}. Supported: .zip, .prg, .set")
            return None

        file_size = os.path.getsize(file_path)

        return FileInfo(
            path=file_path,
            extension=ext,
            size_bytes=file_size,
            is_temporary=False
        )

    def extract_prg_from_zip(self, zip_path: str) -> Optional[List[FileInfo]]:
        """Extract .prg files from a zip archive"""
        self.logger.info("Extracting .prg files from zip...")
        extracted_files = []

        try:
            with zipfile.ZipFile(zip_path, 'r') as archive:
                for entry in archive.namelist():
                    if entry.lower().endswith('.prg'):
                        # Create temp file
                        with tempfile.NamedTemporaryFile(suffix='.prg', delete=False) as tmp:
                            tmp_path = tmp.name

                        # Extract file
                        with archive.open(entry) as source:
                            with open(tmp_path, 'wb') as target:
                                target.write(source.read())

                        file_size = os.path.getsize(tmp_path)
                        extracted_files.append(FileInfo(
                            path=tmp_path,
                            extension='.prg',
                            size_bytes=file_size,
                            is_temporary=True
                        ))

                        self.logger.info(f"Extracted: {entry} ({file_size} bytes)")

            if not extracted_files:
                self.logger.error("No .prg files found in zip archive")
                return None

            return extracted_files

        except zipfile.BadZipFile:
            self.logger.error("Invalid zip file")
            return None
        except Exception as e:
            self.logger.error(f"Failed to extract zip: {str(e)}")
            return None

    def cleanup_temporary_files(self, files: List[FileInfo]) -> None:
        """Remove temporary files"""
        for file_info in files:
            if file_info.is_temporary:
                try:
                    if os.path.exists(file_info.path):
                        os.remove(file_info.path)
                        self.logger.debug(f"Cleaned up temporary file: {file_info.path}")
                except Exception as e:
                    self.logger.warn(f"Failed to delete temporary file {file_info.path}: {str(e)}")

    def cleanup_temporary_download(self, file_path: str) -> None:
        """Remove a downloaded file"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                self.logger.debug(f"Cleaned up downloaded file: {file_path}")
        except Exception as e:
            self.logger.warn(f"Failed to delete temporary file {file_path}: {str(e)}")

    @staticmethod
    def _is_valid_file_type(extension: str) -> bool:
        """Check if file extension is valid"""
        valid_extensions = {'.zip', '.prg', '.set'}
        return extension in valid_extensions
