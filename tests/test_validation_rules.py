#!/usr/bin/env python3
"""
Unit tests for PostmortemRecord validation rules.

Tests field validation including required fields, allowed values, and date parsing.
"""

import pytest
from csv_to_json.postmortem_converter import normalizePostmortemRecord
from csv_to_json.postmortem_schemas import PostmortemRecord


class TestRequiredFieldValidation:
    """Test validation of required fields."""

    def test_validate_id_required(self):
        """Test that ID de incidencia is required."""
        record = {
            'Descripción': 'Test',
            'Estatus': 'Cerrada',
            'Fecha de envío': '01/05/2026 8:00 a',
            'Grupo asignado': 'SOP_TEST',
            'Urgencia': 'Alta',
            'Impacto': 'Masiva'
        }

        pm_record, errors = normalizePostmortemRecord(record)

        assert len(errors) > 0
        assert any('ID de incidencia' in e for e in errors)

    def test_validate_descripcion_required(self):
        """Test that Descripción is required."""
        record = {
            'ID de incidencia': 'INC001',
            'Estatus': 'Cerrada',
            'Fecha de envío': '01/05/2026 8:00 a',
            'Grupo asignado': 'SOP_TEST',
            'Urgencia': 'Alta',
            'Impacto': 'Masiva'
        }

        pm_record, errors = normalizePostmortemRecord(record)

        assert len(errors) > 0

    def test_validate_estatus_required(self):
        """Test that Estatus is required."""
        record = {
            'ID de incidencia': 'INC001',
            'Descripción': 'Test',
            'Fecha de envío': '01/05/2026 8:00 a',
            'Grupo asignado': 'SOP_TEST',
            'Urgencia': 'Alta',
            'Impacto': 'Masiva'
        }

        pm_record, errors = normalizePostmortemRecord(record)

        assert len(errors) > 0

    def test_validate_fecha_envio_required(self):
        """Test that Fecha de envío is required."""
        record = {
            'ID de incidencia': 'INC001',
            'Descripción': 'Test',
            'Estatus': 'Cerrada',
            'Grupo asignado': 'SOP_TEST',
            'Urgencia': 'Alta',
            'Impacto': 'Masiva'
        }

        pm_record, errors = normalizePostmortemRecord(record)

        assert len(errors) > 0

    def test_validate_grupo_asignado_required(self):
        """Test that Grupo asignado is required."""
        record = {
            'ID de incidencia': 'INC001',
            'Descripción': 'Test',
            'Estatus': 'Cerrada',
            'Fecha de envío': '01/05/2026 8:00 a',
            'Urgencia': 'Alta',
            'Impacto': 'Masiva'
        }

        pm_record, errors = normalizePostmortemRecord(record)

        assert len(errors) > 0

    def test_validate_urgencia_required(self):
        """Test that Urgencia is required."""
        record = {
            'ID de incidencia': 'INC001',
            'Descripción': 'Test',
            'Estatus': 'Cerrada',
            'Fecha de envío': '01/05/2026 8:00 a',
            'Grupo asignado': 'SOP_TEST',
            'Impacto': 'Masiva'
        }

        pm_record, errors = normalizePostmortemRecord(record)

        assert len(errors) > 0

    def test_validate_impacto_required(self):
        """Test that Impacto is required."""
        record = {
            'ID de incidencia': 'INC001',
            'Descripción': 'Test',
            'Estatus': 'Cerrada',
            'Fecha de envío': '01/05/2026 8:00 a',
            'Grupo asignado': 'SOP_TEST',
            'Urgencia': 'Alta'
        }

        pm_record, errors = normalizePostmortemRecord(record)

        assert len(errors) > 0


class TestDateValidation:
    """Test date field validation."""

    def test_validate_valid_date_format(self):
        """Test validation of valid date format."""
        record = {
            'ID de incidencia': 'INC001',
            'Descripción': 'Test',
            'Estatus': 'Cerrada',
            'Fecha de envío': '01/05/2026 8:00 a',
            'Grupo asignado': 'SOP_TEST',
            'Urgencia': 'Alta',
            'Impacto': 'Masiva'
        }

        pm_record, errors = normalizePostmortemRecord(record)

        # Should not have date-related errors
        assert not any('Unparseable' in e for e in errors)

    def test_validate_invalid_date_format(self):
        """Test validation of invalid date format."""
        record = {
            'ID de incidencia': 'INC001',
            'Descripción': 'Test',
            'Estatus': 'Cerrada',
            'Fecha de envío': 'INVALID_DATE',
            'Grupo asignado': 'SOP_TEST',
            'Urgencia': 'Alta',
            'Impacto': 'Masiva'
        }

        pm_record, errors = normalizePostmortemRecord(record)

        # Should have date error
        assert any('Unparseable' in e for e in errors)

    def test_validate_invalid_day(self):
        """Test validation rejects invalid day."""
        record = {
            'ID de incidencia': 'INC001',
            'Descripción': 'Test',
            'Estatus': 'Cerrada',
            'Fecha de envío': '32/05/2026',
            'Grupo asignado': 'SOP_TEST',
            'Urgencia': 'Alta',
            'Impacto': 'Masiva'
        }

        pm_record, errors = normalizePostmortemRecord(record)

        assert any('Unparseable' in e for e in errors)

    def test_validate_invalid_month(self):
        """Test validation rejects invalid month."""
        record = {
            'ID de incidencia': 'INC001',
            'Descripción': 'Test',
            'Estatus': 'Cerrada',
            'Fecha de envío': '01/13/2026',
            'Grupo asignado': 'SOP_TEST',
            'Urgencia': 'Alta',
            'Impacto': 'Masiva'
        }

        pm_record, errors = normalizePostmortemRecord(record)

        assert any('Unparseable' in e for e in errors)


class TestAllValidRecords:
    """Test validation of complete valid records."""

    def test_all_fields_valid(self):
        """Test record with all valid fields passes."""
        record = {
            'ID de incidencia': 'INC001',
            'Descripción': 'Test incident',
            'Estatus': 'Cerrada',
            'Fecha de envío': '01/05/2026 8:00 a',
            'Grupo asignado': 'SOP_TEST',
            'Urgencia': 'Alta',
            'Impacto': 'Masiva',
            'Fecha de notificación': '01/05/2026 9:00 a',
            'Fecha de última resolución': '01/05/2026 10:00 a'
        }

        pm_record, errors = normalizePostmortemRecord(record)

        # Should be valid with no errors
        assert pm_record.is_valid
        assert len(errors) == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
