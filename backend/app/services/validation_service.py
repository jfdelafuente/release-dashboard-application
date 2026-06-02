"""
Validation Service
Orchestrates all CSV validation logic
"""

import logging
from pathlib import Path
from typing import Dict, Optional

from app.validators.encoding import detect_encoding, is_encoding_supported
from app.validators.delimiter import detect_delimiter, is_delimiter_supported
from app.validators.headers import validate_headers, get_required_headers
from app.validators.counter import count_csv_rows_with_header
from app.utils.preview import generate_preview, format_file_size
from app.utils.error_messages import (
    get_error_message, missing_headers_error, unsupported_encoding_error,
    no_data_rows_error, delimiter_not_detected_error
)

logger = logging.getLogger(__name__)


class ValidationResult:
    """Result object containing validation outcomes"""

    def __init__(self, file_path: str, original_filename: str):
        self.file_path = file_path
        self.original_filename = original_filename

        # Validation steps
        self.encoding = None
        self.encoding_confidence = 0.0
        self.encoding_supported = False
        self.encoding_error = None

        self.delimiter = None
        self.delimiter_supported = False
        self.delimiter_error = None

        self.headers = []
        self.headers_valid = False
        self.missing_headers = []
        self.headers_error = None

        self.row_counts = {'header_count': 0, 'data_count': 0, 'empty_count': 0, 'total_count': 0}
        self.rows_valid = False
        self.rows_error = None

        # Summary
        self.is_valid = False
        self.all_errors = []
        self.warnings = []
        self.preview_data = {}

    def to_dict(self) -> Dict:
        """Convert result to dictionary for API response"""
        return {
            'valid': self.is_valid,
            'encoding': self.encoding,
            'encoding_confidence': self.encoding_confidence,
            'delimiter': self.delimiter,
            'headers': self.headers,
            'headers_count': len(self.headers),
            'row_counts': self.row_counts,
            'record_count': self.row_counts['data_count'],
            'errors': self.all_errors,
            'warnings': self.warnings,
            'preview': self.preview_data
        }


