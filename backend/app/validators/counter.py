"""
CSV Row Counter
Efficiently counts rows without loading entire file into memory
"""

import csv
from pathlib import Path
from typing import Dict
import logging

logger = logging.getLogger(__name__)


def count_csv_rows(
    file_path: str,
    encoding: str = 'utf-8',
    delimiter: str = ',',
    include_header: bool = False
) -> int:
    """
    Count rows in CSV file efficiently

    Args:
        file_path: Path to CSV file
        encoding: File encoding
        delimiter: CSV delimiter
        include_header: If True, include header row in count

    Returns:
        Number of rows (excluding header by default)
    """
    try:
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        row_count = 0
        with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
            reader = csv.reader(f, delimiter=delimiter)

            # Skip header if not including it
            if not include_header:
                try:
                    next(reader)
                except StopIteration:
                    return 0

            # Count remaining rows
            for row in reader:
                # Only count non-empty rows
                if any(cell.strip() for cell in row):
                    row_count += 1

        logger.info(f"CSV row count: {row_count} (excluding header)")
        return row_count

    except Exception as e:
        logger.error(f"Error counting CSV rows: {e}")
        return 0


def count_csv_rows_with_header(
    file_path: str,
    encoding: str = 'utf-8',
    delimiter: str = ','
) -> Dict[str, int]:
    """
    Count header and data rows separately

    Args:
        file_path: Path to CSV file
        encoding: File encoding
        delimiter: CSV delimiter

    Returns:
        Dict with header_count and data_count
    """
    try:
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        header_count = 0
        data_count = 0
        empty_count = 0

        with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
            reader = csv.reader(f, delimiter=delimiter)

            for i, row in enumerate(reader):
                if i == 0:
                    # First row is header
                    header_count = 1
                else:
                    # Check if row is empty
                    if any(cell.strip() for cell in row):
                        data_count += 1
                    else:
                        empty_count += 1

        return {
            'header_count': header_count,
            'data_count': data_count,
            'empty_count': empty_count,
            'total_count': header_count + data_count + empty_count
        }

    except Exception as e:
        logger.error(f"Error counting CSV rows with header: {e}")
        return {
            'header_count': 0,
            'data_count': 0,
            'empty_count': 0,
            'total_count': 0
        }


def validate_row_count(file_path: str, encoding: str = 'utf-8', delimiter: str = ',') -> Dict:
    """
    Validate and report on CSV row count

    Args:
        file_path: Path to CSV file
        encoding: File encoding
        delimiter: CSV delimiter

    Returns:
        Dict with row count info and validation status
    """
    try:
        counts = count_csv_rows_with_header(file_path, encoding, delimiter)

        result = {
            'valid': counts['data_count'] > 0,
            'row_counts': counts,
            'error': None
        }

        if not result['valid']:
            result['error'] = 'No data rows found in CSV file. Ensure data starts below headers.'

        return result

    except Exception as e:
        return {
            'valid': False,
            'row_counts': {
                'header_count': 0,
                'data_count': 0,
                'empty_count': 0,
                'total_count': 0
            },
            'error': str(e)
        }
