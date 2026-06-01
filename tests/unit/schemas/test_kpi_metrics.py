#!/usr/bin/env python3
"""
Unit tests for PostmortemKPIMetrics aggregation.

Tests KPI initialization, record aggregation, and metric calculations.
"""

import pytest
from csv_to_json.postmortem_schemas import PostmortemKPIMetrics, PostmortemRecord


class TestKPIInitialization:
    """Test KPI metrics initialization."""

    def test_kpi_empty_initialization(self):
        """Test KPI metrics initialized with zero values."""
        kpis = PostmortemKPIMetrics()
        assert kpis.total == 0
        assert len(kpis.by_estatus) == 0
        assert len(kpis.by_urgencia) == 0
        assert len(kpis.by_impacto) == 0

    def test_kpi_dict_representation(self):
        """Test KPI metrics empty dict representation."""
        kpis = PostmortemKPIMetrics()
        result = kpis.to_dict()

        assert result['total'] == 0
        assert result['by_estatus'] == {}
        assert result['by_urgencia'] == {}
        assert result['by_impacto'] == {}


class TestKPIAggregation:
    """Test KPI metrics record aggregation."""

    def test_kpi_single_record_aggregation(self):
        """Test aggregating a single record."""
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

    def test_kpi_multiple_records_aggregation(self):
        """Test aggregating multiple records with different values."""
        kpis = PostmortemKPIMetrics()

        records = [
            PostmortemRecord({
                'Estatus': 'Cerrada',
                'Urgencia': 'Alta',
                'Impacto': 'Masiva'
            }),
            PostmortemRecord({
                'Estatus': 'Cerrada',
                'Urgencia': 'Media',
                'Impacto': 'Masiva'
            }),
            PostmortemRecord({
                'Estatus': 'En Progreso',
                'Urgencia': 'Alta',
                'Impacto': 'Parcial'
            })
        ]

        for record in records:
            kpis.add_record(record)

        assert kpis.total == 3
        assert kpis.by_estatus['Cerrada'] == 2
        assert kpis.by_estatus['En Progreso'] == 1
        assert kpis.by_urgencia['Alta'] == 2
        assert kpis.by_urgencia['Media'] == 1
        assert kpis.by_impacto['Masiva'] == 2
        assert kpis.by_impacto['Parcial'] == 1

    def test_kpi_duplicate_values_aggregation(self):
        """Test aggregating records with same values."""
        kpis = PostmortemKPIMetrics()

        # Same values repeated
        for _ in range(5):
            record = PostmortemRecord({
                'Estatus': 'Cerrada',
                'Urgencia': 'Alta',
                'Impacto': 'Masiva'
            })
            kpis.add_record(record)

        assert kpis.total == 5
        assert kpis.by_estatus['Cerrada'] == 5
        assert kpis.by_urgencia['Alta'] == 5
        assert kpis.by_impacto['Masiva'] == 5

    def test_kpi_many_unique_values(self):
        """Test aggregating with many unique values per dimension."""
        kpis = PostmortemKPIMetrics()

        estatus_values = ['Cerrada', 'En Progreso', 'Cancelada', 'En Espera']
        urgencia_values = ['Baja', 'Media', 'Alta', 'Crítica']
        impacto_values = ['Mínimo', 'Parcial', 'Masiva', 'Crítico']

        # Create records with all combinations (subset)
        for estatus in estatus_values:
            for urgencia in urgencia_values[:2]:  # Use only first 2 urgencias
                record = PostmortemRecord({
                    'Estatus': estatus,
                    'Urgencia': urgencia,
                    'Impacto': 'Masiva'
                })
                kpis.add_record(record)

        assert kpis.total == 8  # 4 estatus * 2 urgencias
        assert len(kpis.by_estatus) == 4
        assert len(kpis.by_urgencia) == 2
        assert all(count == 2 for count in kpis.by_estatus.values())


class TestKPIDictSerialization:
    """Test KPI metrics dict serialization for JSON output."""

    def test_kpi_to_dict_empty(self):
        """Test empty KPI metrics dict representation."""
        kpis = PostmortemKPIMetrics()
        result = kpis.to_dict()

        assert isinstance(result, dict)
        assert 'total' in result
        assert 'by_estatus' in result
        assert 'by_urgencia' in result
        assert 'by_impacto' in result
        assert result['total'] == 0

    def test_kpi_to_dict_with_data(self):
        """Test KPI metrics dict with aggregated data."""
        kpis = PostmortemKPIMetrics()
        record1 = PostmortemRecord({
            'Estatus': 'Cerrada',
            'Urgencia': 'Alta',
            'Impacto': 'Masiva'
        })
        record2 = PostmortemRecord({
            'Estatus': 'En Progreso',
            'Urgencia': 'Media',
            'Impacto': 'Parcial'
        })

        kpis.add_record(record1)
        kpis.add_record(record2)

        result = kpis.to_dict()

        assert result['total'] == 2
        assert result['by_estatus']['Cerrada'] == 1
        assert result['by_estatus']['En Progreso'] == 1
        assert result['by_urgencia']['Alta'] == 1
        assert result['by_urgencia']['Media'] == 1
        assert result['by_impacto']['Masiva'] == 1
        assert result['by_impacto']['Parcial'] == 1

    def test_kpi_dict_json_serializable(self):
        """Test KPI metrics dict is JSON serializable."""
        import json

        kpis = PostmortemKPIMetrics()
        for i in range(3):
            record = PostmortemRecord({
                'Estatus': 'Cerrada' if i < 2 else 'En Progreso',
                'Urgencia': 'Alta' if i < 2 else 'Media',
                'Impacto': 'Masiva'
            })
            kpis.add_record(record)

        result = kpis.to_dict()

        # Should be JSON serializable
        json_str = json.dumps(result)
        assert json_str is not None

        # Deserialize and verify
        deserialized = json.loads(json_str)
        assert deserialized['total'] == 3
        assert deserialized['by_estatus']['Cerrada'] == 2


