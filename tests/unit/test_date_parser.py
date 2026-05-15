#!/usr/bin/env python3
"""
Unit tests for postmortem date parser.

Tests parsePostmortemDate() function covering DD-MMM, DD/MM/YYYY, and edge cases.
"""

import pytest
from csv_to_json.postmortem_schemas import parsePostmortemDate


class TestDateParser:
    """Test date parsing and normalization."""

    def test_parse_ddmmyyyy_format(self):
        """Test parsing DD/MM/YYYY format."""
        result = parsePostmortemDate('26/04/2026')
        assert result == '26/04/2026'

    def test_parse_ddmmyyyy_with_time(self):
        """Test parsing DD/MM/YYYY with time component."""
        result = parsePostmortemDate('26/04/2026 14:30 p')
        assert result == '26/04/2026'

    def test_parse_ddmmyyyy_with_spaces(self):
        """Test parsing with extra whitespace."""
        result = parsePostmortemDate('  26/04/2026  ')
        assert result == '26/04/2026'

    def test_parse_ddmmyyyy_single_digit_day(self):
        """Test parsing with single digit day."""
        result = parsePostmortemDate('5/04/2026')
        assert result == '05/04/2026'

    def test_parse_ddmmyyyy_single_digit_month(self):
        """Test parsing with single digit month."""
        result = parsePostmortemDate('26/4/2026')
        assert result == '26/04/2026'

    def test_parse_ddmmmyyyy_spanish_abbrev(self):
        """Test parsing DD-MMM format with Spanish abbreviations."""
        # Test common months
        assert parsePostmortemDate('26-abr') is not None  # April (abril)
        assert parsePostmortemDate('15-mar') is not None  # March (marzo)
        assert parsePostmortemDate('01-ene') is not None  # January (enero)

    def test_parse_spanish_months_lowercase(self):
        """Test Spanish month abbreviations are case-insensitive."""
        result1 = parsePostmortemDate('26-ABR')
        result2 = parsePostmortemDate('26-abr')
        result3 = parsePostmortemDate('26-Abr')
        # All should parse (may normalize to current year)
        assert result1 is not None
        assert result2 is not None
        assert result3 is not None

    def test_parse_spanish_all_months(self):
        """Test all Spanish month abbreviations."""
        months = ['ene', 'feb', 'mar', 'abr', 'may', 'jun',
                  'jul', 'ago', 'sep', 'oct', 'nov', 'dic']
        for month in months:
            result = parsePostmortemDate(f'15-{month}')
            assert result is not None, f"Failed to parse 15-{month}"

    def test_parse_invalid_date_format(self):
        """Test parsing invalid date formats."""
        assert parsePostmortemDate('invalid') is None
        assert parsePostmortemDate('2026-04-26') is None  # ISO format not supported
        assert parsePostmortemDate('04/26/2026') is None  # MM/DD/YYYY format

    def test_parse_invalid_day(self):
        """Test parsing with invalid day."""
        assert parsePostmortemDate('32/04/2026') is None  # Day 32 in April
        assert parsePostmortemDate('30/02/2026') is None  # Feb 30

    def test_parse_invalid_month(self):
        """Test parsing with invalid month."""
        assert parsePostmortemDate('26/13/2026') is None  # Month 13
        assert parsePostmortemDate('26-xxx') is None  # Unknown month

    def test_parse_empty_string(self):
        """Test parsing empty string."""
        assert parsePostmortemDate('') is None
        assert parsePostmortemDate('   ') is None

    def test_parse_none_input(self):
        """Test parsing None input."""
        assert parsePostmortemDate(None) is None

    def test_date_normalization_ddmmyyyy(self):
        """Test DD/MM/YYYY is normalized consistently."""
        result = parsePostmortemDate('5/4/2026')
        assert result == '05/04/2026'  # Zero-padded

    def test_date_normalization_ddmmmyyyy(self):
        """Test DD-MMM is normalized to DD/MM/YYYY."""
        result = parsePostmortemDate('5-abr')
        # Should normalize to DD/MM/YYYY format
        assert '/' in result
        assert result.startswith('05/')

    def test_parse_edge_case_leap_year(self):
        """Test parsing leap year dates."""
        # 2024 is a leap year
        result = parsePostmortemDate('29/02/2024')
        assert result is not None

        # 2026 is not a leap year
        result = parsePostmortemDate('29/02/2026')
        assert result is None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
