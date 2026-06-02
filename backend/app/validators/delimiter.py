"""
CSV Delimiter Detection
Auto-detects CSV delimiter (comma, semicolon, tab)
"""

import csv
from pathlib import Path
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)

# Supported delimiters
SUPPORTED_DELIMITERS = [',', ';', '\t']


def detect_delimiter(file_path: str, encoding: str = 'utf-8', sample_size: int = 5000) -> str:
    """
    Detect CSV delimiter using csv.Sniffer and fallback heuristics

    Args:
        file_path: Path to CSV file
        encoding: File encoding
        sample_size: Number of bytes to sample

    Returns:
        Detected delimiter character
    """
    try:
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Read sample
        with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
            sample = f.read(sample_size)

        if not sample:
            logger.warning("Empty sample, defaulting to comma")
            return ','

        # Try csv.Sniffer first
        try:
            sniffer = csv.Sniffer()
            delimiter = sniffer.sniff(sample, delimiters=',;\t').delimiter
            logger.info(f"Delimiter detected by Sniffer: '{delimiter}'")
            return delimiter
        except csv.Error:
            logger.debug("Sniffer failed, using fallback heuristics")

        # Fallback: count occurrences
        delimiter = _detect_by_frequency(sample)
        logger.info(f"Delimiter detected by frequency analysis: '{delimiter}'")
        return delimiter

    except Exception as e:
        logger.error(f"Error detecting delimiter: {e}, defaulting to comma")
        return ','


def _detect_by_frequency(sample: str) -> str:
    """
    Detect delimiter by frequency analysis

    Args:
        sample: Sample of file content

    Returns:
        Most likely delimiter
    """
    # Count occurrences of each delimiter in first few lines
    lines = sample.split('\n')[:5]
    counts = {',': 0, ';': 0, '\t': 0}

    for line in lines:
        if not line.strip():
            continue
        for delim in counts:
            counts[delim] += line.count(delim)

    # Return delimiter with highest count
    if not any(counts.values()):
        return ','

    return max(counts.items(), key=lambda x: x[1])[0]


def is_delimiter_supported(delimiter: str) -> bool:
    """
    Check if delimiter is supported

    Args:
        delimiter: Delimiter character to check

    Returns:
        True if supported, False otherwise
    """
    return delimiter in SUPPORTED_DELIMITERS


def get_supported_delimiters() -> list:
    """Get list of supported delimiters"""
    return SUPPORTED_DELIMITERS.copy()


def validate_delimiter(file_path: str, encoding: str = 'utf-8') -> dict:
    """
    Validate and report on file delimiter

    Args:
        file_path: Path to CSV file
        encoding: File encoding

    Returns:
        Dict with delimiter info and validation status
    """
    try:
        delimiter = detect_delimiter(file_path, encoding)
        supported = is_delimiter_supported(delimiter)

        return {
            'delimiter': delimiter,
            'supported': supported,
            'error': None
        }
    except Exception as e:
        return {
            'delimiter': ',',
            'supported': True,
            'error': str(e)
        }


def parse_csv_with_detected_delimiter(file_path: str, encoding: str = 'utf-8') -> list:
    """
    Parse CSV file using detected delimiter

    Args:
        file_path: Path to CSV file
        encoding: File encoding

    Returns:
        List of dicts (parsed CSV rows)
    """
    delimiter = detect_delimiter(file_path, encoding)

    rows = []
    try:
        with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
            reader = csv.DictReader(f, delimiter=delimiter)
            for row in reader:
                if any(row.values()):  # Skip empty rows
                    rows.append(row)
    except Exception as e:
        logger.error(f"Error parsing CSV: {e}")

    return rows
