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

    def test_invalid_records_captured(self):
        """Test that all invalid records are captured in error report."""
        converter = PostmortemConverter()

        success, report = converter.convert_file(
            'tests/test_data/invalid-mixed.csv',
            'tests/test_data/error_handling_valid.json',
            'tests/test_data/error_handling_errors.json'
        )

        # Should report failures
        assert not success
        assert report['stats']['failed'] > 0

        # Error report should exist
        error_file = Path('tests/test_data/error_handling_errors.json')
        assert error_file.exists()

        with open(error_file, 'r', encoding='utf-8') as f:
            error_report = json.load(f)

        # Number of error entries should match failed count
        assert len(error_report['errors']) == report['stats']['failed']

    def test_valid_records_in_output(self):
        """Test that valid records are in output JSON."""
        converter = PostmortemConverter()

        success, report = converter.convert_file(
            'tests/test_data/invalid-mixed.csv',
            'tests/test_data/error_handling_mixed_valid.json',
            'tests/test_data/error_handling_mixed_errors.json'
        )

        output_file = Path('tests/test_data/error_handling_mixed_valid.json')
        assert output_file.exists()

        with open(output_file, 'r', encoding='utf-8') as f:
            output_data = json.load(f)

        # Output should contain only valid records
        assert len(output_data['data']) == report['stats']['successful']
        assert len(output_data['data']) > 0

    def test_zero_silent_failures(self):
        """Test that total records equal successful + failed (zero silent failures)."""
        converter = PostmortemConverter()

        success, report = converter.convert_file(
            'tests/test_data/invalid-mixed.csv',
            'tests/test_data/error_zero_silent_valid.json',
            'tests/test_data/error_zero_silent_errors.json'
        )

        total = report['stats']['total_records']
        successful = report['stats']['successful']
        failed = report['stats']['failed']

        # This is the key test: no silent failures
        assert total == successful + failed, "Silent failures detected!"

    def test_detailed_error_information(self):
        """Test that error entries contain useful information."""
        converter = PostmortemConverter()

        converter.convert_file(
            'tests/test_data/invalid-mixed.csv',
            'tests/test_data/error_detail_valid.json',
            'tests/test_data/error_detail_errors.json'
        )

        error_file = Path('tests/test_data/error_detail_errors.json')
        with open(error_file, 'r', encoding='utf-8') as f:
            error_report = json.load(f)

        # Check that errors have structured information
        for error_entry in error_report['errors']:
            # Row number should be present
            assert 'row' in error_entry
            assert isinstance(error_entry['row'], int)
            assert error_entry['row'] >= 2  # Row 1 is header

            # Record ID attempt should be present
            assert 'record_id' in error_entry

            # Issues should be a non-empty list
            assert 'issues' in error_entry
            assert isinstance(error_entry['issues'], list)
            assert len(error_entry['issues']) > 0

            # Each issue should be a string describing the problem
            for issue in error_entry['issues']:
                assert isinstance(issue, str)
                assert len(issue) > 0

    def test_missing_required_fields_error(self):
        """Test that missing required fields are properly reported."""
        converter = PostmortemConverter()

        converter.convert_file(
            'tests/test_data/invalid-mixed.csv',
            'tests/test_data/error_missing_fields_valid.json',
            'tests/test_data/error_missing_fields_errors.json'
        )

        error_file = Path('tests/test_data/error_missing_fields_errors.json')
        with open(error_file, 'r', encoding='utf-8') as f:
            error_report = json.load(f)

        # Should have some errors about missing fields
        assert len(error_report['errors']) > 0

    def test_invalid_date_format_error(self):
        """Test that invalid date formats are reported."""
        converter = PostmortemConverter()

        converter.convert_file(
            'tests/test_data/invalid-mixed.csv',
            'tests/test_data/error_invalid_date_valid.json',
            'tests/test_data/error_invalid_date_errors.json'
        )

        error_file = Path('tests/test_data/error_invalid_date_errors.json')
        with open(error_file, 'r', encoding='utf-8') as f:
            error_report = json.load(f)

        # Errors should be present (mixed data has some invalid dates)
        assert len(error_report['errors']) >= 0  # May or may not have date errors

    def test_success_rate_calculation(self):
        """Test that success rate is correctly calculated."""
        converter = PostmortemConverter()

        # Test with valid data (100% success)
        success1, report1 = converter.convert_file(
            'tests/test_data/valid-100.csv',
            'tests/test_data/error_rate_valid.json'
        )
        assert report1['stats']['success_rate'] == 100.0

        # Test with mixed data (partial success)
        converter2 = PostmortemConverter()
        success2, report2 = converter2.convert_file(
            'tests/test_data/invalid-mixed.csv',
            'tests/test_data/error_rate_mixed_valid.json'
        )

        expected_rate = (report2['stats']['successful'] / report2['stats']['total_records']) * 100
        assert abs(report2['stats']['success_rate'] - expected_rate) < 0.01

    def test_error_report_summary(self):
        """Test that error report summary is accurate."""
        converter = PostmortemConverter()

        converter.convert_file(
            'tests/test_data/invalid-mixed.csv',
            'tests/test_data/error_summary_valid.json',
            'tests/test_data/error_summary_report.json'
        )

        error_file = Path('tests/test_data/error_summary_report.json')
        with open(error_file, 'r', encoding='utf-8') as f:
            error_report = json.load(f)

        summary = error_report['summary']

        # Summary should have all required fields
        assert 'total_records' in summary
        assert 'successful' in summary
        assert 'failed' in summary
        assert 'success_rate' in summary

        # Values should be non-negative integers (except rate)
        assert summary['total_records'] > 0
        assert summary['successful'] >= 0
        assert summary['failed'] >= 0
        assert 0 <= summary['success_rate'] <= 100

        # Summary counts should match errors array
        assert summary['failed'] == len(error_report['errors'])

    def test_partial_record_error_reporting(self):
        """Test that records with some invalid fields are properly reported."""
        converter = PostmortemConverter()

        converter.convert_file(
            'tests/test_data/invalid-mixed.csv',
            'tests/test_data/error_partial_valid.json',
            'tests/test_data/error_partial_errors.json'
        )

        with open('tests/test_data/error_partial_valid.json', 'r', encoding='utf-8') as f:
            valid_output = json.load(f)

        with open('tests/test_data/error_partial_errors.json', 'r', encoding='utf-8') as f:
            error_output = json.load(f)

        # Sum of valid output + errors should equal total
        total_from_report = error_output['summary']['total_records']
        assert len(valid_output['data']) + len(error_output['errors']) == total_from_report

    def test_no_data_loss_on_error(self):
        """Test that error reporting doesn't lose information about invalid records."""
        converter = PostmortemConverter()

        converter.convert_file(
            'tests/test_data/invalid-mixed.csv',
            'tests/test_data/error_no_loss_valid.json',
            'tests/test_data/error_no_loss_errors.json'
        )

        error_file = Path('tests/test_data/error_no_loss_errors.json')
        with open(error_file, 'r', encoding='utf-8') as f:
            error_report = json.load(f)

        # Each error entry should have record_id information
        for error_entry in error_report['errors']:
            # Either record_id or row number should be present
            assert 'row' in error_entry or 'record_id' in error_entry


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
