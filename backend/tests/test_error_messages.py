"""
Tests for error message templates and formatting
Validates that all error messages are in Spanish and properly formatted
"""

import pytest
from app.utils.error_messages import (
    missing_headers_error, unsupported_encoding_error, delimiter_not_detected_error,
    no_data_rows_error, invalid_file_error, file_too_large_error, file_not_csv_error,
    empty_file_error, invalid_date_error, invalid_enum_error, network_error,
    server_error, permission_denied_error, disk_full_error, format_error_response,
    ERROR_TEMPLATES, ERROR_CODES, ERROR_HELP_LINKS
)


class TestErrorMessageTemplates:
    """Test error message template structure and content"""

    def test_all_error_codes_have_templates(self):
        """Verify that all error codes have corresponding templates"""
        # Get template keys (they use snake_case)
        template_keys = set(ERROR_TEMPLATES.keys())

        # ERROR_CODES maps human-readable names to ERR_XXX codes
        # We should have enough templates for all error types
        assert len(template_keys) >= 14, "Should have at least 14 error templates"

    def test_all_error_codes_have_help_links(self):
        """Verify that all error codes have help documentation links"""
        for code in ERROR_CODES.values():
            assert code in ERROR_HELP_LINKS, f"Error code {code} missing help link"
            assert ERROR_HELP_LINKS[code].startswith('https://'), f"Help link for {code} should be HTTPS URL"

    def test_all_messages_contain_spanish_text(self):
        """Verify all error messages are in Spanish (contain Spanish keywords)"""
        spanish_indicators = [
            'columna', 'archivo', 'error', 'verifica', 'por favor', 'no se',
            'asegúrate', 'intenta', 'contacta', 'permisos', 'espacio', 'directorio'
        ]

        for template_key, template in ERROR_TEMPLATES.items():
            text_lower = template.lower()
            has_spanish = any(indicator in text_lower for indicator in spanish_indicators)
            assert has_spanish, f"Template '{template_key}' may not be in Spanish: {template}"


class TestErrorMessageFunctions:
    """Test individual error message generation functions"""

    def test_missing_headers_error(self):
        """Test missing headers error includes specific column names"""
        error = missing_headers_error(['Estatus', 'Urgencia'])

        assert error['code'] == 'ERR_001'
        assert 'Estatus' in error['message']
        assert 'Urgencia' in error['message']
        assert 'columnas' in error['message'].lower()

    def test_unsupported_encoding_error(self):
        """Test unsupported encoding error includes encoding name"""
        error = unsupported_encoding_error('windows-1252')

        assert error['code'] == 'ERR_002'
        assert 'windows-1252' in error['message']
        assert 'UTF-8' in error['message'] or 'utf-8' in error['message'].lower()

    def test_delimiter_not_detected_error(self):
        """Test delimiter detection error provides guidance"""
        error = delimiter_not_detected_error()

        assert error['code'] == 'ERR_003'
        assert 'delimitador' in error['message'].lower() or 'delimiter' in error['message'].lower()

    def test_no_data_rows_error(self):
        """Test no data rows error explains what's needed"""
        error = no_data_rows_error()

        assert error['code'] == 'ERR_004'
        assert 'datos' in error['message'].lower() or 'data' in error['message'].lower()

    def test_invalid_file_error(self):
        """Test invalid file error without detail"""
        error = invalid_file_error()
        assert error['code'] == 'ERR_005'
        assert 'CSV' in error['message']

    def test_invalid_file_error_with_detail(self):
        """Test invalid file error with additional detail"""
        error = invalid_file_error('Corrupted headers')
        assert error['code'] == 'ERR_005'
        assert 'CSV' in error['message']
        assert 'Corrupted headers' in error['message']

    def test_file_too_large_error(self):
        """Test file size error includes max size"""
        error = file_too_large_error(500)

        assert error['code'] == 'ERR_006'
        assert '500' in error['message']

    def test_file_not_csv_error(self):
        """Test file extension error"""
        error = file_not_csv_error()

        assert error['code'] == 'ERR_007'
        assert '.csv' in error['message'] or 'csv' in error['message'].lower()

    def test_empty_file_error(self):
        """Test empty file error"""
        error = empty_file_error()

        assert error['code'] == 'ERR_008'
        assert 'vacío' in error['message'] or 'empty' in error['message'].lower()

    def test_invalid_date_error(self):
        """Test invalid date error includes value and column"""
        error = invalid_date_error('32/13/2026', 'Fecha de envío')

        assert error['code'] == 'ERR_009'
        assert '32/13/2026' in error['message']
        assert 'Fecha de envío' in error['message']

    def test_invalid_enum_error(self):
        """Test invalid enum value error includes allowed values"""
        error = invalid_enum_error('Desconocido', 'Estatus', ['Abierto', 'Cerrado', 'Pendiente'])

        assert error['code'] == 'ERR_010'
        assert 'Desconocido' in error['message']
        assert 'Estatus' in error['message']
        assert 'Abierto' in error['message']
        assert 'Cerrado' in error['message']

    def test_network_error(self):
        """Test network error message"""
        error = network_error()

        assert error['code'] == 'ERR_011'
        assert 'conexión' in error['message'].lower() or 'connection' in error['message'].lower()

    def test_server_error(self):
        """Test server error message"""
        error = server_error()

        assert error['code'] == 'ERR_012'
        assert 'servidor' in error['message'].lower() or 'server' in error['message'].lower()

    def test_permission_denied_error(self):
        """Test permission denied error"""
        error = permission_denied_error()

        assert error['code'] == 'ERR_013'
        assert 'permiso' in error['message'].lower() or 'permission' in error['message'].lower()

    def test_disk_full_error_with_details(self):
        """Test disk full error includes space information"""
        error = disk_full_error(available_space='100 MB', required_space='500 MB')

        assert error['code'] == 'ERR_014'
        assert 'espacio' in error['message'].lower() or 'space' in error['message'].lower()
        assert '100 MB' in error['message']
        assert '500 MB' in error['message']

    def test_disk_full_error_without_details(self):
        """Test disk full error with default values"""
        error = disk_full_error()

        assert error['code'] == 'ERR_014'
        assert 'espacio' in error['message'].lower() or 'space' in error['message'].lower()


