"""Unit tests for field validation."""

import pytest
from csv_to_json.validators import validate_record, validate_field


class TestValidation:
    """Tests for field validation functionality."""

    def test_validate_valid_record(self):
        """Test validation of a completely valid record."""
        record = {
            "ID de incidencia": "INC000003884945",
            "Prioridad": "Media",
            "Descripción": "LIVEPERSON // DERIO // ERROR FUNCIONAL",
            "Estatus": "Cerrado",
            "Fecha de envío": "02/01/2026 8:14 AM",
            "Grupo asignado": "CEP CAU AGI",
            "Fecha de última resolución": "12/01/2026 8:24 AM",
            "Grupo Resolutor": "CEP CAU AGI",
            "Urgencia": "Baja",
            "Impacto": "Masiva",
            "Grupo Remitente": "SLN Arvato Salamanca"
        }

        is_valid, errors = validate_record(record, 2)
        assert is_valid is True
        assert len(errors) == 0

    def test_validate_missing_required_field(self):
        """Test validation fails when required field is missing."""
        record = {
            "ID de incidencia": "INC000003884945",
            "Descripción": "Test",
            "Estatus": "Cerrado",
            "Fecha de envío": "02/01/2026 8:14 AM",
            # Missing Grupo asignado
            "Urgencia": "Baja",
            "Impacto": "Masiva"
        }

        is_valid, errors = validate_record(record, 2)
        assert is_valid is False
        assert len(errors) > 0

    def test_validate_invalid_estatus(self):
        """Test validation fails with invalid Estatus value."""
        record = {
            "ID de incidencia": "INC000003884945",
            "Descripción": "Test",
            "Estatus": "InvalidStatus",
            "Fecha de envío": "02/01/2026 8:14 AM",
            "Grupo asignado": "Test",
            "Urgencia": "Baja",
            "Impacto": "Masiva"
        }

        is_valid, errors = validate_record(record, 2)
        assert is_valid is False
        assert any("Estatus" in e["field"] for e in errors)

    def test_validate_invalid_urgencia(self):
        """Test validation fails with invalid Urgencia value."""
        record = {
            "ID de incidencia": "INC000003884945",
            "Descripción": "Test",
            "Estatus": "Cerrado",
            "Fecha de envío": "02/01/2026 8:14 AM",
            "Grupo asignado": "Test",
            "Urgencia": "InvalidUrgencia",
            "Impacto": "Masiva"
        }

        is_valid, errors = validate_record(record, 2)
        assert is_valid is False
        assert any("Urgencia" in e["field"] for e in errors)

    def test_validate_invalid_impacto(self):
        """Test validation fails when Impacto is not 'Masiva'."""
        record = {
            "ID de incidencia": "INC000003884945",
            "Descripción": "Test",
            "Estatus": "Cerrado",
            "Fecha de envío": "02/01/2026 8:14 AM",
            "Grupo asignado": "Test",
            "Urgencia": "Baja",
            "Impacto": "Alto"  # Wrong value
        }

        is_valid, errors = validate_record(record, 2)
        assert is_valid is False
        assert any("Impacto" in e["field"] for e in errors)

    def test_validate_invalid_date(self):
        """Test validation fails with invalid date format."""
        record = {
            "ID de incidencia": "INC000003884945",
            "Descripción": "Test",
            "Estatus": "Cerrado",
            "Fecha de envío": "2026-01-02 08:14:00",  # Wrong format
            "Grupo asignado": "Test",
            "Urgencia": "Baja",
            "Impacto": "Masiva"
        }

        is_valid, errors = validate_record(record, 2)
        assert is_valid is False
        assert any("Fecha de envío" in e["field"] for e in errors)

    def test_validate_optional_field_empty(self):
        """Test that optional empty fields don't cause validation failure."""
        record = {
            "ID de incidencia": "INC000003884945",
            "Descripción": "Test",
            "Estatus": "Cerrado",
            "Fecha de envío": "02/01/2026 8:14 AM",
            "Grupo asignado": "Test",
            "Urgencia": "Baja",
            "Impacto": "Masiva",
            "Prioridad": "",  # Empty optional field
            "Fecha de última resolución": ""  # Empty optional field
        }

        is_valid, errors = validate_record(record, 2)
        assert is_valid is True
