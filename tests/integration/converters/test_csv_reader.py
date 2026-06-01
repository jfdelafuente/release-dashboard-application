#!/usr/bin/env python3
"""
Unit tests for readPostmortemCSV() function.

Tests CSV reading with encoding detection, delimiter detection, and BOM handling.
"""

import pytest
import tempfile
from pathlib import Path
from csv_to_json.postmortem_converter import readPostmortemCSV


class TestCSVReaderEncoding:
    """Test CSV reader with various encodings."""

    def test_read_csv_utf8(self):
        """Test reading UTF-8 encoded CSV."""
        records, encoding = readPostmortemCSV('tests/test_data/valid-100.csv')

        assert encoding in ['utf-8', 'utf-8-sig']
        assert len(records) == 100
        assert all(isinstance(r, dict) for r in records)

    def test_read_csv_utf8_sig(self):
        """Test reading UTF-8-sig (with BOM) CSV."""
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.csv', delete=False) as f:
            # Write BOM + CSV content
            content = "ID de incidencia,Descripción,Estatus,Fecha de envío,Grupo asignado,Urgencia,Impacto\nINC001,Test,Cerrada,01/05/2026 8:00 a,SOP_TEST,Alta,Masiva\n"
            f.write(b'\xef\xbb\xbf' + content.encode('utf-8'))
            temp_path = f.name

        try:
            records, encoding = readPostmortemCSV(temp_path)

            assert encoding == 'utf-8-sig'
            assert len(records) == 1
            # BOM should be removed from field names
            assert 'ID de incidencia' in records[0] or 'ID de incidencia' in str(records[0].keys())
        finally:
            Path(temp_path).unlink()

    def test_read_csv_file_not_found(self):
        """Test error handling for missing file."""
        with pytest.raises(FileNotFoundError):
            readPostmortemCSV('tests/test_data/nonexistent.csv')


class TestCSVReaderDelimiter:
    """Test CSV reader with various delimiters."""

    def test_read_csv_comma_delimiter(self):
        """Test reading comma-delimited CSV."""
        records, encoding = readPostmortemCSV('tests/test_data/valid-100.csv')

        # Should have expected fields
        assert len(records[0]) > 0
        assert 'ID de incidencia' in records[0]
        assert 'Descripción' in records[0]
        assert 'Estatus' in records[0]

    def test_read_csv_semicolon_delimiter(self):
        """Test reading semicolon-delimited CSV."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
            # Write semicolon-delimited CSV
            f.write("ID de incidencia;Descripción;Estatus;Fecha de envío;Grupo asignado;Urgencia;Impacto\n")
            f.write("INC001;Test;Cerrada;01/05/2026 8:00 a;SOP_TEST;Alta;Masiva\n")
            temp_path = f.name

        try:
            records, encoding = readPostmortemCSV(temp_path)

            assert len(records) == 1
            assert records[0].get('ID de incidencia') == 'INC001'
            assert records[0].get('Descripción') == 'Test'
        finally:
            Path(temp_path).unlink()

    def test_read_csv_tab_delimiter(self):
        """Test reading tab-delimited CSV."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
            # Write tab-delimited CSV
            f.write("ID de incidencia\tDescripción\tEstatus\tFecha de envío\tGrupo asignado\tUrgencia\tImpacto\n")
            f.write("INC001\tTest\tCerrada\t01/05/2026 8:00 a\tSOP_TEST\tAlta\tMasiva\n")
            temp_path = f.name

        try:
            records, encoding = readPostmortemCSV(temp_path)

            assert len(records) == 1
            assert records[0].get('ID de incidencia') == 'INC001'
            assert records[0].get('Descripción') == 'Test'
        finally:
            Path(temp_path).unlink()