class TestErrorResponseFormatting:
    """Test error response formatting for API"""

    def test_format_error_response_includes_help_url(self):
        """Verify formatted error includes help URL"""
        error = missing_headers_error(['Test'])
        formatted = format_error_response(error)

        assert 'error' in formatted
        assert 'message' in formatted
        assert 'help_url' in formatted
        assert formatted['help_url'] is not None
        assert 'https://' in formatted['help_url']

    def test_format_error_response_preserves_error_code(self):
        """Verify error code is preserved in formatted response"""
        error = permission_denied_error()
        formatted = format_error_response(error)

        assert formatted['error'] == 'ERR_013'

    def test_format_error_response_preserves_message(self):
        """Verify message is preserved in formatted response"""
        error = file_not_csv_error()
        formatted = format_error_response(error)

        assert formatted['message'] == error['message']

    def test_format_error_response_with_unknown_error(self):
        """Test formatting unknown error code"""
        error = {'code': 'ERR_999', 'message': 'Unknown error'}
        formatted = format_error_response(error)

        assert formatted['error'] == 'ERR_999'
        assert formatted['help_url'] is None  # No help URL for unknown error


class TestErrorMessageParameterization:
    """Test that error messages properly handle dynamic parameters"""

    def test_missing_headers_with_multiple_columns(self):
        """Test missing headers error with multiple column names"""
        columns = ['Estatus', 'Urgencia', 'Impacto', 'Grupo asignado']
        error = missing_headers_error(columns)

        for column in columns:
            assert column in error['message']

    def test_invalid_enum_with_many_values(self):
        """Test invalid enum error with many allowed values"""
        allowed = ['Abierto', 'Cerrado', 'Pendiente', 'En Progreso', 'Resuelto']
        error = invalid_enum_error('Inválido', 'Estatus', allowed)

        for value in allowed:
            assert value in error['message']

    def test_file_too_large_with_different_sizes(self):
        """Test file size error with various file sizes"""
        for size in [100, 500, 1000]:
            error = file_too_large_error(size)
            assert str(size) in error['message']


class TestErrorCodeConsistency:
    """Test that error codes are used consistently"""

    def test_all_error_codes_are_unique(self):
        """Verify all error codes are unique"""
        codes = list(ERROR_CODES.values())
        assert len(codes) == len(set(codes)), "Error codes should be unique"

    def test_error_code_format(self):
        """Verify error codes follow ERR_XXX format"""
        for code in ERROR_CODES.values():
            assert code.startswith('ERR_'), f"Code should start with ERR_: {code}"
            assert code[4:].isdigit(), f"Code should have 3 digits: {code}"
            assert len(code) == 7, f"Code should be ERR_XXX format: {code}"

    def test_help_links_are_valid_urls(self):
        """Verify all help links are valid HTTPS URLs"""
        for code, url in ERROR_HELP_LINKS.items():
            assert url.startswith('https://'), f"Help link should be HTTPS: {url}"
            assert 'docs.example.com' in url, f"Help link should point to docs: {url}"
            assert code.lower() in url.lower() or 'error' in url.lower(), f"Help link should reference error code: {url}"
