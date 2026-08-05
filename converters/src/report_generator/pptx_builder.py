"""Ensamblado del informe .pptx: portada, tarjetas de KPI y diapositivas de gráfica.

Estilo inspirado en el dashboard de postmortem y en el informe manual de
referencia ("PostMortem-PostProducción ... .pptx"), pero construido desde
cero con python-pptx (no se parte de una plantilla corporativa — ver
research.md §1).
"""
import io
from pathlib import Path

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

from report_generator.chart_utils import COLOR_ORANGE, COLOR_INK, COLOR_INK_LIGHT, COLOR_BORDER

SLIDE_WIDTH = Inches(13.333)
SLIDE_HEIGHT = Inches(7.5)

_RGB_ORANGE = RGBColor.from_string(COLOR_ORANGE.lstrip("#"))
_RGB_INK = RGBColor.from_string(COLOR_INK.lstrip("#"))
_RGB_INK_LIGHT = RGBColor.from_string(COLOR_INK_LIGHT.lstrip("#"))
_RGB_BORDER = RGBColor.from_string(COLOR_BORDER.lstrip("#"))
_RGB_WHITE = RGBColor(0xFF, 0xFF, 0xFF)

# Paleta del "hero" del rediseño MASORANGE (fondo negro), distinta de la
# usada en las tarjetas de KPI (fondo blanco) — ver
# "MASORANGE dashboard redesign/Release Dashboard.dc.html", sección Portal.
_RGB_HERO_SUBTITLE = RGBColor.from_string("B8B2A9")
_RGB_HERO_DEPT_LABEL = RGBColor.from_string("9E988E")

# Ruta relativa al propio módulo (no al cwd): sigue siendo válida aunque
# generate_postmortem_report.py haga chdir a otro repo (ver _maybe_chdir).
_LOGO_PATH = Path(__file__).parent / "assets" / "masorange-logo-positive.png"


def _blank_slide(prs):
    blank_layout = prs.slide_layouts[6]
    return prs.slides.add_slide(blank_layout)


def _add_textbox(slide, left, top, width, height, text, size, color, bold=False, align=PP_ALIGN.LEFT):
    box = slide.shapes.add_textbox(left, top, width, height)
    tf = box.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color
    run.font.name = "Calibri"
    return box


def _add_title_bar(slide, title_text):
    _add_textbox(
        slide, Inches(0.5), Inches(0.25), SLIDE_WIDTH - Inches(1), Inches(0.6),
        title_text, size=24, color=_RGB_INK, bold=True,
    )
    line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.5), Inches(0.85), SLIDE_WIDTH - Inches(1), Pt(3))
    line.fill.solid()
    line.fill.fore_color.rgb = _RGB_ORANGE
    line.line.fill.background()


def new_presentation(release_name):
    """Crea la Presentation con la portada.

    Sigue el "hero" de portal del rediseño MASORANGE (fondo negro, logo,
    eyebrow naranja, titular grande en blanco, subtítulo gris) — ver
    "MASORANGE dashboard redesign/Release Dashboard.dc.html".
    """
    prs = Presentation()
    prs.slide_width = SLIDE_WIDTH
    prs.slide_height = SLIDE_HEIGHT

    slide = _blank_slide(prs)

    background = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, SLIDE_WIDTH, SLIDE_HEIGHT)
    background.fill.solid()
    background.fill.fore_color.rgb = _RGB_INK
    background.line.fill.background()
    background.shadow.inherit = False

    if _LOGO_PATH.exists():
        slide.shapes.add_picture(str(_LOGO_PATH), Inches(0.6), Inches(0.55), height=Inches(0.32))

    _add_textbox(
        slide, Inches(2.1), Inches(0.5), Inches(4), Inches(0.4),
        "Customer & Service Operations", size=11, color=_RGB_HERO_DEPT_LABEL, bold=True,
    )

    _add_textbox(
        slide, Inches(0.6), Inches(2.9), SLIDE_WIDTH - Inches(1.2), Inches(0.4),
        "POSTMORTEM · MASORANGE", size=13, color=_RGB_ORANGE, bold=True,
    )
    _add_textbox(
        slide, Inches(0.55), Inches(3.3), SLIDE_WIDTH - Inches(1.2), Inches(1.3),
        release_name, size=54, color=_RGB_WHITE, bold=True,
    )
    _add_textbox(
        slide, Inches(0.6), Inches(4.65), SLIDE_WIDTH - Inches(2.5), Inches(0.7),
        "Informe de postmortem — rendimiento de incidencias por despliegue y evolución operativa.",
        size=14, color=_RGB_HERO_SUBTITLE,
    )
    return prs


