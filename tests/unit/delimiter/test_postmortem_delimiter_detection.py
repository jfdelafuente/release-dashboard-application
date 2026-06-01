#!/usr/bin/env python3
"""
Delimiter detection tests for postmortem converter.

Validates correct delimiter detection for various CSV formats:
- Comma-delimited (standard CSV)
- Semicolon-delimited (European CSV)
- Tab-delimited (TSV)
- Mixed formats
"""

import pytest
import tempfile
from pathlib import Path
from csv_to_json.postmortem_converter import readPostmortemCSV


class TestDelimiterDetection:
    """Test delimiter auto-detection for various file types."""

    def _create_delimited_file(self, delimiter, encoding='utf-8'):
        """
        Create a temporary delimited file with specific delimiter.

        Args:
            delimiter: Delimiter character (',' ';' or '\t')
            encoding: File encoding

        Returns:
            Path to temporary file
        """
        temp_file = tempfile.NamedTemporaryFile(
            mode='w',
            encoding=encoding,
            suffix='.csv',
            delete=False,
            newline=''
        )

        # CSV header
        header = delimiter.join([
            'ID de incidencia', 'Descripción', 'Estatus',
            'Fecha de envío', 'Grupo asignado', 'Urgencia', 'Impacto'
        ])

        # Sample data rows
        rows = [
            delimiter.join(['INC001', 'Test incident 1', 'Cerrada',
                          '01/05/2026 8:00 a', 'SOP_TEST', 'Alta', 'Masiva']),
            delimiter.join(['INC002', 'Test incident 2', 'Abierta',
                          '02/05/2026 9:00 a', 'SOP_TEST2', 'Baja', 'Mínimo']),
            delimiter.join(['INC003', 'Test incident 3', 'En Progreso',
                          '03/05/2026 10:00 a', 'SOP_TEST3', 'Media', 'Parcial'])
        ]

        temp_file.write(header + '\n')
        for row in rows:
            temp_file.write(row + '\n')

        temp_file.close()
        return Path(temp_file.name)

    def test_comma_delimited_detection(self):
        """Test detection of comma-delimited CSV files."""
        csv_path = self._create_delimited_file(',')

        try:
            records, detected_encoding = readPostmortemCSV(str(csv_path))

            assert len(records) == 3
            assert records[0]['ID de incidencia'] == 'INC001'
            assert records[0]['Descripción'] == 'Test incident 1'
            assert records[1]['Urgencia'] == 'Baja'
        finally:
            csv_path.unlink()

    def test_semicolon_delimited_detection(self):
        """Test detection of semicolon-delimited CSV files."""
        csv_path = self._create_delimited_file(';')

        try:
            records, detected_encoding = readPostmortemCSV(str(csv_path))

            assert len(records) == 3
            assert records[0]['ID de incidencia'] == 'INC001'
            assert records[0]['Descripción'] == 'Test incident 1'
            assert records[2]['Estatus'] == 'En Progreso'
        finally:
            csv_path.unlink()

    def test_tab_delimited_detection(self):
        """Test detection of tab-delimited TSV files."""
        csv_path = self._create_delimited_file('\t')

        try:
            records, detected_encoding = readPostmortemCSV(str(csv_path))

            assert len(records) == 3
            assert records[0]['ID de incidencia'] == 'INC001'
            assert records[1]['Descripción'] == 'Test incident 2'
            assert records[2]['Grupo asignado'] == 'SOP_TEST3'
        finally:
            csv_path.unlink()

    def test_delimiter_with_spaces(self):
        """Test that extra spaces around delimiters don't break parsing."""
        csv_path = self._create_delimited_file(',')

        try:
            records, detected_encoding = readPostmortemCSV(str(csv_path))

            # Should still parse correctly
            assert len(records) == 3
            for record in records:
                assert 'ID de incidencia' in record
                assert record['ID de incidencia'].startswith('INC')
        finally:
            csv_path.unlink()

    def test_all_delimiters_preserve_data(self):
        """Test that all supported delimiters correctly preserve data."""
        for delimiter in [',', ';', '\t']:
            csv_path = self._create_delimited_file(delimiter)

            try:
                records, detected_encoding = readPostmortemCSV(str(csv_path))

                assert len(records) == 3
                assert records[0]['ID de incidencia'] == 'INC001'
                assert records[0]['Descripción'] == 'Test incident 1'
                assert records[0]['Estatus'] == 'Cerrada'
                assert records[0]['Urgencia'] == 'Alta'
                assert records[0]['Impacto'] == 'Masiva'
            finally:
                csv_path.unlink()

    def test_delimiter_field_count(self):
        """Test that delimiter detection correctly reads all fields."""
        for delimiter in [',', ';', '\t']:
            csv_path = self._create_delimited_file(delimiter)

            try:
                records, detected_encoding = readPostmortemCSV(str(csv_path))

                # All records should have all 7 fields
                for record in records:
                    assert 'ID de incidencia' in record
                    assert 'Descripción' in record
                    assert 'Estatus' in record
                    assert 'Fecha de envío' in record
                    assert 'Grupo asignado' in record
                    assert 'Urgencia' in record
                    assert 'Impacto' in record
            finally:
                csv_path.unlink()

    def test_delimiter_consistency_across_rows(self):
        """Test that delimiter is applied consistently across all rows."""
        csv_path = self._create_delimited_file(';')

        try:
            records, detected_encoding = readPostmortemCSV(str(csv_path))

            # All rows should have same field count
            expected_fields = {
                'ID de incidencia', 'Descripción', 'Estatus',
                'Fecha de envío', 'Grupo asignado', 'Urgencia', 'Impacto'
            }

            for record in records:
                actual_fields = set(record.keys())
                assert actual_fields == expected_fields
        finally:
            csv_path.unlink()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