class TestKPIEdgeCases:
    """Test KPI metrics edge cases."""

    def test_kpi_missing_fields_in_record(self):
        """Test KPI aggregation with missing field values."""
        kpis = PostmortemKPIMetrics()

        record = PostmortemRecord({
            'ID de incidencia': 'INC001'
            # Missing Estatus, Urgencia, Impacto
        })

        kpis.add_record(record)

        # Should count but categorize as Unknown
        assert kpis.total == 1
        assert 'Unknown' in kpis.by_estatus
        assert 'Unknown' in kpis.by_urgencia
        assert 'Unknown' in kpis.by_impacto

    def test_kpi_empty_field_values(self):
        """Test KPI aggregation with empty field values."""
        kpis = PostmortemKPIMetrics()

        record = PostmortemRecord({
            'Estatus': '',
            'Urgencia': '',
            'Impacto': ''
        })

        kpis.add_record(record)

        # Empty fields should not create dict entries
        assert kpis.total == 1
        assert len(kpis.by_estatus) == 0
        assert len(kpis.by_urgencia) == 0
        assert len(kpis.by_impacto) == 0

    def test_kpi_large_dataset(self):
        """Test KPI metrics with large number of records."""
        kpis = PostmortemKPIMetrics()

        # Simulate 1000 records
        for i in range(1000):
            estatus = 'Cerrada' if i % 2 == 0 else 'En Progreso'
            urgencia = ['Alta', 'Media', 'Baja'][i % 3]
            impacto = ['Masiva', 'Parcial', 'Mínimo'][i % 3]

            record = PostmortemRecord({
                'Estatus': estatus,
                'Urgencia': urgencia,
                'Impacto': impacto
            })
            kpis.add_record(record)

        assert kpis.total == 1000
        assert kpis.by_estatus['Cerrada'] == 500
        assert kpis.by_estatus['En Progreso'] == 500
        assert sum(kpis.by_urgencia.values()) == 1000
        assert sum(kpis.by_impacto.values()) == 1000

    def test_kpi_whitespace_handling(self):
        """Test KPI metrics with whitespace in field values."""
        kpis = PostmortemKPIMetrics()

        record1 = PostmortemRecord({
            'Estatus': '  Cerrada  ',  # Extra whitespace
            'Urgencia': 'Alta',
            'Impacto': 'Masiva'
        })
        record2 = PostmortemRecord({
            'Estatus': 'Cerrada',  # No whitespace
            'Urgencia': 'Alta',
            'Impacto': 'Masiva'
        })

        kpis.add_record(record1)
        kpis.add_record(record2)

        # Should count both regardless of whitespace
        assert kpis.total == 2
        # Note: Whitespace handling depends on normalization layer
        # This test documents expected behavior


class TestKPICalculationAccuracy:
    """Test KPI metrics calculation accuracy."""

    def test_kpi_totals_match_dimension_sums(self):
        """Test that total equals sum of any single dimension."""
        kpis = PostmortemKPIMetrics()

        records_data = [
            {'Estatus': 'Cerrada', 'Urgencia': 'Alta', 'Impacto': 'Masiva'},
            {'Estatus': 'Cerrada', 'Urgencia': 'Media', 'Impacto': 'Parcial'},
            {'Estatus': 'En Progreso', 'Urgencia': 'Alta', 'Impacto': 'Masiva'},
            {'Estatus': 'En Progreso', 'Urgencia': 'Baja', 'Impacto': 'Mínimo'},
            {'Estatus': 'Cancelada', 'Urgencia': 'Media', 'Impacto': 'Parcial'}
        ]

        for data in records_data:
            record = PostmortemRecord(data)
            kpis.add_record(record)

        # Total should match sum of any dimension
        estatus_sum = sum(kpis.by_estatus.values())
        urgencia_sum = sum(kpis.by_urgencia.values())
        impacto_sum = sum(kpis.by_impacto.values())

        assert kpis.total == 5
        assert estatus_sum == 5
        assert urgencia_sum == 5
        assert impacto_sum == 5


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
