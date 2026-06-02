"""
Tests for upload endpoints
Tests file upload, validation, and confirmation
"""

import pytest
from pathlib import Path
from io import BytesIO
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class TestUploadEndpoint:
    """Tests for POST /api/upload endpoint"""

    @pytest.mark.unit
    def test_upload_valid_csv(self, sample_csv_content):
        """Test uploading a valid CSV file"""
        csv_data = sample_csv_content.encode('utf-8')

        response = client.post(
            '/api/upload',
            files={'file': ('test.csv', BytesIO(csv_data), 'text/csv')}
        )

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert 'metadata' in data
        assert data['metadata']['encoding_detected'] == 'utf-8'
        assert data['metadata']['record_count'] > 0

    @pytest.mark.unit
    def test_upload_non_csv_file(self):
        """Test uploading non-CSV file"""
        response = client.post(
            '/api/upload',
            files={'file': ('test.txt', BytesIO(b'test content'), 'text/plain')}
        )

        assert response.status_code == 400
        data = response.json()
        assert 'error' in data['detail']

    @pytest.mark.unit
    def test_upload_empty_file(self):
        """Test uploading empty file"""
        response = client.post(
            '/api/upload',
            files={'file': ('test.csv', BytesIO(b''), 'text/csv')}
        )

        assert response.status_code == 400
        data = response.json()
        assert data['detail']['error'] == 'ERR_008'

    @pytest.mark.unit
    def test_upload_missing_headers(self, invalid_csv_content):
        """Test uploading CSV with missing headers"""
        csv_data = invalid_csv_content.encode('utf-8')

        response = client.post(
            '/api/upload',
            files={'file': ('test.csv', BytesIO(csv_data), 'text/csv')}
        )

        assert response.status_code == 400
        data = response.json()
        assert data['detail']['error'] == 'ERR_001'
        assert 'missing' in data['detail']['message'].lower()

    @pytest.mark.unit
    def test_upload_empty_csv(self, empty_csv_content):
        """Test uploading CSV with headers only"""
        csv_data = empty_csv_content.encode('utf-8')

        response = client.post(
            '/api/upload',
            files={'file': ('test.csv', BytesIO(csv_data), 'text/csv')}
        )

        assert response.status_code == 400
        data = response.json()
        assert data['detail']['error'] == 'ERR_004'

    @pytest.mark.unit
    def test_upload_response_structure(self, sample_csv_content):
        """Test upload response contains all required metadata"""
        csv_data = sample_csv_content.encode('utf-8')

        response = client.post(
            '/api/upload',
            files={'file': ('test.csv', BytesIO(csv_data), 'text/csv')}
        )

        assert response.status_code == 200
        data = response.json()

        # Check response structure
        assert 'success' in data
        assert 'message' in data
        assert 'temp_file_path' in data
        assert 'metadata' in data

        # Check metadata
        metadata = data['metadata']
        assert 'filename' in metadata
        assert 'file_size' in metadata
        assert 'file_size_formatted' in metadata
        assert 'encoding_detected' in metadata
        assert 'delimiter_detected' in metadata
        assert 'headers' in metadata
        assert 'headers_count' in metadata
        assert 'record_count' in metadata
        assert 'warnings' in metadata

    @pytest.mark.unit
    def test_upload_with_warnings(self, sample_csv_content):
        """Test upload response includes warnings when applicable"""
        csv_data = sample_csv_content.encode('utf-8')

        response = client.post(
            '/api/upload',
            files={'file': ('test.csv', BytesIO(csv_data), 'text/csv')}
        )

        assert response.status_code == 200
        data = response.json()
        assert 'warnings' in data['metadata']
        assert isinstance(data['metadata']['warnings'], list)


class TestHealthEndpoint:
    """Tests for GET /health endpoint"""

    @pytest.mark.unit
    def test_health_check(self):
        """Test health check endpoint"""
        response = client.get('/health')

        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'ok'
        assert 'service' in data
        assert 'version' in data


class TestIntegrationUpload:
    """Integration tests for upload workflow"""

    @pytest.mark.integration
    def test_upload_validation_integration(self, sample_csv_content, mock_data_dirs):
        """Test complete upload validation flow"""
        csv_data = sample_csv_content.encode('utf-8')

        response = client.post(
            '/api/upload',
            files={'file': ('test.csv', BytesIO(csv_data), 'text/csv')}
        )

        assert response.status_code == 200
        data = response.json()

        # Verify all validation checks passed
        assert data['success'] is True
        assert data['metadata']['encoding_detected'] in [
            'utf-8', 'utf-8-sig', 'windows-1252', 'latin-1', 'iso-8859-15'
        ]
        assert data['metadata']['delimiter_detected'] in [',', ';', '\\t']
        assert len(data['metadata']['headers']) > 0
        assert data['metadata']['record_count'] > 0


class TestErrorHandling:
    """Tests for error handling in upload"""

    @pytest.mark.unit
    def test_upload_error_format(self):
        """Test error response format"""
        response = client.post(
            '/api/upload',
            files={'file': ('test.txt', BytesIO(b'test'), 'text/plain')}
        )

        assert response.status_code == 400
        data = response.json()

        # Check error format
        assert 'detail' in data
        assert 'error' in data['detail']
        assert 'message' in data['detail']

    @pytest.mark.unit
    def test_upload_error_codes(self):
        """Test specific error codes are returned"""
        # Test ERR_007 (not CSV)
        response = client.post(
            '/api/upload',
            files={'file': ('test.txt', BytesIO(b'test'), 'text/plain')}
        )
        assert response.json()['detail']['error'] == 'ERR_007'

        # Test ERR_008 (empty)
        response = client.post(
            '/api/upload',
            files={'file': ('test.csv', BytesIO(b''), 'text/csv')}
        )
        assert response.json()['detail']['error'] == 'ERR_008'
