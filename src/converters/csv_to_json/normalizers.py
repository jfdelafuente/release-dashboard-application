"""
Field normalization utilities.

Normalizes field values before validation (trim, casing, format standardization).
"""

import re
from datetime import datetime
from .schemas import DATE_FORMAT, NORMALIZE_FIELDS


def normalize_field(field_name: str, value: str) -> str:
    """
    Normalize a field value according to normalization rules.

    Args:
        field_name: Name of the field
        value: Original value from CSV

    Returns:
        Normalized value
    """
    if value is None:
        return ""

    # All fields: trim whitespace
    value = value.strip()

    # Apply field-specific normalization
    if field_name in NORMALIZE_FIELDS:
        rule = NORMALIZE_FIELDS[field_name]

        if rule == "title_case":
            value = normalize_title_case(value)
        elif rule == "extract_text_and_title_case":
            value = normalize_urgencia(value)

    return value


def normalize_title_case(value: str) -> str:
    """Normalize to title case."""
    return value.title() if value else value


def normalize_urgencia(value: str) -> str:
    """
    Normalize Urgencia field from "N-Text" format to text-only.

    Examples:
        "4-Baja" → "Baja"
        "3-Medio" → "Medio"
        "2-Alta" → "Alta"
        "1-Crítica" → "Crítica"
    """
    # Try to extract text portion from "N-Text" format
    match = re.match(r'^\d+\s*-\s*(.+)$', value)
    if match:
        extracted = match.group(1).strip()
        return normalize_title_case(extracted)

    # If no match, normalize the value as-is
    return normalize_title_case(value)


def normalize_datetime(date_str: str) -> str:
    """
    Validate and normalize datetime string.

    Accepts flexible formats:
    - dd/mm/yyyy HH:mm (24-hour format)
    - dd/mm/yyyy HH:mm AM/PM (12-hour format, case-insensitive)
    - dd/mm/yyyy HH:mm a/p (12-hour format shorthand, case-insensitive)

    Handles data quality issues:
    - Removes AM/PM indicators if hour is in 24-hour format (>12)
    - Normalizes mixed formats gracefully
    - Converts single-digit hours (0:mm, 1:mm) to zero-padded format (00:mm, 01:mm)

    Args:
        date_str: Date string from CSV

    Returns:
        Normalized date string in dd/mm/yyyy HH:mm format

    Raises:
        ValueError: If date cannot be parsed
    """
    if not date_str:
        raise ValueError("Date string is empty")

    date_str = date_str.strip()

    # Normalize: remove extra spaces
    normalized = re.sub(r'\s+', ' ', date_str)

    # Normalize single-digit hours to zero-padded format (e.g., "0:46" → "00:46", "1:30" → "01:30")
    # Match patterns like "d/m/yyyy h:mm" and convert to "d/m/yyyy hh:mm"
    normalized = re.sub(r'(\d{1,2}/\d{1,2}/\d{4})\s+(\d):', r'\1 0\2:', normalized)

    # First, try 24-hour format without AM/PM
    try:
        dt = datetime.strptime(normalized, "%d/%m/%Y %H:%M")
        return dt.strftime("%d/%m/%Y %H:%M")
    except ValueError:
        pass

    # If that fails, try removing AM/PM indicators and retry
    # (handles mixed format like "15:36 a" which should be "15:36" or "0:46 a" which should be "00:46")
    normalized_no_ampm = re.sub(r'\s+[aApP][mM]?\s*$', '', normalized)
    if normalized_no_ampm != normalized:
        try:
            dt = datetime.strptime(normalized_no_ampm, "%d/%m/%Y %H:%M")
            # Accept 24-hour format (hour > 12) or hour 0 (which is midnight/00:00)
            # Hour 0 with "a" suffix likely means "0:46 a" = "00:46 AM" (midnight)
            if dt.hour > 12 or dt.hour == 0:
                return dt.strftime("%d/%m/%Y %H:%M")
        except ValueError:
            pass

    # If still failing, try with proper 12-hour format
    # Convert to uppercase and normalize a/p to AM/PM
    normalized_upper = normalized.upper()
    normalized_upper = re.sub(r'\s+A\s*$', ' AM', normalized_upper)
    normalized_upper = re.sub(r'\s+P\s*$', ' PM', normalized_upper)

    # Try 12-hour format patterns
    formats_12h = [
        "%d/%m/%Y %I:%M %p",   # with space before AM/PM
        "%d/%m/%Y %I:%M%p",    # without space before AM/PM
    ]

    for fmt in formats_12h:
        try:
            dt = datetime.strptime(normalized_upper, fmt)
            # Convert to 24-hour format
            return dt.strftime("%d/%m/%Y %H:%M")
        except ValueError:
            continue

    # If all formats fail, raise error
    raise ValueError(
        f"Invalid date format: '{date_str}'. Expected dd/mm/yyyy HH:mm"
    )
