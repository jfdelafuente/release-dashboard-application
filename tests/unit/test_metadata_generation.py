#!/usr/bin/env python3
"""
Unit tests for ConversionMetadata generation.

Tests metadata structure including ISO 8601 timestamps, filename tracking, and KPI presence.
"""

import pytest
from datetime import datetime
from csv_to_json.postmortem_schemas import ConversionMetadata, PostmortemKPIMetrics, PostmortemRecord


class TestMetadataGeneration:
    """Test ConversionMetadata generation."""

    def test_metadata_creation_with_empty_kpis(self):
        """Test metadata creation with empty KPIs."""
        kpis = PostmortemKPIMetrics()
        metadata = ConversionMetadata('test.csv', 0, kpis)

        assert metadata.type == 'postmortem'
        assert metadata.version == '1.0'
        assert metadata.source_filename == 'test.csv'
        assert metadata.record_count == 0

    def test_metadata_creation_with_populated_kpis(self):
        """Test metadata creation with populated KPIs."""
        kpis = PostmortemKPIMetrics()
        record = PostmortemRecord({
            'Estatus': 'Cerrada',
            'Urgencia': 'Alta',
            'Impacto': 'Masiva'
        })
        kpis.add_record(record)

        metadata = ConversionMetadata('incidents.csv', 1, kpis)

        assert metadata.type == 'postmortem'
        assert metadata.source_filename == 'incidents.csv'
        assert metadata.record_count == 1
        assert metadata.kpis.total == 1

    def test_metadata_filename_tracking(self):
        """Test that metadata tracks source filename."""
        kpis = PostmortemKPIMetrics()

        filenames = ['data.csv', 'incidents.csv', 'postmortem_2026.csv']
        for filename in filenames:
            metadata = ConversionMetadata(filename, 10, kpis)
            assert metadata.source_filename == filename

    def test_metadata_record_count_tracking(self):
        """Test that metadata tracks record count."""
        kpis = PostmortemKPIMetrics()

        for count in [0, 1, 10, 100, 1000]:
            metadata = ConversionMetadata('test.csv', count, kpis)
            assert metadata.record_count == count

    def test_metadata_type_and_version(self):
        """Test metadata type and version fields."""
        kpis = PostmortemKPIMetrics()
        metadata = ConversionMetadata('test.csv', 100, kpis)

        assert metadata.type == 'postmortem'
        assert metadata.version == '1.0'
        assert isinstance(metadata.type, str)
        assert isinstance(metadata.version, str)


class TestMetadataTimestamp:
    """Test metadata timestamp handling."""

    def test_metadata_timestamp_created(self):
        """Test that metadata has created timestamp."""
        kpis = PostmortemKPIMetrics()
        metadata = ConversionMetadata('test.csv', 10, kpis)

        assert hasattr(metadata, 'created')
        assert metadata.created is not None
        assert isinstance(metadata.created, str)

    def test_metadata_timestamp_iso8601_format(self):
        """Test that timestamp is ISO 8601 format with Z suffix."""
        kpis = PostmortemKPIMetrics()
        metadata = ConversionMetadata('test.csv', 10, kpis)

        timestamp = metadata.created

        # Should end with 'Z'
        assert timestamp.endswith('Z')
        # Should be parseable as datetime
        try:
            datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        except ValueError:
            pytest.fail(f"Invalid ISO 8601 timestamp: {timestamp}")

    def test_metadata_timestamp_valid_datetime(self):
        """Test that timestamp represents a valid datetime."""
        kpis = PostmortemKPIMetrics()
        metadata = ConversionMetadata('test.csv', 10, kpis)

        timestamp_str = metadata.created.replace('Z', '+00:00')
        dt = datetime.fromisoformat(timestamp_str)

        # Should be recent (within last hour)
        now = datetime.now(dt.tzinfo)
        diff = now - dt
        assert diff.total_seconds() < 3600  # Less than 1 hour ago


class TestMetadataKPIs:
    """Test metadata KPI integration."""

    def test_metadata_includes_kpis(self):
        """Test that metadata includes KPI object."""
        kpis = PostmortemKPIMetrics()
        record = PostmortemRecord({
            'Estatus': 'Cerrada',
            'Urgencia': 'Alta',
            'Impacto': 'Masiva'
        })
        kpis.add_record(record)

        metadata = ConversionMetadata('test.csv', 1, kpis)

        assert metadata.kpis is not None
        assert isinstance(metadata.kpis, PostmortemKPIMetrics)

    def test_metadata_kpis_aggregation(self):
        """Test that metadata KPIs correctly aggregate."""
        kpis = PostmortemKPIMetrics()

        for i in range(5):
            record = PostmortemRecord({
                'Estatus': 'Cerrada' if i % 2 == 0 else 'En Progreso',
                'Urgencia': 'Alta',
                'Impacto': 'Masiva'
            })
            kpis.add_record(record)

        metadata = ConversionMetadata('test.csv', 5, kpis)

        assert metadata.kpis.total == 5
        assert metadata.kpis.by_estatus['Cerrada'] == 3
        assert metadata.kpis.by_estatus['En Progreso'] == 2


