"""Colores y utilidades compartidas por todas las gráficas del informe.

Los valores hex replican exactamente los usados en los dashboards
(dashboards/postmortem/index.html y dashboards/release-kpis/app.js), para
que el informe sea visualmente reconocible como "del mismo sistema" (FR-007).
"""
import plotly.io as pio

# Paleta MASORANGE/Orange (ver dashboards/postmortem/index.html)
COLOR_ORANGE = "#FF7900"
COLOR_ORANGE_LIGHT = "#FFC08A"
COLOR_ORANGE_DARK = "#E66D00"
COLOR_AMBER = "#FFD200"
COLOR_GREY = "#B8B2A9"
COLOR_INK = "#0C0B09"
COLOR_INK_LIGHT = "#5C5852"
COLOR_BORDER = "#E2DDD5"

# Verde/rojo de estado (ver dashboards/assets/tokens.css: --success/--danger)
COLOR_SUCCESS = "#1D8754"
COLOR_DANGER = "#D43A2F"

# Objetivo de % de resolución (PaP / 1ª semana / Mesa) — igual que
# KPI_TARGET_PCT en dashboards/release-kpis/app.js.
KPI_TARGET_PCT = 75

# Paleta cíclica usada por "Por Sistema" (createSystemChart) y "Incidencias No
# Cerradas" (createOpenIncidentsChart) para desglosar por Estado.
STATUS_PALETTE = [
    COLOR_ORANGE, COLOR_ORANGE_LIGHT, COLOR_ORANGE_DARK,
    COLOR_AMBER, COLOR_GREY, COLOR_INK_LIGHT, COLOR_BORDER,
]

FONT_FAMILY = "Inter, sans-serif"

BASE_LAYOUT = dict(
    font=dict(family=FONT_FAMILY, size=11, color=COLOR_INK_LIGHT),
    paper_bgcolor="white",
    plot_bgcolor="white",
)


def export_figure_to_png(fig, width=1200, height=650, scale=2):
    """Exporta una plotly.graph_objects.Figure a PNG (bytes) vía Kaleido."""
    return pio.to_image(fig, format="png", width=width, height=height, scale=scale)
