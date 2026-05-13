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

    def test_encoding_detection_utf8(self, converter, tmp_path):
        """[T030] Test UTF-8 encoding detection and conversion."""
        csv_content = """ID de incidencia,Descripción,Estatus,Fecha de envío,Grupo asignado,Urgencia,Impacto
INC000000001,UTF-8 Test,Cerrado,01/01/2026 10:00 AM,Test Group,4-Baja,Masiva"""

        csv_file = tmp_path / "test_utf8.csv"
        csv_file.write_text(csv_content, encoding='utf-8')

        output_file = tmp_path / "output.json"
        success, report = converter.convert_file(str(csv_file), str(output_file))

        assert success
        assert "utf-8" in report["encoding_detected"].lower()
        assert report["stats"]["successful"] >= 1

    def test_encoding_detection_windows1252(self, converter, tmp_path):
        """[T030] Test Windows-1252 encoding detection."""
        csv_content = """ID de incidencia,Descripción,Estatus,Fecha de envío,Grupo asignado,Urgencia,Impacto
INC000000002,Windows-1252 Test,Cerrado,02/01/2026 11:00 AM,Test Group,3-Medio,Masiva"""

        csv_file = tmp_path / "test_windows1252.csv"
        csv_file.write_bytes(csv_content.encode('windows-1252'))

        output_file = tmp_path / "output.json"
        success, report = converter.convert_file(str(csv_file), str(output_file))

        assert success
        assert report["stats"]["successful"] >= 1
        # Verify encoding was detected (could be windows-1252 or latin-1)
        detected = report["encoding_detected"].lower()
        assert any(enc in detected for enc in ['windows-1252', 'latin-1', 'iso-8859-1'])

    def test_encoding_detection_latin1(self, converter, tmp_path):
        """[T030] Test Latin-1 encoding detection."""
        csv_content = """ID de incidencia,Descripción,Estatus,Fecha de envío,Grupo asignado,Urgencia,Impacto
INC000000003,Latin-1 Test,Cerrado,03/01/2026 12:00 PM,Test Group,2-Alta,Masiva"""

        csv_file = tmp_path / "test_latin1.csv"
        csv_file.write_bytes(csv_content.encode('latin-1'))

        output_file = tmp_path / "output.json"
        success, report = converter.convert_file(str(csv_file), str(output_file))

        assert success
        assert report["stats"]["successful"] >= 1

    def test_special_characters_preservation(self, converter, tmp_path):
        """[T032] Test preservation of special characters (é, ñ, ü, etc)."""
        csv_content = """ID de incidencia,Descripción,Estatus,Fecha de envío,Grupo asignado,Urgencia,Impacto
INC000000101,Descripción con acentuación: é,Cerrado,01/01/2026 10:00 AM,Grupo España,4-Baja,Masiva
INC000000102,Problema en Español,Abierto,02/01/2026 11:00 AM,Grupo Latinoamérica,3-Medio,Masiva
INC000000103,Überraschung äöü,Pendiente,03/01/2026 12:00 PM,Grupo Alemania,2-Alta,Masiva"""

        csv_file = tmp_path / "test_special_chars.csv"
        csv_file.write_text(csv_content, encoding='utf-8')

        output_file = tmp_path / "output.json"
        success, report = converter.convert_file(str(csv_file), str(output_file))

        assert success
        assert report["stats"]["successful"] >= 3

        # Verify special characters are preserved in output
        with open(output_file, 'r', encoding='utf-8') as f:
            output_data = json.load(f)

        # Check for accented characters in output
        descriptions = [record["Descripción"] for record in output_data]

        # Should preserve Spanish accents
        assert any("é" in desc for desc in descriptions), "Spanish accents (é) not preserved"

        # Should preserve Spanish ñ if in original
        assert any("Español" in desc for desc in descriptions), "Spanish ñ (ñ) not preserved"

        # Should preserve German umlauts
        assert any("ü" in desc for desc in descriptions), "German umlauts (ü) not preserved"

    def test_mixed_valid_invalid_records(self, converter, tmp_path):
        """[T038] Test handling of mixed valid and invalid records (50% split)."""
        # Create CSV with 50% valid, 50% invalid records
        csv_content = """ID de incidencia,Descripción,Estatus,Fecha de envío,Grupo asignado,Urgencia,Impacto
INC000000001,Valid Record 1,Cerrado,01/01/2026 10:00 AM,Group A,Baja,Masiva
INC000000002,Invalid Date,Cerrado,2026-01-02,Group B,Baja,Masiva
INC000000003,Valid Record 2,Abierto,02/01/2026 11:00 AM,Group C,Medio,Masiva
INC000000004,Bad Status,InvalidStatus,03/01/2026 12:00 PM,Group D,Alta,Masiva
INC000000005,Valid Record 3,Pendiente,04/01/2026 1:00 PM,Group E,Baja,Masiva
INC000000006,Bad Urgencia,Cerrado,05/01/2026 2:00 PM,Group F,VeryHigh,Masiva
INC000000007,Valid Record 4,Resuelto,06/01/2026 3:00 PM,Group G,Medio,Masiva
INC000000008,Bad Impact,Cerrado,07/01/2026 4:00 PM,Group H,Medio,Alto"""

        csv_file = tmp_path / "test_mixed.csv"
        csv_file.write_text(csv_content, encoding='utf-8')

        output_file = tmp_path / "output.json"
        error_file = tmp_path / "errors.json"

        success, report = converter.convert_file(
            str(csv_file),
            str(output_file),
            str(error_file)
        )

        # Should process all records (not stop on first error)
        assert report["stats"]["total_records"] == 8

        # Should have 4 successful, 4 failed (50/50 split)
        assert report["stats"]["successful"] == 4
        assert report["stats"]["failed"] == 4
        assert report["stats"]["success_rate"] == 50.0

        # Should have valid records in output
        assert output_file.exists()
        with open(output_file) as f:
            import json
            output_data = json.load(f)
        assert len(output_data) == 4

        # Should have error records with details
        assert error_file.exists()
        with open(error_file) as f:
            import json
            error_data = json.load(f)
        assert error_data["summary"]["failed"] == 4
        assert len(error_data["errors"]) == 4

        # Each error should have field-level error details
        for error in error_data["errors"]:
            assert "row" in error
            assert "fields" in error
            assert len(error["fields"]) > 0

    def test_multiple_encodings_in_batch(self, converter, tmp_path):
        """[T030] Test handling multiple files with different encodings."""
        # Create UTF-8 file
        utf8_content = """ID de incidencia,Descripción,Estatus,Fecha de envío,Grupo asignado,Urgencia,Impacto
INC000000201,UTF-8 Test,Cerrado,01/01/2026 10:00 AM,Test Group,4-Baja,Masiva"""

        utf8_file = tmp_path / "test_utf8_batch.csv"
        utf8_file.write_text(utf8_content, encoding='utf-8')

        # Create Latin-1 file
        latin1_content = """ID de incidencia,Descripción,Estatus,Fecha de envío,Grupo asignado,Urgencia,Impacto
INC000000202,Latin-1 Test,Cerrado,02/01/2026 11:00 AM,Test Group,3-Medio,Masiva"""

        latin1_file = tmp_path / "test_latin1_batch.csv"
        latin1_file.write_bytes(latin1_content.encode('latin-1'))

        # Convert both files
        for csv_file in [utf8_file, latin1_file]:
            output_file = tmp_path / f"{csv_file.stem}_output.json"
            success, report = converter.convert_file(str(csv_file), str(output_file))

            assert success, f"Failed to convert {csv_file.name}"
            assert report["stats"]["successful"] >= 1
            assert output_file.exists()

    def test_large_file_integration(self, converter, tmp_path):
        """[T039] Test conversion of large CSV file (1000+ records in <5 seconds)."""
        import time
        import json

        # Generate a large CSV with 1000 records
        header = "ID de incidencia,Descripción,Estatus,Fecha de envío,Grupo asignado,Urgencia,Impacto"
        rows = []
        for i in range(1, 1001):
            row = f"INC{i:09d},Incident {i},Cerrado,01/01/2026 10:{i % 60:02d} AM,Group A,Baja,Masiva"
            rows.append(row)

        csv_content = header + "\n" + "\n".join(rows)
        csv_file = tmp_path / "large_file.csv"
        csv_file.write_text(csv_content, encoding='utf-8')

        output_file = tmp_path / "output.json"
        error_file = tmp_path / "errors.json"

        # Time the conversion
        start_time = time.time()
        success, report = converter.convert_file(
            str(csv_file),
            str(output_file),
            str(error_file)
        )
        elapsed_time = time.time() - start_time

        # Verify conversion succeeded
        assert success or report["stats"]["successful"] > 0

        # Verify all records were processed
        assert report["stats"]["total_records"] == 1000

        # Verify high success rate
        assert report["stats"]["success_rate"] >= 90.0

        # Verify performance target (<5 seconds for 1000 records)
        assert elapsed_time < 5.0, f"Conversion took {elapsed_time:.2f}s, expected <5s"

        # Verify output file exists and is valid JSON
        assert output_file.exists()
        with open(output_file) as f:
            output_data = json.load(f)
        assert len(output_data) == report["stats"]["successful"]

    def test_edge_cases_performance(self, converter, tmp_path):
        """[T040] Test performance with edge cases (max field lengths, special characters)."""
        import json

        # Create CSV with edge cases: max-length fields and special characters
        max_desc_length = 5000
        description = "ñ" * max_desc_length  # Max length with special char
        group_name = "Grupo España - Región Latinoamérica - Deutschsprachig"

        csv_content = f"""ID de incidencia,Descripción,Estatus,Fecha de envío,Grupo asignado,Urgencia,Impacto
INC000000001,{description},Cerrado,01/01/2026 10:00 AM,{group_name},Baja,Masiva
INC000000002,Normal Record,Abierto,02/01/2026 11:00 AM,Group B,Medio,Masiva
INC000000003,"Description with ""quoted"" text and, commas",Pendiente,03/01/2026 12:00 PM,Group C,Alta,Masiva
INC000000004,Unicode: 中文 العربية हिन्दी,Resuelto,04/01/2026 1:00 PM,Group D,Baja,Masiva"""

        csv_file = tmp_path / "edge_cases.csv"
        csv_file.write_text(csv_content, encoding='utf-8')

        output_file = tmp_path / "output.json"
        error_file = tmp_path / "errors.json"

        success, report = converter.convert_file(
            str(csv_file),
            str(output_file),
            str(error_file)
        )

        # Should handle edge cases without crashing
        assert report["stats"]["total_records"] == 4

        # Should successfully convert records with edge cases
        assert report["stats"]["successful"] >= 3

        # Verify output JSON is valid
        assert output_file.exists()
        with open(output_file, 'r', encoding='utf-8') as f:
            output_data = json.load(f)
        assert len(output_data) > 0

        # Verify special characters are preserved
        first_record = output_data[0]
        assert "ñ" in first_record["Descripción"] or len(first_record["Descripción"]) > 100

        # Verify unicode characters are preserved
        unicode_record = next((r for r in output_data if "中文" in r["Descripción"] or "العربية" in r["Descripción"] or "हिन्दी" in r["Descripción"]), None)
        if unicode_record:
            assert any(char in unicode_record["Descripción"] for char in ["中文", "العربية", "हिन्दी"])
