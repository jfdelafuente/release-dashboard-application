"""
Test helper utilities for CSV/JSON comparison and validation.
"""
import csv
import json
from typing import Dict, List, Any


def read_csv_as_dicts(filepath: str) -> List[Dict[str, str]]:
    """Read CSV file and return as list of dictionaries."""
    records = []
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        records = list(reader)
    return records


def read_json_file(filepath: str) -> Dict[str, Any]:
    """Read JSON file and return as dictionary."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def compare_json_structures(json1: Dict, json2: Dict) -> tuple[bool, List[str]]:
    """
    Compare two JSON structures and return differences.

    Returns:
        (is_equal, list_of_differences)
    """
    differences = []

    # Check metadata
    if json1.get('_metadata', {}) != json2.get('_metadata', {}):
        differences.append("Metadata mismatch")

    # Check data array length
    data1 = json1.get('data', [])
    data2 = json2.get('data', [])

    if len(data1) != len(data2):
        differences.append(f"Record count mismatch: {len(data1)} vs {len(data2)}")

    # Check first record structure
    if data1 and data2:
        keys1 = set(data1[0].keys())
        keys2 = set(data2[0].keys())
        if keys1 != keys2:
            missing = keys1 - keys2
            extra = keys2 - keys1
            if missing:
                differences.append(f"Missing fields: {missing}")
            if extra:
                differences.append(f"Extra fields: {extra}")

    return len(differences) == 0, differences


def validate_kpi_structure(kpis: Dict[str, Any], converter_type: str = 'massive') -> List[str]:
    """
    Validate KPI structure matches expected schema.

    Args:
        kpis: KPI dictionary
        converter_type: 'massive' or 'postmortem'

    Returns:
        List of validation errors (empty if valid)
    """
    errors = []

    if converter_type == 'massive':
        required_fields = [
            'total_incidencias',
            'total_pendientes',
            'trend_7d',
            'trend_15d',
            'trend_30d',
            'by_estatus',
            'by_urgencia',
            'by_impacto'
        ]
        for field in required_fields:
            if field not in kpis:
                errors.append(f"Missing KPI field: {field}")

    elif converter_type == 'postmortem':
        required_fields = ['dashboard_hub', 'by_estatus', 'by_urgencia', 'by_impacto']
        for field in required_fields:
            if field not in kpis:
                errors.append(f"Missing postmortem KPI field: {field}")

        dashboard_hub_fields = ['cerradas_percent', 'pap_resueltas_percent', 'mesa_resueltas_percent']
        hub = kpis.get('dashboard_hub', {})
        for field in dashboard_hub_fields:
            if field not in hub:
                errors.append(f"Missing Dashboard Hub KPI: {field}")

    return errors


def validate_error_report(error_report: Dict[str, Any]) -> List[str]:
    """Validate error report structure."""
    errors = []

    if 'summary' not in error_report:
        errors.append("Missing 'summary' in error report")
    else:
        summary = error_report['summary']
        required = ['total_records', 'successful', 'failed', 'success_rate']
        for field in required:
            if field not in summary:
                errors.append(f"Missing summary field: {field}")

    if 'errors' not in error_report:
        errors.append("Missing 'errors' array in error report")
    else:
        for i, error in enumerate(error_report['errors']):
            if 'row' not in error:
                errors.append(f"Error {i}: Missing 'row' field")
            if 'issues' not in error:
                errors.append(f"Error {i}: Missing 'issues' array")
            else:
                for issue in error['issues']:
                    if 'field' not in issue or 'error' not in issue:
                        errors.append(f"Error {i}: Malformed issue entry")

    return errors
