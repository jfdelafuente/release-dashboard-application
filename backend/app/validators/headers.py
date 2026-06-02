"""
CSV Headers Validation
Validates that required headers are present in CSV file
"""

import csv
from pathlib import Path
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

# Required headers for massive incidents CSV
REQUIRED_HEADERS = [
    'ID de incidencia',
    'Descripción',
    'Estatus',
    'Fecha de envío',
    'Grupo asignado',
    'Urgencia',
    'Impacto'
]

# Optional but expected headers
OPTIONAL_HEADERS = [
    'Fecha de última resolución'
]


def validate_headers(
    file_path: str,
    encoding: str = 'utf-8',
    delimiter: str = ',',
    required_headers: Optional[List[str]] = None
) -> Dict:
    """
    Validate CSV headers

    Args:
        file_path: Path to CSV file
        encoding: File encoding
        delimiter: CSV delimiter
        required_headers: List of required headers (uses default if None)

    Returns:
        Dict with validation status, missing headers, found headers
    """
    if required_headers is None:
        required_headers = REQUIRED_HEADERS

    try:
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Read first row to get headers
        with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
            reader = csv.reader(f, delimiter=delimiter)
            try:
                headers = next(reader)
            except StopIteration:
                return {
                    'valid': False,
                    'headers': [],
                    'required_headers': required_headers,
                    'missing_headers': required_headers,
                    'extra_headers': [],
                    'error': 'No headers found in CSV file'
                }

        # Clean headers (strip whitespace)
        headers = [h.strip() for h in headers if h.strip()]

        # Check for BOM characters and remove if present
        if headers and headers[0].startswith('\ufeff'):
            headers[0] = headers[0][1:]

        # Find missing headers
        missing = [h for h in required_headers if h not in headers]
        extra = [h for h in headers if h not in required_headers + OPTIONAL_HEADERS]

        valid = len(missing) == 0

        result = {
            'valid': valid,
            'headers': headers,
            'required_headers': required_headers,
            'optional_headers': OPTIONAL_HEADERS,
            'missing_headers': missing,
            'extra_headers': extra,
            'error': None
        }

        if not valid:
            result['error'] = f"Missing required headers: {', '.join(missing)}"

        logger.info(f"Headers validation: valid={valid}, headers count={len(headers)}")
        if missing:
            logger.warning(f"Missing headers: {missing}")

        return result

    except Exception as e:
        logger.error(f"Error validating headers: {e}")
        return {
            'valid': False,
            'headers': [],
            'required_headers': required_headers,
            'missing_headers': required_headers,
            'extra_headers': [],
            'error': str(e)
        }


def get_required_headers() -> List[str]:
    """Get list of required headers"""
    return REQUIRED_HEADERS.copy()


def get_optional_headers() -> List[str]:
    """Get list of optional headers"""
    return OPTIONAL_HEADERS.copy()


def are_headers_valid(
    headers: List[str],
    required_headers: Optional[List[str]] = None
) -> bool:
    """
    Check if headers contain all required columns

    Args:
        headers: List of header names
        required_headers: List of required headers (uses default if None)

    Returns:
        True if all required headers present, False otherwise
    """
    if required_headers is None:
        required_headers = REQUIRED_HEADERS

    return all(h in headers for h in required_headers)


def normalize_headers(headers: List[str]) -> List[str]:
    """
    Normalize header names (strip whitespace, handle BOM)

    Args:
        headers: List of header names

    Returns:
        Normalized list of header names
    """
    normalized = []
    for h in headers:
        # Strip whitespace
        h = h.strip()
        # Remove BOM if present
        if h.startswith('\ufeff'):
            h = h[1:]
        normalized.append(h)
    return normalized
