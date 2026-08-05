"""Tests de report_generator.release_kpis_charts."""
from report_generator.release_kpis_charts import (
    build_incidencias_por_release_chart,
    build_kpi_pap_chart,
    build_kpi_post_chart,
    KPI_TARGET_PCT,
)


def _releases():
    return [
        {"name": "2026R6", "pap_entrada": 53, "pap_resueltas": 46, "post_entrada": 38, "post_resueltas": 33, "pct_pap": 87, "pct_first_week": 87},
        {"name": "2026R7", "pap_entrada": 70, "pap_resueltas": 54, "post_entrada": 107, "post_resueltas": 84, "pct_pap": 77, "pct_first_week": 79},
    ]


class TestBuildIncidenciasPorReleaseChart:
    def test_four_traces_two_bars_two_lines(self):
        fig = build_incidencias_por_release_chart(_releases())
        assert len(fig.data) == 4
        names = [t.name for t in fig.data]
        assert names == ["PaP Entrada", "Post Entrada", "% PaP", "% 1ª semana"]

    def test_one_point_per_release(self):
        releases = _releases()
        fig = build_incidencias_por_release_chart(releases)
        assert list(fig.data[0].x) == [r["name"] for r in releases]


class TestBuildKpiChart:
    def test_includes_target_line_at_75_percent(self):
        fig = build_kpi_pap_chart(_releases())
        target_trace = next(t for t in fig.data if "Objetivo" in t.name)
        assert all(v == KPI_TARGET_PCT for v in target_trace.y)

    def test_pendientes_is_entrada_minus_resueltas(self):
        fig = build_kpi_pap_chart(_releases())
        pendientes_trace = next(t for t in fig.data if t.name == "Pendientes")
        assert list(pendientes_trace.y) == [53 - 46, 70 - 54]

    def test_post_chart_uses_post_fields(self):
        fig = build_kpi_post_chart(_releases())
        resueltas_trace = next(t for t in fig.data if t.name == "Solucionadas")
        assert list(resueltas_trace.y) == [33, 84]

    def test_both_kpi_charts_share_same_target(self):
        """Réplica deliberada de la discrepancia documentada en spec.md: ambas
        gráficas usan el mismo KPI_TARGET_PCT (75%), no se corrige aquí."""
        fig_pap = build_kpi_pap_chart(_releases())
        fig_post = build_kpi_post_chart(_releases())
        target_pap = next(t for t in fig_pap.data if "Objetivo" in t.name).y[0]
        target_post = next(t for t in fig_post.data if "Objetivo" in t.name).y[0]
        assert target_pap == target_post == 75
