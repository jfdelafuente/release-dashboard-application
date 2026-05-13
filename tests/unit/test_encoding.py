"""Unit tests for encoding detection."""

import pytest
from csv_to_json.encoding import detect_encoding, decode_file


class TestEncodingDetection:
    """Tests for encoding detection functionality."""

    def test_detect_utf8(self):
        """Test UTF-8 encoding detection."""
        text = "ID,Name\n001,José\n002,María"
        utf8_bytes = text.encode('utf-8')

        encoding = detect_encoding(utf8_bytes)
        assert encoding in ['utf-8', 'utf-8-sig']

    def test_detect_utf8_sig(self):
        """Test UTF-8 with BOM detection."""
        text = "ID,Name"
        utf8_sig_bytes = text.encode('utf-8-sig')

        encoding = detect_encoding(utf8_sig_bytes)
        assert encoding == 'utf-8-sig'

    def test_detect_windows1252(self):
        """Test Windows-1252 encoding detection."""
        text = "ID,Name\n001,José"
        cp1252_bytes = text.encode('windows-1252')

        encoding = detect_encoding(cp1252_bytes)
        assert encoding in ['windows-1252', 'cp1252', 'utf-8']

    def test_detect_latin1(self):
        """Test Latin-1 encoding detection."""
        text = "ID,Name\n001,Pérez"
        latin1_bytes = text.encode('latin-1')

        encoding = detect_encoding(latin1_bytes)
        # Latin-1 can be detected as various encodings due to similar byte patterns
        assert encoding in ['latin-1', 'iso-8859-1', 'utf-8', 'windows-1252']

    def test_decode_file_utf8(self):
        """Test file decoding with UTF-8."""
        text = "ID,Name,Descripción\n001,José,Test"
        utf8_bytes = text.encode('utf-8')

        decoded, encoding = decode_file(utf8_bytes)
        assert "José" in decoded
        assert encoding in ['utf-8', 'utf-8-sig']

    def test_decode_empty_file(self):
        """Test decoding empty file."""
        encoding = detect_encoding(b'')
        assert encoding == 'utf-8'

    def test_special_characters_preserved(self):
        """Test that special characters are preserved during encoding detection."""
        text = "ID,Descripción\n001,LIVEPERSON // DERIO // ERROR FUNCIONAL"
        utf8_bytes = text.encode('utf-8')

        decoded, _ = decode_file(utf8_bytes)
        assert "LIVEPERSON" in decoded
        assert "//" in decoded
