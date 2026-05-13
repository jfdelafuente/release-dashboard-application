#!/usr/bin/env python3
"""
Unit tests for KPI calculation in postmortem conversion.

Tests KPI structure initialization and aggregation during file processing.
"""

import pytest
from csv_to_json.postmortem_schemas import PostmortemKPIMetrics, PostmortemRecord


class TestKPICalculation:
    """Test KPI calculation from postmortem records."""

    def test_kpi_empty_dataset(self):
        """Test KPI calculation with empty dataset."""
        kpis = PostmortemKPIMetrics()

        result = kpis.to_dict()

        assert result['total'] == 0
        assert result['by_estatus'] == {}
        assert result['by_urgencia'] == {}
        assert result['by_impacto'] == {}

    def test_kpi_single_record(self):
        """Test KPI calculation with single record."""
        kpis = PostmortemKPIMetrics()
        record = PostmortemRecord({
            'Estatus': 'Cerrada',
            'Urgencia': 'Alta',
            'Impacto': 'Masiva'
        })

        kpis.add_record(record)
        result = kpis.to_dict()

        assert result['total'] == 1
        assert result['by_estatus']['Cerrada'] == 1
        assert result['by_urgencia']['Alta'] == 1
        assert result['by_impacto']['Masiva'] == 1

    def test_kpi_multiple_records_aggregation(self):
        """Test KPI aggregation with multiple records."""
        kpis = PostmortemKPIMetrics()

        for i in range(10):
            record = PostmortemRecord({
                'Estatus': 'Cerrada' if i % 2 == 0 else 'En Progreso',
                'Urgencia': 'Alta' if i < 5 else 'Media',
                'Impacto': 'Masiva'
            })
            kpis.add_record(record)

        result = kpis.to_dict()

        assert result['total'] == 10
        assert result['by_estatus']['Cerrada'] == 5
        assert result['by_estatus']['En Progreso'] == 5
        assert result['by_urgencia']['Alta'] == 5
        assert result['by_urgencia']['Media'] == 5
        assert result['by_impacto']['Masiva'] == 10

    def test_kpi_by_estatus_aggregation(self):
        """Test KPI aggregation by Estatus."""
        kpis = PostmortemKPIMetrics()

        estatus_values = ['Cerrada', 'En Progreso', 'Cancelada']
        for _ in range(3):
            for estatus in estatus_values:
                record = PostmortemRecord({
                    'Estatus': estatus,
                    'Urgencia': 'Alta',
                    'Impacto': 'Masiva'
                })
                kpis.add_record(record)

        result = kpis.to_dict()

        assert result['total'] == 9
        assert result['by_estatus']['Cerrada'] == 3
        assert result['by_estatus']['En Progreso'] == 3
        assert result['by_estatus']['Cancelada'] == 3

    def test_kpi_by_urgencia_aggregation(self):
        """Test KPI aggregation by Urgencia."""
        kpis = PostmortemKPIMetrics()

        urgencia_values = ['Baja', 'Media', 'Alta', 'Crítica']
        for _ in range(2):
            for urgencia in urgencia_values:
                record = PostmortemRecord({
                    'Estatus': 'Cerrada',
                    'Urgencia': urgencia,
                    'Impacto': 'Masiva'
                })
                kpis.add_record(record)

        result = kpis.to_dict()

        assert result['total'] == 8
        for urgencia in urgencia_values:
            assert result['by_urgencia'][urgencia] == 2

    def test_kpi_by_impacto_aggregation(self):
        """Test KPI aggregation by Impacto."""
        kpis = PostmortemKPIMetrics()

        impacto_values = ['Mínimo', 'Parcial', 'Masiva', 'Crítico']
        for _ in range(3):
            for impacto in impacto_values:
                record = PostmortemRecord({
                    'Estatus': 'Cerrada',
                    'Urgencia': 'Alta',
                    'Impacto': impacto
                })
                kpis.add_record(record)

        result = kpis.to_dict()

        assert result['total'] == 12
        for impacto in impacto_values:
            assert result['by_impacto'][impacto] == 3

    def test_kpi_mixed_values_distribution(self):
        """Test KPI with mixed values distribution."""
        kpis = PostmortemKPIMetrics()

        records_data = [
            {'Estatus': 'Cerrada', 'Urgencia': 'Alta', 'Impacto': 'Masiva'},
            {'Estatus': 'Cerrada', 'Urgencia': 'Media', 'Impacto': 'Parcial'},
            {'Estatus': 'En Progreso', 'Urgencia': 'Alta', 'Impacto': 'Masiva'},
            {'Estatus': 'Cancelada', 'Urgencia': 'Baja', 'Impacto': 'Mínimo'},
            {'Estatus': 'Cerrada', 'Urgencia': 'Crítica', 'Impacto': 'Crítico'},
        ]

        for data in records_data:
            record = PostmortemRecord(data)
            kpis.add_record(record)

        result = kpis.to_dict()

        assert result['total'] == 5
        assert result['by_estatus']['Cerrada'] == 3
        assert result['by_urgencia']['Alta'] == 2
        assert result['by_impacto']['Masiva'] == 2

    def test_kpi_100_records(self):
        """Test KPI calculation with 100 records (realistic scenario)."""
        kpis = PostmortemKPIMetrics()

        for i in range(100):
            record = PostmortemRecord({
                'Estatus': ['Cerrada', 'En Progreso', 'Cancelada'][i % 3],
                'Urgencia': ['Baja', 'Media', 'Alta', 'Crítica'][i % 4],
                'Impacto': ['Mínimo', 'Parcial', 'Masiva', 'Crítico'][i % 4]
            })
            kpis.add_record(record)

        result = kpis.to_dict()

        assert result['total'] == 100
        assert sum(result['by_estatus'].values()) == 100
        assert sum(result['by_urgencia'].values()) == 100
        assert sum(result['by_impacto'].values()) == 100

    def test_kpi_preserves_unrelated_fields(self):
        """Test that KPI only counts relevant fields."""
        kpis = PostmortemKPIMetrics()

        record = PostmortemRecord({
            'ID de incidencia': 'INC001',
            'Descripción': 'Test',
            'Estatus': 'Cerrada',
            'Urgencia': 'Alta',
            'Impacto': 'Masiva',
            'Grupo asignado': 'SOP_TEST'  # Not counted in KPI
        })

        kpis.add_record(record)
        result = kpis.to_dict()

        # KPI should only have relevant fields
        assert 'ID de incidencia' not in str(result)
        assert result['total'] == 1
        assert result['by_estatus']['Cerrada'] == 1


