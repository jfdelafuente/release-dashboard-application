"""
CSV Preview Generator
Extracts file metadata and preview information
"""

import os
from pathlib import Path
from typing import Dict, List
import logging

from app.validators.encoding import detect_encoding
from app.validators.delimiter import detect_delimiter
from app.validators.headers import validate_headers
from app.validators.counter import count_csv_rows_with_header

logger = logging.getLogger(__name__)


def format_file_size(size_bytes: int) -> str:
    """
    Format bytes to human-readable size

    Args:
        size_bytes: Size in bytes

    Returns:
        Formatted size string
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def generate_preview(file_path: str) -> Dict:
    """
    Generate complete preview metadata for a CSV file

    Args:
        file_path: Path to CSV file

    Returns:
        Dict with file metadata and validation results
    """
    try:
        file_path = Path(file_path)

        if not file_path.exists():
            return {
                'success': False,
                'error': 'File not found'
            }

        # Get file info
        stat = file_path.stat()
        file_size = stat.st_size
        filename = file_path.name

        preview = {
            'success': True,
            'filename': filename,
            'file_size_bytes': file_size,
            'file_size_formatted': format_file_size(file_size),
            'file_path': str(file_path)
        }

        # Detect encoding
        encoding, encoding_confidence = detect_encoding(str(file_path))
        preview['encoding_detected'] = encoding
        preview['encoding_confidence'] = round(encoding_confidence, 2)

        # Detect delimiter
        delimiter = detect_delimiter(str(file_path), encoding)
        preview['delimiter_detected'] = repr(delimiter)[1:-1]  # Convert to readable format
        preview['delimiter_detected_raw'] = delimiter

        # Validate headers
        headers_result = validate_headers(str(file_path), encoding, delimiter)
        preview['headers_valid'] = headers_result['valid']
        preview['headers'] = headers_result['headers']
        preview['headers_count'] = len(headers_result['headers'])
        if headers_result['missing_headers']:
            preview['missing_headers'] = headers_result['missing_headers']

        # Count rows
        row_counts = count_csv_rows_with_header(str(file_path), encoding, delimiter)
        preview['row_counts'] = row_counts
        preview['record_count'] = row_counts['data_count']

        # Generate warnings
        preview['warnings'] = generate_warnings(preview)

        logger.info(f"Preview generated for: {filename}")
        logger.debug(f"Preview details: {preview}")

        return preview

    except Exception as e:
        logger.error(f"Error generating preview: {e}")
        return {
            'success': False,
            'error': str(e)
        }


def generate_warnings(preview: Dict) -> List[str]:
    """
    Generate list of warnings based on preview data

    Args:
        preview: Preview dict from generate_preview

    Returns:
        List of warning messages
    """
    warnings = []

    # Check file size
    if preview.get('file_size_bytes', 0) > 100 * 1024 * 1024:  # > 100MB
        warnings.append('El archivo es grande (>100MB). El procesamiento puede tardar más tiempo.')

    # Check encoding
    if preview.get('encoding_detected') != 'utf-8':
        warnings.append(f'Codificación inusual detectada: {preview.get("encoding_detected")}')

    # Check encoding confidence
    if preview.get('encoding_confidence', 0) < 0.7:
        warnings.append('Baja confianza en la detección de codificación.')

    # Check delimiter
    delimiter = preview.get('delimiter_detected', '')
    if delimiter != ',':
        warnings.append(f'Delimitador detectado: "{delimiter}" (no es coma)')

    # Check row count
    if preview.get('record_count', 0) == 0:
        warnings.append('No se encontraron filas de datos.')

    # Check for empty rows
    if preview.get('row_counts', {}).get('empty_count', 0) > 0:
        warnings.append(f'{preview.get("row_counts", {}).get("empty_count", 0)} filas vacías detectadas.')

    return warnings


def get_file_info(file_path: str) -> Dict:
    """
    Get basic file information

    Args:
        file_path: Path to file

    Returns:
        Dict with file info
    """
    try:
        file_path = Path(file_path)

        if not file_path.exists():
            return {'error': 'File not found'}

        stat = file_path.stat()

        return {
            'filename': file_path.name,
            'path': str(file_path),
            'size_bytes': stat.st_size,
            'size_formatted': format_file_size(stat.st_size),
            'created': Path(file_path).stat().st_ctime,
            'modified': stat.st_mtime,
            'is_file': file_path.is_file(),
            'is_directory': file_path.is_dir()
        }

    except Exception as e:
        logger.error(f"Error getting file info: {e}")
        return {'error': str(e)}


def compare_previews(preview1: Dict, preview2: Dict) -> Dict:
    """
    Compare two CSV file previews

    Args:
        preview1: First preview dict
        preview2: Second preview dict

    Returns:
        Dict with comparison results
    """
    comparison = {
        'same_encoding': preview1.get('encoding_detected') == preview2.get('encoding_detected'),
        'same_delimiter': preview1.get('delimiter_detected_raw') == preview2.get('delimiter_detected_raw'),
        'same_headers': preview1.get('headers') == preview2.get('headers'),
        'same_row_count': preview1.get('record_count') == preview2.get('record_count'),
        'size_difference_bytes': abs(
            preview1.get('file_size_bytes', 0) - preview2.get('file_size_bytes', 0)
        )
    }

    return comparison
