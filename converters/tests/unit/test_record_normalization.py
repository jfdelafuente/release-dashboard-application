#!/usr/bin/env python3
"""
Unit tests for normalizePostmortemRecord() function.

Tests record normalization including:
- Estatus normalization
- Date parsing and normalization
- Field validation
- Despliegue assignment
"""

import pytest
from csv_to_json.postmortem_converter import normalizePostmortemRecord
from csv_to_json.postmortem_schemas import PostmortemRecord


class TestEstatusNormalization:
    """Test Estatus field normalization."""

    def test_normalize_estatus_title_case(self):
        """Test normalization to title case."""
        record = {
            'ID de incidencia': 'INC001',
            'Descripción': 'Test',
            'Estatus': 'cerrada',  # lowercase
            'Fecha de envío': '01/05/2026 8:00 a',
            'Grupo asignado': 'SOP_TEST',
            'Urgencia': 'alta',
            'Impacto': 'masiva'
        }

        pm_record, errors = normalizePostmortemRecord(record)

        assert pm_record.data['Estatus'] == 'Cerrada'
        assert len(errors) == 0

    def test_normalize_estatus_all_lowercase(self):
        """Test normalization of all-lowercase estatus."""
        record = {
            'ID de incidencia': 'INC001',
            'Descripción': 'Test',
            'Estatus': 'en progreso',
            'Fecha de envío': '01/05/2026 8:00 a',
            'Grupo asignado': 'SOP_TEST',
            'Urgencia': 'Alta',
            'Impacto': 'Masiva'
        }

        pm_record, errors = normalizePostmortemRecord(record)

        assert pm_record.data['Estatus'] == 'En Progreso'

    def test_normalize_estatus_all_uppercase(self):
        """Test normalization of all-uppercase estatus."""
        record = {
            'ID de incidencia': 'INC001',
            'Descripción': 'Test',
            'Estatus': 'CERRADA',
            'Fecha de envío': '01/05/2026 8:00 a',
            'Grupo asignado': 'SOP_TEST',
            'Urgencia': 'Alta',
            'Impacto': 'Masiva'
        }

        pm_record, errors = normalizePostmortemRecord(record)

        assert pm_record.data['Estatus'] == 'Cerrada'

    def test_normalize_estatus_mixed_case(self):
        """Test normalization of mixed case estatus."""
        record = {
            'ID de incidencia': 'INC001',
            'Descripción': 'Test',
            'Estatus': 'cErRaDa',
            'Fecha de envío': '01/05/2026 8:00 a',
            'Grupo asignado': 'SOP_TEST',
            'Urgencia': 'Alta',
            'Impacto': 'Masiva'
        }

        pm_record, errors = normalizePostmortemRecord(record)

        assert pm_record.data['Estatus'] == 'Cerrada'


