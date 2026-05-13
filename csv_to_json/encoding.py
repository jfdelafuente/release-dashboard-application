"""
Encoding detection for CSV files.

Automatically detects file encoding (UTF-8, UTF-8-sig, Windows-1252, Latin-1, ISO-8859-15).
"""


def detect_encoding(file_bytes: bytes) -> str:
    """
    Detect file encoding from byte signatures and content.

    Tries BOM signatures first, then falls back to trying common encodings.

    Args:
        file_bytes: Raw bytes from file

    Returns:
        Detected encoding name (e.g., 'utf-8', 'windows-1252')
    """
    if not file_bytes:
        return 'utf-8'

    # Check BOM (Byte Order Mark) signatures
    if file_bytes.startswith(b'\xef\xbb\xbf'):
        return 'utf-8-sig'
    if file_bytes.startswith(b'\xff\xfe'):
        return 'utf-16'
    if file_bytes.startswith(b'\xff\xfe\x00\x00'):
        return 'utf-32-le'
    if file_bytes.startswith(b'\x00\x00\xfe\xff'):
        return 'utf-32-be'

    # Try common encodings in order of likelihood
    encodings_to_try = [
        'utf-8',           # Most common
        'windows-1252',    # Windows (common source for CSV exports)
        'latin-1',         # ISO-8859-1 (European)
        'iso-8859-15',     # Latin-9
        'cp1252',          # Windows-1252 alias
    ]

    for encoding in encodings_to_try:
        try:
            file_bytes.decode(encoding)
            return encoding
        except (UnicodeDecodeError, LookupError):
            continue

    # Default fallback
    return 'utf-8'


def decode_file(file_bytes: bytes) -> tuple[str, str]:
    """
    Decode file bytes using detected encoding.

    Args:
        file_bytes: Raw bytes from file

    Returns:
        Tuple of (decoded_text, detected_encoding)
    """
    encoding = detect_encoding(file_bytes)

    try:
        text = file_bytes.decode(encoding)
        return text, encoding
    except Exception:
        # Final fallback - use utf-8 with error handling
        text = file_bytes.decode('utf-8', errors='replace')
        return text, 'utf-8 (with replacements)'
