"""Test end-to-end: releases-data.js sintético -> generate_report() -> abrir el .pptx resultante.

Todos los KPIs y gráficas del informe se calculan a partir de
releases-data.js (ver generate_postmortem_report.py) — el JSON de
postmortem por release ya no interviene en la generación.
"""
from pptx import Presentation
from pptx.dml.color import RGBColor

from generate_postmortem_report import generate_report
from report_generator.chart_utils import COLOR_SUCCESS, COLOR_DANGER


_RELEASES_JS = """"use strict";
const RAW_RELEASES = [
  ["2026R6", 2026, "7-jun.", "Junio", 50, 40, 30, 20],
  ["2026TEST", 2026, "10-jul.", "Julio", 20, 18, 10, 6],
];
"""
# 2026TEST: pct_pap = round(100*18/20) = 90 (>= 75, verde)
#           pct_first_week = round(100*6/10) = 60 (< 75, rojo)
#           total_incidencias = 20 + 10 = 30


def _write_releases_js(tmp_path, content=_RELEASES_JS):
    path = tmp_path / "releases-data.js"
    path.write_text(content, encoding="utf-8")
    return path


def _patch_releases_source(monkeypatch, releases_path):
    monkeypatch.setattr("generate_postmortem_report.DEFAULT_RELEASES_DATA_PATH", releases_path)
    monkeypatch.setattr(
        "generate_postmortem_report.load_release_kpis_context",
        lambda: __import__(
            "report_generator.release_kpis_data", fromlist=["load_release_kpis_context"]
        ).load_release_kpis_context(path=releases_path),
    )


def _find_run_color(slide, text):
    for shape in slide.shapes:
        if shape.has_text_frame and shape.text_frame.text.strip() == text:
            return shape.text_frame.paragraphs[0].runs[0].font.color.rgb
    return None


class TestGenerateReportE2E:
    def test_generates_pptx_with_expected_slides_and_kpis(self, tmp_path, monkeypatch):
        releases_path = _write_releases_js(tmp_path)
        _patch_releases_source(monkeypatch, releases_path)

        report_path = tmp_path / "report.pptx"
        result = generate_report("2026TEST", output_path=report_path)

        assert result["success"] is True
        assert report_path.exists()

        prs = Presentation(str(report_path))
        # Portada + Métricas Globales (3 KPIs + gráfica) + Comparativa (2 gráficas)
        assert len(prs.slides) == 3

        kpi_slide = prs.slides[1]
        slide_text = "\n".join(s.text_frame.text for s in kpi_slide.shapes if s.has_text_frame)
        assert "30" in slide_text  # total_incidencias
        assert "90%" in slide_text  # pct_pap
        assert "60%" in slide_text  # pct_first_week ("% Resueltas Mesa")
        assert "Objetivo: 75%" in slide_text
        assert "18 de 20 incidencias PaP resueltas el día del PaP" in slide_text
        assert "6 de 10 incidencias Mesa" in slide_text

        assert _find_run_color(kpi_slide, "90%") == RGBColor.from_string(COLOR_SUCCESS.lstrip("#"))
        assert _find_run_color(kpi_slide, "60%") == RGBColor.from_string(COLOR_DANGER.lstrip("#"))

        last_slide_text = "\n".join(s.text_frame.text for s in prs.slides[2].shapes if s.has_text_frame)
        assert "KPI % PaP" in last_slide_text
        assert "KPI % 1ª semana" in last_slide_text

    def test_unknown_release_returns_error_without_creating_file(self, tmp_path, monkeypatch):
        releases_path = _write_releases_js(tmp_path)
        _patch_releases_source(monkeypatch, releases_path)

        report_path = tmp_path / "report.pptx"
        result = generate_report("NOPE", output_path=report_path)

        assert result["success"] is False
        assert "NOPE" in result["error"]
        assert not report_path.exists()

    def test_locked_output_file_raises_friendly_message(self, tmp_path, monkeypatch):
        """Si el .pptx anterior está abierto en otro programa (p. ej.
        PowerPoint), Windows deniega la escritura con PermissionError. El
        mensaje debe ser accionable, no el error crudo del sistema."""
        releases_path = _write_releases_js(tmp_path)
        _patch_releases_source(monkeypatch, releases_path)
        monkeypatch.setattr(
            "pptx.presentation.Presentation.save",
            lambda self, path: (_ for _ in ()).throw(PermissionError("[Errno 13] Permission denied")),
        )

        report_path = tmp_path / "2026TEST-postmortem-report.pptx"
        try:
            generate_report("2026TEST", output_path=report_path)
            assert False, "Se esperaba PermissionError"
        except PermissionError as e:
            assert "abierto en otro programa" in str(e)
            assert report_path.name in str(e)


class TestGenerateReportCaching:
    """El informe no debe regenerarse si ya existe y es más reciente que
    releases-data.js — evita repetir el renderizado de las 3 gráficas en
    cada clic cuando nadie ha subido datos nuevos desde la última vez."""

    def test_skips_regeneration_when_report_is_newer_than_source(self, tmp_path, monkeypatch):
        import time

        releases_path = _write_releases_js(tmp_path)
        monkeypatch.setattr("generate_postmortem_report.DEFAULT_RELEASES_DATA_PATH", releases_path)

        calls = {"count": 0}
        real_load = __import__(
            "report_generator.release_kpis_data", fromlist=["load_release_kpis_context"]
        ).load_release_kpis_context

        def _counting_load():
            calls["count"] += 1
            return real_load(path=releases_path)

        monkeypatch.setattr("generate_postmortem_report.load_release_kpis_context", _counting_load)

        report_path = tmp_path / "report.pptx"
        first = generate_report("2026TEST", output_path=report_path)
        assert first["success"] is True
        assert calls["count"] == 1
        first_mtime = report_path.stat().st_mtime

        # Segunda llamada sin cambios en releases-data.js: no debe regenerar.
        second = generate_report("2026TEST", output_path=report_path)
        assert second["success"] is True
        assert calls["count"] == 1
        assert report_path.stat().st_mtime == first_mtime

        # releases-data.js cambia (más reciente que el informe): ahora sí debe regenerar.
        time.sleep(0.05)
        releases_path.write_text(releases_path.read_text(encoding="utf-8"), encoding="utf-8")
        assert releases_path.stat().st_mtime > first_mtime

        third = generate_report("2026TEST", output_path=report_path)
        assert third["success"] is True
        assert calls["count"] == 2
