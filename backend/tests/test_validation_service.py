"""
Tests for Validation Service
Tests the validation orchestrator and all validation workflows
"""

import pytest
from pathlib import Path
import time

from app.services.validation_service import ValidationService, create_validation_service


class TestValidationService:
    """Tests for ValidationService"""

    @pytest.fixture
    def service(self):
        """Create validation service"""
        return create_validation_service()

    @pytest.mark.unit
    def test_validate_valid_csv(self, service, sample_csv_content, temp_dir):
        """Test validation of valid CSV"""
        csv_file = Path(temp_dir) / "test_valid.csv"
        csv_file.write_text(sample_csv_content)

        result = service.validate_file(str(csv_file), "test_valid.csv")

        assert result.is_valid is True
        assert result.encoding is not None
        assert result.delimiter is not None
        assert len(result.headers) > 0
        assert result.row_counts['data_count'] > 0
        assert len(result.all_errors) == 0

    @pytest.mark.unit
    def test_validate_missing_headers(self, service, invalid_csv_content, temp_dir):
        """Test validation with missing headers"""
        csv_file = Path(temp_dir) / "test_missing.csv"
        csv_file.write_text(invalid_csv_content)

        result = service.validate_file(str(csv_file), "test_missing.csv")

        assert result.is_valid is False
        assert result.headers_valid is False
        assert len(result.missing_headers) > 0
        assert result.headers_error is not None
        assert len(result.all_errors) > 0

    @pytest.mark.unit
    def test_validate_empty_csv(self, service, empty_csv_content, temp_dir):
        """Test validation of empty CSV"""
        csv_file = Path(temp_dir) / "test_empty.csv"
        csv_file.write_text(empty_csv_content)

        result = service.validate_file(str(csv_file), "test_empty.csv")

        assert result.is_valid is False
        assert result.rows_valid is False
        assert result.row_counts['data_count'] == 0
        assert result.rows_error is not None

    @pytest.mark.unit
    def test_validation_result_to_dict(self, service, sample_csv_content, temp_dir):
        """Test ValidationResult to_dict conversion"""
        csv_file = Path(temp_dir) / "test_dict.csv"
        csv_file.write_text(sample_csv_content)

        result = service.validate_file(str(csv_file), "test_dict.csv")
        result_dict = result.to_dict()

        assert 'valid' in result_dict
        assert 'encoding' in result_dict
        assert 'delimiter' in result_dict
        assert 'headers' in result_dict
        assert 'row_counts' in result_dict
        assert 'errors' in result_dict
        assert 'warnings' in result_dict

    @pytest.mark.unit
    def test_encoding_detection_in_validation(self, service, sample_csv_content, temp_dir):
        """Test encoding detection during validation"""
        csv_file = Path(temp_dir) / "test_encoding.csv"
        csv_file.write_text(sample_csv_content, encoding='utf-8')

        result = service.validate_file(str(csv_file), "test_encoding.csv")

        assert result.encoding == 'utf-8'
        assert result.encoding_supported is True
        assert result.encoding_confidence > 0

    @pytest.mark.unit
    def test_delimiter_detection_in_validation(self, service, temp_dir):
        """Test delimiter detection during validation"""
        content = "ID de incidencia,Descripción,Estatus,Fecha de envío,Grupo asignado,Urgencia,Impacto\n" \
                  "INC001,Test,Abierto,01/01/2026 10:00 AM,Team,Alta,Masiva\n"
        csv_file = Path(temp_dir) / "test_delimiter.csv"
        csv_file.write_text(content)

        result = service.validate_file(str(csv_file), "test_delimiter.csv")

        assert result.delimiter == ','
        assert result.delimiter_supported is True

    @pytest.mark.unit
    def test_warnings_generation(self, service, sample_csv_content, temp_dir):
        """Test warning generation during validation"""
        csv_file = Path(temp_dir) / "test_warnings.csv"
        csv_file.write_text(sample_csv_content)

        result = service.validate_file(str(csv_file), "test_warnings.csv")

        assert 'warnings' in result.to_dict()
        assert isinstance(result.warnings, list)

    @pytest.mark.integration
    def test_full_validation_pipeline(self, service, sample_csv_content, temp_dir):
        """Test complete validation pipeline"""
        csv_file = Path(temp_dir) / "test_pipeline.csv"
        csv_file.write_text(sample_csv_content)

        result = service.validate_file(str(csv_file), "test_pipeline.csv")

        # All validation steps should complete
        assert result.encoding is not None
        assert result.delimiter is not None
        assert len(result.headers) > 0
        assert result.row_counts['data_count'] >= 0

        # Check result structure
        result_dict = result.to_dict()
        assert result_dict['valid'] == result.is_valid

    @pytest.mark.slow
    def test_large_csv_validation(self, service, temp_dir):
        """Test validation of large CSV file (performance)"""
        # Create large CSV
        csv_file = Path(temp_dir) / "test_large.csv"
        with open(csv_file, 'w') as f:
            f.write("ID de incidencia,Descripción,Estatus,Fecha de envío,Grupo asignado,Urgencia,Impacto\n")
            for i in range(1000):
                f.write(f"INC{i:06d},Test {i},Abierto,01/01/2026 10:00 AM,Team,Alta,Masiva\n")

        # Validate
        start_time = time.time()
        result = service.validate_file(str(csv_file), "test_large.csv")
        elapsed = time.time() - start_time

        # Should complete in reasonable time (< 2 seconds)
        assert elapsed < 2.0
        assert result.is_valid is True
        assert result.row_counts['data_count'] == 1000


