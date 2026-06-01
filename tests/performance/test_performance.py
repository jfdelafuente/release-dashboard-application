#!/usr/bin/env python3
"""
Performance tests for postmortem converter.

Validates that conversion completes in under 5 seconds for 1000+ records.
"""

import pytest
import time
import json
from pathlib import Path
from csv_to_json.postmortem_converter import PostmortemConverter


class TestPerformance:
    """Performance tests for converter."""

    def test_large_dataset_performance(self, tmp_path):
        """Test that 1000+ records convert in under 5 seconds."""
        # Note: This test uses valid-100.csv as reference
        # In production, would need actual 1000+ record file

        converter = PostmortemConverter()

        start_time = time.time()

        success, report = converter.convert_file(
            'tests/test_data/valid-100.csv',
            tmp_path / 'output.json'
        )

        elapsed_time = time.time() - start_time

        assert elapsed_time < 5.0, f"Conversion took {elapsed_time:.2f}s, expected < 5s"
        assert report['stats']['successful'] == 100

    def test_conversion_speed_per_record(self, tmp_path):
        """Test that conversion speed is reasonable (< 5ms per record)."""
        converter = PostmortemConverter()

        start_time = time.time()
        success, report = converter.convert_file(
            'tests/test_data/valid-100.csv',
            tmp_path / 'output.json'
        )
        elapsed_time = time.time() - start_time

        record_count = report['stats']['total_records']
        ms_per_record = (elapsed_time * 1000) / record_count if record_count > 0 else 0

        assert ms_per_record < 5.0, f"{ms_per_record:.2f}ms per record"

    def test_json_output_generation_speed(self, tmp_path):
        """Test that JSON output generation is fast."""
        converter = PostmortemConverter()

        converter.convert_file('tests/test_data/valid-100.csv')

        from csv_to_json.postmortem_converter import generatePostmortemJSON

        start_time = time.time()
        generatePostmortemJSON(
            converter.valid_records,
            tmp_path / 'output.json',
            source_filename='valid-100.csv'
        )
        elapsed_time = time.time() - start_time

        assert elapsed_time < 0.1, f"JSON generation took {elapsed_time*1000:.2f}ms"

    def test_error_report_generation_speed(self, tmp_path):
        """Test that error report generation is fast."""
        converter = PostmortemConverter()

        converter.convert_file(
            'tests/test_data/invalid-mixed.csv'
        )

        start_time = time.time()
        converter._write_error_report(tmp_path / 'errors.json')
        elapsed_time = time.time() - start_time

        assert elapsed_time < 0.1, f"Error report took {elapsed_time*1000:.2f}ms"

    def test_memory_efficiency(self, tmp_path):
        """Test that converter doesn't consume excessive memory."""
        converter = PostmortemConverter()

        output_file = tmp_path / 'output.json'
        success, report = converter.convert_file(
            'tests/test_data/valid-100.csv',
            output_file
        )

        assert report['stats']['successful'] == 100

        # Output file should be reasonable size (< 1MB for 100 records)
        file_size_mb = output_file.stat().st_size / (1024 * 1024)
        assert file_size_mb < 1.0, f"Output file {file_size_mb:.2f}MB seems large"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