class TestMetadataDictSerialization:
    """Test metadata dict serialization."""

    def test_metadata_to_dict(self):
        """Test metadata to_dict() method."""
        kpis = PostmortemKPIMetrics()
        record = PostmortemRecord({
            'Estatus': 'Cerrada',
            'Urgencia': 'Alta',
            'Impacto': 'Masiva'
        })
        kpis.add_record(record)

        metadata = ConversionMetadata('test.csv', 1, kpis)
        result = metadata.to_dict()

        # Check dict structure
        assert 'type' in result
        assert 'version' in result
        assert 'created' in result
        assert 'source_filename' in result
        assert 'record_count' in result
        assert 'conversion_timestamp' in result
        assert 'kpis' in result

    def test_metadata_dict_contains_all_fields(self):
        """Test that dict representation includes all required fields."""
        kpis = PostmortemKPIMetrics()
        metadata = ConversionMetadata('test.csv', 100, kpis)
        result = metadata.to_dict()

        assert result['type'] == 'postmortem'
        assert result['version'] == '1.0'
        assert result['source_filename'] == 'test.csv'
        assert result['record_count'] == 100
        assert 'created' in result
        assert 'conversion_timestamp' in result
        assert 'kpis' in result

    def test_metadata_dict_kpis_serialized(self):
        """Test that KPIs are serialized in dict."""
        kpis = PostmortemKPIMetrics()
        record = PostmortemRecord({
            'Estatus': 'Cerrada',
            'Urgencia': 'Alta',
            'Impacto': 'Masiva'
        })
        kpis.add_record(record)

        metadata = ConversionMetadata('test.csv', 1, kpis)
        result = metadata.to_dict()

        kpis_dict = result['kpis']
        assert 'total' in kpis_dict
        assert 'by_estatus' in kpis_dict
        assert 'by_urgencia' in kpis_dict
        assert 'by_impacto' in kpis_dict

    def test_metadata_dict_json_serializable(self):
        """Test that metadata dict is JSON serializable."""
        import json

        kpis = PostmortemKPIMetrics()
        for i in range(3):
            record = PostmortemRecord({
                'Estatus': 'Cerrada' if i < 2 else 'En Progreso',
                'Urgencia': 'Alta',
                'Impacto': 'Masiva'
            })
            kpis.add_record(record)

        metadata = ConversionMetadata('test.csv', 3, kpis)
        result = metadata.to_dict()

        # Should be JSON serializable
        json_str = json.dumps(result)
        assert json_str is not None

        # Should deserialize back correctly
        deserialized = json.loads(json_str)
        assert deserialized['record_count'] == 3
        assert deserialized['kpis']['total'] == 3


class TestMetadataEdgeCases:
    """Test metadata edge cases."""

    def test_metadata_zero_records(self):
        """Test metadata with zero records."""
        kpis = PostmortemKPIMetrics()
        metadata = ConversionMetadata('empty.csv', 0, kpis)

        result = metadata.to_dict()

        assert result['record_count'] == 0
        assert result['kpis']['total'] == 0

    def test_metadata_large_dataset(self):
        """Test metadata with large dataset."""
        kpis = PostmortemKPIMetrics()

        for i in range(1000):
            record = PostmortemRecord({
                'Estatus': ['Cerrada', 'En Progreso', 'Cancelada'][i % 3],
                'Urgencia': ['Baja', 'Media', 'Alta'][i % 3],
                'Impacto': 'Masiva'
            })
            kpis.add_record(record)

        metadata = ConversionMetadata('large.csv', 1000, kpis)
        result = metadata.to_dict()

        assert result['record_count'] == 1000
        assert result['kpis']['total'] == 1000

    def test_metadata_special_chars_in_filename(self):
        """Test metadata with special characters in filename."""
        kpis = PostmortemKPIMetrics()

        filenames = [
            'data-2026-05.csv',
            'postmortem_Q2_2026.csv',
            'incidents (1).csv',
            'data [backup].csv'
        ]

        for filename in filenames:
            metadata = ConversionMetadata(filename, 10, kpis)
            assert metadata.source_filename == filename


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