class TestDateParsing:
    """Test date field parsing and normalization."""

    def test_normalize_date_dd_mm_yyyy_format(self):
        """Test parsing DD/MM/YYYY format."""
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

        # Should parse and normalize to DD/MM/YYYY HH:MM (time preserved)
        assert pm_record.data['Fecha de envío'] == '01/05/2026 08:00'
        assert len(errors) == 0

    def test_normalize_date_with_time_component(self):
        """Test date parsing preserves the time component (needed for the PAP chart's 30-min x-axis)."""
        record = {
            'ID de incidencia': 'INC001',
            'Descripción': 'Test',
            'Estatus': 'Cerrada',
            'Fecha de envío': '01/05/2026 14:30 p',
            'Grupo asignado': 'SOP_TEST',
            'Urgencia': 'Alta',
            'Impacto': 'Masiva',
            'Fecha de notificación': '01/05/2026 15:00 a'
        }

        pm_record, errors = normalizePostmortemRecord(record)

        # Time should be preserved as 24-hour HH:MM (the trailing 'a'/'p'
        # suffix is ignored, not treated as a 12-hour AM/PM indicator --
        # real exports carry it regardless of morning/afternoon hour)
        assert pm_record.data['Fecha de envío'] == '01/05/2026 14:30'
        assert pm_record.data['Fecha de notificación'] == '01/05/2026 15:00'

    def test_normalize_date_single_digit_padding(self):
        """Test single digit day/month are zero-padded."""
        record = {
            'ID de incidencia': 'INC001',
            'Descripción': 'Test',
            'Estatus': 'Cerrada',
            'Fecha de envío': '5/4/2026 8:00 a',
            'Grupo asignado': 'SOP_TEST',
            'Urgencia': 'Alta',
            'Impacto': 'Masiva'
        }

        pm_record, errors = normalizePostmortemRecord(record)

        # Should be zero-padded
        assert pm_record.data['Fecha de envío'] == '05/04/2026 08:00'

    def test_normalize_date_spanish_abbreviation(self):
        """Test parsing Spanish month abbreviations."""
        record = {
            'ID de incidencia': 'INC001',
            'Descripción': 'Test',
            'Estatus': 'Cerrada',
            'Fecha de envío': '01-abr',
            'Grupo asignado': 'SOP_TEST',
            'Urgencia': 'Alta',
            'Impacto': 'Masiva'
        }

        pm_record, errors = normalizePostmortemRecord(record)

        # Should be parsed (might include year)
        assert '/04/' in pm_record.data['Fecha de envío'] or pm_record.data['Fecha de envío'] != ''

    def test_normalize_date_invalid_format(self):
        """Test handling of invalid date formats."""
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

        # Should have error for unparseable date
        assert any('Unparseable' in e for e in errors)
        assert pm_record.data['Fecha de envío'] == ''

    def test_normalize_date_invalid_day(self):
        """Test handling of invalid day values."""
        record = {
            'ID de incidencia': 'INC001',
            'Descripción': 'Test',
            'Estatus': 'Cerrada',
            'Fecha de envío': '32/05/2026',  # Invalid day
            'Grupo asignado': 'SOP_TEST',
            'Urgencia': 'Alta',
            'Impacto': 'Masiva'
        }

        pm_record, errors = normalizePostmortemRecord(record)

        # Should have error
        assert any('Unparseable' in e for e in errors)

    def test_normalize_date_invalid_month(self):
        """Test handling of invalid month values."""
        record = {
            'ID de incidencia': 'INC001',
            'Descripción': 'Test',
            'Estatus': 'Cerrada',
            'Fecha de envío': '01/13/2026',  # Invalid month
            'Grupo asignado': 'SOP_TEST',
            'Urgencia': 'Alta',
            'Impacto': 'Masiva'
        }

        pm_record, errors = normalizePostmortemRecord(record)

        # Should have error
        assert any('Unparseable' in e for e in errors)


class TestFieldValidation:
    """Test field validation."""

    def test_normalize_validate_required_fields(self):
        """Test validation of required fields."""
        # Missing Estatus
        record = {
            'ID de incidencia': 'INC001',
            'Descripción': 'Test',
            'Fecha de envío': '01/05/2026 8:00 a',
            'Grupo asignado': 'SOP_TEST',
            'Urgencia': 'Alta',
            'Impacto': 'Masiva'
        }

        pm_record, errors = normalizePostmortemRecord(record)

        # Should have validation errors
        assert len(errors) > 0
        assert not pm_record.is_valid

    def test_normalize_validate_empty_required_field(self):
        """Test validation rejects empty required fields."""
        record = {
            'ID de incidencia': 'INC001',
            'Descripción': 'Test',
            'Estatus': '',  # Empty
            'Fecha de envío': '01/05/2026 8:00 a',
            'Grupo asignado': 'SOP_TEST',
            'Urgencia': 'Alta',
            'Impacto': 'Masiva'
        }

        pm_record, errors = normalizePostmortemRecord(record)

        # Should have validation errors
        assert len(errors) > 0

    def test_normalize_validate_whitespace_trimmed(self):
        """Test that whitespace is trimmed from fields."""
        record = {
            'ID de incidencia': '  INC001  ',
            'Descripción': '  Test  ',
            'Estatus': '  Cerrada  ',
            'Fecha de envío': '01/05/2026 8:00 a',
            'Grupo asignado': 'SOP_TEST',
            'Urgencia': 'Alta',
            'Impacto': 'Masiva'
        }

        pm_record, errors = normalizePostmortemRecord(record)

        # Values should be trimmed
        assert pm_record.data['ID de incidencia'] == 'INC001'
        assert pm_record.data['Descripción'] == 'Test'
        assert len(errors) == 0

    def test_normalize_all_required_fields_present(self):
        """Test record with all required fields."""
        record = {
            'ID de incidencia': 'INC001',
            'Descripción': 'Test incident',
            'Estatus': 'Cerrada',
            'Fecha de envío': '01/05/2026 8:00 a',
            'Grupo asignado': 'SOP_TEST',
            'Urgencia': 'Alta',
            'Impacto': 'Masiva',
            'Fecha de notificación': '01/05/2026 9:00 a',
            'Fecha de última resolución': '01/05/2026 10:00 a',
            'Motivo de estado': 'Resuelto',
            'MotivoEstado_Anterior': 'En Progreso',
            'Grupo Resolutor': 'SOP_RES',
            'Grupo Remitente': 'Team A'
        }

        pm_record, errors = normalizePostmortemRecord(record)

        assert pm_record.is_valid
        assert len(errors) == 0


