"""
CSV to JSON Workflow for Massive Incidents Dashboard

A robust data conversion pipeline that transforms massive incident CSV files
into dashboard-compatible JSON format, with automatic encoding/delimiter detection,
field validation, normalization, and detailed error reporting.

Main exports:
- CsvToJsonConverter: Main converter class
- IncidentRecord: Output record type
"""
from __future__ import annotations

__version__ = "1.0.0"
__author__ = "Release Dashboard Team"

from .converter import CsvToJsonConverter

__all__ = ["CsvToJsonConverter"]
