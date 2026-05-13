"""Unit tests for field normalization."""

import pytest
from csv_to_json.normalizers import (
    normalize_field, normalize_title_case, normalize_urgencia, normalize_datetime
)


class TestNormalization:
    """Tests for field normalization functionality."""

    def test_normalize_whitespace(self):
        """Test that whitespace is trimmed."""
        assert normalize_field("ID de incidencia", "  INC000001  ") == "INC000001"
        assert normalize_field("Descripción", "  Test  ") == "Test"

    def test_normalize_estatus_casing(self):
        """Test Estatus normalization to title case."""
        assert normalize_field("Estatus", "cerrado") == "Cerrado"
        assert normalize_field("Estatus", "ABIERTO") == "Abierto"
        assert normalize_field("Estatus", "en progreso") == "En Progreso"

    def test_normalize_urgencia_with_prefix(self):
        """Test Urgencia normalization from 'N-Text' format."""
        assert normalize_field("Urgencia", "4-Baja") == "Baja"
        assert normalize_field("Urgencia", "3-Medio") == "Medio"
        assert normalize_field("Urgencia", "2-Alta") == "Alta"
        assert normalize_field("Urgencia", "1-Crítica") == "Crítica"

    def test_normalize_urgencia_with_spaces(self):
        """Test Urgencia normalization with variant spacing."""
        assert normalize_field("Urgencia", "4 - Baja") == "Baja"
        assert normalize_field("Urgencia", "3-medio") == "Medio"

    def test_normalize_impacto(self):
        """Test Impacto normalization."""
        assert normalize_field("Impacto", "masiva") == "Masiva"
        assert normalize_field("Impacto", "MASIVA") == "Masiva"

    def test_normalize_title_case(self):
        """Test title case normalization."""
        assert normalize_title_case("cerrado") == "Cerrado"
        assert normalize_title_case("ABIERTO") == "Abierto"
        assert normalize_title_case("en progreso") == "En Progreso"

    def test_normalize_datetime_valid(self):
        """Test datetime normalization with valid format."""
        result = normalize_datetime("02/01/2026 8:14 AM")
        assert result == "02/01/2026 8:14 AM"

        result = normalize_datetime("31/12/2026 11:59 PM")
        assert result == "31/12/2026 11:59 PM"

    def test_normalize_datetime_invalid(self):
        """Test datetime normalization with invalid format."""
        with pytest.raises(ValueError, match="Invalid date format"):
            normalize_datetime("2026-01-02 08:14:00")

        with pytest.raises(ValueError, match="Invalid date format"):
            normalize_datetime("32/13/2026 25:99 AM")

    def test_normalize_field_empty_value(self):
        """Test normalization of empty values."""
        assert normalize_field("Descripción", "") == ""
        assert normalize_field("Descripción", "   ") == ""
