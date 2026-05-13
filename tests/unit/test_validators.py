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


class TestErrorMessageFormatting:
    """[T037] Tests for error message format and content."""

    def test_required_field_error_message(self):
        """Test that missing required field error contains field name and clear message."""
        record = {
            "ID de incidencia": "INC000003884945",
            "Descripción": "Test",
            "Estatus": "Cerrado",
            "Fecha de envío": "02/01/2026 8:14 AM",
            # Missing Grupo asignado
            "Urgencia": "Baja",
            "Impacto": "Masiva"
        }

        is_valid, errors = validate_record(record, 5)
        assert is_valid is False
        assert len(errors) > 0

        # Error should contain field name
        error = next(e for e in errors if e["field"] == "Grupo asignado")
        assert "Grupo asignado" in error["error"]
        assert "empty" in error["error"].lower() or "missing" in error["error"].lower()
        assert "original" in error
        assert "field" in error

    def test_enum_validation_error_message(self):
        """Test that enum validation error lists allowed values."""
        record = {
            "ID de incidencia": "INC000003884945",
            "Descripción": "Test",
            "Estatus": "InvalidStatus",  # Invalid enum value
            "Fecha de envío": "02/01/2026 8:14 AM",
            "Grupo asignado": "Test",
            "Urgencia": "Baja",
            "Impacto": "Masiva"
        }

        is_valid, errors = validate_record(record, 10)
        assert is_valid is False

        error = next(e for e in errors if e["field"] == "Estatus")
        assert "Estatus" in error["error"]
        assert "InvalidStatus" in error["error"]
        assert "Allowed values" in error["error"] or "allowed" in error["error"].lower()

    def test_urgencia_enum_error_message(self):
        """Test that Urgencia enum error is clear and actionable."""
        record = {
            "ID de incidencia": "INC000003884945",
            "Descripción": "Test",
            "Estatus": "Cerrado",
            "Fecha de envío": "02/01/2026 8:14 AM",
            "Grupo asignado": "Test",
            "Urgencia": "Muy Alta",  # Invalid
            "Impacto": "Masiva"
        }

        is_valid, errors = validate_record(record, 15)
        assert is_valid is False

        error = next(e for e in errors if e["field"] == "Urgencia")
        assert "Urgencia" in error["error"]
        assert "Muy Alta" in error["error"]
        assert error["original"] == "Muy Alta"

    def test_date_format_error_message(self):
        """Test that date format error explains expected format."""
        record = {
            "ID de incidencia": "INC000003884945",
            "Descripción": "Test",
            "Estatus": "Cerrado",
            "Fecha de envío": "2026/01/02 08:14",  # Wrong format
            "Grupo asignado": "Test",
            "Urgencia": "Baja",
            "Impacto": "Masiva"
        }

        is_valid, errors = validate_record(record, 20)
        assert is_valid is False

        error = next(e for e in errors if e["field"] == "Fecha de envío")
        assert "Fecha de envío" in error["error"] or "date" in error["error"].lower()
        assert "2026/01/02 08:14" in error["error"]

    def test_max_length_error_message(self):
        """Test that max length error includes field name and limit."""
        record = {
            "ID de incidencia": "INC" + "X" * 50,  # Exceeds max_length of 50
            "Descripción": "Test",
            "Estatus": "Cerrado",
            "Fecha de envío": "02/01/2026 8:14 AM",
            "Grupo asignado": "Test",
            "Urgencia": "Baja",
            "Impacto": "Masiva"
        }

        is_valid, errors = validate_record(record, 25)
        assert is_valid is False

        # Should have error about ID de incidencia length
        error = next((e for e in errors if "ID de incidencia" in e.get("error", "")), None)
        if error:
            assert "max length" in error["error"].lower()

    def test_error_contains_original_value(self):
        """Test that error objects always contain original value for debugging."""
        record = {
            "ID de incidencia": "INC000003884945",
            "Descripción": "Test",
            "Estatus": "BadStatus",
            "Fecha de envío": "02/01/2026 8:14 AM",
            "Grupo asignado": "Test",
            "Urgencia": "Baja",
            "Impacto": "Masiva"
        }

        is_valid, errors = validate_record(record, 30)
        assert is_valid is False

        # Every error should have original value
        for error in errors:
            assert "original" in error
            assert isinstance(error["original"], str)

    def test_multiple_field_errors(self):
        """Test that all field errors are reported (not just first one)."""
        record = {
            "ID de incidencia": "INC000003884945",
            "Descripción": "Test",
            "Estatus": "BadStatus",
            "Fecha de envío": "BadDate",
            "Grupo asignado": "Test",
            "Urgencia": "BadUrgencia",
            "Impacto": "BadImpacto"
        }

        is_valid, errors = validate_record(record, 35)
        assert is_valid is False
        # Should report multiple errors, not just stop at first
        assert len(errors) >= 4  # Estatus, Fecha de envío, Urgencia, Impacto

    def test_validate_field_function_error_message(self):
        """Test validate_field function returns clear error messages."""
        is_valid, error_msg = validate_field("Estatus", "InvalidValue", "InvalidValue")
        assert is_valid is False
        assert len(error_msg) > 0
        assert "Estatus" in error_msg
        assert "InvalidValue" in error_msg

    def test_validate_field_required_error(self):
        """Test validate_field error for required field."""
        is_valid, error_msg = validate_field("ID de incidencia", "", "")
        assert is_valid is False
        assert "required" in error_msg.lower() or "empty" in error_msg.lower()
        assert "ID de incidencia" in error_msg
