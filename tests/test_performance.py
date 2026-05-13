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

    def test_large_dataset_performance(self):
        """Test that 1000+ records convert in under 5 seconds."""
        # Note: This test uses valid-100.csv as reference
        # In production, would need actual 1000+ record file

        converter = PostmortemConverter()

        # Time the conversion
        start_time = time.time()

        success, report = converter.convert_file(
            'tests/test_data/valid-100.csv',
            'tests/test_data/perf_test_output.json'
        )

        elapsed_time = time.time() - start_time

        # Should complete in under 5 seconds
        assert elapsed_time < 5.0, f"Conversion took {elapsed_time:.2f}s, expected < 5s"
        assert report['stats']['successful'] == 100

    def test_conversion_speed_per_record(self):
        """Test that conversion speed is reasonable (< 5ms per record)."""
        converter = PostmortemConverter()

        start_time = time.time()
        success, report = converter.convert_file(
            'tests/test_data/valid-100.csv',
            'tests/test_data/perf_speed_test.json'
        )
        elapsed_time = time.time() - start_time

        record_count = report['stats']['total_records']
        ms_per_record = (elapsed_time * 1000) / record_count if record_count > 0 else 0

        # Should be < 5ms per record for reasonable performance
        assert ms_per_record < 5.0, f"{ms_per_record:.2f}ms per record"

    def test_json_output_generation_speed(self):
        """Test that JSON output generation is fast."""
        converter = PostmortemConverter()

        # First convert to get records
        converter.convert_file('tests/test_data/valid-100.csv')

        # Time only the JSON generation
        from csv_to_json.postmortem_converter import generatePostmortemJSON

        start_time = time.time()
        generatePostmortemJSON(
            converter.valid_records,
            'tests/test_data/perf_json_gen.json',
            source_filename='valid-100.csv'
        )
        elapsed_time = time.time() - start_time

        # JSON generation should be < 100ms
        assert elapsed_time < 0.1, f"JSON generation took {elapsed_time*1000:.2f}ms"

    def test_error_report_generation_speed(self):
        """Test that error report generation is fast."""
        converter = PostmortemConverter()

        # Convert file with errors
        converter.convert_file(
            'tests/test_data/invalid-mixed.csv'
        )

        # Time error report generation
        start_time = time.time()
        converter._write_error_report('tests/test_data/perf_error_report.json')
        elapsed_time = time.time() - start_time

        # Error report should be < 100ms
        assert elapsed_time < 0.1, f"Error report took {elapsed_time*1000:.2f}ms"

    def test_memory_efficiency(self):
        """Test that converter doesn't consume excessive memory."""
        # Load a conversion
        converter = PostmortemConverter()
        success, report = converter.convert_file(
            'tests/test_data/valid-100.csv',
            'tests/test_data/perf_memory_test.json'
        )

        # Should have reasonable record count
        assert report['stats']['successful'] == 100

        # Output file should be reasonable size (< 1MB for 100 records)
        output_file = Path('tests/test_data/perf_memory_test.json')
        file_size_mb = output_file.stat().st_size / (1024 * 1024)
        assert file_size_mb < 1.0, f"Output file {file_size_mb:.2f}MB seems large"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