def _add_kpi_card(slide, left, top, width, height, value_text, label_text, detail_text=None):
    card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    card.fill.solid()
    card.fill.fore_color.rgb = _RGB_WHITE
    card.line.color.rgb = _RGB_BORDER
    card.line.width = Pt(1)
    card.shadow.inherit = False

    stripe = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, left, top, Pt(4), height)
    stripe.fill.solid()
    stripe.fill.fore_color.rgb = _RGB_ORANGE
    stripe.line.fill.background()

    pad = Inches(0.2)
    _add_textbox(slide, left + pad, top + Inches(0.15), width - 2 * pad, Inches(0.6), value_text, size=28, color=_RGB_INK, bold=True)
    _add_textbox(slide, left + pad, top + Inches(0.75), width - 2 * pad, Inches(0.35), label_text, size=11, color=_RGB_INK_LIGHT, bold=True)
    if detail_text:
        _add_textbox(slide, left + pad, top + Inches(1.05), width - 2 * pad, Inches(0.35), detail_text, size=9, color=_RGB_INK_LIGHT)


# (value, label, detail) por tarjeta, mismo orden que Métricas Globales del dashboard
_KPI_CARD_FIELDS = [
    ("total_incidencias", "Total Incidencias", None),
    ("total_pendientes", "Total Pendientes", None),
    ("pct_cerradas", "% Cerradas", "cerradas_detalle"),
    ("tiempo_medio_resolucion", "Tiempo Medio de Resolución", "tiempo_medio_detalle"),
    ("pct_resueltas_pap", "% Resueltas PaP", "pap_detalle"),
    ("pap_pendientes", "Total Pendientes PaP", None),
    ("pct_resueltas_mesa", "% Resueltas Mesa", "mesa_detalle"),
    ("mesa_pendientes", "Total Pendientes Mesa", None),
]


def add_kpi_slide(prs, report_data):
    """Añade la diapositiva con las 8 tarjetas de KPI (2 filas x 4 columnas)."""
    slide = _blank_slide(prs)
    _add_title_bar(slide, f"Métricas Globales — {report_data['release_name']}")

    cols, rows = 4, 2
    gap = Inches(0.25)
    margin = Inches(0.5)
    card_w = (SLIDE_WIDTH - 2 * margin - (cols - 1) * gap) / cols
    card_h = Inches(1.6)
    top0 = Inches(1.3)

    for idx, (field, label, detail_field) in enumerate(_KPI_CARD_FIELDS):
        row, col = divmod(idx, cols)
        left = margin + col * (card_w + gap)
        top = top0 + row * (card_h + gap)

        value = report_data.get(field)
        value_text = f"{value}%" if field.startswith("pct_") else ("-" if value is None else str(value))
        detail_text = report_data.get(detail_field) if detail_field else None
        _add_kpi_card(slide, left, top, card_w, card_h, value_text, label, detail_text)

    return slide


def add_chart_image_slide(prs, title, png_bytes):
    """Añade una diapositiva con un título y una gráfica (imagen PNG) centrada."""
    slide = _blank_slide(prs)
    _add_title_bar(slide, title)

    image_stream = io.BytesIO(png_bytes)
    max_width = SLIDE_WIDTH - Inches(1)
    max_height = SLIDE_HEIGHT - Inches(1.5)
    slide.shapes.add_picture(image_stream, Inches(0.5), Inches(1.1), width=max_width, height=max_height)
    return slide


def add_chart_slides(prs, charts):
    """Añade una diapositiva por cada (título, png_bytes) de `charts`.

    Entradas con png_bytes=None se omiten (p. ej. la gráfica PaP cuando la
    release no tiene incidencias PaP).
    """
    for title, png_bytes in charts:
        if png_bytes is not None:
            add_chart_image_slide(prs, title, png_bytes)
