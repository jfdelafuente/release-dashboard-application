#!/usr/bin/env python3
"""
Integration test for postmortem normalization.

Tests complete normalization pipeline with edge cases including:
- Various field name cases
- Multiple date formats
- Estatus value variations
- Zero silent failures
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

        success, report = converter.convert_file(
            'tests/test_data/normalization-edge-cases.csv',
            tmp_path / 'output.json'
        )

        assert report['stats']['successful'] > 0

    def test_normalized_output_structure(self, tmp_path):
        """Test that normalized output has correct structure."""
        converter = PostmortemConverter()

        converter.convert_file(
            'tests/test_data/normalization-edge-cases.csv',
            tmp_path / 'output.json'
        )

        with open(tmp_path / 'output.json', 'r', encoding='utf-8') as f:
            data = json.load(f)

        assert '_metadata' in data
        assert 'data' in data
        assert isinstance(data['data'], list)

    def test_estatus_normalization_in_output(self, tmp_path):
        """Test that Estatus values are normalized to title case."""
        converter = PostmortemConverter()

        converter.convert_file(
            'tests/test_data/normalization-edge-cases.csv',
            tmp_path / 'output.json'
        )

        with open(tmp_path / 'output.json', 'r', encoding='utf-8') as f:
            data = json.load(f)

        for record in data['data']:
            estatus = record.get('Estatus')
            if estatus:
                assert estatus[0].isupper() or estatus == ''

    def test_date_normalization_in_output(self, tmp_path):
        """Test that dates are normalized to DD/MM/YYYY format."""
        converter = PostmortemConverter()

        converter.convert_file(
            'tests/test_data/normalization-edge-cases.csv',
            tmp_path / 'output.json'
        )

        with open(tmp_path / 'output.json', 'r', encoding='utf-8') as f:
            data = json.load(f)

        for record in data['data']:
            fecha = record.get('Fecha de envío')
            if fecha and fecha != '':
                parts = fecha.split('/')
                assert len(parts) == 3, f"Date not in DD/MM/YYYY format: {fecha}"
                assert len(parts[0]) == 2, f"Day not 2 digits: {fecha}"
                assert len(parts[1]) == 2, f"Month not 2 digits: {fecha}"
                assert len(parts[2]) == 4, f"Year not 4 digits: {fecha}"

    def test_zero_silent_failures(self, tmp_path):
        """Test that there are zero silent failures."""
        converter = PostmortemConverter()

        success, report = converter.convert_file(
            'tests/test_data/normalization-edge-cases.csv',
            tmp_path / 'output.json',
            tmp_path / 'errors.json'
        )

        total = report['stats']['total_records']
        successful = report['stats']['successful']
        failed = report['stats']['failed']

        assert total == successful + failed, "Silent failures detected!"

    def test_error_report_complete(self, tmp_path):
        """Test that error report is complete and detailed."""
        converter = PostmortemConverter()

        converter.convert_file(
            'tests/test_data/normalization-edge-cases.csv',
            tmp_path / 'output.json',
            tmp_path / 'errors.json'
        )

        with open(tmp_path / 'errors.json', 'r', encoding='utf-8') as f:
            error_report = json.load(f)

        assert 'summary' in error_report
        assert 'errors' in error_report
        assert error_report['summary']['total_records'] > 0

    def test_mixed_case_normalization(self, tmp_path):
        """Test normalization of mixed case values."""
        converter = PostmortemConverter()

        converter.convert_file(
            'tests/test_data/normalization-edge-cases.csv',
            tmp_path / 'output.json'
        )

        with open(tmp_path / 'output.json', 'r', encoding='utf-8') as f:
            data = json.load(f)

        for record in data['data']:
            if record.get('ID de incidencia') == 'INC003':
                assert record['Estatus'] == 'En Progreso'
                assert record['Urgencia'] == 'Media'

    def test_field_trimming(self, tmp_path):
        """Test that extra spaces are trimmed from fields."""
        converter = PostmortemConverter()

        converter.convert_file(
            'tests/test_data/normalization-edge-cases.csv',
            tmp_path / 'output.json'
        )

        with open(tmp_path / 'output.json', 'r', encoding='utf-8') as f:
            data = json.load(f)

        for record in data['data']:
            if record.get('ID de incidencia') == 'INC009':
                urgencia = record.get('Urgencia')
                assert urgencia == 'Alta', f"Spaces not trimmed from Urgencia: '{urgencia}'"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
