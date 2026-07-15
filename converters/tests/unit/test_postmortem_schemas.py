#!/usr/bin/env python3
"""
Unit tests for postmortem schema definitions.

Tests PostmortemRecord, KPIMetrics, Metadata, and ValidationError classes.
"""

import pytest
from datetime import datetime
from csv_to_json.postmortem_schemas import (
    PostmortemRecord,
    PostmortemKPIMetrics,
    ConversionMetadata,
    ValidationError
)


class TestPostmortemRecord:
    """Test PostmortemRecord schema and validation."""

    def test_record_creation(self):
        """Test creating a basic postmortem record."""
        data = {
            'ID de incidencia': 'INC001',
            'Descripción': 'Test incident',
            'Estatus': 'Cerrada',
            'Fecha de envío': '01/05/2026',
            'Grupo asignado': 'Team A',
            'Urgencia': 'Alta',
            'Impacto': 'Masiva'
        }
        record = PostmortemRecord(data)
        assert record.data == data
        assert record.is_valid is True

    def test_record_validation_required_fields(self):
        """Test validation of required fields."""
        # Missing required field
        data = {
            'ID de incidencia': 'INC001',
            'Descripción': 'Test',
            # Missing: Estatus, Fecha de envío, Grupo asignado, Urgencia, Impacto
        }
        record = PostmortemRecord(data)
        assert record.validate() is False
        assert len(record.errors) > 0

    def test_record_validation_empty_required_field(self):
        """Test validation fails for empty required fields."""
        data = {
            'ID de incidencia': 'INC001',
            'Descripción': 'Test',
            'Estatus': '',  # Empty string
            'Fecha de envío': '01/05/2026',
            'Grupo asignado': 'Team A',
            'Urgencia': 'Alta',
            'Impacto': 'Masiva'
        }
        record = PostmortemRecord(data)
        assert record.validate() is False

    def test_record_to_dict(self):
        """Test converting record to dictionary."""
        data = {
            'ID de incidencia': 'INC001',
            'Descripción': 'Test incident',
            'Estatus': 'Cerrada'
        }
        record = PostmortemRecord(data)
        result = record.to_dict()
        assert result == data


class TestPostmortemKPIMetrics:
    """Test KPI metrics aggregation."""

    def test_kpi_creation(self):
        """Test creating KPI metrics object."""
        kpis = PostmortemKPIMetrics()
        assert kpis.total == 0
        assert len(kpis.by_estatus) == 0
        assert len(kpis.by_urgencia) == 0
        assert len(kpis.by_impacto) == 0

    def test_kpi_add_record(self):
        """Test adding records to KPI aggregates."""
        kpis = PostmortemKPIMetrics()
        record = PostmortemRecord({
            'ID de incidencia': 'INC001',
            'Estatus': 'Cerrada',
            'Urgencia': 'Alta',
            'Impacto': 'Masiva'
        })
        kpis.add_record(record)
        assert kpis.total == 1
        assert kpis.by_estatus['Cerrada'] == 1
        assert kpis.by_urgencia['Alta'] == 1
        assert kpis.by_impacto['Masiva'] == 1

    def test_kpi_multiple_records(self):
        """Test aggregating multiple records."""
        kpis = PostmortemKPIMetrics()
        for i in range(3):
            record = PostmortemRecord({
                'Estatus': 'Cerrada' if i < 2 else 'En Progreso',
                'Urgencia': 'Alta' if i < 2 else 'Media',
                'Impacto': 'Masiva'
            })
            kpis.add_record(record)

        assert kpis.total == 3
        assert kpis.by_estatus['Cerrada'] == 2
        assert kpis.by_estatus['En Progreso'] == 1
        assert kpis.by_urgencia['Alta'] == 2
        assert kpis.by_urgencia['Media'] == 1
        assert kpis.by_impacto['Masiva'] == 3

    def test_kpi_to_dict(self):
        """Test converting KPIs to dictionary."""
        kpis = PostmortemKPIMetrics()
        record = PostmortemRecord({'Estatus': 'Cerrada', 'Urgencia': 'Alta', 'Impacto': 'Media'})
        kpis.add_record(record)

        result = kpis.to_dict()
        assert result['total'] == 1
        assert result['by_estatus']['Cerrada'] == 1
        assert result['by_urgencia']['Alta'] == 1
        assert result['by_impacto']['Media'] == 1


class TestConversionMetadata:
    """Test conversion metadata generation."""

    def test_metadata_creation(self):
        """Test creating metadata object."""
        kpis = PostmortemKPIMetrics()
        metadata = ConversionMetadata('test.csv', 100, kpis)

        assert metadata.type == 'postmortem'
        assert metadata.version == '1.0'
        assert metadata.source_filename == 'test.csv'
        assert metadata.record_count == 100

    def test_metadata_timestamp_format(self):
        """Test metadata timestamp is ISO 8601 format."""
        kpis = PostmortemKPIMetrics()
        metadata = ConversionMetadata('test.csv', 100, kpis)

        # Should be valid ISO 8601 format with Z suffix
        assert metadata.created.endswith('Z')
        # Should be parseable as datetime
        datetime.fromisoformat(metadata.created.replace('Z', '+00:00'))

    def test_metadata_to_dict(self):
        """Test converting metadata to dictionary."""
        kpis = PostmortemKPIMetrics()
        record = PostmortemRecord({'Estatus': 'Cerrada', 'Urgencia': 'Alta', 'Impacto': 'Media'})
        kpis.add_record(record)

        metadata = ConversionMetadata('test.csv', 1, kpis)
        result = metadata.to_dict()

        assert result['type'] == 'postmortem'
        assert result['version'] == '1.0'
        assert result['source_filename'] == 'test.csv'
        assert result['record_count'] == 1
        assert 'kpis' in result
        assert result['kpis']['total'] == 1

    def test_metadata_with_release_name(self):
        """Test that release_name is included in to_dict() when provided."""
        kpis = PostmortemKPIMetrics()
        metadata = ConversionMetadata('test.csv', 0, kpis, release_name='2026R6-MESA')

        assert metadata.release_name == '2026R6-MESA'
        result = metadata.to_dict()
        assert result['release_name'] == '2026R6-MESA'

    def test_metadata_without_release_name(self):
        """Test that release_name defaults to None when not provided (backward compatibility)."""
        kpis = PostmortemKPIMetrics()
        metadata = ConversionMetadata('test.csv', 0, kpis)

        assert metadata.release_name is None
        result = metadata.to_dict()
        assert result['release_name'] is None


class TestValidationError:
    """Test validation error tracking."""

    def test_error_creation(self):
        """Test creating validation error."""
        error = ValidationError(23, 'INC000023')
        assert error.row == 23
        assert error.record_id == 'INC000023'
        assert error.error_type == 'validation'
        assert len(error.issues) == 0

    def test_error_add_issue(self):
        """Test adding issues to error."""
        error = ValidationError(23, 'INC000023')
        error.add_issue('Fecha de envío', 'Unparseable date format')
        error.add_issue('Urgencia', 'Invalid value Desconocida', 'Desconocida')

        assert len(error.issues) == 2
        assert error.issues[0]['field'] == 'Fecha de envío'
        assert error.issues[1]['value'] == 'Desconocida'

    def test_error_to_dict(self):
        """Test converting error to dictionary."""
        error = ValidationError(23)
        error.add_issue('Estatus', 'Missing required field')

        result = error.to_dict()
        assert result['row'] == 23
        assert result['error_type'] == 'validation'
        assert len(result['issues']) == 1
        assert result['issues'][0]['field'] == 'Estatus'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
