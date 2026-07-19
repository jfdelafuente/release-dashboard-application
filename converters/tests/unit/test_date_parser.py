#!/usr/bin/env python3
"""
Unit tests for postmortem date parser.

Tests parsePostmortemDate() function covering DD-MMM, DD/MM/YYYY, and edge cases.
"""

import pytest
from csv_to_json.postmortem_schemas import parsePostmortemDate, parsePostmortemDateTime


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


class TestDateTimeParser:
    """Test parsePostmortemDateTime() — preserves time-of-day (PAP chart's 30-min x-axis)."""

    def test_preserves_morning_time(self):
        """Test that a morning time is preserved as 24-hour HH:MM."""
        result = parsePostmortemDateTime('26/04/2026 8:49 a')
        assert result == '26/04/2026 08:49'

    def test_preserves_afternoon_time_despite_a_suffix(self):
        """Test that an afternoon 24h hour is preserved as-is, ignoring the 'a' suffix.

        Real exports carry the 'a' suffix regardless of morning/afternoon
        hour (e.g. '14:02 a', '22:18 a'), so it is not a reliable 12-hour
        AM/PM indicator here and must not trigger a +12h conversion.
        """
        result = parsePostmortemDateTime('07/06/2026 14:02 a')
        assert result == '07/06/2026 14:02'

    def test_p_suffix_also_ignored(self):
        """Test that a 'p' suffix is likewise not treated as a 12-hour PM indicator."""
        result = parsePostmortemDateTime('01/05/2026 9:15 p')
        assert result == '01/05/2026 09:15'

    def test_date_only_defaults_to_midnight(self):
        """Test that a date without a time component defaults to 00:00."""
        result = parsePostmortemDateTime('26/04/2026')
        assert result == '26/04/2026 00:00'

    def test_spanish_abbreviation_defaults_to_midnight(self):
        """Test that the legacy DD-MMM format (no time) defaults to 00:00."""
        result = parsePostmortemDateTime('26-abr')
        assert result is not None
        assert result.endswith(' 00:00')

    def test_single_digit_hour_and_minute_zero_padded(self):
        """Test that single-digit hour/minute are zero-padded."""
        result = parsePostmortemDateTime('01/05/2026 8:05 a')
        assert result == '01/05/2026 08:05'

    def test_invalid_date_returns_none(self):
        """Test that an unparseable date still returns None, regardless of any time part."""
        assert parsePostmortemDateTime('invalid 8:00 a') is None

    def test_empty_and_none_return_none(self):
        """Test empty string and None input."""
        assert parsePostmortemDateTime('') is None
        assert parsePostmortemDateTime(None) is None

    def test_malformed_time_part_falls_back_to_midnight(self):
        """Test that a date with an unparseable trailing time part still returns the date, at 00:00."""
        result = parsePostmortemDateTime('26/04/2026 garbage')
        assert result == '26/04/2026 00:00'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
