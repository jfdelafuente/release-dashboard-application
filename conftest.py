"""
PyTest configuration: Ensure src/converters is in Python path for module imports.
This allows tests to import csv_to_json module after code migration to src/converters/.
"""

import sys
from pathlib import Path

# Add src/converters to Python path so tests can find csv_to_json module
src_converters_path = Path(__file__).parent / "src" / "converters"
if str(src_converters_path) not in sys.path:
    sys.path.insert(0, str(src_converters_path))
