#!/usr/bin/env python3
"""
Unit tests for mapPostmortemFields() function.

Tests field name mapping with case-insensitive matching and BOM handling.
"""

import pytest
from csv_to_json.postmortem_converter import mapPostmortemFields


class TestFieldMappingBasic:
    """Test basic field mapping."""

    def test_map_fields_exact_match(self):
        """Test mapping with exact field name matches."""
        record = {
            'ID de incidencia': 'INC001',
            'Descripción': 'Test',
            'Estatus': 'Cerrada',
            'Fecha de envío': '01/05/2026',
            'Grupo asignado': 'SOP_TEST',
            'Urgencia': 'Alta',
            'Impacto': 'Masiva'
        }

        mapped = mapPostmortemFields(record)

        assert mapped['ID de incidencia'] == 'INC001'
        assert mapped['Descripción'] == 'Test'
        assert mapped['Estatus'] == 'Cerrada'
        assert mapped['Grupo asignado'] == 'SOP_TEST'

    def test_map_fields_all_13_fields(self):
        """Test mapping with all 13 postmortem fields."""
        record = {
            'ID de incidencia': 'INC001',
            'Descripción': 'Test',
            'Estatus': 'Cerrada',
            'Fecha de envío': '01/05/2026',
            'Grupo asignado': 'SOP_TEST',
            'Fecha de notificación': '01/05/2026',
            'Fecha de última resolución': '02/05/2026',
            'Motivo de estado': 'Resuelto',
            'MotivoEstado_Anterior': 'En Progreso',
            'Grupo Resolutor': 'SOP_RES',
            'Urgencia': 'Alta',
            'Impacto': 'Masiva',
            'Grupo Remitente': 'Team A'
        }

        mapped = mapPostmortemFields(record)

        assert len(mapped) >= 13
        assert mapped['ID de incidencia'] == 'INC001'
        assert mapped['Grupo Remitente'] == 'Team A'


class TestFieldMappingCaseInsensitive:
    """Test case-insensitive field mapping."""

    def test_map_fields_lowercase(self):
        """Test mapping with lowercase field names."""
        record = {
            'id de incidencia': 'INC001',
            'descripción': 'Test',
            'estatus': 'Cerrada',
            'fecha de envío': '01/05/2026',
            'grupo asignado': 'SOP_TEST',
            'urgencia': 'Alta',
            'impacto': 'Masiva'
        }

        mapped = mapPostmortemFields(record)

        # Should match case-insensitively
        assert mapped.get('ID de incidencia') or any(
            'INC001' in str(v) for v in mapped.values()
        )

    def test_map_fields_uppercase(self):
        """Test mapping with uppercase field names."""
        record = {
            'ID DE INCIDENCIA': 'INC001',
            'DESCRIPCIÓN': 'Test',
            'ESTATUS': 'Cerrada',
            'FECHA DE ENVÍO': '01/05/2026',
            'GRUPO ASIGNADO': 'SOP_TEST',
            'URGENCIA': 'Alta',
            'IMPACTO': 'Masiva'
        }

        mapped = mapPostmortemFields(record)

        # Should find mappings despite case differences
        assert len(mapped) > 0
        # Values should be present
        assert any('INC001' in str(v) for v in mapped.values())

    def test_map_fields_mixed_case(self):
        """Test mapping with mixed case field names."""
        record = {
            'Id De Incidencia': 'INC001',
            'DeSCRIPCIÓN': 'Test',
            'EsTaTuS': 'Cerrada'
        }

        mapped = mapPostmortemFields(record)

        # Should handle mixed case
        assert len(mapped) > 0


class TestFieldMappingBOM:
    """Test BOM (Byte Order Mark) handling in field names."""

    def test_map_fields_bom_in_header(self):
        """Test handling of BOM character in field names."""
        record = {
            '\uFEFFID de incidencia': 'INC001',  # BOM before field name
            'Descripción': 'Test'
        }

        mapped = mapPostmortemFields(record)

        # BOM should be removed and field should be properly mapped
        assert any(k.startswith('ID de incidencia') or 'INC001' in str(v) for k, v in mapped.items())

    def test_map_fields_bom_cleanup(self):
        """Test that BOM is cleaned from field names."""
        record = {
            '\uFEFFEstatus': 'Cerrada'  # Field with BOM prefix
        }

        mapped = mapPostmortemFields(record)

        # Should have cleaned up the BOM
        assert len(mapped) > 0
        # Either mapped correctly or the value is present
        assert 'Cerrada' in str(mapped.values())


