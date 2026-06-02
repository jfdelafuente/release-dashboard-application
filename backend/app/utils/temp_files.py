"""
Temporary File Manager
Handles cleanup of old/failed temporary files
"""

import os
import shutil
from pathlib import Path
from typing import List
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class TempFileManager:
    """Manages temporary file lifecycle"""

    def __init__(self, temp_dir: str, cleanup_age_hours: int = 1):
        """
        Initialize temp file manager

        Args:
            temp_dir: Directory for temporary files
            cleanup_age_hours: Age in hours after which temp files are deleted
        """
        self.temp_dir = Path(temp_dir)
        self.cleanup_age_hours = cleanup_age_hours
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"TempFileManager initialized: {self.temp_dir}")

    def create_temp_file(self, original_filename: str, content: bytes) -> str:
        """
        Create a temporary file

        Args:
            original_filename: Original filename to preserve extension
            content: File content as bytes

        Returns:
            Path to temporary file
        """
        try:
            # Generate unique temp filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
            ext = Path(original_filename).suffix
            temp_filename = f"{timestamp}{ext}"
            temp_path = self.temp_dir / temp_filename

            # Write content
            with open(temp_path, 'wb') as f:
                f.write(content)

            logger.info(f"Temporary file created: {temp_path}")
            return str(temp_path)

        except Exception as e:
            logger.error(f"Error creating temporary file: {e}")
            raise

    def delete_temp_file(self, file_path: str) -> bool:
        """
        Delete a temporary file

        Args:
            file_path: Path to temp file

        Returns:
            True if deleted, False otherwise
        """
        try:
            file_path = Path(file_path)
            if file_path.exists():
                file_path.unlink()
                logger.info(f"Temporary file deleted: {file_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting temporary file: {e}")
            return False

    def cleanup_old_files(self) -> int:
        """
        Delete temporary files older than cleanup_age_hours

        Returns:
            Number of files deleted
        """
        try:
            cutoff_time = datetime.now() - timedelta(hours=self.cleanup_age_hours)
            deleted_count = 0

            for file_path in self.temp_dir.glob('*'):
                if not file_path.is_file():
                    continue

                # Get file modification time
                mod_time = datetime.fromtimestamp(file_path.stat().st_mtime)

                if mod_time < cutoff_time:
                    try:
                        file_path.unlink()
                        deleted_count += 1
                        logger.debug(f"Old temporary file deleted: {file_path}")
                    except Exception as e:
                        logger.warning(f"Could not delete old temp file {file_path}: {e}")

            if deleted_count > 0:
                logger.info(f"Cleanup completed: {deleted_count} old temp files deleted")

            return deleted_count

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            return 0

    def cleanup_all(self) -> int:
        """
        Delete all temporary files

        Returns:
            Number of files deleted
        """
        try:
            deleted_count = 0

            for file_path in self.temp_dir.glob('*'):
                if file_path.is_file():
                    try:
                        file_path.unlink()
                        deleted_count += 1
                    except Exception as e:
                        logger.warning(f"Could not delete temp file {file_path}: {e}")

            logger.info(f"All temporary files deleted: {deleted_count} files")
            return deleted_count

        except Exception as e:
            logger.error(f"Error during full cleanup: {e}")
            return 0

    def get_temp_files_list(self) -> List[dict]:
        """
        Get list of all temporary files

        Returns:
            List of dicts with file info
        """
        files = []
        try:
            for file_path in self.temp_dir.glob('*'):
                if file_path.is_file():
                    stat = file_path.stat()
                    files.append({
                        'path': str(file_path),
                        'name': file_path.name,
                        'size': stat.st_size,
                        'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
                    })
        except Exception as e:
            logger.error(f"Error listing temp files: {e}")

        return files

    def get_disk_usage(self) -> dict:
        """
        Get disk usage statistics for temp directory

        Returns:
            Dict with usage info
        """
        try:
            total_size = sum(f.stat().st_size for f in self.temp_dir.glob('*') if f.is_file())
            file_count = len(list(self.temp_dir.glob('*')))

            return {
                'total_size_bytes': total_size,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'file_count': file_count
            }
        except Exception as e:
            logger.error(f"Error calculating disk usage: {e}")
            return {'total_size_bytes': 0, 'total_size_mb': 0, 'file_count': 0}
