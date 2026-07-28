#!/usr/bin/env python3
"""
End-to-end integration test for postmortem CSV to JSON conversion.

Tests complete conversion pipeline:
- Load valid-100.csv
- Process 100 records
- Validate JSON structure
- Verify field mapping
- Check metadata and KPIs
"""

import pytest
import json
from pathlib import Path
from csv_to_json.postmortem_converter import PostmortemConverter


class TestPostmortemE2EConversion:
    """End-to-end postmortem conversion tests."""

    def test_e2e_convert_valid_100_records(self, tmp_path):
        """Test conversion of valid-100.csv with 100 valid records."""
        converter = PostmortemConverter()

        success, report = converter.convert_file(
            'tests/test_data/valid-100.csv',
            tmp_path / 'output.json'
        )

        assert success is True
        assert report['stats']['total_records'] == 100
        assert report['stats']['successful'] == 100
        assert report['stats']['failed'] == 0
        assert report['stats']['success_rate'] == 100.0

    def test_e2e_json_structure(self, tmp_path):
        """Test that output JSON has correct structure."""
        converter = PostmortemConverter()

        converter.convert_file(
            'tests/test_data/valid-100.csv',
            tmp_path / 'output.json'
        )

        with open(tmp_path / 'output.json', 'r', encoding='utf-8') as f:
            data = json.load(f)

        assert '_metadata' in data
        assert 'data' in data

    def test_e2e_metadata_structure(self, tmp_path):
        """Test that metadata has all required fields."""
        converter = PostmortemConverter()

        converter.convert_file(
            'tests/test_data/valid-100.csv',
            tmp_path / 'output.json'
        )

        with open(tmp_path / 'output.json', 'r', encoding='utf-8') as f:
            data = json.load(f)

        metadata = data['_metadata']

        assert 'type' in metadata
        assert metadata['type'] == 'postmortem'
        assert 'version' in metadata
        assert metadata['version'] == '1.0'
        assert 'created' in metadata
        assert 'source_filename' in metadata
        assert 'record_count' in metadata
        assert 'kpis' in metadata

    def test_e2e_metadata_timestamp_iso8601(self, tmp_path):
        """Test that metadata timestamp is ISO 8601 format."""
        converter = PostmortemConverter()

        converter.convert_file(
            'tests/test_data/valid-100.csv',
            tmp_path / 'output.json'
        )

        with open(tmp_path / 'output.json', 'r', encoding='utf-8') as f:
            data = json.load(f)

        timestamp = data['_metadata']['created']

        assert timestamp.endswith('Z')
        from datetime import datetime
        try:
            datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        except ValueError:
            pytest.fail(f"Invalid ISO 8601 timestamp: {timestamp}")

    def test_e2e_kpis_in_metadata(self, tmp_path):
        """Test that KPIs are calculated and in metadata."""
        converter = PostmortemConverter()

        converter.convert_file(
            'tests/test_data/valid-100.csv',
            tmp_path / 'output.json'
        )

        with open(tmp_path / 'output.json', 'r', encoding='utf-8') as f:
            data = json.load(f)

        kpis = data['_metadata']['kpis']

        assert 'total' in kpis
        assert kpis['total'] == 100
        assert 'by_estatus' in kpis
        assert 'by_urgencia' in kpis
        assert 'by_impacto' in kpis

    def test_e2e_all_records_in_output(self, tmp_path):
        """Test that all 100 records are in output JSON."""
        converter = PostmortemConverter()

        converter.convert_file(
            'tests/test_data/valid-100.csv',
            tmp_path / 'output.json'
        )

        with open(tmp_path / 'output.json', 'r', encoding='utf-8') as f:
            data = json.load(f)

        assert len(data['data']) == 100

    def test_e2e_field_mapping_correct(self, tmp_path):
        """Test that CSV fields are correctly mapped to output."""
        converter = PostmortemConverter()

        converter.convert_file(
            'tests/test_data/valid-100.csv',
            tmp_path / 'output.json'
        )

        with open(tmp_path / 'output.json', 'r', encoding='utf-8') as f:
            data = json.load(f)

        record = data['data'][0]

        expected_fields = [
            'ID de incidencia', 'Descripción', 'Estatus', 'Fecha de envío',
            'Grupo asignado', 'Urgencia', 'Impacto'
        ]

        for field in expected_fields:
            assert field in record or field in str(record.keys())

    def test_e2e_date_normalization(self, tmp_path):
        """Test that dates are normalized in output."""
        converter = PostmortemConverter()

        converter.convert_file(
            'tests/test_data/valid-100.csv',
            tmp_path / 'output.json'
        )

        with open(tmp_path / 'output.json', 'r', encoding='utf-8') as f:
            data = json.load(f)

        for record in data['data'][:5]:
            fecha = record.get('Fecha de envío')
            if fecha:
                # parsePostmortemDateTime() preserva la hora: "DD/MM/YYYY HH:MM"
                date_part = fecha.split(' ')[0]
                parts = date_part.split('/')
                assert len(parts) == 3
                assert len(parts[0]) == 2  # DD
                assert len(parts[1]) == 2  # MM
                assert len(parts[2]) == 4  # YYYY

    def test_e2e_despliegue_derivation(self, tmp_path):
        """Test that Despliegue is derived correctly (oldest date = PAP)."""
        converter = PostmortemConverter()

        converter.convert_file(
            'tests/test_data/valid-100.csv',
            tmp_path / 'output.json'
        )

        with open(tmp_path / 'output.json', 'r', encoding='utf-8') as f:
            data = json.load(f)

        records = data['data']

        despliegue_values = [r.get('Despliegue') for r in records]
        pap_count = sum(1 for d in despliegue_values if d == 'PAP')
        mesa_count = sum(1 for d in despliegue_values if d == 'MESA')

        assert pap_count == 1, f"Expected 1 PAP, got {pap_count}"
        assert mesa_count == 99, f"Expected 99 MESA, got {mesa_count}"

    def test_e2e_encoding_detection(self, tmp_path):
        """Test that encoding is correctly detected."""
        converter = PostmortemConverter()

        success, report = converter.convert_file(
            'tests/test_data/valid-100.csv',
            tmp_path / 'output.json'
        )

        assert 'encoding_detected' in report
        assert report['encoding_detected'] in ['utf-8', 'utf-8-sig', 'windows-1252', 'latin-1']

    def test_e2e_json_valid(self, tmp_path):
        """Test that output JSON is valid and complete."""
        converter = PostmortemConverter()

        converter.convert_file(
            'tests/test_data/valid-100.csv',
            tmp_path / 'output.json'
        )

        with open(tmp_path / 'output.json', 'r', encoding='utf-8') as f:
            data = json.load(f)

        assert isinstance(data, dict)
        assert '_metadata' in data
        assert 'data' in data
        assert isinstance(data['data'], list)
        assert len(data['data']) > 0

    def test_e2e_invalid_mixed_with_errors(self, tmp_path):
        """Test E2E conversion with invalid-mixed.csv."""
        converter = PostmortemConverter()

        success, report = converter.convert_file(
            'tests/test_data/invalid-mixed.csv',
            tmp_path / 'output.json',
            tmp_path / 'errors.json'
        )

        assert success is False
        assert report['stats']['failed'] > 0
        assert report['stats']['successful'] < report['stats']['total_records']

    def test_e2e_error_report_structure(self, tmp_path):
        """Test that error report has correct structure."""
        converter = PostmortemConverter()

        converter.convert_file(
            'tests/test_data/invalid-mixed.csv',
            tmp_path / 'output.json',
            tmp_path / 'errors.json'
        )

        with open(tmp_path / 'errors.json', 'r', encoding='utf-8') as f:
            error_report = json.load(f)

        assert 'summary' in error_report
        assert 'errors' in error_report
        assert 'total_records' in error_report['summary']
        assert 'successful' in error_report['summary']
        assert 'failed' in error_report['summary']
        assert 'success_rate' in error_report['summary']

    def test_e2e_record_count_matches(self, tmp_path):
        """Test that record count in metadata matches actual records."""
        converter = PostmortemConverter()

        converter.convert_file(
            'tests/test_data/valid-100.csv',
            tmp_path / 'output.json'
        )

        with open(tmp_path / 'output.json', 'r', encoding='utf-8') as f:
            data = json.load(f)

        assert data['_metadata']['record_count'] == len(data['data'])