class ValidationService:
    """Orchestrates CSV validation pipeline"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def validate_file(self, file_path: str, original_filename: str) -> ValidationResult:
        """
        Run complete validation pipeline

        Args:
            file_path: Path to CSV file
            original_filename: Original filename for reference

        Returns:
            ValidationResult object with all validation details
        """
        result = ValidationResult(file_path, original_filename)

        try:
            # Step 1: Detect encoding
            self._validate_encoding(result)
            if result.encoding_error:
                return result

            # Step 2: Detect delimiter
            self._validate_delimiter(result)
            if result.delimiter_error:
                return result

            # Step 3: Validate headers
            self._validate_headers(result)
            if result.headers_error:
                return result

            # Step 4: Count rows
            self._validate_rows(result)
            if result.rows_error:
                return result

            # Step 5: Generate warnings
            self._generate_warnings(result)

            # Step 6: Generate preview data
            self._generate_preview(result)

            # Mark as valid if all steps passed
            result.is_valid = (
                result.encoding_supported and
                result.delimiter_supported and
                result.headers_valid and
                result.rows_valid
            )

            self.logger.info(f"Validation complete: {original_filename} - Valid: {result.is_valid}")
            return result

        except Exception as e:
            self.logger.error(f"Validation error: {e}", exc_info=True)
            result.all_errors.append(str(e))
            result.is_valid = False
            return result

    def _validate_encoding(self, result: ValidationResult) -> None:
        """Validate file encoding"""
        try:
            encoding, confidence = detect_encoding(result.file_path)
            result.encoding = encoding
            result.encoding_confidence = confidence

            if not is_encoding_supported(encoding):
                result.encoding_error = get_error_message(
                    'unsupported_encoding',
                    encoding=encoding
                )
                result.all_errors.append(result.encoding_error)
                result.encoding_supported = False
                return

            result.encoding_supported = True
            self.logger.debug(f"Encoding validated: {encoding} (confidence: {confidence})")

        except Exception as e:
            result.encoding_error = str(e)
            result.all_errors.append(f"Encoding detection error: {e}")
            self.logger.error(f"Encoding validation error: {e}")

    def _validate_delimiter(self, result: ValidationResult) -> None:
        """Validate CSV delimiter"""
        try:
            delimiter = detect_delimiter(result.file_path, result.encoding)
            result.delimiter = delimiter

            if not is_delimiter_supported(delimiter):
                result.delimiter_error = get_error_message('delimiter_not_detected')
                result.all_errors.append(result.delimiter_error)
                result.delimiter_supported = False
                return

            result.delimiter_supported = True
            self.logger.debug(f"Delimiter validated: {repr(delimiter)}")

        except Exception as e:
            result.delimiter_error = str(e)
            result.all_errors.append(f"Delimiter detection error: {e}")
            self.logger.error(f"Delimiter validation error: {e}")

    def _validate_headers(self, result: ValidationResult) -> None:
        """Validate CSV headers"""
        try:
            headers_result = validate_headers(
                result.file_path,
                result.encoding,
                result.delimiter
            )

            result.headers = headers_result['headers']
            result.headers_valid = headers_result['valid']
            result.missing_headers = headers_result['missing_headers']

            if not result.headers_valid:
                result.headers_error = get_error_message(
                    'missing_headers',
                    columns=', '.join(result.missing_headers)
                )
                result.all_errors.append(result.headers_error)
                return

            self.logger.debug(f"Headers validated: {len(result.headers)} columns")

        except Exception as e:
            result.headers_error = str(e)
            result.all_errors.append(f"Headers validation error: {e}")
            self.logger.error(f"Headers validation error: {e}")

    def _validate_rows(self, result: ValidationResult) -> None:
        """Validate row count"""
        try:
            row_counts = count_csv_rows_with_header(
                result.file_path,
                result.encoding,
                result.delimiter
            )

            result.row_counts = row_counts
            result.rows_valid = row_counts['data_count'] > 0

            if not result.rows_valid:
                result.rows_error = get_error_message('no_data_rows')
                result.all_errors.append(result.rows_error)
                return

            self.logger.debug(f"Rows validated: {row_counts['data_count']} data rows")

        except Exception as e:
            result.rows_error = str(e)
            result.all_errors.append(f"Row validation error: {e}")
            self.logger.error(f"Row validation error: {e}")

    def _generate_warnings(self, result: ValidationResult) -> None:
        """Generate validation warnings"""
        warnings = []

        # Check encoding
        if result.encoding != 'utf-8':
            warnings.append(f"Unusual encoding detected: {result.encoding}")

        # Check encoding confidence
        if result.encoding_confidence < 0.7:
            warnings.append("Low confidence in encoding detection")

        # Check delimiter
        if result.delimiter != ',':
            warnings.append(f"Unusual delimiter detected: {repr(result.delimiter)}")

        # Check for empty rows
        if result.row_counts.get('empty_count', 0) > 0:
            warnings.append(f"{result.row_counts['empty_count']} empty rows found")

        result.warnings = warnings
        if warnings:
            self.logger.info(f"Validation warnings: {warnings}")

    def _generate_preview(self, result: ValidationResult) -> None:
        """Generate preview data"""
        try:
            preview = generate_preview(result.file_path)

            if preview.get('success'):
                result.preview_data = {
                    'filename': preview.get('filename'),
                    'file_size_formatted': preview.get('file_size_formatted'),
                    'encoding': result.encoding,
                    'delimiter': result.delimiter,
                    'headers': result.headers,
                    'record_count': result.row_counts['data_count']
                }

        except Exception as e:
            self.logger.warning(f"Error generating preview: {e}")


def create_validation_service() -> ValidationService:
    """Factory function to create validation service"""
    return ValidationService()
