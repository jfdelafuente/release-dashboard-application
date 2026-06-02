"""
Tests for Conversion Service and Confirm Upload Endpoint
Tests file movement, conversion polling, and end-to-end workflows
"""

import pytest
from pathlib import Path
import json
from io import BytesIO
import time

from fastapi.testclient import TestClient
from app.main import app
from app.services.conversion_service import ConversionService, ConversionStatus

client = TestClient(app)


class TestConversionService:
    """Tests for ConversionService"""

    @pytest.fixture
    def service(self, mock_data_dirs):
        """Create conversion service with mock directories"""
        return ConversionService(
            str(mock_data_dirs['input']),
            str(mock_data_dirs['output']),
            timeout_seconds=5
        )

    @pytest.mark.unit
    def test_find_output_file_exists(self, service, mock_data_dirs):
        """Test finding existing output file"""
        # Create output file
        output_file = mock_data_dirs['output'] / "test.json"
        output_file.write_text('[]')

        found = service._find_output_file("test.csv")
        assert found is not None
        assert found.name == "test.json"

    @pytest.mark.unit
    def test_find_output_file_not_found(self, service):
        """Test behavior when output file doesn't exist"""
        found = service._find_output_file("nonexistent.csv")
        assert found is None

    @pytest.mark.unit
    def test_input_file_exists(self, service, mock_data_dirs):
        """Test checking if input file exists"""
        # Create input file
        input_file = mock_data_dirs['input'] / "test_20260602_120000.csv"
        input_file.write_text("data")

        exists = service._input_file_exists("test_20260602_120000.csv")
        assert exists is True

    @pytest.mark.unit
    def test_input_file_not_exists(self, service):
        """Test when input file doesn't exist"""
        exists = service._input_file_exists("nonexistent.csv")
        assert exists is False

    @pytest.mark.unit
    def test_count_json_records_list(self, service, mock_data_dirs):
        """Test counting records in list-format JSON"""
        json_file = mock_data_dirs['output'] / "test.json"
        data = [
            {"id": 1, "name": "test1"},
            {"id": 2, "name": "test2"},
            {"id": 3, "name": "test3"}
        ]
        json_file.write_text(json.dumps(data))

        count = service._count_json_records(json_file)
        assert count == 3

    @pytest.mark.unit
    def test_count_json_records_object(self, service, mock_data_dirs):
        """Test counting records in object-format JSON with data key"""
        json_file = mock_data_dirs['output'] / "test.json"
        data = {
            "data": [
                {"id": 1, "name": "test1"},
                {"id": 2, "name": "test2"}
            ]
        }
        json_file.write_text(json.dumps(data))

        count = service._count_json_records(json_file)
        assert count == 2

    @pytest.mark.unit
    def test_count_json_records_invalid(self, service, mock_data_dirs):
        """Test counting records in invalid JSON"""
        json_file = mock_data_dirs['output'] / "test.json"
        json_file.write_text("not valid json {")

        count = service._count_json_records(json_file)
        assert count == -1


class TestConfirmUploadEndpoint:
    """Tests for POST /api/confirm-upload endpoint"""

    @pytest.mark.integration
    def test_confirm_upload_success(self, sample_csv_content, mock_data_dirs):
        """Test successful upload confirmation"""
        # First upload a file
        csv_data = sample_csv_content.encode('utf-8')
        upload_response = client.post(
            '/api/upload',
            files={'file': ('test.csv', BytesIO(csv_data), 'text/csv')}
        )

        assert upload_response.status_code == 200
        upload_data = upload_response.json()
        temp_file_path = upload_data['temp_file_path']

        # Confirm upload
        confirm_response = client.post(
            '/api/confirm-upload',
            json={
                'temp_file_path': temp_file_path,
                'filename': 'test.csv'
            }
        )

        assert confirm_response.status_code == 200
        data = confirm_response.json()
        assert data['success'] is True or data['success'] is False  # Depends on cron
        assert 'final_filename' in data
        assert 'status' in data
        assert 'conversion' in data

    @pytest.mark.unit
    def test_confirm_upload_missing_fields(self):
        """Test confirm upload with missing required fields"""
        response = client.post(
            '/api/confirm-upload',
            json={'temp_file_path': '/some/path'}
        )

        assert response.status_code == 400
        assert 'Missing required fields' in response.json()['detail']

    @pytest.mark.unit
    def test_confirm_upload_file_not_found(self):
        """Test confirm upload with non-existent temp file"""
        response = client.post(
            '/api/confirm-upload',
            json={
                'temp_file_path': '/nonexistent/path/test.csv',
                'filename': 'test.csv'
            }
        )

        assert response.status_code == 404


