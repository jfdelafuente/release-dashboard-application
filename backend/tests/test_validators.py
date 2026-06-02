"""
Test suite for CSV validators
Tests all validators: encoding, delimiter, headers, counter
"""

import pytest
from pathlib import Path
import tempfile
import csv

from app.validators.encoding import detect_encoding, is_encoding_supported
from app.validators.delimiter import detect_delimiter, is_delimiter_supported
from app.validators.headers import validate_headers, are_headers_valid, get_required_headers
from app.validators.counter import count_csv_rows, count_csv_rows_with_header, validate_row_count


class TestEncodingDetector:
    """Tests for encoding detection"""

    @pytest.mark.unit
    def test_detect_utf8_encoding(self, sample_csv_content, temp_dir):
        """Test UTF-8 encoding detection"""
        csv_file = Path(temp_dir) / "test_utf8.csv"
        csv_file.write_text(sample_csv_content, encoding='utf-8')

        encoding, confidence = detect_encoding(str(csv_file))
        assert encoding == 'utf-8'
        assert confidence > 0

    @pytest.mark.unit
    def test_supported_encoding(self):
        """Test checking supported encoding"""
        assert is_encoding_supported('utf-8')
        assert is_encoding_supported('windows-1252')
        assert is_encoding_supported('latin-1')
        assert not is_encoding_supported('unsupported-encoding')

    @pytest.mark.unit
    def test_invalid_file(self, temp_dir):
        """Test encoding detection with non-existent file"""
        with pytest.raises(FileNotFoundError):
            detect_encoding(str(Path(temp_dir) / "nonexistent.csv"))


class TestDelimiterDetector:
    """Tests for delimiter detection"""

    @pytest.mark.unit
    def test_detect_comma_delimiter(self, sample_csv_content, temp_dir):
        """Test comma delimiter detection"""
        csv_file = Path(temp_dir) / "test_comma.csv"
        csv_file.write_text(sample_csv_content)

        delimiter = detect_delimiter(str(csv_file))
        assert delimiter == ','

    @pytest.mark.unit
    def test_detect_semicolon_delimiter(self, temp_dir):
        """Test semicolon delimiter detection"""
        content = "ID;Name;Status\n123;Test;Active\n"
        csv_file = Path(temp_dir) / "test_semicolon.csv"
        csv_file.write_text(content)

        delimiter = detect_delimiter(str(csv_file))
        assert delimiter == ';'

    @pytest.mark.unit
    def test_supported_delimiter(self):
        """Test checking supported delimiter"""
        assert is_delimiter_supported(',')
        assert is_delimiter_supported(';')
        assert is_delimiter_supported('\t')
        assert not is_delimiter_supported('|')

    @pytest.mark.unit
    def test_delimiter_default_to_comma(self, temp_dir):
        """Test defaulting to comma for ambiguous files"""
        csv_file = Path(temp_dir) / "test_empty.csv"
        csv_file.write_text("")

        delimiter = detect_delimiter(str(csv_file))
        # Should default to comma for empty file
        assert delimiter in [',', '']


class TestHeadersValidator:
    """Tests for headers validation"""

    @pytest.mark.unit
    def test_valid_headers(self, sample_csv_content, temp_dir):
        """Test validation with all required headers"""
        csv_file = Path(temp_dir) / "test_headers.csv"
        csv_file.write_text(sample_csv_content)

        result = validate_headers(str(csv_file))
        assert result['valid'] is True
        assert len(result['missing_headers']) == 0

    @pytest.mark.unit
    def test_missing_headers(self, invalid_csv_content, temp_dir):
        """Test validation with missing required headers"""
        csv_file = Path(temp_dir) / "test_missing.csv"
        csv_file.write_text(invalid_csv_content)

        result = validate_headers(str(csv_file))
        assert result['valid'] is False
        assert len(result['missing_headers']) > 0

    @pytest.mark.unit
    def test_are_headers_valid(self):
        """Test header validation utility"""
        headers = ['ID de incidencia', 'Descripción', 'Estatus', 'Fecha de envío',
                   'Grupo asignado', 'Urgencia', 'Impacto']
        assert are_headers_valid(headers)

        partial_headers = ['ID de incidencia', 'Descripción']
        assert not are_headers_valid(partial_headers)

    @pytest.mark.unit
    def test_get_required_headers(self):
        """Test getting required headers list"""
        headers = get_required_headers()
        assert 'ID de incidencia' in headers
        assert 'Estatus' in headers
        assert len(headers) > 0