class TestValidationErrors:
    """Tests for validation error handling"""

    @pytest.mark.unit
    def test_nonexistent_file(self):
        """Test validation of non-existent file"""
        service = create_validation_service()
        result = service.validate_file('/nonexistent/path.csv', 'test.csv')

        assert result.is_valid is False
        assert len(result.all_errors) > 0

    @pytest.mark.unit
    def test_multiple_validation_errors(self, service, temp_dir):
        """Test handling multiple validation errors"""
        # Create CSV with missing headers and no data
        content = "ID de incidencia,Descripción\n"
        csv_file = Path(temp_dir) / "test_multi_error.csv"
        csv_file.write_text(content)

        result = service.validate_file(str(csv_file), "test_multi_error.csv")

        assert result.is_valid is False
        assert len(result.all_errors) > 0


class TestValidationResult:
    """Tests for ValidationResult class"""

    @pytest.mark.unit
    def test_validation_result_init(self):
        """Test ValidationResult initialization"""
        from app.services.validation_service import ValidationResult

        result = ValidationResult("/path/to/file.csv", "file.csv")

        assert result.file_path == "/path/to/file.csv"
        assert result.original_filename == "file.csv"
        assert result.is_valid is False
        assert len(result.all_errors) == 0
        assert len(result.warnings) == 0

    @pytest.mark.unit
    def test_validation_result_to_dict_structure(self, service, sample_csv_content, temp_dir):
        """Test ValidationResult dict structure"""
        csv_file = Path(temp_dir) / "test_result.csv"
        csv_file.write_text(sample_csv_content)

        result = service.validate_file(str(csv_file), "test.csv")
        result_dict = result.to_dict()

        # Required fields
        assert 'valid' in result_dict
        assert 'encoding' in result_dict
        assert 'delimiter' in result_dict
        assert 'headers' in result_dict
        assert 'headers_count' in result_dict
        assert 'row_counts' in result_dict
        assert 'record_count' in result_dict
        assert 'errors' in result_dict
        assert 'warnings' in result_dict
        assert 'preview' in result_dict

        # Type checks
        assert isinstance(result_dict['valid'], bool)
        assert isinstance(result_dict['headers'], list)
        assert isinstance(result_dict['headers_count'], int)
        assert isinstance(result_dict['record_count'], int)
        assert isinstance(result_dict['errors'], list)
        assert isinstance(result_dict['warnings'], list)