class TestPostmortemReleaseNamePropagation:
    """Test that release_name flows through convert_file() into _metadata.

    Uses a minimal inline CSV (via tmp_path) instead of tests/test_data/*.csv,
    since those fixture files are missing from the repo (pre-existing issue,
    unrelated to this feature).
    """

    def _write_minimal_csv(self, path):
        path.write_text(
            "ID de incidencia,Descripción,Estatus,Fecha de envío,Grupo asignado,Urgencia,Impacto\n"
            "INC001,Incidente de prueba,Cerrado,26/04/2026,SOP_TEST,Alta,Medio\n",
            encoding='utf-8'
        )

    def test_e2e_release_name_in_metadata(self, tmp_path):
        """Test that a release_name passed to convert_file() ends up in _metadata."""
        input_csv = tmp_path / "input.csv"
        self._write_minimal_csv(input_csv)
        output_file = tmp_path / "output.json"

        converter = PostmortemConverter()
        converter.convert_file(str(input_csv), str(output_file), release_name="2026R4-PRUEBA")

        with open(output_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        assert data['_metadata']['release_name'] == "2026R4-PRUEBA"

    def test_e2e_release_name_absent_by_default(self, tmp_path):
        """Test that _metadata.release_name is None when not provided (backward compatibility)."""
        input_csv = tmp_path / "input.csv"
        self._write_minimal_csv(input_csv)
        output_file = tmp_path / "output.json"

        converter = PostmortemConverter()
        converter.convert_file(str(input_csv), str(output_file))

        with open(output_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        assert data['_metadata']['release_name'] is None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