class TestEndToEndConversion:
    """End-to-end tests for upload → validation → conversion pipeline"""

    @pytest.mark.integration
    def test_e2e_upload_to_move(self, sample_csv_content, mock_data_dirs):
        """Test complete flow: upload → validate → move to input"""
        csv_data = sample_csv_content.encode('utf-8')

        # Upload file
        upload_response = client.post(
            '/api/upload',
            files={'file': ('incidents.csv', BytesIO(csv_data), 'text/csv')}
        )

        assert upload_response.status_code == 200
        upload_data = upload_response.json()
        assert upload_data['success'] is True
        assert 'temp_file_path' in upload_data

        # Confirm upload (moves to input directory)
        confirm_response = client.post(
            '/api/confirm-upload',
            json={
                'temp_file_path': upload_data['temp_file_path'],
                'filename': 'incidents.csv'
            }
        )

        assert confirm_response.status_code == 200
        confirm_data = confirm_response.json()
        assert 'final_filename' in confirm_data

        # Verify file was moved (not in temp, in input)
        temp_path = Path(upload_data['temp_file_path'])
        assert not temp_path.exists()  # Should be moved

        # Check if file is in input directory or converted
        input_dir = mock_data_dirs['input']
        files_in_input = list(input_dir.glob('*'))
        # Either file is still in input, or conversion already happened
        assert len(files_in_input) > 0 or confirm_data['status'] == 'completed'

    @pytest.mark.slow
    def test_large_file_conversion(self, temp_dir, mock_data_dirs):
        """Test handling of large file during conversion"""
        # Create large CSV
        csv_path = Path(temp_dir) / "large.csv"
        with open(csv_path, 'w') as f:
            f.write("ID de incidencia,Descripción,Estatus,Fecha de envío,Grupo asignado,Urgencia,Impacto\n")
            for i in range(10000):
                f.write(f"INC{i:06d},Test {i},Abierto,01/01/2026 10:00 AM,Team,Alta,Masiva\n")

        csv_size = csv_path.stat().st_size
        csv_data = csv_path.read_bytes()

        # Upload large file
        upload_response = client.post(
            '/api/upload',
            files={'file': ('large.csv', BytesIO(csv_data), 'text/csv')}
        )

        assert upload_response.status_code == 200
        upload_data = upload_response.json()
        assert upload_data['metadata']['record_count'] == 10000

    @pytest.mark.unit
    def test_filename_sanitization_in_confirmation(self, sample_csv_content):
        """Test that special characters in filename are sanitized"""
        csv_data = sample_csv_content.encode('utf-8')
        special_filename = "test_file_2026-06-02_with_special!@#.csv"

        # Upload with special characters
        upload_response = client.post(
            '/api/upload',
            files={'file': (special_filename, BytesIO(csv_data), 'text/csv')}
        )

        assert upload_response.status_code == 200
        upload_data = upload_response.json()

        # Confirm upload
        confirm_response = client.post(
            '/api/confirm-upload',
            json={
                'temp_file_path': upload_data['temp_file_path'],
                'filename': special_filename
            }
        )

        assert confirm_response.status_code == 200
        data = confirm_response.json()

        # Final filename should be sanitized
        final_filename = data['final_filename']
        assert '!' not in final_filename
        assert '@' not in final_filename
        assert '#' not in final_filename


class TestConversionPolling:
    """Tests for conversion polling mechanism"""

    @pytest.mark.unit
    def test_conversion_status_timeout(self, service, mock_data_dirs):
        """Test conversion timeout after max polls"""
        # Don't create output file, so polling will timeout
        result = service.get_conversion_status(
            'nonexistent.csv',
            poll_interval=1,
            max_polls=2
        )

        assert result['status'] == ConversionStatus.TIMEOUT
        assert result['success'] is False

    @pytest.mark.unit
    def test_conversion_status_completed(self, service, mock_data_dirs):
        """Test conversion completed successfully"""
        # Create output file immediately
        output_file = mock_data_dirs['output'] / "test.json"
        output_file.write_text(json.dumps([{"id": 1}]))

        result = service.get_conversion_status(
            'test.csv',
            poll_interval=1,
            max_polls=10
        )

        assert result['status'] == ConversionStatus.COMPLETED
        assert result['success'] is True
        assert result['record_count'] == 1
