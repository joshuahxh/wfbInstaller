import os
import tempfile
from typing import Optional
from urllib.parse import urlparse

import requests

from logger import Logger
from models import FileInfo


class DownloadService:
    def __init__(self, logger: Logger):
        self.logger = logger
        self.timeout = 300

    def download_file(self, url: str) -> Optional[FileInfo]:
        """Download a file from a URL"""
        # Validate URL
        try:
            parsed = urlparse(url)
            if parsed.scheme not in ('http', 'https'):
                self.logger.error("Invalid URL format")
                return None
        except Exception:
            self.logger.error("Invalid URL format")
            return None

        self.logger.info(f"Downloading from {url}...")

        # Ensure file=app query parameter
        download_url = self._ensure_app_query_parameter(url)

        try:
            # Create temp file
            with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp:
                tmp_path = tmp.name

            # Download file
            response = requests.get(download_url, timeout=self.timeout, stream=True)
            response.raise_for_status()

            with open(tmp_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            file_size = os.path.getsize(tmp_path)
            self.logger.info(f"Downloaded successfully: {file_size} bytes")

            return FileInfo(
                path=tmp_path,
                extension='.zip',
                size_bytes=file_size,
                is_temporary=True
            )

        except requests.RequestException as e:
            self.logger.error(f"Download failed: {str(e)}")
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error during download: {str(e)}")
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            return None

    @staticmethod
    def _ensure_app_query_parameter(url: str) -> str:
        """Ensure the file=app query parameter is present"""
        if 'file=app' in url:
            return url

        separator = '&' if '?' in url else '?'
        return url + separator + 'file=app'
