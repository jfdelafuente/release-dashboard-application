"""Réplica de las 3 gráficas generales de dashboards/release-kpis/app.js.

Muestran SIEMPRE el conjunto completo de releases (FR-005/006 — "de forma
general", no filtradas a la release del informe), en el mismo orden
cronológico ascendente que usan las gráficas del dashboard (no el de la
tabla, que se muestra invertido).
"""
import plotly.graph_objects as go

from report_generator.chart_utils import (
    BASE_LAYOUT, COLOR_ORANGE, COLOR_INK, COLOR_ORANGE_LIGHT, COLOR_SUCCESS, KPI_TARGET_PCT,
)

_KPI_SEG_RESUELTAS = COLOR_ORANGE
_KPI_SEG_PENDIENTES = COLOR_ORANGE_LIGHT

_DEFAULT_LEGEND_FONT_SIZE = 18
_MARGIN = dict(l=70, r=70, t=70, b=80)

# El doble del tamaño de fuente base (BASE_LAYOUT en chart_utils.py, 11px),
# para las etiquetas de texto que acompañan a cada punto de las líneas (%).
_POINT_LABEL_FONT_SIZE = 22

_AXIS_TICK_FONT_SIZE = 16
_AXIS_TITLE_FONT_SIZE = 18


def _legend(font_size=_DEFAULT_LEGEND_FONT_SIZE):
    return dict(
        orientation="h", x=0.5, xanchor="center", y=1.12, yanchor="bottom",
        bgcolor="rgba(255,255,255,0.9)", bordercolor="#E2DDD5", borderwidth=1, font=dict(size=font_size),
    )


def _axis(title, **extra):
    return dict(
        title=dict(text=title, font=dict(size=_AXIS_TITLE_FONT_SIZE)),
        tickfont=dict(size=_AXIS_TICK_FONT_SIZE),
        **extra,
    )


def build_incidencias_por_release_chart(releases, legend_font_size=_DEFAULT_LEGEND_FONT_SIZE):
    """Réplica de renderBarChart(): barras apiladas (PaP+Post) + líneas % PaP / % 1ª semana."""
    names = [r["name"] for r in releases]

    fig = go.Figure()
    fig.add_trace(go.Bar(x=names, y=[r["pap_entrada"] for r in releases], name="PaP Entrada", marker_color=COLOR_ORANGE, yaxis="y"))
    fig.add_trace(go.Bar(x=names, y=[r["post_entrada"] for r in releases], name="Post Entrada", marker_color=COLOR_INK, yaxis="y"))
    fig.add_trace(go.Scatter(
        x=names, y=[r["pct_pap"] for r in releases], name="% PaP", mode="lines+markers+text",
        line=dict(color=COLOR_ORANGE, width=2), marker=dict(size=6),
        text=[f"{r['pct_pap']}%" for r in releases], textposition="top center", textfont=dict(size=_POINT_LABEL_FONT_SIZE), yaxis="y2",
    ))
    fig.add_trace(go.Scatter(
        x=names, y=[r["pct_first_week"] for r in releases], name="% 1ª semana", mode="lines+markers+text",
        line=dict(color=COLOR_INK, width=2), marker=dict(size=6),
        text=[f"{r['pct_first_week']}%" for r in releases], textposition="bottom center", textfont=dict(size=_POINT_LABEL_FONT_SIZE), yaxis="y2",
    ))
    fig.update_layout(
        **BASE_LAYOUT, legend=_legend(legend_font_size), margin=_MARGIN, barmode="stack", hovermode="x unified",
        xaxis=_axis("Release", tickangle=-45, showgrid=True, gridcolor="#E2DDD5"),
        yaxis=_axis("Incidencias", showgrid=True, gridcolor="#E2DDD5"),
        yaxis2=_axis("% Resuelto", overlaying="y", side="right", range=[0, 105], showgrid=False),
    )
    return fig


def _build_kpi_chart(releases, entrada_field, resueltas_field, pct_field, line_color, window_label, legend_font_size):
    """Réplica de buildKpiChartData(): barras resueltas/pendientes + línea % + objetivo."""
    names = [r["name"] for r in releases]
    resueltas = [r[resueltas_field] for r in releases]
    pendientes = [r[entrada_field] - r[resueltas_field] for r in releases]
    pct = [r[pct_field] for r in releases]

    fig = go.Figure()
    fig.add_trace(go.Bar(x=names, y=resueltas, name="Solucionadas", marker_color=_KPI_SEG_RESUELTAS, yaxis="y"))
    fig.add_trace(go.Bar(x=names, y=pendientes, name="Pendientes", marker_color=_KPI_SEG_PENDIENTES, yaxis="y"))
    fig.add_trace(go.Scatter(
        x=names, y=pct, name=f"% {window_label}", mode="lines+markers+text",
        line=dict(color=line_color, width=2), marker=dict(size=6),
        text=[f"{v}%" for v in pct], textposition="top center", textfont=dict(size=_POINT_LABEL_FONT_SIZE), yaxis="y2",
    ))
    fig.add_trace(go.Scatter(
        x=names, y=[KPI_TARGET_PCT] * len(names), name=f"Objetivo {KPI_TARGET_PCT}%", mode="lines",
        line=dict(color=COLOR_SUCCESS, width=1.5, dash="dash"), yaxis="y2",
    ))
    fig.update_layout(
        **BASE_LAYOUT, legend=_legend(legend_font_size), margin=_MARGIN, barmode="stack", hovermode="x unified",
        xaxis=_axis("Release", tickangle=-45, showgrid=True, gridcolor="#E2DDD5"),
        yaxis=_axis("Incidencias", showgrid=True, gridcolor="#E2DDD5"),
        yaxis2=_axis(f"% {window_label}", overlaying="y", side="right", range=[0, 105], showgrid=False),
    )
    return fig


def build_kpi_pap_chart(releases, legend_font_size=_DEFAULT_LEGEND_FONT_SIZE):
    return _build_kpi_chart(releases, "pap_entrada", "pap_resueltas", "pct_pap", COLOR_ORANGE, "PaP", legend_font_size)


def build_kpi_post_chart(releases, legend_font_size=_DEFAULT_LEGEND_FONT_SIZE):
    return _build_kpi_chart(releases, "post_entrada", "post_resueltas", "pct_first_week", COLOR_INK, "1ª semana", legend_font_size)
