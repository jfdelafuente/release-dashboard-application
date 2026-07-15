#!/usr/bin/env python3
"""
Postmortem CSV to JSON Converter - Schemas and Data Structures

Defines all data models for postmortem incident processing:
- PostmortemRecord: Single incident postmortem entry
- PostmortemKPIMetrics: Aggregated statistics
- ConversionMetadata: File-level audit trail
- ValidationError: Row-level error tracking
- Date parsing and Despliegue derivation logic
"""
from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional, Any
import re


class PostmortemRecord:
    """Represents a single incident postmortem entry from CSV input."""

    # 13 Input fields from CSV
    REQUIRED_FIELDS = [
        'ID de incidencia',
        'Descripción',
        'Estatus',
        'Fecha de envío',
        'Grupo asignado',
        'Urgencia',
        'Impacto'
    ]

    OPTIONAL_FIELDS = [
        'Fecha de notificación',
        'Fecha de última resolución',
        'Motivo de estado',
        'MotivoEstado_Anterior',
        'Grupo Resolutor',
        'Grupo Remitente'
    ]

    ALL_INPUT_FIELDS = REQUIRED_FIELDS + OPTIONAL_FIELDS

    def __init__(self, data: Dict[str, Any]):
        """Initialize from CSV row data."""
        self.data = data
        self.is_valid = True
        self.errors = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert record to output dictionary."""
        return dict(self.data)

    def validate(self) -> bool:
        """Validate required fields are present and non-empty."""
        self.errors = []
        for field in self.REQUIRED_FIELDS:
            if field not in self.data or not str(self.data.get(field, '')).strip():
                self.errors.append(f"Missing or empty required field: {field}")
                self.is_valid = False
        return self.is_valid


class PostmortemKPIMetrics:
    """Aggregated statistics calculated during conversion.

    Includes both basic metrics (by_estatus, by_urgencia, by_impacto)
    and Dashboard Hub specific metrics (cerradas%, resueltas PAP%, resueltas MESA%).
    """

    def __init__(self):
        self.total = 0
        self.by_estatus: Dict[str, int] = {}
        self.by_urgencia: Dict[str, int] = {}
        self.by_impacto: Dict[str, int] = {}

        # Dashboard Hub KPIs (for postmortem dashboard)
        self.cerradas_count = 0  # Count of Cerrado status
        self.pap_total = 0  # Count of PAP despliegue
        self.pap_resueltas = 0  # Count of PAP with Cerrado or Resuelto
        self.mesa_total = 0  # Count of MESA despliegue
        self.mesa_resueltas = 0  # Count of MESA with Cerrado or Resuelto

    def to_dict(self) -> Dict[str, Any]:
        """Convert KPI metrics to output dictionary."""
        # Calculate percentages
        cerradas_percent = round((self.cerradas_count / self.total * 100)) if self.total > 0 else 0
        pap_percent = round((self.pap_resueltas / self.pap_total * 100)) if self.pap_total > 0 else 0
        mesa_percent = round((self.mesa_resueltas / self.mesa_total * 100)) if self.mesa_total > 0 else 0

        return {
            'total': self.total,
            'by_estatus': self.by_estatus,
            'by_urgencia': self.by_urgencia,
            'by_impacto': self.by_impacto,
            # Dashboard Hub KPIs
            'dashboard_hub': {
                'total_incidencias': self.total,
                'cerradas_percent': cerradas_percent,
                'pap_resueltas_percent': pap_percent,
                'mesa_resueltas_percent': mesa_percent,
                'pap_total': self.pap_total,
                'mesa_total': self.mesa_total
            }
        }

    def add_record(self, record: PostmortemRecord):
        """Add record to KPI aggregates."""
        self.total += 1

        # By Estatus
        estatus = record.data.get('Estatus', 'Unknown')
        if estatus:
            self.by_estatus[estatus] = self.by_estatus.get(estatus, 0) + 1

            # Count cerradas for Dashboard Hub (includes both Cerrado and Resuelto)
            if 'cerrado' in estatus.lower() or 'resuelto' in estatus.lower():
                self.cerradas_count += 1

        # By Urgencia
        urgencia = record.data.get('Urgencia', 'Unknown')
        if urgencia:
            self.by_urgencia[urgencia] = self.by_urgencia.get(urgencia, 0) + 1

        # By Impacto
        impacto = record.data.get('Impacto', 'Unknown')
        if impacto:
            self.by_impacto[impacto] = self.by_impacto.get(impacto, 0) + 1

        # Dashboard Hub KPIs (Despliegue-based)
        despliegue = record.data.get('Despliegue', '')
        if despliegue == 'PAP':
            self.pap_total += 1
            # Count as resueltas if status is Cerrado or Resuelto
            if estatus and ('cerrado' in estatus.lower() or 'resuelto' in estatus.lower()):
                self.pap_resueltas += 1
        elif despliegue == 'MESA':
            self.mesa_total += 1
            # Count as resueltas if status is Cerrado or Resuelto
            if estatus and ('cerrado' in estatus.lower() or 'resuelto' in estatus.lower()):
                self.mesa_resueltas += 1


class ConversionMetadata:
    """File-level metadata attached to output JSON."""

    def __init__(
        self,
        source_filename: str,
        record_count: int,
        kpis: PostmortemKPIMetrics,
        release_name: Optional[str] = None
    ):
        self.type = 'postmortem'
        self.version = '1.0'
        self.created = datetime.now().isoformat() + 'Z'
        self.source_filename = source_filename
        self.release_name = release_name
        self.record_count = record_count
        self.kpis = kpis

    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to output dictionary."""
        return {
            'type': self.type,
            'version': self.version,
            'created': self.created,
            'source_filename': self.source_filename,
            'release_name': self.release_name,
            'record_count': self.record_count,
            'conversion_timestamp': self.created,
            'kpis': self.kpis.to_dict()
        }


