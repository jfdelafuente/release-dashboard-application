"""
File Name Sanitizer
Removes dangerous characters and prevents directory traversal attacks
"""

import re
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Characters to remove from filenames
DANGEROUS_CHARS_PATTERN = re.compile(r'[<>:"|?*\x00-\x1f]')
DIRECTORY_TRAVERSAL_PATTERN = re.compile(r'\.\.|\0|[/\\]')


def sanitize_filename(filename: str, max_length: int = 255) -> str:
    """
    Sanitize filename by removing/escaping dangerous characters

    Args:
        filename: Original filename
        max_length: Maximum length for filename (excluding extension)

    Returns:
        Sanitized filename
    """
    if not filename:
        raise ValueError("Filename cannot be empty")

    # Remove directory separators (prevent directory traversal)
    filename = DIRECTORY_TRAVERSAL_PATTERN.sub('_', filename)

    # Remove dangerous characters
    filename = DANGEROUS_CHARS_PATTERN.sub('_', filename)

    # Remove leading/trailing spaces and dots
    filename = filename.strip('. ')

    # Truncate if too long
    if len(filename) > max_length:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        max_name_length = max_length - len(ext) - 1 if ext else max_length
        filename = name[:max_name_length]
        if ext:
            filename = f"{filename}.{ext}"

    if not filename or filename == '_' * len(filename):
        raise ValueError("Filename is invalid after sanitization")

    logger.debug(f"Sanitized filename: {filename}")
    return filename


def prevent_directory_traversal(file_path: str, allowed_directory: str) -> bool:
    """
    Verify that file path is within allowed directory

    Args:
        file_path: Full path to file
        allowed_directory: Directory where file should be

    Returns:
        True if file is within allowed directory, False otherwise
    """
    try:
        file_path = Path(file_path).resolve()
        allowed_dir = Path(allowed_directory).resolve()

        # Check if file is within allowed directory
        return str(file_path).startswith(str(allowed_dir))

    except (ValueError, OSError) as e:
        logger.error(f"Path resolution error: {e}")
        return False


def validate_file_path(file_path: str, allowed_directory: str) -> dict:
    """
    Validate file path for security issues

    Args:
        file_path: Path to validate
        allowed_directory: Directory where file should be

    Returns:
        Dict with validation status and messages
    """
    result = {
        'valid': True,
        'errors': []
    }

    # Check for directory traversal attempts
    if '..' in file_path or file_path.startswith('/') or file_path.startswith('\\'):
        result['valid'] = False
        result['errors'].append('Path contains directory traversal characters')
        logger.warning(f"Directory traversal attempt detected: {file_path}")

    # Check if file would be in allowed directory
    if not prevent_directory_traversal(file_path, allowed_directory):
        result['valid'] = False
        result['errors'].append('File path is outside allowed directory')
        logger.warning(f"File outside allowed directory: {file_path}")

    # Check for null bytes
    if '\x00' in file_path:
        result['valid'] = False
        result['errors'].append('File path contains null bytes')
        logger.warning('Null byte detected in file path')

    return result


def escape_csv_field(value: str) -> str:
    """
    Escape potentially dangerous characters in CSV fields

    Args:
        value: Field value to escape

    Returns:
        Escaped value
    """
    if not isinstance(value, str):
        return str(value)

    # Remove control characters
    value = ''.join(char for char in value if ord(char) >= 32 or char in '\n\r\t')

    # Escape double quotes
    value = value.replace('"', '""')

    # If field contains comma, newline, or quote, wrap in quotes
    if any(char in value for char in [',', '\n', '"']):
        value = f'"{value}"'

    return value


def remove_bom(text: str) -> str:
    """
    Remove Byte Order Mark (BOM) from text

    Args:
        text: Text potentially containing BOM

    Returns:
        Text without BOM
    """
    if text.startswith('\ufeff'):
        return text[1:]
    return text


def sanitize_csv_row(row: dict) -> dict:
    """
    Sanitize a CSV row by escaping all fields

    Args:
        row: Dict representing CSV row

    Returns:
        Sanitized row
    """
    sanitized = {}
    for key, value in row.items():
        sanitized[key] = escape_csv_field(value) if value else ''
    return sanitized
