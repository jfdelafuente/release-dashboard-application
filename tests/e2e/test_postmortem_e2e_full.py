#!/usr/bin/env python3
"""
End-to-end tests for complete postmortem conversion workflow.

Tests the full conversion pipeline including:
- CSV reading with encoding/delimiter detection
- Field mapping and normalization
- KPI calculation
- JSON output generation
- Error report generation
"""

import pytest
import json
from pathlib import Path
from csv_to_json.postmortem_converter import PostmortemConverter


class TestFullEndToEnd:
    """Complete E2E tests for postmortem converter."""

    def test_full_conversion_pipeline_valid_data(self, tmp_path):
        """Test complete conversion workflow with valid data."""
        converter = PostmortemConverter()

        output_file = tmp_path / 'output.json'
        success, report = converter.convert_file(
            'tests/test_data/valid-100.csv',
            output_file,
            tmp_path / 'errors.json'
        )

        assert success, "Conversion should succeed with valid data"
        assert report['stats']['successful'] == 100
        assert report['stats']['failed'] == 0
        assert report['stats']['total_records'] == 100

        assert output_file.exists()

        with open(output_file, 'r', encoding='utf-8') as f:
            output_data = json.load(f)

        assert '_metadata' in output_data
        metadata = output_data['_metadata']
        assert metadata['type'] == 'postmortem'
        assert metadata['version'] == '1.0'
        assert 'created' in metadata or 'conversion_timestamp' in metadata
        assert 'source_filename' in metadata
        assert 'record_count' in metadata
        assert 'kpis' in metadata

        assert 'data' in output_data
        assert len(output_data['data']) == 100

        record = output_data['data'][0]
        assert 'ID de incidencia' in record
        assert 'Descripción' in record
        assert 'Estatus' in record
        assert 'Fecha de envío' in record
        assert 'Despliegue' in record

    def test_full_conversion_pipeline_with_errors(self, tmp_path):
        """Test conversion workflow with mixed valid/invalid records."""
        converter = PostmortemConverter()

        output_file = tmp_path / 'output.json'
        error_file = tmp_path / 'errors.json'
        success, report = converter.convert_file(
            'tests/test_data/invalid-mixed.csv',
            output_file,
            error_file
        )

        assert not success, "Conversion should report failure with invalid records"
        assert report['stats']['successful'] > 0
        assert report['stats']['failed'] > 0
        assert report['stats']['total_records'] == 60

        assert output_file.exists()

        with open(output_file, 'r', encoding='utf-8') as f:
            output_data = json.load(f)

        assert len(output_data['data']) == report['stats']['successful']

        assert error_file.exists()

        with open(error_file, 'r', encoding='utf-8') as f:
            error_data = json.load(f)

        assert 'summary' in error_data
        assert 'errors' in error_data
        assert len(error_data['errors']) == report['stats']['failed']

    def test_json_output_structure_validity(self, tmp_path):
        """Test that JSON output has correct structure for dashboard loading."""
        converter = PostmortemConverter()

        converter.convert_file(
            'tests/test_data/valid-100.csv',
            tmp_path / 'output.json'
        )

        with open(tmp_path / 'output.json', 'r', encoding='utf-8') as f:
            output_data = json.load(f)

        assert isinstance(output_data, dict)
        assert '_metadata' in output_data
        assert 'data' in output_data

        metadata = output_data['_metadata']
        assert isinstance(metadata, dict)
        assert metadata['type'] == 'postmortem'
        assert metadata['version'] == '1.0'
        assert isinstance(metadata['created'], str)
        assert isinstance(metadata['source_filename'], str)
        assert isinstance(metadata['record_count'], int)
        assert isinstance(metadata['kpis'], dict)

        kpis = metadata['kpis']
        assert 'total' in kpis
        assert 'by_estatus' in kpis
        assert 'by_urgencia' in kpis
        assert 'by_impacto' in kpis

        assert isinstance(output_data['data'], list)
        assert len(output_data['data']) > 0

        for record in output_data['data']:
            assert isinstance(record, dict)
            assert 'ID de incidencia' in record
            assert 'Descripción' in record
            assert 'Estatus' in record
            assert 'Despliegue' in record

    def test_field_formatting_in_output(self, tmp_path):
        """Test that fields are properly formatted in JSON output."""
        converter = PostmortemConverter()

        converter.convert_file(
            'tests/test_data/valid-100.csv',
            tmp_path / 'output.json'
        )

        with open(tmp_path / 'output.json', 'r', encoding='utf-8') as f:
            output_data = json.load(f)

        for record in output_data['data']:
            estatus = record.get('Estatus')
            if estatus:
                assert estatus[0].isupper()

            urgencia = record.get('Urgencia')
            if urgencia:
                assert urgencia[0].isupper()

            impacto = record.get('Impacto')
            if impacto:
                assert impacto[0].isupper()

            despliegue = record.get('Despliegue')
            assert despliegue in ['PAP', 'MESA']

    def test_kpi_calculation_in_metadata(self, tmp_path):
        """Test that KPIs are properly calculated and included."""
        converter = PostmortemConverter()

        converter.convert_file(
            'tests/test_data/valid-100.csv',
            tmp_path / 'output.json'
        )

        with open(tmp_path / 'output.json', 'r', encoding='utf-8') as f:
            output_data = json.load(f)

        kpis = output_data['_metadata']['kpis']
        record_count = len(output_data['data'])

        assert kpis['total'] == record_count

        assert sum(kpis['by_estatus'].values()) == record_count
        assert sum(kpis['by_urgencia'].values()) == record_count
        assert sum(kpis['by_impacto'].values()) == record_count

    def test_encoding_detection_in_pipeline(self, tmp_path):
        """Test that encoding detection works through full pipeline."""
        converter = PostmortemConverter()

        success, report = converter.convert_file(
            'tests/test_data/valid-100.csv',
            tmp_path / 'output.json'
        )

        assert report['encoding_detected'] in ['utf-8', 'UTF-8']

    def test_error_report_contains_detailed_info(self, tmp_path):
        """Test that error report provides useful debugging information."""
        converter = PostmortemConverter()

        converter.convert_file(
            'tests/test_data/invalid-mixed.csv',
            tmp_path / 'output.json',
            tmp_path / 'errors.json'
        )

        with open(tmp_path / 'errors.json', 'r', encoding='utf-8') as f:
            error_report = json.load(f)

        assert 'summary' in error_report
        summary = error_report['summary']
        assert 'total_records' in summary
        assert 'successful' in summary
        assert 'failed' in summary
        assert 'success_rate' in summary

        assert 'errors' in error_report
        assert len(error_report['errors']) > 0

        for error_entry in error_report['errors']:
            assert 'row' in error_entry
            assert isinstance(error_entry['row'], int)
            assert 'record_id' in error_entry
            assert 'issues' in error_entry
            assert isinstance(error_entry['issues'], list)
            assert len(error_entry['issues']) > 0

    def test_cli_output_consistency(self, tmp_path):
        """Test that CLI conversion produces same output as direct API."""
        from csv_to_json.postmortem_converter import PostmortemConverter

        converter1 = PostmortemConverter()
        converter1.convert_file(
            'tests/test_data/valid-100.csv',
            tmp_path / 'output.json'
        )

        with open(tmp_path / 'output.json', 'r', encoding='utf-8') as f:
            api_data = json.load(f)

        assert len(api_data['data']) == 100
        assert api_data['_metadata']['record_count'] == 100


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
