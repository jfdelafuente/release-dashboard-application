"""
Pytest configuration for CSV-to-JSON converter tests.

Provides common fixtures, markers, and test utilities for all converter tests.
"""
import json
import os
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def tmp_test_dir():
    """Create a temporary test directory."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
def test_data_dir():
    """Return path to test data directory."""
    return Path(__file__).parent / "test_data"


@pytest.fixture
def sample_csv_massive(test_data_dir):
    """Return path to sample massive incidents CSV file."""
    csv_file = test_data_dir / "valid-100.csv"
    if not csv_file.exists():
        pytest.skip(f"Test data file not found: {csv_file}")
    return csv_file


@pytest.fixture
def sample_csv_postmortem(test_data_dir):
    """Return path to sample postmortem CSV file."""
    csv_file = test_data_dir / "postmortem-sample.csv"
    if not csv_file.exists():
        pytest.skip(f"Test data file not found: {csv_file}")
    return csv_file


@pytest.fixture
def json_reader():
    """Utility fixture for reading JSON files."""
    def _read_json(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return _read_json


@pytest.fixture
def json_writer():
    """Utility fixture for writing JSON files."""
    def _write_json(filepath, data):
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    return _write_json


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "unit: unit tests")
    config.addinivalue_line("markers", "integration: integration tests")
    config.addinivalue_line("markers", "performance: performance/scaling tests")
    config.addinivalue_line("markers", "edge_case: edge case tests")


# Performance profiling fixtures
@pytest.fixture
def performance_timer():
    """Timer for measuring performance."""
    import time
    class Timer:
        def __init__(self):
            self.start_time = None
            self.elapsed = 0

        def __enter__(self):
            self.start_time = time.time()
            return self

        def __exit__(self, *args):
            self.elapsed = time.time() - self.start_time

    return Timer


@pytest.fixture
def memory_tracker():
    """Track memory usage during test."""
    try:
        import psutil
        process = psutil.Process()

        class MemoryTracker:
            def __init__(self):
                self.start_memory = None
                self.peak_memory = 0
                self.end_memory = None

            def start(self):
                self.start_memory = process.memory_info().rss / (1024 * 1024)  # MB
                self.peak_memory = self.start_memory

            def update(self):
                current = process.memory_info().rss / (1024 * 1024)
                self.peak_memory = max(self.peak_memory, current)

            def end(self):
                self.end_memory = process.memory_info().rss / (1024 * 1024)
                return self.peak_memory - self.start_memory

        return MemoryTracker()
    except ImportError:
        pytest.skip("psutil not installed for memory tracking")