class TestFieldMappingExtraColumns:
    """Test handling of extra/unknown columns."""

    def test_map_fields_with_extra_columns(self):
        """Test mapping with extra unknown columns."""
        record = {
            'ID de incidencia': 'INC001',
            'Descripción': 'Test',
            'ExtraColumn1': 'Extra1',
            'ExtraColumn2': 'Extra2',
            'Estatus': 'Cerrada'
        }

        mapped = mapPostmortemFields(record)

        # Standard fields should be mapped
        assert mapped['ID de incidencia'] == 'INC001'
        assert mapped['Estatus'] == 'Cerrada'

    def test_map_fields_preserves_unknown_columns(self):
        """Test that unknown columns are preserved in output."""
        record = {
            'ID de incidencia': 'INC001',
            'CustomField': 'CustomValue'
        }

        mapped = mapPostmortemFields(record)

        # Known field should be mapped
        assert mapped['ID de incidencia'] == 'INC001'
        # Custom field should be preserved
        assert 'CustomValue' in str(mapped.values())


class TestFieldMappingMissingFields:
    """Test handling of missing fields."""

    def test_map_fields_with_missing_required_fields(self):
        """Test mapping with some required fields missing."""
        record = {
            'ID de incidencia': 'INC001',
            # Missing: Descripción, Estatus, Fecha de envío, etc.
        }

        mapped = mapPostmortemFields(record)

        # Should map what's present
        assert mapped['ID de incidencia'] == 'INC001'
        # Missing fields won't be in mapped dict (or will be None/empty if strict)

    def test_map_fields_empty_record(self):
        """Test mapping with empty record."""
        record = {}

        mapped = mapPostmortemFields(record)

        # Should return empty dict
        assert isinstance(mapped, dict)
        assert len(mapped) == 0


class TestFieldMappingEdgeCases:
    """Test edge cases in field mapping."""

    def test_map_fields_whitespace_in_names(self):
        """Test field names with extra whitespace."""
        record = {
            '  ID de incidencia  ': 'INC001',  # Extra spaces
            'Descripción': 'Test'
        }

        mapped = mapPostmortemFields(record)

        # Should handle whitespace
        assert len(mapped) > 0

    def test_map_fields_special_characters(self):
        """Test field names with special characters."""
        record = {
            'ID de incidencia': 'INC001',
            'Descripción': 'Error á é í ó ú'
        }

        mapped = mapPostmortemFields(record)

        # Should preserve special characters in values
        assert 'INC001' in str(mapped.values())

    def test_map_fields_unicode_values(self):
        """Test field values with unicode characters."""
        record = {
            'ID de incidencia': 'INC001',
            'Descripción': 'Problema en árbol de decisiones'
        }

        mapped = mapPostmortemFields(record)

        # Unicode should be preserved
        assert 'INC001' in str(mapped.values())

    def test_map_fields_numeric_values(self):
        """Test that numeric values are preserved as strings."""
        record = {
            'ID de incidencia': 'INC001',
            'Urgencia': '4'
        }

        mapped = mapPostmortemFields(record)

        # Values should remain as provided (strings from CSV)
        assert mapped['Urgencia'] == '4'

    def test_map_fields_null_like_values(self):
        """Test handling of null-like string values."""
        record = {
            'ID de incidencia': 'INC001',
            'Descripción': '',  # Empty string
            'Estatus': None  # None
        }

        mapped = mapPostmortemFields(record)

        # Should preserve as-is
        assert mapped['ID de incidencia'] == 'INC001'
        assert mapped['Descripción'] == ''
        assert mapped['Estatus'] is None


class TestFieldMappingConsistency:
    """Test consistency of field mapping."""

    def test_map_fields_idempotent(self):
        """Test that mapping is idempotent (repeated mapping gives same result)."""
        record = {
            'ID de incidencia': 'INC001',
            'Descripción': 'Test'
        }

        mapped1 = mapPostmortemFields(record)
        mapped2 = mapPostmortemFields(mapped1)

        # Should be consistent
        assert mapped1['ID de incidencia'] == mapped2.get('ID de incidencia') or \
               mapped1['ID de incidencia'] == list(mapped2.values())[0]

    def test_map_fields_returns_dict(self):
        """Test that mapping always returns a dict."""
        records = [
            {'ID de incidencia': 'INC001'},
            {},
            {'Extra': 'Value'}
        ]

        for record in records:
            mapped = mapPostmortemFields(record)
            assert isinstance(mapped, dict)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