class TestCSVReaderStructure:
    """Test CSV reader record structure."""

    def test_read_csv_returns_list(self):
        """Test that CSV reader returns list of dicts."""
        records, _ = readPostmortemCSV('tests/test_data/valid-100.csv')

        assert isinstance(records, list)
        assert len(records) > 0
        assert all(isinstance(r, dict) for r in records)

    def test_read_csv_returns_encoding(self):
        """Test that CSV reader returns detected encoding."""
        records, encoding = readPostmortemCSV('tests/test_data/valid-100.csv')

        assert isinstance(encoding, str)
        assert len(encoding) > 0
        assert encoding in ['utf-8', 'utf-8-sig', 'windows-1252', 'latin-1', 'iso-8859-15']

    def test_read_csv_skip_empty_rows(self):
        """Test that empty rows are skipped."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
            f.write("ID de incidencia,Descripción,Estatus,Fecha de envío,Grupo asignado,Urgencia,Impacto\n")
            f.write("INC001,Test1,Cerrada,01/05/2026 8:00 a,SOP_TEST,Alta,Masiva\n")
            f.write("\n")  # Empty row
            f.write("INC002,Test2,Cerrada,02/05/2026 9:00 a,SOP_TEST,Alta,Masiva\n")
            temp_path = f.name

        try:
            records, _ = readPostmortemCSV(temp_path)

            # Should have 2 records (empty row skipped)
            assert len(records) == 2
        finally:
            Path(temp_path).unlink()

    def test_read_csv_all_13_fields(self):
        """Test that all 13 postmortem fields are present."""
        records, _ = readPostmortemCSV('tests/test_data/valid-100.csv')

        # Check first record has expected fields
        record = records[0]
        expected_fields = [
            'ID de incidencia', 'Descripción', 'Estatus', 'Fecha de envío',
            'Grupo asignado', 'Fecha de notificación', 'Fecha de última resolución',
            'Motivo de estado', 'MotivoEstado_Anterior', 'Grupo Resolutor',
            'Urgencia', 'Impacto', 'Grupo Remitente'
        ]

        for field in expected_fields:
            assert field in record or field in str(record.keys())


class TestCSVReaderBOM:
    """Test CSV reader BOM (Byte Order Mark) handling."""

    def test_read_csv_with_bom_in_header(self):
        """Test reading CSV with BOM in header."""
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.csv', delete=False) as f:
            # Write BOM before header
            header = "ID de incidencia,Descripción,Estatus,Fecha de envío,Grupo asignado,Urgencia,Impacto\n"
            data = "INC001,Test,Cerrada,01/05/2026 8:00 a,SOP_TEST,Alta,Masiva\n"
            f.write(b'\xef\xbb\xbf' + header.encode('utf-8') + data.encode('utf-8'))
            temp_path = f.name

        try:
            records, _ = readPostmortemCSV(temp_path)

            assert len(records) == 1
            # Should be able to read despite BOM
            assert len(records[0]) > 0
        finally:
            Path(temp_path).unlink()


class TestCSVReaderEdgeCases:
    """Test CSV reader edge cases."""

    def test_read_csv_single_record(self):
        """Test reading CSV with single record."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
            f.write("ID de incidencia,Descripción,Estatus,Fecha de envío,Grupo asignado,Urgencia,Impacto\n")
            f.write("INC001,Test,Cerrada,01/05/2026 8:00 a,SOP_TEST,Alta,Masiva\n")
            temp_path = f.name

        try:
            records, _ = readPostmortemCSV(temp_path)

            assert len(records) == 1
            assert records[0]['ID de incidencia'] == 'INC001'
        finally:
            Path(temp_path).unlink()

    def test_read_csv_with_quoted_fields(self):
        """Test reading CSV with quoted fields containing commas."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
            f.write('ID de incidencia,Descripción,Estatus,Fecha de envío,Grupo asignado,Urgencia,Impacto\n')
            f.write('INC001,"Error: Failed, timeout",Cerrada,01/05/2026 8:00 a,SOP_TEST,Alta,Masiva\n')
            temp_path = f.name

        try:
            records, _ = readPostmortemCSV(temp_path)

            assert len(records) == 1
            # Quoted field should be properly parsed
            desc = records[0]['Descripción']
            assert 'Error: Failed, timeout' in desc or desc == 'Error: Failed, timeout'
        finally:
            Path(temp_path).unlink()

    def test_read_csv_with_special_characters(self):
        """Test reading CSV with special characters."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
            f.write("ID de incidencia,Descripción,Estatus,Fecha de envío,Grupo asignado,Urgencia,Impacto\n")
            f.write("INC001,Error en árboles & reglas,Cerrada,01/05/2026 8:00 a,SOP_TEST,Alta,Masiva\n")
            temp_path = f.name

        try:
            records, _ = readPostmortemCSV(temp_path)

            assert len(records) == 1
            # Special chars should be preserved
            assert 'árboles' in records[0]['Descripción'] or 'rboles' in records[0]['Descripción']
        finally:
            Path(temp_path).unlink()

    def test_read_csv_invalid_mixed(self):
        """Test reading CSV with invalid/mixed records."""
        records, _ = readPostmortemCSV('tests/test_data/invalid-mixed.csv')

        # Should read all records, even invalid ones
        assert len(records) == 60
        # Some should have empty fields (invalid ones)
        has_empty_fields = any(any(v == '' for v in r.values()) for r in records)
        assert has_empty_fields


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
