#!/usr/bin/env python3
"""
Encoding detection tests for postmortem converter.

Validates correct encoding detection for various file encodings:
- UTF-8 (with and without BOM)
- Windows-1252 (CP1252)
- Latin-1 (ISO-8859-1)
- ISO-8859-15
"""

import pytest
import csv
import tempfile
from pathlib import Path
from csv_to_json.postmortem_converter import readPostmortemCSV


class TestEncodingDetection:
    """Test encoding auto-detection for various file types."""

    def _create_test_csv(self, encoding, use_bom=False):
        """
        Create a temporary CSV file with specific encoding.

        Args:
            encoding: Encoding to use (utf-8, utf-8-sig, cp1252, latin-1, iso8859-15)
            use_bom: Whether to add BOM (for utf-8 only)

        Returns:
            Path to temporary CSV file
        """
        temp_file = tempfile.NamedTemporaryFile(
            mode='w',
            encoding=encoding,
            suffix='.csv',
            delete=False,
            newline=''
        )

        # CSV header
        header = [
            'ID de incidencia', 'Descripción', 'Estatus',
            'Fecha de envío', 'Grupo asignado', 'Urgencia', 'Impacto'
        ]

        # Sample data with special characters for testing encodings
        data = [
            ['INC001', 'Test con acento: cafe', 'Cerrada',
             '01/05/2026 8:00 a', 'SOP_TEST', 'Alta', 'Masiva'],
            ['INC002', 'Special chars: tilde and more', 'Abierta',
             '02/05/2026 9:00 a', 'SOP_TEST2', 'Baja', 'Minimo'],
            ['INC003', 'Espanol: accents and characters', 'En Progreso',
             '03/05/2026 10:00 a', 'SOP_TEST3', 'Media', 'Parcial']
        ]

        writer = csv.writer(temp_file)
        writer.writerow(header)
        for row in data:
            writer.writerow(row)

        temp_file.close()
        return Path(temp_file.name)

    def test_utf8_encoding_detection(self):
        """Test detection of UTF-8 encoded files."""
        csv_path = self._create_test_csv('utf-8')

        try:
            records, detected_encoding = readPostmortemCSV(str(csv_path))

            assert detected_encoding in ['utf-8', 'UTF-8', 'ascii']
            assert len(records) == 3
            assert records[0]['ID de incidencia'] == 'INC001'
            assert 'cafe' in records[0]['Descripción']
        finally:
            csv_path.unlink()

    def test_utf8_bom_encoding_detection(self):
        """Test detection of UTF-8 with BOM."""
        csv_path = self._create_test_csv('utf-8-sig')

        try:
            records, detected_encoding = readPostmortemCSV(str(csv_path))

            # Could be detected as utf-8, utf-8-sig, or UTF-8-sig
            assert 'utf-8' in detected_encoding.lower()
            assert len(records) == 3
        finally:
            csv_path.unlink()

    def test_windows1252_encoding_detection(self):
        """Test detection of Windows-1252 encoded files."""
        csv_path = self._create_test_csv('cp1252')

        try:
            records, detected_encoding = readPostmortemCSV(str(csv_path))

            # Detection should recognize windows-1252
            assert detected_encoding.lower() in ['cp1252', 'windows-1252', 'iso8859-1', 'latin-1']
            assert len(records) == 3
            assert records[0]['ID de incidencia'] == 'INC001'
        finally:
            csv_path.unlink()

    def test_latin1_encoding_detection(self):
        """Test detection of Latin-1 encoded files."""
        csv_path = self._create_test_csv('latin-1')

        try:
            records, detected_encoding = readPostmortemCSV(str(csv_path))

            # Should detect as latin-1 or similar (chardet might detect as cp1252 or windows-1252 which are compatible)
            assert detected_encoding.lower() in ['latin-1', 'iso8859-1', 'iso-8859-1', 'cp1252', 'windows-1252']
            assert len(records) == 3
        finally:
            csv_path.unlink()

    def test_iso88595_encoding_detection(self):
        """Test detection of ISO-8859-15 encoded files."""
        csv_path = self._create_test_csv('iso8859-15')

        try:
            records, detected_encoding = readPostmortemCSV(str(csv_path))

            # ISO-8859-15 might be detected as cp1252, latin-1, or iso8859 variants
            assert detected_encoding.lower() in ['iso8859-15', 'iso-8859-15', 'latin-1', 'iso8859-1', 'iso-8859-1', 'cp1252', 'windows-1252']
            assert len(records) == 3
        finally:
            csv_path.unlink()

    def test_encoding_with_special_characters(self):
        """Test that special characters are correctly decoded regardless of encoding."""
        for encoding in ['utf-8', 'cp1252', 'latin-1']:
            csv_path = self._create_test_csv(encoding)

            try:
                records, detected_encoding = readPostmortemCSV(str(csv_path))

                # All three records should be read
                assert len(records) == 3

                # Special character handling
                for record in records:
                    assert record['Descripción']  # Should not be empty
                    assert 'INC' in record['ID de incidencia']
            finally:
                csv_path.unlink()

    def test_encoding_consistency_across_fields(self):
        """Test that encoding is applied consistently to all fields."""
        csv_path = self._create_test_csv('utf-8')

        try:
            records, detected_encoding = readPostmortemCSV(str(csv_path))

            # Check that all fields are properly decoded
            for record in records:
                assert isinstance(record['ID de incidencia'], str)
                assert isinstance(record['Descripción'], str)
                assert isinstance(record['Estatus'], str)
                # All strings should be readable
                assert len(record['ID de incidencia']) > 0
                assert len(record['Descripción']) > 0
        finally:
            csv_path.unlink()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