class ValidationError:
    """Represents a single validation failure."""

    def __init__(self, row: int, record_id: Optional[str] = None):
        self.row = row
        self.record_id = record_id
        self.error_type = 'validation'
        self.issues: List[Dict[str, str]] = []

    def add_issue(self, field: str, error: str, value: Optional[str] = None):
        """Add field-level issue to error."""
        issue = {'field': field, 'error': error}
        if value:
            issue['value'] = value
        self.issues.append(issue)

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to output dictionary."""
        return {
            'row': self.row,
            'record_id': self.record_id,
            'error_type': self.error_type,
            'issues': self.issues
        }


def parsePostmortemDate(date_str: str) -> Optional[str]:
    """
    Parse postmortem date from various formats and normalize to DD/MM/YYYY.

    Supports:
    - DD-MMM format (e.g., "26-abr")
    - DD/MM/YYYY format (e.g., "26/04/2026")
    - DD/MM/YYYY HH:MM a/p format

    Returns normalized DD/MM/YYYY format or None if unparseable.
    """
    if not date_str:
        return None

    date_str = date_str.strip()

    # Remove time component if present (HH:MM a/p)
    if ' ' in date_str:
        date_str = date_str.split()[0]

    # Try DD/MM/YYYY format
    if '/' in date_str:
        parts = date_str.split('/')
        if len(parts) == 3:
            try:
                day, month, year = parts
                # Pad single digits
                day = day.zfill(2)
                month = month.zfill(2)
                # Parse to validate
                dt = datetime(int(year), int(month), int(day))
                return f"{day}/{month}/{year}"
            except (ValueError, IndexError):
                return None

    # Try DD-MMM format (Spanish month abbreviations)
    if '-' in date_str:
        parts = date_str.split('-')
        if len(parts) == 2:
            try:
                day, month_abbr = parts
                day = day.zfill(2)
                month_abbr = month_abbr.lower()

                # Spanish month abbreviations
                months = {
                    'ene': 1, 'feb': 2, 'mar': 3, 'abr': 4, 'may': 5, 'jun': 6,
                    'jul': 7, 'ago': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dic': 12
                }

                if month_abbr in months:
                    month_num = months[month_abbr]
                    # Assume current year if not specified
                    year = datetime.now().year
                    dt = datetime(year, month_num, int(day))
                    return f"{day}/{month_num:02d}/{year}"
            except (ValueError, KeyError, IndexError):
                return None

    return None


def derivateDespliegue(records: List[PostmortemRecord]) -> Dict[str, str]:
    """
    Derive Despliegue field for each record based on oldest date.

    Returns dict mapping record ID to Despliegue value (PAP or MESA).
    - PAP: ALL records with the oldest date (first day)
    - MESA: All other records
    """
    despliegue_map = {}
    min_date_tuple = None  # Store as (YYYY, MM, DD) for correct comparison

    # First pass: Find the oldest date
    for record in records:
        for date_field in ['Fecha de envío', 'Fecha de notificación', 'Fecha de última resolución']:
            date_str = record.data.get(date_field)
            if date_str:
                parsed_date = parsePostmortemDate(date_str)  # Returns DD/MM/YYYY
                if parsed_date:
                    # Convert DD/MM/YYYY to (YYYY, MM, DD) tuple for correct comparison
                    parts = parsed_date.split('/')
                    if len(parts) == 3:
                        date_tuple = (int(parts[2]), int(parts[1]), int(parts[0]))  # YYYY, MM, DD
                        if min_date_tuple is None or date_tuple < min_date_tuple:
                            min_date_tuple = date_tuple

    # Second pass: Assign Despliegue values
    if min_date_tuple:
        first_with_min_date = False  # Track if we've already assigned PAP to first record
        for record in records:
            record_id = record.data.get('ID de incidencia')

            # Find oldest date in this record
            record_min_date = None
            for date_field in ['Fecha de envío', 'Fecha de notificación', 'Fecha de última resolución']:
                date_str = record.data.get(date_field)
                if date_str:
                    parsed_date = parsePostmortemDate(date_str)
                    if parsed_date:
                        parts = parsed_date.split('/')
                        if len(parts) == 3:
                            date_tuple = (int(parts[2]), int(parts[1]), int(parts[0]))
                            if record_min_date is None or date_tuple < record_min_date:
                                record_min_date = date_tuple

            # Only first record with the minimum date gets PAP
            if record_min_date and record_min_date[:3] == min_date_tuple[:3]:
                if not first_with_min_date:
                    despliegue_map[record_id] = 'PAP'
                    first_with_min_date = True
                else:
                    despliegue_map[record_id] = 'MESA'
            else:
                despliegue_map[record_id] = 'MESA'
    else:
        # Handle case where no dates were parseable (all get MESA except first)
        for i, record in enumerate(records):
            record_id = record.data.get('ID de incidencia')
            if i == 0:
                despliegue_map[record_id] = 'PAP'
            else:
                despliegue_map[record_id] = 'MESA'

    return despliegue_map
