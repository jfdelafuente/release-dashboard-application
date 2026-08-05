"""Test end-to-end: dataset sintético -> generate_report() -> abrir el .pptx resultante."""
import json

from pptx import Presentation

from generate_postmortem_report import generate_report
from report_generator.kpi_calculator import calculate_kpis


def _write_release(output_dir, release_name, records):
    path = output_dir / f"{release_name}-postmortem.json"
    path.write_text(
        json.dumps({"_metadata": {"release_name": release_name}, "data": records}, ensure_ascii=False),
        encoding="utf-8",
    )
    return path


def _synthetic_records():
    return [
        {"ID de incidencia": "INC1", "Estatus": "Cerrado", "Despliegue": "PAP",
         "Fecha de envío": "10/06/2026 08:00", "Fecha de última resolución": "10/06/2026 10:00",
         "Grupo asignado": "SOP_A"},
        {"ID de incidencia": "INC2", "Estatus": "Asignado", "Despliegue": "PAP",
         "Fecha de envío": "10/06/2026 09:00", "Fecha de última resolución": "",
         "Grupo asignado": "SOP_B"},
        {"ID de incidencia": "INC3", "Estatus": "Cerrado", "Despliegue": "MESA",
         "Fecha de envío": "12/06/2026 08:00", "Fecha de última resolución": "12/06/2026 09:30",
         "Grupo asignado": "SOP_A"},
        {"ID de incidencia": "INC4", "Estatus": "Pendiente", "Despliegue": "MESA",
         "Fecha de envío": "12/06/2026 09:00", "Fecha de última resolución": "",
         "Grupo asignado": "SOP_B"},
    ]


class TestGenerateReportE2E:
    def test_generates_pptx_with_expected_slides_and_kpis(self, tmp_path, monkeypatch):
        output_dir = tmp_path / "data" / "output"
        output_dir.mkdir(parents=True)
        records = _synthetic_records()
        _write_release(output_dir, "2026TEST", records)

        monkeypatch.setattr(
            "generate_postmortem_report.load_postmortem_records",
            lambda release_name, output_dir=None: records if release_name == "2026TEST" else None,
        )

        report_path = tmp_path / "report.pptx"
        result = generate_report("2026TEST", output_path=report_path)

        assert result["success"] is True
        assert report_path.exists()

        prs = Presentation(str(report_path))
        # Portada + KPIs + 4 gráficas propias de postmortem
        assert len(prs.slides) == 6

        expected_kpis = calculate_kpis(records)
        kpi_slide = prs.slides[1]
        slide_text = "\n".join(
            s.text_frame.text for s in kpi_slide.shapes if s.has_text_frame
        )
        assert str(expected_kpis["total_incidencias"]) in slide_text
        assert f"{expected_kpis['pct_cerradas']}%" in slide_text

    def test_unknown_release_returns_error_without_creating_file(self, tmp_path, monkeypatch):
        from report_generator.data_loader import ReleaseNotFoundError

        def _raise(*args, **kwargs):
            raise ReleaseNotFoundError("No hay datos de postmortem cargados para la release 'NOPE'")

        monkeypatch.setattr("generate_postmortem_report.load_postmortem_records", _raise)

        report_path = tmp_path / "report.pptx"
        result = generate_report("NOPE", output_path=report_path)

        assert result["success"] is False
        assert "NOPE" in result["error"]
        assert not report_path.exists()
