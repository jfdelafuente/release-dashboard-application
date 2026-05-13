#!/usr/bin/env python3
"""
Postmortem CSV to JSON converter module.

Orchestrates the conversion pipeline for postmortem incident data:
1. Read CSV with encoding and delimiter detection
2. Map field names with BOM handling
3. Normalize records
4. Generate JSON with metadata
5. Create error reports
"""

import json
import csv
from pathlib import Path
from typing import Tuple, Dict, List, Any, Optional

from csv_to_json.encoding import decode_file
from csv_to_json.delimiter import detect_delimiter
from csv_to_json.postmortem_schemas import (
    PostmortemRecord,
    PostmortemKPIMetrics,
    ConversionMetadata,
    parsePostmortemDate,
    derivateDespliegue
)


def readPostmortemCSV(file_path: str) -> Tuple[List[Dict[str, str]], str]:
    """
    Read postmortem CSV file with encoding and delimiter detection.

    Args:
        file_path: Path to CSV file

    Returns:
        Tuple of (records as list of dicts, detected_encoding)
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"Input file not found: {file_path}")

    # Read raw bytes
    with open(file_path, 'rb') as f:
        file_bytes = f.read()

    # Decode with encoding detection
    file_text, detected_encoding = decode_file(file_bytes)

    # Detect delimiter
    delimiter = detect_delimiter(file_text)

    # Parse CSV
    records = []
    reader = csv.DictReader(file_text.strip().split('\n'), delimiter=delimiter)

    for row in reader:
        if row:  # Skip empty rows
            records.append(row)

    return records, detected_encoding


def mapPostmortemFields(
    csv_record: Dict[str, str],
    strict: bool = False
) -> Dict[str, str]:
    """
    Map CSV field names to output field names.

    Handles:
    - Case-insensitive field name matching
    - BOM character removal (\uFEFF)
    - Optional strict mode (fail on missing required fields)

    Args:
        csv_record: Raw CSV row as dict
        strict: If True, raise error on missing required fields

    Returns:
        Record with cleaned field names
    """
    # Expected 13 fields for postmortem
    expected_fields = {
        'ID de incidencia': None,
        'Descripción': None,
        'Estatus': None,
        'Fecha de envío': None,
        'Grupo asignado': None,
        'Fecha de notificación': None,
        'Fecha de última resolución': None,
        'Motivo de estado': None,
        'MotivoEstado_Anterior': None,
        'Grupo Resolutor': None,
        'Urgencia': None,
        'Impacto': None,
        'Grupo Remitente': None
    }

    # Create mapping from CSV headers (with BOM cleanup)
    mapped_record = {}

    for csv_key, csv_value in csv_record.items():
        # Remove BOM character if present
        clean_key = csv_key.lstrip('\ufeff') if csv_key else csv_key

        # Try exact match first
        if clean_key in expected_fields:
            mapped_record[clean_key] = csv_value
        # Try case-insensitive match
        else:
            found = False
            for expected_key in expected_fields.keys():
                if expected_key.lower() == clean_key.lower():
                    mapped_record[expected_key] = csv_value
                    found = True
                    break

            # If no match found, preserve as-is (might be extra column)
            if not found:
                mapped_record[clean_key] = csv_value

    return mapped_record


def normalizePostmortemRecord(
    record: Dict[str, str]
) -> Tuple[PostmortemRecord, List[str]]:
    """
    Normalize a postmortem record.

    Performs:
    - Field validation (required fields)
    - Date parsing and normalization
    - Field trimming and cleanup
    - Creates PostmortemRecord object

    Args:
        record: Raw CSV record dict

    Returns:
        Tuple of (PostmortemRecord, errors list)
    """
    errors = []

    # Map fields
    mapped = mapPostmortemFields(record)

    # Normalize fields
    normalized = {}
    for field_name, field_value in mapped.items():
        # Trim whitespace
        value = str(field_value).strip() if field_value else ''

        # Normalize by field type
        if field_name in ['Estatus', 'Urgencia', 'Impacto']:
            # Title case normalization
            value = value.title() if value else ''

        elif field_name in [
            'Fecha de envío',
            'Fecha de notificación',
            'Fecha de última resolución'
        ]:
            # Date parsing - parse and normalize
            if value:
                parsed = parsePostmortemDate(value)
                if parsed:
                    value = parsed
                else:
                    errors.append(f"{field_name}: Unparseable date format: {value}")
                    value = ''

        normalized[field_name] = value

    # Create PostmortemRecord
    pm_record = PostmortemRecord(normalized)

    # Validate
    pm_record.validate()
    if pm_record.errors:
        errors.extend(pm_record.errors)

    return pm_record, errors


def generatePostmortemJSON(
    records: List[PostmortemRecord],
    output_path: str,
    source_filename: str = 'unknown',
    include_metadata: bool = True
) -> Dict[str, Any]:
    """
    Generate JSON output with postmortem records and optional metadata.

    Performs:
    - Creates valid PostmortemRecord objects
    - Calculates KPIs from records
    - Generates metadata with timestamps
    - Writes JSON to file

    Args:
        records: List of PostmortemRecord objects
        output_path: Path for output JSON file
        source_filename: Original CSV filename for metadata
        include_metadata: Whether to include metadata section

    Returns:
        Report dict with stats
    """
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Prepare output data
    output_data = {}

    # Calculate KPIs
    kpis = PostmortemKPIMetrics()
    output_records = []

    for record in records:
        # Add to KPI aggregation
        kpis.add_record(record)
        # Add to output
        output_records.append(record.to_dict())

    # Add metadata if requested
    if include_metadata:
        metadata = ConversionMetadata(
            source_filename=source_filename,
            record_count=len(output_records),
            kpis=kpis
        )
        output_data['_metadata'] = metadata.to_dict()

    # Add records
    output_data['data'] = output_records

    # Write to file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    return {
        'output_path': str(output_file),
        'record_count': len(output_records),
        'kpis': kpis.to_dict() if include_metadata else None
    }


class PostmortemConverter:
    """Complete postmortem CSV to JSON converter."""

    def __init__(self):
        """Initialize converter."""
        self.valid_records = []
        self.invalid_records = []
        self.errors = []
        self.stats = {
            'total_records': 0,
            'successful': 0,
            'failed': 0,
            'success_rate': 0.0
        }
        self.detected_encoding = None
        self.kpis = None

    def convert_file(
        self,
        input_path: str,
        output_path: Optional[str] = None,
        error_report_path: Optional[str] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Convert postmortem CSV to JSON.

        Args:
            input_path: Path to input CSV
            output_path: Path for output JSON
            error_report_path: Path for error report

        Returns:
            Tuple of (success, report)
        """
        input_file = Path(input_path)

        # Read CSV
        records, self.detected_encoding = readPostmortemCSV(str(input_file))
        self.stats['total_records'] = len(records)

        # Process each record
        for row_num, record in enumerate(records, start=2):
            pm_record, errors = normalizePostmortemRecord(record)

            if not errors and pm_record.is_valid:
                self.valid_records.append(pm_record)
                self.stats['successful'] += 1
            else:
                self.invalid_records.append({
                    'row': row_num,
                    'record': pm_record,
                    'errors': errors
                })
                self.stats['failed'] += 1

        # Calculate stats
        if self.stats['total_records'] > 0:
            self.stats['success_rate'] = (
                self.stats['successful'] / self.stats['total_records'] * 100
            )

        # Derive Despliegue for valid records BEFORE generating JSON
        # (KPIs need to include Despliegue counts)
        despliegue_map = derivateDespliegue(self.valid_records)
        for record in self.valid_records:
            record_id = record.data.get('ID de incidencia')
            if record_id in despliegue_map:
                record.data['Despliegue'] = despliegue_map[record_id]

        # Generate outputs
        if output_path:
            generatePostmortemJSON(
                self.valid_records,
                output_path,
                source_filename=input_file.name
            )

        if error_report_path:
            self._write_error_report(error_report_path)

        # Return report
        return self.stats['failed'] == 0, {
            'stats': self.stats,
            'encoding_detected': self.detected_encoding,
            'valid_count': self.stats['successful'],
            'invalid_count': self.stats['failed'],
            'errors': self.errors
        }

    def _write_error_report(self, error_report_path: str):
        """Write error report to file."""
        report_file = Path(error_report_path)
        report_file.parent.mkdir(parents=True, exist_ok=True)

        report_data = {
            'summary': {
                'total_records': self.stats['total_records'],
                'successful': self.stats['successful'],
                'failed': self.stats['failed'],
                'success_rate': self.stats['success_rate']
            },
            'errors': []
        }

        # Add detailed error info
        for invalid in self.invalid_records:
            error_entry = {
                'row': invalid['row'],
                'record_id': invalid['record'].data.get('ID de incidencia'),
                'issues': invalid['errors']
            }
            report_data['errors'].append(error_entry)

        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
