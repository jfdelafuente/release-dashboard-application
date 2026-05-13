"""
CSV delimiter detection.

Automatically detects CSV delimiter (comma, semicolon, tab).
"""

import csv


def detect_delimiter(file_text: str, sample_lines: int = 5) -> str:
    """
    Detect CSV delimiter using csv.Sniffer with fallback logic.

    Args:
        file_text: CSV file text
        sample_lines: Number of lines to sample for detection

    Returns:
        Detected delimiter character (e.g., ',', ';', '\t')
    """
    if not file_text:
        return ','

    # Extract sample lines for detection
    lines = file_text.split('\n')
    sample = '\n'.join(lines[:sample_lines])

    # Try csv.Sniffer first
    try:
        dialect = csv.Sniffer().sniff(sample)
        return dialect.delimiter
    except csv.Error:
        pass

    # Fallback: Try common delimiters manually
    for delimiter in [',', ';', '\t']:
        count = file_text.count(delimiter)
        # If delimiter appears more than 5 times, likely correct
        if count > 5:
            return delimiter

    # Default to comma if nothing found
    return ','


def parse_csv_with_delimiter(file_text: str, delimiter: str = None) -> list[dict]:
    """
    Parse CSV text with detected or specified delimiter.

    Args:
        file_text: CSV file text
        delimiter: Delimiter to use (auto-detect if None)

    Returns:
        List of dictionaries (one per row)
    """
    if delimiter is None:
        delimiter = detect_delimiter(file_text)

    records = []
    reader = csv.DictReader(file_text.strip().split('\n'), delimiter=delimiter)

    for row in reader:
        if row:  # Skip empty rows
            records.append(row)

    return records
