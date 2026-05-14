"""
Field validation logic.

Validates incident record fields against schema rules (presence, type, format, values).
"""

from .schemas import FIELD_VALIDATORS, ALLOWED_VALUES, REQUIRED_FIELDS
from .normalizers import normalize_datetime


class ValidationError(Exception):
    """Raised when field validation fails."""
    pass


def validate_record(record: dict, row_number: int) -> tuple[bool, list[dict]]:
    """
    Validate all fields in a record.

    Args:
        record: Dictionary of field name → value pairs
        row_number: Row number in CSV (for error reporting)

    Returns:
        Tuple of (is_valid, errors) where errors is list of error dicts
    """
    errors = []

    # Check required fields
    for field_name in REQUIRED_FIELDS:
        value = record.get(field_name, "")
        if not value or value.strip() == "":
            errors.append({
                "field": field_name,
                "original": value,
                "error": f"Required field '{field_name}' is empty or missing"
            })

    # Validate each field present in record
    for field_name, value in record.items():
        if field_name not in FIELD_VALIDATORS:
            # Unknown field - pass through as-is (allowed per spec)
            continue

        validator_config = FIELD_VALIDATORS[field_name]

        # Required field check
        if validator_config.get("required") and (not value or value.strip() == ""):
            errors.append({
                "field": field_name,
                "original": value,
                "error": f"Required field '{field_name}' is empty"
            })
            continue

        # Skip validation of empty optional fields
        if not validator_config.get("required") and (not value or value.strip() == ""):
            continue

        # Type-specific validation
        field_type = validator_config.get("type")

        if field_type == "enum":
            allowed = validator_config.get("allowed_values", [])
            if value not in allowed:
                errors.append({
                    "field": field_name,
                    "original": value,
                    "error": f"Invalid {field_name} value: '{value}'. "
                             f"Allowed values: {allowed}"
                })

        elif field_type == "datetime":
            try:
                normalize_datetime(value)
            except ValueError as e:
                errors.append({
                    "field": field_name,
                    "original": value,
                    "error": str(e)
                })

        elif field_type == "text":
            # Check max length
            max_length = validator_config.get("max_length")
            if max_length and len(value) > max_length:
                errors.append({
                    "field": field_name,
                    "original": value,
                    "error": f"Field '{field_name}' exceeds max length {max_length}"
                })

    return len(errors) == 0, errors


def validate_field(field_name: str, value: str, normalized_value: str = None) -> tuple[bool, str]:
    """
    Validate a single field.

    Args:
        field_name: Name of the field
        value: Original value from CSV
        normalized_value: Normalized value (if applicable)

    Returns:
        Tuple of (is_valid, error_message)
    """
    if field_name not in FIELD_VALIDATORS:
        return True, ""

    config = FIELD_VALIDATORS[field_name]

    # Use normalized value if provided
    check_value = normalized_value if normalized_value is not None else value

    # Required field check
    if config.get("required") and (not check_value or check_value.strip() == ""):
        return False, f"Required field '{field_name}' is empty"

    # Skip validation of empty optional fields
    if not config.get("required") and (not check_value or check_value.strip() == ""):
        return True, ""

    # Enum validation
    if config.get("type") == "enum":
        allowed = config.get("allowed_values", [])
        if check_value not in allowed:
            return False, (f"Invalid {field_name} value: '{check_value}'. "
                          f"Allowed values: {allowed}")

    return True, ""
