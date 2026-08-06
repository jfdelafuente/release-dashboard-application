"""Test de integración: las gráficas del informe muestran las últimas 9
releases de releases-data.js (no solo la seleccionada, y no todo el
histórico), y el informe falla con un mensaje claro si releases-data.js no
está disponible — desde el rediseño, es la única fuente de datos del informe."""
import generate_postmortem_report
from generate_postmortem_report import generate_report, CHART_RELEASE_COUNT


_RELEASES_JS = """"use strict";
const RAW_RELEASES = [
  ["2026R6", 2026, "7-jun.", "Junio", 53, 46, 38, 33],
  ["2026R7", 2026, "7-jul.", "Julio", 70, 54, 107, 84],
  ["2026R8", 2026, "7-ago.", "Agosto", 40, 35, 20, 18],
];
"""

# 12 releases (> CHART_RELEASE_COUNT=9) para poder comprobar el recorte a las
# últimas 9 en las gráficas, sin afectar a las tarjetas de KPI de la release
# seleccionada (que siguen buscándose en la lista completa).
_RELEASES_JS_MANY = """"use strict";
const RAW_RELEASES = [
""" + "\n".join(
    f'  ["2026R{i}", 2026, "{i}-ene.", "Enero", 10, 8, 5, 4],'
    for i in range(1, 13)
) + """
];
"""


def _write_releases_js(tmp_path, content=_RELEASES_JS):
    path = tmp_path / "releases-data.js"
    path.write_text(content, encoding="utf-8")
    return path


class TestReleaseKpisContextInReport:
    def test_charts_show_only_last_9_releases(self, tmp_path, monkeypatch):
        releases_data_path = _write_releases_js(tmp_path, _RELEASES_JS_MANY)
        monkeypatch.setattr("generate_postmortem_report.DEFAULT_RELEASES_DATA_PATH", releases_data_path)
        monkeypatch.setattr(
            "generate_postmortem_report.load_release_kpis_context",
            lambda: __import__(
                "report_generator.release_kpis_data", fromlist=["load_release_kpis_context"]
            ).load_release_kpis_context(path=releases_data_path),
        )

        seen_release_names = []
        real_build_chart = generate_postmortem_report.build_incidencias_por_release_chart

        def _spy_build_chart(releases):
            seen_release_names.append([r["name"] for r in releases])
            return real_build_chart(releases)

        monkeypatch.setattr("generate_postmortem_report.build_incidencias_por_release_chart", _spy_build_chart)

        report_path = tmp_path / "report.pptx"
        # "2026R1" es la release más antigua, fuera de la ventana de las
        # últimas 9 — su tarjeta de KPI debe seguir generándose igual.
        result = generate_report("2026R1", output_path=report_path)
        assert result["success"] is True
        assert len(seen_release_names) == 1
        assert seen_release_names[0] == [f"2026R{i}" for i in range(4, 13)]
        assert len(seen_release_names[0]) == CHART_RELEASE_COUNT

        from pptx import Presentation

        prs = Presentation(str(report_path))
        assert len(prs.slides) == 3
        kpi_slide_text = "\n".join(
            s.text_frame.text for s in prs.slides[1].shapes if s.has_text_frame
        )
        assert "2026R1" in kpi_slide_text

    def test_report_fails_clearly_when_release_kpis_data_missing(self, tmp_path, monkeypatch):
        """Ver Edge Cases de spec.md: sin releases-data.js no hay ningún dato
        que mostrar (KPIs y gráficas comparten esa única fuente), así que el
        informe debe fallar con un mensaje claro en vez de generarse vacío."""
        monkeypatch.setattr(
            "generate_postmortem_report.load_release_kpis_context",
            lambda: (_ for _ in ()).throw(FileNotFoundError("releases-data.js no encontrado")),
        )

        report_path = tmp_path / "report.pptx"
        result = generate_report("2026R6", output_path=report_path)

        assert result["success"] is False
        assert "KPIs de Release" in result["error"]
        assert not report_path.exists()
