"""
Conversion Service
Handles file conversion tracking and status polling
"""

import logging
import time
import json
from pathlib import Path
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class ConversionStatus:
    """Status tracking for file conversions"""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"

    @classmethod
    def all_statuses(cls):
        return [cls.PENDING, cls.PROCESSING, cls.COMPLETED, cls.FAILED, cls.TIMEOUT]


class ConversionService:
    """Manages file conversion workflow"""

    def __init__(self, data_input_dir: str, data_output_dir: str, timeout_seconds: int = 120):
        """
        Initialize conversion service

        Args:
            data_input_dir: Directory where CSV files are moved
            data_output_dir: Directory where converted JSON files are stored
            timeout_seconds: Maximum wait time for conversion (default 2 minutes)
        """
        self.data_input_dir = Path(data_input_dir)
        self.data_output_dir = Path(data_output_dir)
        self.timeout_seconds = timeout_seconds
        self.logger = logging.getLogger(__name__)

    def get_conversion_status(self, filename: str, poll_interval: int = 1, max_polls: int = 120) -> Dict:
        """
        Poll for conversion status until complete or timeout

        Args:
            filename: Original filename (without timestamp)
            poll_interval: Seconds between polls (default 1)
            max_polls: Maximum number of polls (default 120 = 2 minutes)

        Returns:
            Dict with status, output_file, record_count, etc.
        """
        start_time = datetime.now()
        poll_count = 0

        while poll_count < max_polls:
            # Check if output file exists
            output_file = self._find_output_file(filename)

            if output_file:
                # File has been converted
                record_count = self._count_json_records(output_file)

                return {
                    'status': ConversionStatus.COMPLETED,
                    'success': True,
                    'output_file': str(output_file),
                    'record_count': record_count,
                    'elapsed_seconds': (datetime.now() - start_time).total_seconds(),
                    'message': f'File converted successfully ({record_count} records)'
                }

            # Check if input file still exists (being processed)
            if not self._input_file_exists(filename):
                # Input file was consumed, conversion in progress or failed
                poll_count += 1
                time.sleep(poll_interval)
                continue

            # Still waiting
            poll_count += 1
            time.sleep(poll_interval)

            elapsed = (datetime.now() - start_time).total_seconds()
            if elapsed > self.timeout_seconds:
                self.logger.warning(f"Conversion timeout for: {filename}")
                return {
                    'status': ConversionStatus.TIMEOUT,
                    'success': False,
                    'elapsed_seconds': elapsed,
                    'message': f'Conversion did not complete within {self.timeout_seconds} seconds'
                }

        # Max polls exceeded
        self.logger.warning(f"Conversion polling exceeded max attempts for: {filename}")
        return {
            'status': ConversionStatus.FAILED,
            'success': False,
            'elapsed_seconds': (datetime.now() - start_time).total_seconds(),
            'message': 'Conversion process did not complete'
        }

    def _find_output_file(self, original_filename: str) -> Optional[Path]:
        """
        Find converted output file for given input

        Args:
            original_filename: Original input filename

        Returns:
            Path to output file if found, None otherwise
        """
        if not self.data_output_dir.exists():
            return None

        # Look for files matching the pattern
        base_name = Path(original_filename).stem

        # Check for exact match (base_name.json)
        exact_match = self.data_output_dir / f"{base_name}.json"
        if exact_match.exists():
            return exact_match

        # Check for files starting with base_name
        for file in self.data_output_dir.glob(f"{base_name}*"):
            if file.is_file() and file.suffix == '.json':
                return file

        return None

    def _input_file_exists(self, original_filename: str) -> bool:
        """
        Check if input file exists (is still being processed)

        Args:
            original_filename: Filename to check

        Returns:
            True if file exists in input directory
        """
        if not self.data_input_dir.exists():
            return False

        # Look for files with this name (might have timestamp prefix)
        for file in self.data_input_dir.glob(f"*{original_filename}"):
            if file.is_file():
                return True

        # Direct match
        direct_path = self.data_input_dir / original_filename
        return direct_path.exists()

    def _count_json_records(self, json_file: Path) -> int:
        """
        Count records in converted JSON file

        Args:
            json_file: Path to JSON file

        Returns:
            Number of records (or -1 if error)
        """
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Handle different JSON structures
            if isinstance(data, list):
                return len(data)
            elif isinstance(data, dict):
                # Check for 'data' key
                if 'data' in data:
                    return len(data['data']) if isinstance(data['data'], list) else 1
                return 1
            return 0

        except Exception as e:
            self.logger.error(f"Error counting JSON records: {e}")
            return -1

    def verify_conversion(self, input_filename: str, output_filename: str) -> bool:
        """
        Verify that conversion was successful

        Args:
            input_filename: Original input filename
            output_filename: Expected output filename

        Returns:
            True if output file exists and is valid JSON
        """
        output_path = self.data_output_dir / output_filename

        if not output_path.exists():
            self.logger.warning(f"Output file not found: {output_path}")
            return False

        # Verify it's valid JSON
        try:
            with open(output_path, 'r', encoding='utf-8') as f:
                json.load(f)
            return True
        except json.JSONDecodeError:
            self.logger.error(f"Invalid JSON in output file: {output_path}")
            return False
        except Exception as e:
            self.logger.error(f"Error verifying output file: {e}")
            return False


def create_conversion_service(
    data_input_dir: str,
    data_output_dir: str,
    timeout_seconds: int = 120
) -> ConversionService:
    """Factory function to create conversion service"""
    return ConversionService(data_input_dir, data_output_dir, timeout_seconds)
