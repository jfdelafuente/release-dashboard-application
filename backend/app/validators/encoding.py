"""
CSV Encoding Detection
Auto-detects file encoding from byte patterns
"""

import chardet
from pathlib import Path
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)

# Supported encodings in priority order
SUPPORTED_ENCODINGS = [
    'utf-8',
    'utf-8-sig',
    'windows-1252',
    'latin-1',
    'iso-8859-15'
]

# BOM (Byte Order Mark) signatures
BOM_SIGNATURES = {
    b'\xef\xbb\xbf': 'utf-8-sig',
    b'\xff\xfe': 'utf-16-le',
    b'\xfe\xff': 'utf-16-be',
    b'\xff\xfe\x00\x00': 'utf-32-le',
    b'\x00\x00\xfe\xff': 'utf-32-be',
}


def detect_encoding(file_path: str, sample_size: int = 10000) -> Tuple[str, float]:
    """
    Detect file encoding using multiple methods

    Args:
        file_path: Path to CSV file
        sample_size: Number of bytes to sample for detection

    Returns:
        Tuple of (encoding, confidence) where confidence is 0-1
    """
    try:
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        with open(file_path, 'rb') as f:
            raw_data = f.read(sample_size)

        # Check for BOM first
        for bom, encoding in BOM_SIGNATURES.items():
            if raw_data.startswith(bom):
                logger.debug(f"Detected BOM signature: {encoding}")
                return encoding, 1.0

        # Use chardet for detection
        detection = chardet.detect(raw_data)
        detected_encoding = detection.get('encoding', 'utf-8')
        confidence = detection.get('confidence', 0)

        # Normalize encoding name
        detected_encoding = normalize_encoding(detected_encoding)

        logger.info(
            f"Encoding detected: {detected_encoding} (confidence: {confidence:.2f})"
        )

        # Check if encoding is supported
        if detected_encoding not in SUPPORTED_ENCODINGS:
            logger.warning(
                f"Detected encoding '{detected_encoding}' not officially supported. "
                f"Falling back to utf-8"
            )
            return 'utf-8', 0.5

        return detected_encoding, confidence

    except Exception as e:
        logger.error(f"Error detecting encoding: {e}")
        return 'utf-8', 0.0


def normalize_encoding(encoding: Optional[str]) -> str:
    """
    Normalize encoding name to standard format

    Args:
        encoding: Raw encoding name from detection

    Returns:
        Normalized encoding name
    """
    if not encoding:
        return 'utf-8'

    # Convert to lowercase and replace common variations
    encoding = encoding.lower().strip()
    encoding = encoding.replace('_', '-')

    # Map common variations to standard names
    encoding_map = {
        'utf8': 'utf-8',
        'utf-8-sig': 'utf-8-sig',
        'utf8-sig': 'utf-8-sig',
        'cp1252': 'windows-1252',
        'windows1252': 'windows-1252',
        'iso-8859-1': 'latin-1',
        'iso-latin-1': 'latin-1',
        'latin1': 'latin-1',
        'iso-8859-15': 'iso-8859-15',
        'iso-latin-9': 'iso-8859-15',
    }

    return encoding_map.get(encoding, encoding)


def is_encoding_supported(encoding: str) -> bool:
    """
    Check if encoding is supported

    Args:
        encoding: Encoding name to check

    Returns:
        True if supported, False otherwise
    """
    normalized = normalize_encoding(encoding)
    return normalized in SUPPORTED_ENCODINGS


def get_supported_encodings() -> list:
    """Get list of supported encodings"""
    return SUPPORTED_ENCODINGS.copy()


def validate_encoding(file_path: str) -> dict:
    """
    Validate and report on file encoding

    Args:
        file_path: Path to CSV file

    Returns:
        Dict with encoding info and validation status
    """
    try:
        encoding, confidence = detect_encoding(file_path)
        supported = is_encoding_supported(encoding)

        return {
            'encoding': encoding,
            'confidence': confidence,
            'supported': supported,
            'error': None
        }
    except Exception as e:
        return {
            'encoding': 'utf-8',
            'confidence': 0.0,
            'supported': True,
            'error': str(e)
        }