class TestRowCounter:
    """Tests for CSV row counting"""

    @pytest.mark.unit
    def test_count_rows(self, sample_csv_content, temp_dir):
        """Test counting data rows"""
        csv_file = Path(temp_dir) / "test_count.csv"
        csv_file.write_text(sample_csv_content)

        count = count_csv_rows(str(csv_file))
        assert count > 0

    @pytest.mark.unit
    def test_count_with_header(self, sample_csv_content, temp_dir):
        """Test counting rows with header details"""
        csv_file = Path(temp_dir) / "test_count_header.csv"
        csv_file.write_text(sample_csv_content)

        counts = count_csv_rows_with_header(str(csv_file))
        assert counts['header_count'] == 1
        assert counts['data_count'] > 0

    @pytest.mark.unit
    def test_count_empty_csv(self, empty_csv_content, temp_dir):
        """Test counting empty CSV"""
        csv_file = Path(temp_dir) / "test_empty_count.csv"
        csv_file.write_text(empty_csv_content)

        count = count_csv_rows(str(csv_file))
        assert count == 0

    @pytest.mark.unit
    def test_validate_row_count(self, sample_csv_content, temp_dir):
        """Test row count validation"""
        csv_file = Path(temp_dir) / "test_validate_count.csv"
        csv_file.write_text(sample_csv_content)

        result = validate_row_count(str(csv_file))
        assert result['valid'] is True
        assert result['row_counts']['data_count'] > 0


class TestIntegration:
    """Integration tests for all validators"""

    @pytest.mark.integration
    def test_full_validation_pipeline(self, sample_csv_content, temp_dir):
        """Test complete validation pipeline"""
        csv_file = Path(temp_dir) / "test_full.csv"
        csv_file.write_text(sample_csv_content)

        # Test encoding
        encoding, _ = detect_encoding(str(csv_file))
        assert is_encoding_supported(encoding)

        # Test delimiter
        delimiter = detect_delimiter(str(csv_file), encoding)
        assert is_delimiter_supported(delimiter)

        # Test headers
        headers_result = validate_headers(str(csv_file), encoding, delimiter)
        assert headers_result['valid']

        # Test row count
        count = count_csv_rows(str(csv_file), encoding, delimiter)
        assert count > 0

    @pytest.mark.integration
    def test_invalid_csv_validation(self, invalid_csv_content, temp_dir):
        """Test validation of invalid CSV"""
        csv_file = Path(temp_dir) / "test_invalid.csv"
        csv_file.write_text(invalid_csv_content)

        # Should fail on headers
        result = validate_headers(str(csv_file))
        assert result['valid'] is False


# Additional edge case tests
class TestEdgeCases:
    """Test edge cases and error handling"""

    @pytest.mark.unit
    def test_file_not_found(self, temp_dir):
        """Test handling of missing file"""
        with pytest.raises(FileNotFoundError):
            count_csv_rows(str(Path(temp_dir) / "nonexistent.csv"))

    @pytest.mark.unit
    def test_bom_handling(self, temp_dir):
        """Test handling of BOM in file"""
        csv_file = Path(temp_dir) / "test_bom.csv"
        content = "ID de incidencia,Descripción,Estatus,Fecha de envío,Grupo asignado,Urgencia,Impacto\n"
        csv_file.write_bytes(b'\xef\xbb\xbf' + content.encode('utf-8'))

        encoding, _ = detect_encoding(str(csv_file))
        assert encoding == 'utf-8-sig'
