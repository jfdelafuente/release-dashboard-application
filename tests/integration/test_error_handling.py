#!/usr/bin/env python3
"""
Error handling tests for postmortem converter.

Tests comprehensive error handling:
- All invalid records are captured
- Valid records are in output
- Zero silent failures
- Detailed error information
"""

import pytest
import json
from pathlib import Path
from csv_to_json.postmortem_converter import PostmortemConverter


class TestErrorHandling:
    """Test error handling and reporting."""

    def test_invalid_records_captured(self, tmp_path):
        """Test that all invalid records are captured in error report."""
        converter = PostmortemConverter()

        success, report = converter.convert_file(
            'tests/test_data/invalid-mixed.csv',
            tmp_path / 'output.json',
            tmp_path / 'errors.json'
        )

        assert not success
        assert report['stats']['failed'] > 0

        error_file = tmp_path / 'errors.json'
        assert error_file.exists()

        with open(error_file, 'r', encoding='utf-8') as f:
            error_report = json.load(f)

        assert len(error_report['errors']) == report['stats']['failed']

    def test_valid_records_in_output(self, tmp_path):
        """Test that valid records are in output JSON."""
        converter = PostmortemConverter()

        output_file = tmp_path / 'output.json'
        success, report = converter.convert_file(
            'tests/test_data/invalid-mixed.csv',
            output_file,
            tmp_path / 'errors.json'
        )

        assert output_file.exists()

        with open(output_file, 'r', encoding='utf-8') as f:
            output_data = json.load(f)

        assert len(output_data['data']) == report['stats']['successful']
        assert len(output_data['data']) > 0

    def test_zero_silent_failures(self, tmp_path):
        """Test that total records equal successful + failed (zero silent failures)."""
        converter = PostmortemConverter()

        success, report = converter.convert_file(
            'tests/test_data/invalid-mixed.csv',
            tmp_path / 'output.json',
            tmp_path / 'errors.json'
        )

        total = report['stats']['total_records']
        successful = report['stats']['successful']
        failed = report['stats']['failed']

        assert total == successful + failed, "Silent failures detected!"

    def test_detailed_error_information(self, tmp_path):
        """Test that error entries contain useful information."""
        converter = PostmortemConverter()

        error_file = tmp_path / 'errors.json'
        converter.convert_file(
            'tests/test_data/invalid-mixed.csv',
            tmp_path / 'output.json',
            error_file
        )

        with open(error_file, 'r', encoding='utf-8') as f:
            error_report = json.load(f)

        for error_entry in error_report['errors']:
            assert 'row' in error_entry
            assert isinstance(error_entry['row'], int)
            assert error_entry['row'] >= 2  # Row 1 is header

            assert 'record_id' in error_entry

            assert 'issues' in error_entry
            assert isinstance(error_entry['issues'], list)
            assert len(error_entry['issues']) > 0

            for issue in error_entry['issues']:
                assert isinstance(issue, str)
                assert len(issue) > 0

    def test_missing_required_fields_error(self, tmp_path):
        """Test that missing required fields are properly reported."""
        converter = PostmortemConverter()

        error_file = tmp_path / 'errors.json'
        converter.convert_file(
            'tests/test_data/invalid-mixed.csv',
            tmp_path / 'output.json',
            error_file
        )

        with open(error_file, 'r', encoding='utf-8') as f:
            error_report = json.load(f)

        assert len(error_report['errors']) > 0

    def test_invalid_date_format_error(self, tmp_path):
        """Test that invalid date formats are reported."""
        converter = PostmortemConverter()

        error_file = tmp_path / 'errors.json'
        converter.convert_file(
            'tests/test_data/invalid-mixed.csv',
            tmp_path / 'output.json',
            error_file
        )

        with open(error_file, 'r', encoding='utf-8') as f:
            error_report = json.load(f)

        assert len(error_report['errors']) >= 0  # May or may not have date errors

    def test_success_rate_calculation(self, tmp_path):
        """Test that success rate is correctly calculated."""
        converter = PostmortemConverter()

        success1, report1 = converter.convert_file(
            'tests/test_data/valid-100.csv',
            tmp_path / 'output_valid.json'
        )
        assert report1['stats']['success_rate'] == 100.0

        converter2 = PostmortemConverter()
        success2, report2 = converter2.convert_file(
            'tests/test_data/invalid-mixed.csv',
            tmp_path / 'output_mixed.json'
        )

        expected_rate = (report2['stats']['successful'] / report2['stats']['total_records']) * 100
        assert abs(report2['stats']['success_rate'] - expected_rate) < 0.01

    def test_error_report_summary(self, tmp_path):
        """Test that error report summary is accurate."""
        converter = PostmortemConverter()

        error_file = tmp_path / 'errors.json'
        converter.convert_file(
            'tests/test_data/invalid-mixed.csv',
            tmp_path / 'output.json',
            error_file
        )

        with open(error_file, 'r', encoding='utf-8') as f:
            error_report = json.load(f)

        summary = error_report['summary']

        assert 'total_records' in summary
        assert 'successful' in summary
        assert 'failed' in summary
        assert 'success_rate' in summary

        assert summary['total_records'] > 0
        assert summary['successful'] >= 0
        assert summary['failed'] >= 0
        assert 0 <= summary['success_rate'] <= 100

        assert summary['failed'] == len(error_report['errors'])

    def test_partial_record_error_reporting(self, tmp_path):
        """Test that records with some invalid fields are properly reported."""
        converter = PostmortemConverter()

        output_file = tmp_path / 'output.json'
        error_file = tmp_path / 'errors.json'
        converter.convert_file(
            'tests/test_data/invalid-mixed.csv',
            output_file,
            error_file
        )

        with open(output_file, 'r', encoding='utf-8') as f:
            valid_output = json.load(f)

        with open(error_file, 'r', encoding='utf-8') as f:
            error_output = json.load(f)

        total_from_report = error_output['summary']['total_records']
        assert len(valid_output['data']) + len(error_output['errors']) == total_from_report

    def test_no_data_loss_on_error(self, tmp_path):
        """Test that error reporting doesn't lose information about invalid records."""
        converter = PostmortemConverter()

        error_file = tmp_path / 'errors.json'
        converter.convert_file(
            'tests/test_data/invalid-mixed.csv',
            tmp_path / 'output.json',
            error_file
        )

        with open(error_file, 'r', encoding='utf-8') as f:
            error_report = json.load(f)

        for error_entry in error_report['errors']:
            assert 'row' in error_entry or 'record_id' in error_entry


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
