"""
Field normalization utilities.

Normalizes field values before validation (trim, casing, format standardization).
"""

import re
from datetime import datetime
from csv_to_json.schemas import DATE_FORMAT, NORMALIZE_FIELDS


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

    Preserves format from CSV ("dd/mm/yyyy HH:mm AM/PM").

    Args:
        date_str: Date string from CSV

    Returns:
        Normalized (validated) date string

    Raises:
        ValueError: If date cannot be parsed
    """
    if not date_str:
        raise ValueError("Date string is empty")

    try:
        # Parse the date
        dt = datetime.strptime(date_str.strip(), DATE_FORMAT)
        # Return in original format (preserved exactly)
        return date_str.strip()
    except ValueError as e:
        raise ValueError(
            f"Invalid date format: '{date_str}'. Expected dd/mm/yyyy HH:mm AM/PM"
        )