class TestKPIAggregationPerformance:
    """Test KPI aggregation performance."""

    def test_kpi_single_pass_aggregation(self):
        """Test that KPI aggregation is single-pass (efficient)."""
        kpis = PostmortemKPIMetrics()

        # Add 1000 records in single pass
        for i in range(1000):
            record = PostmortemRecord({
                'Estatus': 'Cerrada' if i % 2 == 0 else 'En Progreso',
                'Urgencia': 'Alta',
                'Impacto': 'Masiva'
            })
            kpis.add_record(record)

        result = kpis.to_dict()

        assert result['total'] == 1000
        assert result['by_estatus']['Cerrada'] == 500
        assert result['by_estatus']['En Progreso'] == 500


class TestKPIDataStructure:
    """Test KPI data structure."""

    def test_kpi_dict_format(self):
        """Test KPI dict has correct format."""
        kpis = PostmortemKPIMetrics()
        record = PostmortemRecord({
            'Estatus': 'Cerrada',
            'Urgencia': 'Alta',
            'Impacto': 'Masiva'
        })
        kpis.add_record(record)

        result = kpis.to_dict()

        # Check structure
        assert 'total' in result
        assert 'by_estatus' in result
        assert 'by_urgencia' in result
        assert 'by_impacto' in result

        # Check types
        assert isinstance(result['total'], int)
        assert isinstance(result['by_estatus'], dict)
        assert isinstance(result['by_urgencia'], dict)
        assert isinstance(result['by_impacto'], dict)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
