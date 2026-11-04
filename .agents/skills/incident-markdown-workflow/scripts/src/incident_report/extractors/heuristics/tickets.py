"""
Heurísticas para extracción y filtrado de códigos de incidencia / tickets (INC, TT, PROB, PRB, IM)
y títulos de postmortem.
"""

import re
from bs4 import BeautifulSoup
from incident_report.domain.models import IncidentReport
from incident_report.extractors.heuristics.common import is_trivial_value

EXCLUDED_TICKET_KEY_TERMS = [
    "relacionad",
    "asociad",
    "otro",
    "previo",
    "anterior",
    "recurrent",
    "creaci",
    "fin",
    "cierre",
    "seguimiento",
    "gesti",
    "detectad",
    "detecci",
    "alarma",
    "tiempo",
    "aviso",
    "escalad",
]

PRIMARY_TICKET_KEYS = [
    "ticket de la incidencia masiva",
    "ticket de la incidencia",
    "id de la incidencia",
    "id incidencia",
    "ticket incidencia",
    "número de ticket",
    "numero de ticket",
    "nº ticket",
    "código de incidencia",
    "codigo de incidencia",
    "ticket id",
    "id ticket",
    "ticket masivo",
    "incidencia masiva",
]

SECONDARY_TICKET_KEYS = [
    "ticket / tt",
    "ticket/tt",
    "ticket",
    "tt",
    "incidencia",
]


def is_primary_incident_id_key(k: str) -> bool:
    """Identifica si una etiqueta de tabla corresponde al ID de ticket principal de la incidencia."""
    if any(ex in k for ex in EXCLUDED_TICKET_KEY_TERMS):
        return False
    return any(pk in k for pk in PRIMARY_TICKET_KEYS)


def is_secondary_incident_id_key(k: str) -> bool:
    """Identifica si una etiqueta de tabla es candidata secundaria a ID de ticket."""
    if any(ex in k for ex in EXCLUDED_TICKET_KEY_TERMS + ["tipo"]):
        return False
    return any(sk in k for sk in SECONDARY_TICKET_KEYS)


def extract_clean_incident_id(v: str) -> str:
    """Extrae un identificador limpio de ticket a partir del texto de una celda."""
    if not v or is_trivial_value(v):
        return ""
    m = re.search(
        r"\b(INC-?\d+|TT\s*[\w\d]+|PROB-?\d+|PRB-?\d+|IM\d+|\d{4,8}[A-Z]\d+)\b",
        v,
        re.IGNORECASE,
    )
    if m:
        return m.group(1).strip()
    v_clean = v.strip()
    if len(v_clean) <= 35 and "\n" not in v_clean and "," not in v_clean and ";" not in v_clean:
        return v_clean
    return ""


def extract_title_and_id(soup: BeautifulSoup, report: IncidentReport) -> None:
    """Extrae el título y el código inicial de incidencia desde el encabezado principal (H1 / title)."""
    title_tag = soup.find("h1", id="title-text") or soup.find("h1") or soup.find("title")
    if not title_tag:
        return

    raw_title = title_tag.get_text().strip()
    tt_match = re.search(
        r"(TT\s*[\w\d]+|INC-?[\w\d]+|IM[\d]+|PRB-?[\w\d]+|PROB-?[\w\d]+)",
        raw_title,
        re.IGNORECASE,
    )
    if tt_match:
        report.incident_id = tt_match.group(1).strip()
        clean_title = re.sub(
            r"^(?:Postmortem|Incidencia)?\s*[:-]?\s*(?:\[POSTMORTEM\]\s*[:-]?\s*)?(TT\s*[\w\d]+|INC-?[\w\d]+|PRB-?[\w\d]+|PROB-?[\w\d]+)\s*[:-]?\s*(?:\[POSTMORTEM\]\s*[:-]?\s*)?",
            "",
            raw_title,
            flags=re.IGNORECASE,
        ).strip()
        clean_title = clean_title.lstrip("- :").strip()
        report.title = clean_title if clean_title else raw_title
    else:
        report.title = raw_title

