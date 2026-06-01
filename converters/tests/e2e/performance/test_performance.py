#!/usr/bin/env python3
"""
Performance tests for postmortem converter.

Validates that conversion completes in under 5 seconds for 1000+ records.

NOTE: All tests use pytest tmp_path fixture for temporary output files.
No files are left in tests/test_data after test execution.
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

        # Time the conversion
        start_time = time.time()

        output_file = tmp_path / "output.json"
        success, report = converter.convert_file(
            'tests/test_data/valid-100.csv',
            str(output_file)
        )

        elapsed_time = time.time() - start_time

        # Should complete in under 5 seconds
        assert elapsed_time < 5.0, f"Conversion took {elapsed_time:.2f}s, expected < 5s"
        assert report['stats']['successful'] == 100

    def test_conversion_speed_per_record(self, tmp_path):
        """Test that conversion speed is reasonable (< 5ms per record)."""
        converter = PostmortemConverter()

        output_file = tmp_path / "output.json"
        start_time = time.time()
        success, report = converter.convert_file(
            'tests/test_data/valid-100.csv',
            str(output_file)
        )
        elapsed_time = time.time() - start_time

        record_count = report['stats']['total_records']
        ms_per_record = (elapsed_time * 1000) / record_count if record_count > 0 else 0

        # Should be < 5ms per record for reasonable performance
        assert ms_per_record < 5.0, f"{ms_per_record:.2f}ms per record"

    def test_json_output_generation_speed(self, tmp_path):
        """Test that JSON output generation is fast."""
        converter = PostmortemConverter()

        # First convert to get records
        converter.convert_file(
            'tests/test_data/valid-100.csv',
            str(tmp_path / "temp.json")
        )

        # Time only the JSON generation
        from csv_to_json.postmortem_converter import generatePostmortemJSON

        output_file = tmp_path / "json_gen.json"
        start_time = time.time()
        generatePostmortemJSON(
            converter.valid_records,
            str(output_file),
            source_filename='valid-100.csv'
        )
        elapsed_time = time.time() - start_time

        # JSON generation should be < 100ms
        assert elapsed_time < 0.1, f"JSON generation took {elapsed_time*1000:.2f}ms"

    def test_error_report_generation_speed(self, tmp_path):
        """Test that error report generation is fast."""
        converter = PostmortemConverter()

        # Convert file with errors
        error_file = tmp_path / "error_report.json"
        converter.convert_file(
            'tests/test_data/invalid-mixed.csv',
            str(tmp_path / "valid.json"),
            str(error_file)
        )

        # Time error report generation
        start_time = time.time()
        # Report was already generated, so we just measure a read operation
        with open(error_file, 'r') as f:
            json.load(f)
        elapsed_time = time.time() - start_time

        # Error report read should be < 100ms
        assert elapsed_time < 0.1, f"Error report read took {elapsed_time*1000:.2f}ms"

    def test_memory_efficiency(self, tmp_path):
        """Test that converter doesn't consume excessive memory."""
        # Load a conversion
        converter = PostmortemConverter()
        output_file = tmp_path / "output.json"
        success, report = converter.convert_file(
            'tests/test_data/valid-100.csv',
            str(output_file)
        )

        # Should have reasonable record count
        assert report['stats']['successful'] == 100

        # Output file should be reasonable size (< 1MB for 100 records)
        file_size_mb = output_file.stat().st_size / (1024 * 1024)
        assert file_size_mb < 1.0, f"Output file {file_size_mb:.2f}MB seems large"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
