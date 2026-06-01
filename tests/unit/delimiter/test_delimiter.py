"""Unit tests for delimiter detection."""

import pytest
from csv_to_json.delimiter import detect_delimiter, parse_csv_with_delimiter


class TestDelimiterDetection:
    """Tests for delimiter detection functionality."""

    def test_detect_comma_delimiter(self):
        """Test comma delimiter detection."""
        csv_text = "ID,Name,Status\n001,Test,Closed\n002,Test2,Open"
        delimiter = detect_delimiter(csv_text)
        assert delimiter == ','

    def test_detect_semicolon_delimiter(self):
        """Test semicolon delimiter detection."""
        csv_text = "ID;Name;Status\n001;Test;Closed\n002;Test2;Open"
        delimiter = detect_delimiter(csv_text)
        assert delimiter == ';'

    def test_detect_tab_delimiter(self):
        """Test tab delimiter detection."""
        csv_text = "ID\tName\tStatus\n001\tTest\tClosed\n002\tTest2\tOpen"
        delimiter = detect_delimiter(csv_text)
        assert delimiter == '\t'

    def test_parse_csv_comma(self):
        """Test CSV parsing with comma delimiter."""
        csv_text = "ID,Name\n001,José\n002,María"
        records = parse_csv_with_delimiter(csv_text, delimiter=',')

        assert len(records) == 2
        assert records[0]['ID'] == '001'
        assert records[0]['Name'] == 'José'

    def test_parse_csv_semicolon(self):
        """Test CSV parsing with semicolon delimiter."""
        csv_text = "ID;Name\n001;José\n002;María"
        records = parse_csv_with_delimiter(csv_text, delimiter=';')

        assert len(records) == 2
        assert records[0]['ID'] == '001'
        assert records[0]['Name'] == 'José'

    def test_parse_csv_auto_detect(self):
        """Test CSV parsing with auto-detected delimiter."""
        csv_text = "ID,Name,Status\n001,Test,Closed\n002,Test2,Open"
        records = parse_csv_with_delimiter(csv_text)

        assert len(records) == 2
        assert records[0]['ID'] == '001'
        assert records[0]['Status'] == 'Closed'

    def test_parse_csv_quoted_fields(self):
        """Test CSV parsing with quoted fields containing delimiters."""
        csv_text = 'ID,Description\n001,"Test, with comma"\n002,"Another, test"'
        records = parse_csv_with_delimiter(csv_text, delimiter=',')

        assert len(records) == 2
        assert records[0]['Description'] == 'Test, with comma'
