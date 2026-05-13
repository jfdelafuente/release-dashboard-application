"""
CSV to JSON Workflow for Massive Incidents Dashboard

A robust data conversion pipeline that transforms massive incident CSV files
into dashboard-compatible JSON format, with automatic encoding/delimiter detection,
field validation, normalization, and detailed error reporting.

Main exports:
- CsvToJsonConverter: Main converter class
- IncidentRecord: Output record type
"""

__version__ = "1.0.0"
__author__ = "Release Dashboard Team"

from csv_to_json.converter import CsvToJsonConverter

__all__ = ["CsvToJsonConverter"]
