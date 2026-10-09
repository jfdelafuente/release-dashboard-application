"""Colores y utilidades compartidas por todas las gráficas del informe.

Los valores hex replican exactamente los usados en los dashboards
(dashboards/postmortem/index.html y dashboards/release-kpis/app.js), para
que el informe sea visualmente reconocible como "del mismo sistema" (FR-007).
"""
import io
import logging
import numpy as np

logger = logging.getLogger(__name__)

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


def _render_with_matplotlib(fig, width=1200, height=650, scale=2):
    """Renderiza una plotly Figure usando Matplotlib con backend Agg (puro Python).

    Genera PNGs de alta definición en memoria en ~100-150ms sin invocar
    procesos externos, navegadores (Chrome/Chromium) ni librerías X11.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig_json = fig.to_plotly_json() if hasattr(fig, "to_plotly_json") else (fig if isinstance(fig, dict) else {})
    data = fig_json.get("data", [])
    layout = fig_json.get("layout", {})

    dpi = int(120 * (scale or 1))
    fig_w = width / 100
    fig_h = height / 100
    fig_mpl, ax1 = plt.subplots(figsize=(fig_w, fig_h), dpi=dpi)
    fig_mpl.patch.set_facecolor("white")
    ax1.set_facecolor("white")

    # Detección de orientación horizontal
    is_horizontal = any(t.get("orientation") == "h" for t in data if t.get("type") == "bar")

    # Detección de eje secundario Y2
    has_y2 = any(t.get("yaxis") in ("y2", 2, "yaxis2") for t in data)
    ax2 = ax1.twinx() if (has_y2 and not is_horizontal) else None

    barmode = layout.get("barmode", "group")
    bar_traces = [t for t in data if t.get("type") == "bar"]
    scatter_traces = [t for t in data if t.get("type") in ("scatter", None) and t.get("mode") is not None]

    if is_horizontal:
        cat_labels = []
        for t in bar_traces:
            if "y" in t and t["y"]:
                for item in t["y"]:
                    if item not in cat_labels:
                        cat_labels.append(item)
        cat_indices = np.arange(len(cat_labels))
        cat_map = {lbl: i for i, lbl in enumerate(cat_labels)}

        stacked_left = np.zeros(len(cat_indices), dtype=float)
        for i, t in enumerate(bar_traces):
            vals = np.zeros(len(cat_indices), dtype=float)
            for y_item, x_item in zip(t.get("y", []), t.get("x", [])):
                if y_item in cat_map:
                    vals[cat_map[y_item]] = float(x_item or 0)
            color = t.get("marker", {}).get("color", COLOR_ORANGE)
            label = t.get("name", "")
            if barmode == "stack":
                ax1.barh(cat_indices, vals, left=stacked_left, color=color, label=label, height=0.6, edgecolor="none")
                stacked_left += vals
            else:
                n_bars = len(bar_traces)
                bh = 0.8 / max(n_bars, 1)
                offset = (i - (n_bars - 1) / 2) * bh
                ax1.barh(cat_indices + offset, vals, color=color, label=label, height=bh * 0.9, edgecolor="none")

        ax1.set_yticks(cat_indices)
        ax1.set_yticklabels(cat_labels, fontsize=10, color=COLOR_INK)
        ax1.invert_yaxis()
    else:
        cat_labels = []
        for t in data:
            if "x" in t and t["x"]:
                cat_labels = list(t["x"])
                break
        cat_indices = np.arange(len(cat_labels))

        stacked_pos = np.zeros(len(cat_indices), dtype=float)
        for i, t in enumerate(bar_traces):
            y_vals = np.array([float(v) if v is not None else 0.0 for v in t.get("y", [])], dtype=float)
            if len(y_vals) < len(cat_indices):
                y_vals = np.pad(y_vals, (0, len(cat_indices) - len(y_vals)))
            elif len(y_vals) > len(cat_indices):
                y_vals = y_vals[:len(cat_indices)]
            color = t.get("marker", {}).get("color", COLOR_ORANGE)
            label = t.get("name", "")
            if barmode == "stack":
                ax1.bar(cat_indices, y_vals, bottom=stacked_pos, color=color, label=label, width=0.55, edgecolor="none")
                stacked_pos += y_vals
            else:
                n_bars = len(bar_traces)
                bw = 0.8 / max(n_bars, 1)
                offset = (i - (n_bars - 1) / 2) * bw
                ax1.bar(cat_indices + offset, y_vals, color=color, label=label, width=bw * 0.9, edgecolor="none")

        for t in scatter_traces:
            target_ax = ax2 if t.get("yaxis") in ("y2", 2, "yaxis2") and ax2 else ax1
            y_raw = list(t.get("y", []))
            y_vals = [float(v) if v is not None else np.nan for v in y_raw]
            mode = t.get("mode", "lines")
            line = t.get("line", {})
            marker = t.get("marker", {})
            color = line.get("color") or marker.get("color") or COLOR_INK
            width_pt = line.get("width", 2)
            dash = line.get("dash", "solid")
            ls = "--" if dash == "dash" else ("dotted" if dash == "dot" else "-")

            has_lines = "lines" in mode
            has_markers = "markers" in mode
            has_text = "text" in mode

            x_pts = cat_indices[:len(y_vals)]
            target_ax.plot(
                x_pts, y_vals,
                linestyle=ls if has_lines else "None",
                linewidth=width_pt if has_lines else 0,
                marker="o" if has_markers else "None",
                markersize=marker.get("size", 6) if has_markers else 0,
                color=color,
                label=t.get("name", ""),
                zorder=5,
            )

            if has_text and "text" in t and t["text"]:
                text_pos = t.get("textposition", "top center")
                text_font = t.get("textfont", {})
                font_sz = text_font.get("size", 11) * 0.55
                va = "bottom" if "top" in text_pos else ("top" if "bottom" in text_pos else "center")
                y_offset = 6 if "top" in text_pos else (-8 if "bottom" in text_pos else 0)
                for xi, yi, txt in zip(x_pts, y_vals, t["text"]):
                    if yi is not None and not np.isnan(yi) and str(txt).strip():
                        target_ax.annotate(
                            str(txt),
                            (xi, yi),
                            textcoords="offset points",
                            xytext=(0, y_offset),
                            ha="center",
                            va=va,
                            fontsize=font_sz,
                            fontweight="bold",
                            color=color,
                        )

        xaxis = layout.get("xaxis", {})
        tickangle = xaxis.get("tickangle", 0)
        ax1.set_xticks(cat_indices)
        ax1.set_xticklabels(
            cat_labels,
            rotation=-tickangle if tickangle < 0 else tickangle,
            ha="right" if tickangle != 0 else "center",
            fontsize=10,
            color=COLOR_INK,
        )
        if xaxis.get("title", {}).get("text"):
            ax1.set_xlabel(xaxis["title"]["text"], fontsize=11, color=COLOR_INK, fontweight="bold")

    yaxis = layout.get("yaxis", {})
    yaxis2 = layout.get("yaxis2", {})
    if yaxis.get("title", {}).get("text"):
        ax1.set_ylabel(yaxis["title"]["text"], fontsize=11, color=COLOR_INK, fontweight="bold")
    ax1.tick_params(labelsize=10, labelcolor=COLOR_INK)
    ax1.grid(True, color=COLOR_BORDER, linestyle="-", linewidth=0.7, alpha=0.8)
    ax1.set_axisbelow(True)

    ax1.spines["top"].set_visible(False)
    ax1.spines["right"].set_visible(False if not ax2 else True)
    ax1.spines["left"].set_color(COLOR_BORDER)
    ax1.spines["bottom"].set_color(COLOR_BORDER)

    if ax2:
        if yaxis2.get("title", {}).get("text"):
            ax2.set_ylabel(yaxis2["title"]["text"], fontsize=11, color=COLOR_INK, fontweight="bold")
        if yaxis2.get("range"):
            ax2.set_ylim(yaxis2["range"])
        ax2.tick_params(labelsize=10, labelcolor=COLOR_INK)
        ax2.grid(False)
        ax2.spines["top"].set_visible(False)
        ax2.spines["left"].set_visible(False)
        ax2.spines["right"].set_color(COLOR_BORDER)
        ax2.spines["bottom"].set_color(COLOR_BORDER)

    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels() if ax2 else ([], [])
    handles = h1 + h2
    labels = l1 + l2

    if handles:
        leg_layout = layout.get("legend", {})
        leg_font_sz = leg_layout.get("font", {}).get("size", 11) * 0.6
        ncol = min(len(labels), 5)
        ax1.legend(
            handles, labels,
            loc="lower center",
            bbox_to_anchor=(0.5, 1.02),
            ncol=ncol,
            frameon=True,
            facecolor="white",
            edgecolor=COLOR_BORDER,
            fontsize=leg_font_sz,
            handlelength=1.5,
            handletextpad=0.5,
            columnspacing=1.0,
        )

    buf = io.BytesIO()
    fig_mpl.savefig(buf, format="png", dpi=dpi, facecolor="white", edgecolor="none", bbox_inches="tight")
    plt.close(fig_mpl)
    return buf.getvalue()


def export_figure_to_png(fig, width=1200, height=650, scale=2):
    """Exporta una plotly.graph_objects.Figure a PNG (bytes).

    Usa Matplotlib con backend 'Agg' como motor nativo de alto rendimiento
    (render en ~100-150ms sin navegador ni dependencias X11 de Linux).
    Mantiene fallback automático a Kaleido si Matplotlib no está disponible.
    """
    try:
        return _render_with_matplotlib(fig, width=width, height=height, scale=scale)
    except Exception as exc:
        logger.warning("Fallo al renderizar con Matplotlib (%s). Intentando con Kaleido...", exc)
        import plotly.io as pio
        return pio.to_image(fig, format="png", width=width, height=height, scale=scale)

