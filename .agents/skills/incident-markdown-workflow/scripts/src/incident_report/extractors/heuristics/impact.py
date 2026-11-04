"""
Heurísticas para extracción y separación de Impacto General vs Impacto de Negocio.
"""

import re
from incident_report.domain.models import IncidentReport
from incident_report.extractors.heuristics.common import is_trivial_value

IMPACT_KEYS = [
    "impacto",
    "afectación",
    "afectacion",
    "impact",
    "alcance",
    "servicios afectados",
    "clientes afectados",
]


def is_business_impact_key(k: str) -> bool:
    """Detecta si un encabezado o clave corresponde específicamente a Impacto de Negocio."""
    t = k.lower()
    return ("impacto" in t and "negocio" in t) or "business impact" in t


def format_business_impact(text: str) -> str:
    """
    Formatea el texto de impacto de negocio como lista estructurada de viñetas markdown
    (`- **Área**: descripción`) cuando detecta áreas operativas.
    """
    if not text or is_trivial_value(text):
        return "—"
    if text.strip().startswith("- ") or text.strip().startswith("* ") or text.strip().startswith("|"):
        return text.strip()

    prefix_pattern = r"(?:Afecci[oó]n\s+a|Afectaci[oó]n\s+a|Impacto\s+en)\s+"
    if re.search(prefix_pattern, text, flags=re.I):
        items = re.findall(
            rf"{prefix_pattern}([A-Za-zÀ-ÿ0-9\s/()]+?):\s*(.*?)(?={prefix_pattern}[A-Za-zÀ-ÿ0-9\s/()]+?:|$)",
            text,
            flags=re.DOTALL | re.I,
        )
    else:
        items = re.findall(
            r"(?:^|\n)\s*([A-Za-zÀ-ÿ0-9 /()]{2,35}?):\s*(.*?)(?=\n\s*[A-Za-zÀ-ÿ0-9 /()]{2,35}?:|$)",
            text,
            flags=re.DOTALL,
        )

    if items:
        bullets = []
        for topic, desc in items:
            topic = re.sub(r"\s+", " ", topic).strip()
            topic = re.sub(
                r"^(?:Afecci[oó]n\s+a|Afectaci[oó]n\s+a|Impacto\s+en)\s+",
                "",
                topic,
                flags=re.I,
            ).strip()
            desc = re.sub(r"\s+", " ", desc).strip()
            if topic and desc:
                bullets.append(f"- **{topic}**: {desc}")
        if bullets:
            return "\n".join(bullets)
    return text.strip()


def set_impact(report: IncidentReport, content: str) -> None:
    """
    Asigna el impacto general y, si contiene embebido un bloque 'Impacto en/de/al Negocio',
    lo separa automáticamente hacia `report.business_impact`.
    """
    if not content or is_trivial_value(content):
        return
    split_m = re.split(
        r"(?:###?\s*)?(?:Impacto\s+(?:en|de|al|a|para)\s+(?:el\s+)?Negocio|Business\s+Impact)\s*[:\n]?",
        content,
        flags=re.I,
    )
    if len(split_m) > 1:
        clean_impact = split_m[0].strip()
        if clean_impact and (
            not report.impact or is_trivial_value(report.impact) or "negocio" in report.impact.lower()
        ):
            report.impact = clean_impact
        raw_biz = split_m[1].strip()
        if not report.business_impact or report.business_impact == "—":
            report.business_impact = format_business_impact(raw_biz)
    else:
        if not report.impact or is_trivial_value(report.impact):
            report.impact = content
