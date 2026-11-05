"""
Estilos corporativos, paleta de colores, formateo tipográfico y posicionamiento de cajas de texto PPTX.
"""

import re
from typing import List, Tuple
from pptx.dml.color import RGBColor
from pptx.util import Inches, Pt
from incident_report.config import resolve_template_path

ORANGE_COLOR = RGBColor(237, 125, 49)
BLACK_COLOR = RGBColor(0, 0, 0)
MAX_CHRONO_ROWS = 15
DEFAULT_TEMPLATE_PATH = resolve_template_path()


def clean_executive_text(text: str, max_chars: int = 350) -> str:
    """
    Limpia, normaliza y condensa texto para visualización en diapositivas ejecutivas.
    Recorta limpiamente en límites de frase o palabra sin dejar preposiciones colgadas.
    """
    if not text:
        return "—"
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= max_chars:
        return text

    cut = text[:max_chars]
    last_period = cut.rfind(".")
    if last_period > max_chars * 0.6:
        return cut[: last_period + 1].strip()

    last_space = cut.rfind(" ")
    if last_space > 0:
        clean_cut = cut[:last_space].strip()
        clean_cut = re.sub(
            r"\s+(?:en|de|y|a|el|la|los|las|del|con|para|por)\s*$",
            "",
            clean_cut,
            flags=re.IGNORECASE,
        )
        return clean_cut + "..."
    return cut + "..."


def extract_business_areas(business_impact: str) -> List[str]:
    """
    Extrae los nombres de áreas de negocio de alto nivel (ej. 'Ventas', 'Provisión', 'Atención al Cliente')
    sin incluir las descripciones operativas extensas.
    """
    if not business_impact or business_impact.strip() in ["—", "-", "N/A", "None"]:
        return []

    cleaned = re.sub(
        r"^(?:###?\s*)?Impacto\s+(?:en|de)\s+Negocio\s*[:\n]?",
        "",
        business_impact.strip(),
        flags=re.I,
    )
    cleaned = cleaned.replace("**", "").replace("__", "")

    areas = []
    matches = re.findall(
        r"(?:^|[\n\r•\-\*]|(?:Afecci[oó]n\s+(?:a|en)|Afectaci[oó]n\s+(?:a|en)|Impacto\s+en))\s*([A-Za-zÀ-ÿ\s/()]{2,40}?)\s*:\s*",
        cleaned,
        flags=re.I,
    )
    for a in matches:
        a = a.strip()
        a = re.sub(
            r"^(?:Afecci[oó]n\s+(?:a|en)|Afectaci[oó]n\s+(?:a|en)|Impacto\s+en)\s+",
            "",
            a,
            flags=re.I,
        ).strip()
        if (
            a
            and a.lower()
            not in ["negocio", "impacto", "clientes", "general", "servicio", "servicios", "nota"]
            and a not in areas
        ):
            areas.append(a)

    if not areas:
        parts = [p.strip().rstrip(".") for p in re.split(r"[,;]\s*|\s+y\s+", cleaned) if p.strip()]
        cleaned_parts = []
        for p in parts:
            p_clean = re.sub(
                r"^(?:Afecci[oó]n\s+(?:a|en)|Afectaci[oó]n\s+(?:a|en)|Impacto\s+en)\s+",
                "",
                p,
                flags=re.I,
            ).strip()
            if p_clean and p_clean.lower() not in ["negocio", "impacto"] and len(p_clean) < 40:
                cleaned_parts.append(p_clean)
        if cleaned_parts:
            areas = cleaned_parts

    return areas


def format_impact_content(impact_raw: str, business_impact_raw: str = "") -> Tuple[str, str]:
    """
    Formatea la sección de impacto para el informe ejecutivo PowerPoint:
    - main_impact: Texto completo del impacto general (sin truncar).
    - business_summary: Referencia concisa a las áreas de negocio afectadas.
    """
    if not impact_raw:
        return ("—", "")

    split_m = re.split(
        r"(?:###?\s*)?Impacto\s+(?:en|de)\s+Negocio\s*[:\n]?",
        impact_raw,
        flags=re.I,
    )
    main_text = split_m[0].strip()
    embedded_biz = split_m[1].strip() if len(split_m) > 1 else ""

    main_clean = re.sub(r"^#{1,6}\s+.*$", "", main_text, flags=re.MULTILINE)
    main_lines = [l.strip() for l in main_clean.splitlines() if l.strip()]
    main_impact = " ".join(main_lines) if main_lines else main_text

    biz_source = (
        business_impact_raw
        if (business_impact_raw and business_impact_raw.strip() != "—")
        else embedded_biz
    )
    areas = extract_business_areas(biz_source)

    business_summary = ""
    if areas:
        if len(areas) > 4:
            areas_str = ", ".join(areas[:3]) + ", etc."
        elif len(areas) > 1:
            areas_str = ", ".join(areas[:-1]) + " y " + areas[-1]
        else:
            areas_str = areas[0]
        business_summary = f"Impacto en Negocio: {areas_str}."

    return (main_impact, business_summary)