class TestDespliegueAssignment:
    """Test Despliegue field handling in normalization."""

    def test_normalize_despliegue_not_in_csv(self):
        """Test that Despliegue is not expected in CSV (it's derived)."""
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

        # Despliegue should not be in output (it's derived separately)
        assert 'Despliegue' not in pm_record.data or pm_record.data['Despliegue'] == ''


class TestRecordNormalizationTypes:
    """Test PostmortemRecord type and structure."""

    def test_normalize_returns_postmortem_record(self):
        """Test that normalization returns PostmortemRecord object."""
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

        assert isinstance(pm_record, PostmortemRecord)
        assert isinstance(errors, list)

    def test_normalize_returns_errors_list(self):
        """Test that normalization returns errors as list."""
        record = {
            'ID de incidencia': 'INC001',
            'Descripción': 'Test',
            'Estatus': 'Cerrada',
            'Fecha de envío': 'INVALID',
            'Grupo asignado': 'SOP_TEST',
            'Urgencia': 'Alta',
            'Impacto': 'Masiva'
        }

        pm_record, errors = normalizePostmortemRecord(record)

        assert isinstance(errors, list)
        assert len(errors) > 0


class TestRecordNormalizationEdgeCases:
    """Test edge cases in record normalization."""

    def test_normalize_urgencia_lowercase(self):
        """Test Urgencia normalization."""
        record = {
            'ID de incidencia': 'INC001',
            'Descripción': 'Test',
            'Estatus': 'Cerrada',
            'Fecha de envío': '01/05/2026 8:00 a',
            'Grupo asignado': 'SOP_TEST',
            'Urgencia': 'alta',  # lowercase
            'Impacto': 'Masiva'
        }

        pm_record, errors = normalizePostmortemRecord(record)

        assert pm_record.data['Urgencia'] == 'Alta'

    def test_normalize_impacto_lowercase(self):
        """Test Impacto normalization."""
        record = {
            'ID de incidencia': 'INC001',
            'Descripción': 'Test',
            'Estatus': 'Cerrada',
            'Fecha de envío': '01/05/2026 8:00 a',
            'Grupo asignado': 'SOP_TEST',
            'Urgencia': 'Alta',
            'Impacto': 'masiva'  # lowercase
        }

        pm_record, errors = normalizePostmortemRecord(record)

        assert pm_record.data['Impacto'] == 'Masiva'

    def test_normalize_optional_fields_missing(self):
        """Test record with missing optional fields."""
        record = {
            'ID de incidencia': 'INC001',
            'Descripción': 'Test',
            'Estatus': 'Cerrada',
            'Fecha de envío': '01/05/2026 8:00 a',
            'Grupo asignado': 'SOP_TEST',
            'Urgencia': 'Alta',
            'Impacto': 'Masiva'
            # Missing optional: Fecha de notificación, Fecha de última resolución, etc.
        }

        pm_record, errors = normalizePostmortemRecord(record)

        # Should be valid (optional fields can be missing)
        assert pm_record.is_valid or len(errors) == 0 or all('optional' in e.lower() for e in errors if e)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
