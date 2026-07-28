#!/usr/bin/env python3
"""
Integration test for postmortem normalization.

Tests complete normalization pipeline with edge cases including:
- Various field name cases
- Multiple date formats
- Estatus value variations
- Zero silent failures

NOTE: All tests use pytest tmp_path fixture for temporary output files.
No files are left in tests/test_data after test execution.
"""

import pytest
import json
from pathlib import Path
from csv_to_json.postmortem_converter import PostmortemConverter


class TestNormalizationIntegration:
    """Integration tests for postmortem normalization."""

    def test_normalize_edge_cases_csv(self, tmp_path):
        """Test normalization of edge cases CSV file."""
        converter = PostmortemConverter()

        output_file = tmp_path / "output.json"

        success, report = converter.convert_file(
            'tests/test_data/normalization-edge-cases.csv',
            str(output_file)
        )

        # Should have some success
        assert report['stats']['successful'] > 0

    def test_normalized_output_structure(self, tmp_path):
        """Test that normalized output has correct structure."""
        converter = PostmortemConverter()

        output_file = tmp_path / "output.json"

        converter.convert_file(
            'tests/test_data/normalization-edge-cases.csv',
            str(output_file)
        )

        with open(output_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Check structure
        assert '_metadata' in data
        assert 'data' in data
        assert isinstance(data['data'], list)

    def test_estatus_normalization_in_output(self, tmp_path):
        """Test that Estatus values are normalized to title case."""
        converter = PostmortemConverter()

        output_file = tmp_path / "output.json"

        converter.convert_file(
            'tests/test_data/normalization-edge-cases.csv',
            str(output_file)
        )

        with open(output_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Check that Estatus values are title-cased
        for record in data['data']:
            estatus = record.get('Estatus')
            if estatus:
                # Should be title-cased (not all lowercase or all uppercase)
                assert estatus[0].isupper() or estatus == ''

    def test_date_normalization_in_output(self, tmp_path):
        """Test that dates are normalized to DD/MM/YYYY format."""
        converter = PostmortemConverter()

        output_file = tmp_path / "output.json"

        converter.convert_file(
            'tests/test_data/normalization-edge-cases.csv',
            str(output_file)
        )

        with open(output_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Check date format
        for record in data['data']:
            fecha = record.get('Fecha de envío')
            if fecha and fecha != '':
                # parsePostmortemDateTime() preserva la hora: "DD/MM/YYYY HH:MM"
                date_part = fecha.split(' ')[0]
                parts = date_part.split('/')
                assert len(parts) == 3, f"Date not in DD/MM/YYYY format: {fecha}"
                assert len(parts[0]) == 2, f"Day not 2 digits: {fecha}"
                assert len(parts[1]) == 2, f"Month not 2 digits: {fecha}"
                assert len(parts[2]) == 4, f"Year not 4 digits: {fecha}"

    def test_zero_silent_failures(self, tmp_path):
        """Test that there are zero silent failures."""
        converter = PostmortemConverter()

        output_file = tmp_path / "output.json"
        error_file = tmp_path / "errors.json"

        success, report = converter.convert_file(
            'tests/test_data/normalization-edge-cases.csv',
            str(output_file),
            str(error_file)
        )

        # Total records should equal successful + failed
        total = report['stats']['total_records']
        successful = report['stats']['successful']
        failed = report['stats']['failed']

        assert total == successful + failed, "Silent failures detected!"

    def test_error_report_complete(self, tmp_path):
        """Test that error report is complete and detailed."""
        converter = PostmortemConverter()

        output_file = tmp_path / "output.json"
        error_file = tmp_path / "errors.json"

        converter.convert_file(
            'tests/test_data/normalization-edge-cases.csv',
            str(output_file),
            str(error_file)
        )

        with open(error_file, 'r', encoding='utf-8') as f:
            error_report = json.load(f)

        # Check error report structure
        assert 'summary' in error_report
        assert 'errors' in error_report
        assert error_report['summary']['total_records'] > 0

    def test_mixed_case_normalization(self, tmp_path):
        """Test normalization of mixed case values."""
        converter = PostmortemConverter()

        output_file = tmp_path / "output.json"

        converter.convert_file(
            'tests/test_data/normalization-edge-cases.csv',
            str(output_file)
        )

        with open(output_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Find record with mixed case
        for record in data['data']:
            if record.get('ID de incidencia') == 'INC003':
                # Estatus "En Progreso" should be title-cased
                assert record['Estatus'] == 'En Progreso'
                # Urgencia "Media" should be title-cased
                assert record['Urgencia'] == 'Media'

    def test_field_trimming(self, tmp_path):
        """Test that extra spaces are trimmed from fields."""
        converter = PostmortemConverter()

        output_file = tmp_path / "output.json"

        converter.convert_file(
            'tests/test_data/normalization-edge-cases.csv',
            str(output_file)
        )

        with open(output_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Find record with spaces (INC009)
        for record in data['data']:
            if record.get('ID de incidencia') == 'INC009':
                # Fields should be trimmed
                urgencia = record.get('Urgencia')
                assert urgencia == 'Alta', f"Spaces not trimmed from Urgencia: '{urgencia}'"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