def format_impact_lines(impact_raw: str, business_impact_raw: str = "") -> List[str]:
    """Formateador retrocompatible de líneas de impacto."""
    main_impact, biz_summary = format_impact_content(impact_raw, business_impact_raw)
    if biz_summary:
        return [main_impact, biz_summary]
    return [main_impact]


def format_event_text(event_raw: str, max_chars: int = 180) -> str:
    """Limpia y condensa eventos de cronología en hitos ejecutivos."""
    if not event_raw:
        return "—"
    text = re.sub(r"\s+", " ", event_raw).strip()
    if len(text) <= max_chars:
        return text

    text = re.sub(
        r"Entre las sedes afectadas se incluyen.*",
        "afectando a múltiples sedes de ATC.",
        text,
        flags=re.IGNORECASE,
    )
    if len(text) <= max_chars:
        return text

    cut = text[:max_chars]
    last_period = cut.rfind(".")
    if last_period > max_chars * 0.6:
        return cut[: last_period + 1].strip()

    last_space = cut.rfind(" ")
    if last_space > 0:
        clean_cut = cut[:last_space].strip()
        clean_cut = re.sub(
            r"\s+(?:en|de|y|a|el|la|los|las|del|con|para|por)\s*$",
            "",
            clean_cut,
            flags=re.IGNORECASE,
        )
        return clean_cut + "..."
    return cut + "..."


def style_impact_textbox(shape, raw_impact: str, raw_business_impact: str = "") -> None:
    """Posiciona y formatea el cuadro de texto de Impacto (CuadroTexto 10)."""
    shape.left = Inches(0.40)
    shape.top = Inches(0.91)
    shape.width = Inches(9.20)
    shape.height = Inches(0.58)

    tf = shape.text_frame
    tf.word_wrap = True
    tf.margin_left = Pt(2)
    tf.margin_right = Pt(2)
    tf.margin_top = Pt(1)
    tf.margin_bottom = Pt(1)
    tf.clear()

    main_impact, biz_summary = format_impact_content(raw_impact, raw_business_impact)

    total_chars = len(main_impact) + len(biz_summary)
    if total_chars > 360:
        font_size = Pt(7.5)
    elif total_chars > 260:
        font_size = Pt(8.0)
    else:
        font_size = Pt(8.5)

    p1 = tf.paragraphs[0]
    p1.space_after = Pt(2) if biz_summary else Pt(0)
    p1.line_spacing = 1.05
    run1 = p1.add_run()
    run1.text = main_impact
    run1.font.size = font_size
    run1.font.bold = False

    if biz_summary:
        p2 = tf.add_paragraph()
        p2.space_after = Pt(0)
        p2.line_spacing = 1.05

        label_match = re.match(r"^(Impacto\s+en\s+Negocio\s*:\s*)(.*)", biz_summary, flags=re.I)
        if label_match:
            lbl_run = p2.add_run()
            lbl_run.text = label_match.group(1)
            lbl_run.font.size = font_size
            lbl_run.font.bold = True

            val_run = p2.add_run()
            val_run.text = label_match.group(2)
            val_run.font.size = font_size
            val_run.font.bold = False
        else:
            r2 = p2.add_run()
            r2.text = biz_summary
            r2.font.size = font_size
            r2.font.bold = False


def style_cause_textbox(shape, raw_cause: str) -> None:
    """Posiciona y formatea el cuadro de texto de Causa Raíz (CuadroTexto 21)."""
    shape.left = Inches(0.40)
    shape.top = Inches(1.95)
    shape.width = Inches(4.70)
    shape.height = Inches(1.25)

    tf = shape.text_frame
    tf.word_wrap = True
    tf.margin_left = Pt(2)
    tf.margin_right = Pt(2)
    tf.margin_top = Pt(1)
    tf.margin_bottom = Pt(1)
    tf.clear()

    cause_text = clean_executive_text(raw_cause, 450)
    font_size = Pt(7.5) if len(cause_text) > 300 else Pt(8.5)

    p = tf.paragraphs[0]
    p.space_after = Pt(2)
    p.line_spacing = 1.05
    run = p.add_run()
    run.text = cause_text
    run.font.size = font_size
    run.font.bold = False


def style_solution_textbox(shape, raw_solution: str) -> None:
    """Posiciona y formatea el cuadro de texto de Solución (CuadroTexto 22)."""
    shape.left = Inches(5.25)
    shape.top = Inches(1.95)
    shape.width = Inches(4.45)
    shape.height = Inches(1.25)

    tf = shape.text_frame
    tf.word_wrap = True
    tf.margin_left = Pt(2)
    tf.margin_right = Pt(2)
    tf.margin_top = Pt(1)
    tf.margin_bottom = Pt(1)
    tf.clear()

    sol_text = clean_executive_text(raw_solution, 450)
    font_size = Pt(7.5) if len(sol_text) > 300 else Pt(8.5)

    p = tf.paragraphs[0]
    p.space_after = Pt(2)
    p.line_spacing = 1.05
    run = p.add_run()
    run.text = sol_text
    run.font.size = font_size
    run.font.bold = False

