#!/usr/bin/env python3
"""
Unit tests for Estatus field normalization.

Tests normalization to title case for Estatus, Urgencia, and Impacto fields.
"""

import pytest
from csv_to_json.postmortem_converter import normalizePostmortemRecord
from csv_to_json.postmortem_schemas import PostmortemRecord


class TestEstatusNormalizationCases:
    """Test Estatus normalization to title case."""

    def test_estatus_lowercase_to_title(self):
        """Test lowercase Estatus normalized to title case."""
        record = {
            'ID de incidencia': 'INC001',
            'Descripción': 'Test',
            'Estatus': 'cerrada',
            'Fecha de envío': '01/05/2026 8:00 a',
            'Grupo asignado': 'SOP_TEST',
            'Urgencia': 'Alta',
            'Impacto': 'Masiva'
        }

        pm_record, _ = normalizePostmortemRecord(record)

        assert pm_record.data['Estatus'] == 'Cerrada'

    def test_estatus_uppercase_to_title(self):
        """Test uppercase Estatus normalized to title case."""
        record = {
            'ID de incidencia': 'INC001',
            'Descripción': 'Test',
            'Estatus': 'CERRADA',
            'Fecha de envío': '01/05/2026 8:00 a',
            'Grupo asignado': 'SOP_TEST',
            'Urgencia': 'Alta',
            'Impacto': 'Masiva'
        }

        pm_record, _ = normalizePostmortemRecord(record)

        assert pm_record.data['Estatus'] == 'Cerrada'

    def test_estatus_mixed_case_to_title(self):
        """Test mixed case Estatus normalized to title case."""
        record = {
            'ID de incidencia': 'INC001',
            'Descripción': 'Test',
            'Estatus': 'eN pRoGrEsO',
            'Fecha de envío': '01/05/2026 8:00 a',
            'Grupo asignado': 'SOP_TEST',
            'Urgencia': 'Alta',
            'Impacto': 'Masiva'
        }

        pm_record, _ = normalizePostmortemRecord(record)

        assert pm_record.data['Estatus'] == 'En Progreso'

    def test_estatus_already_title_case(self):
        """Test already-normalized Estatus unchanged."""
        record = {
            'ID de incidencia': 'INC001',
            'Descripción': 'Test',
            'Estatus': 'Cerrada',
            'Fecha de envío': '01/05/2026 8:00 a',
            'Grupo asignado': 'SOP_TEST',
            'Urgencia': 'Alta',
            'Impacto': 'Masiva'
        }

        pm_record, _ = normalizePostmortemRecord(record)

        assert pm_record.data['Estatus'] == 'Cerrada'

    def test_urgencia_normalization(self):
        """Test Urgencia field normalization."""
        record = {
            'ID de incidencia': 'INC001',
            'Descripción': 'Test',
            'Estatus': 'Cerrada',
            'Fecha de envío': '01/05/2026 8:00 a',
            'Grupo asignado': 'SOP_TEST',
            'Urgencia': 'crítica',
            'Impacto': 'Masiva'
        }

        pm_record, _ = normalizePostmortemRecord(record)

        assert pm_record.data['Urgencia'] == 'Crítica'

    def test_impacto_normalization(self):
        """Test Impacto field normalization."""
        record = {
            'ID de incidencia': 'INC001',
            'Descripción': 'Test',
            'Estatus': 'Cerrada',
            'Fecha de envío': '01/05/2026 8:00 a',
            'Grupo asignado': 'SOP_TEST',
            'Urgencia': 'Alta',
            'Impacto': 'crítico'
        }

        pm_record, _ = normalizePostmortemRecord(record)

        assert pm_record.data['Impacto'] == 'Crítico'

    def test_multiple_word_estatus_normalization(self):
        """Test multi-word Estatus normalization."""
        record = {
            'ID de incidencia': 'INC001',
            'Descripción': 'Test',
            'Estatus': 'en espera',
            'Fecha de envío': '01/05/2026 8:00 a',
            'Grupo asignado': 'SOP_TEST',
            'Urgencia': 'Alta',
            'Impacto': 'Masiva'
        }

        pm_record, _ = normalizePostmortemRecord(record)

        # Should be title-cased
        assert pm_record.data['Estatus'] == 'En Espera'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
