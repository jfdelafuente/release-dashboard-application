"""
Upload Logger
Tracks all CSV upload activities for audit and debugging
"""

import logging
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional
import os

logger = logging.getLogger(__name__)


class UploadLogger:
    """Handles upload tracking and logging"""

    def __init__(self, log_file: Optional[str] = None):
        """
        Initialize upload logger

        Args:
            log_file: Path to JSON log file for structured logging
        """
        self.log_file = log_file or Path(__file__).parent.parent.parent / "logs" / "uploads.json"
        self.log_file = Path(self.log_file)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

    def log_upload(self, upload_info: Dict) -> bool:
        """
        Log an upload event

        Args:
            upload_info: Dict with upload details
                - timestamp: ISO format timestamp
                - filename: Original filename
                - file_size: Size in bytes
                - encoding: Detected encoding
                - delimiter: Detected delimiter
                - row_count: Number of data rows
                - headers_count: Number of headers
                - status: upload/validation/processing/completed/failed
                - errors: List of errors (if any)

        Returns:
            True if logged successfully
        """
        try:
            # Ensure timestamp exists
            if 'timestamp' not in upload_info:
                upload_info['timestamp'] = datetime.utcnow().isoformat()

            # Read existing logs
            logs = self._read_logs()

            # Append new entry
            logs.append(upload_info)

            # Write updated logs
            with open(self.log_file, 'w', encoding='utf-8') as f:
                json.dump(logs, f, indent=2, ensure_ascii=False)

            logger.info(f"Upload logged: {upload_info.get('filename', 'unknown')}")
            return True

        except Exception as e:
            logger.error(f"Error logging upload: {e}")
            return False

    def log_upload_start(self, filename: str, file_size: int) -> bool:
        """Log start of upload"""
        return self.log_upload({
            'filename': filename,
            'file_size': file_size,
            'status': 'upload',
            'timestamp': datetime.utcnow().isoformat()
        })

    def log_validation(
        self,
        filename: str,
        encoding: str,
        delimiter: str,
        row_count: int,
        headers_count: int,
        valid: bool,
        errors: Optional[list] = None
    ) -> bool:
        """Log validation results"""
        return self.log_upload({
            'filename': filename,
            'status': 'validation',
            'encoding': encoding,
            'delimiter': delimiter,
            'row_count': row_count,
            'headers_count': headers_count,
            'valid': valid,
            'errors': errors or [],
            'timestamp': datetime.utcnow().isoformat()
        })

    def log_processing(self, filename: str) -> bool:
        """Log start of processing"""
        return self.log_upload({
            'filename': filename,
            'status': 'processing',
            'timestamp': datetime.utcnow().isoformat()
        })

    def log_completion(self, filename: str, output_file: str, record_count: int) -> bool:
        """Log successful completion"""
        return self.log_upload({
            'filename': filename,
            'status': 'completed',
            'output_file': output_file,
            'record_count': record_count,
            'timestamp': datetime.utcnow().isoformat()
        })

    def log_error(self, filename: str, error: str, status: str = 'failed') -> bool:
        """Log error"""
        return self.log_upload({
            'filename': filename,
            'status': status,
            'error': error,
            'timestamp': datetime.utcnow().isoformat()
        })

    def get_upload_history(self, filename: Optional[str] = None, limit: int = 100) -> list:
        """
        Get upload history

        Args:
            filename: Filter by filename (optional)
            limit: Maximum number of records to return

        Returns:
            List of upload records
        """
        try:
            logs = self._read_logs()

            if filename:
                logs = [log for log in logs if log.get('filename') == filename]

            return logs[-limit:]  # Return last N records

        except Exception as e:
            logger.error(f"Error reading upload history: {e}")
            return []

    def get_statistics(self) -> Dict:
        """Get upload statistics"""
        try:
            logs = self._read_logs()

            if not logs:
                return {
                    'total_uploads': 0,
                    'successful': 0,
                    'failed': 0,
                    'total_data_size': 0,
                    'total_records': 0
                }

            stats = {
                'total_uploads': len(logs),
                'successful': len([l for l in logs if l.get('status') == 'completed']),
                'failed': len([l for l in logs if l.get('status') == 'failed']),
                'total_data_size': sum(l.get('file_size', 0) for l in logs),
                'total_records': sum(l.get('record_count', 0) for l in logs),
            }

            # Success rate
            if stats['total_uploads'] > 0:
                stats['success_rate'] = round(
                    (stats['successful'] / stats['total_uploads']) * 100, 2
                )

            return stats

        except Exception as e:
            logger.error(f"Error calculating statistics: {e}")
            return {}

    def _read_logs(self) -> list:
        """Read all logs from file"""
        if not self.log_file.exists():
            return []

        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []

    def clear_logs(self) -> bool:
        """Clear all upload logs"""
        try:
            with open(self.log_file, 'w', encoding='utf-8') as f:
                json.dump([], f)
            logger.warning("Upload logs cleared")
            return True
        except Exception as e:
            logger.error(f"Error clearing logs: {e}")
            return False


# Global instance
_upload_logger = None


def get_upload_logger() -> UploadLogger:
    """Get or create global upload logger instance"""
    global _upload_logger
    if _upload_logger is None:
        _upload_logger = UploadLogger()
    return _upload_logger
