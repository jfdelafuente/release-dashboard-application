"""Integration tests for CSV to JSON converter."""

import json
import pytest
from pathlib import Path
from csv_to_json.converter import CsvToJsonConverter


class TestConverterEndToEnd:
    """End-to-end tests for complete conversion pipeline."""

    @pytest.fixture
    def converter(self):
        """Create a fresh converter instance."""
        return CsvToJsonConverter()

    @pytest.fixture
    def sample_csv(self, tmp_path):
        """Create a sample CSV file for testing."""
        csv_content = """ID de incidencia,Prioridad,Descripción,Estatus,Fecha de envío,Grupo asignado,Fecha de última resolución,Grupo Resolutor,Urgencia,Impacto,Grupo Remitente
INC000003884945,Media,LIVEPERSON // DERIO // ERROR FUNCIONAL,Cerrado,02/01/2026 8:14 AM,CEP CAU AGI,12/01/2026 8:24 AM,CEP CAU AGI,4-Baja,Masiva,SLN Arvato Salamanca
INC000003884989,Media,PRDIAS-25896 LIVEPERSON // CORUÑA // ERROR FUNCIONAL,Cerrado,02/01/2026 3:18 PM,CEP CAU AGI,23/02/2026 8:32 AM,CEP CAU AGI,3-Medio,Masiva,SLN Arvato Salamanca
INC000003885040,Alta,INDISPONIBILIDAD/ aotlxprvin10211/SL2,Cerrado,02/01/2026 1:02 AM,RTV-TECSE RED DATOS,02/01/2026 5:17 AM,GNOC,2-Alta,Masiva,Operador (A.G.I.)"""

        csv_file = tmp_path / "test_incidents.csv"
        csv_file.write_text(csv_content, encoding='utf-8')
        return csv_file

    def test_convert_sample_csv(self, converter, sample_csv, tmp_path):
        """Test end-to-end conversion of sample CSV."""
        output_file = tmp_path / "output.json"
        error_file = tmp_path / "errors.json"

        success, report = converter.convert_file(
            str(sample_csv),
            str(output_file),
            str(error_file)
        )

        # Check stats
        assert report["stats"]["total_records"] == 3
        assert report["stats"]["successful"] >= 3
        assert report["stats"]["failed"] == 0

        # Check output file was created
        assert output_file.exists()

        # Check JSON output
        with open(output_file) as f:
            output_data = json.load(f)

        assert len(output_data) >= 3
        assert output_data[0]["ID de incidencia"] == "INC000003884945"
        assert output_data[0]["Urgencia"] == "Baja"  # Normalized from "4-Baja"

    def test_convert_utf8_sig_csv(self, converter, tmp_path):
        """Test conversion of UTF-8 with BOM encoded CSV."""
        csv_content = """ID de incidencia,Descripción,Estatus,Fecha de envío,Grupo asignado,Urgencia,Impacto
INC000000001,Test Descripción,Cerrado,01/01/2026 10:00 AM,Test Group,4-Baja,Masiva"""

        csv_file = tmp_path / "test_utf8sig.csv"
        csv_file.write_bytes(csv_content.encode('utf-8-sig'))

        output_file = tmp_path / "output.json"

        success, report = converter.convert_file(
            str(csv_file),
            str(output_file)
        )

        assert report["stats"]["successful"] >= 1
        assert "utf-8" in report["encoding_detected"].lower()

    def test_convert_with_invalid_records(self, converter, tmp_path):
        """Test conversion with some invalid records."""
        csv_content = """ID de incidencia,Descripción,Estatus,Fecha de envío,Grupo asignado,Urgencia,Impacto
INC000000001,Valid Record,Cerrado,01/01/2026 10:00 AM,Test Group,4-Baja,Masiva
INC000000002,Invalid Status,InvalidStatus,01/01/2026 10:00 AM,Test Group,4-Baja,Masiva
INC000000003,Valid Record 2,Abierto,02/01/2026 11:00 AM,Test Group,3-Medio,Masiva"""

        csv_file = tmp_path / "test_mixed.csv"
        csv_file.write_text(csv_content, encoding='utf-8')

        output_file = tmp_path / "output.json"
        error_file = tmp_path / "errors.json"

        success, report = converter.convert_file(
            str(csv_file),
            str(output_file),
            str(error_file)
        )

        # Should have 2 valid records and 1 error
        assert report["stats"]["total_records"] == 3
        assert report["stats"]["successful"] == 2
        assert len(report["errors"]) > 0

        # Check error report was created
        assert error_file.exists()

    def test_converter_stats(self, converter, sample_csv, tmp_path):
        """Test that converter correctly tracks statistics."""
        converter.convert_file(str(sample_csv))

        stats = converter.get_stats()
        assert stats["total_records"] == 3
        assert stats["successful"] >= 3
        assert stats["success_rate"] > 0
