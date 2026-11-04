"""
Heurísticas para extracción de metadatos temporales (Inicio, Fin, Duración) y tabla de metadatos.
"""

import re
from bs4 import BeautifulSoup
from incident_report.domain.models import IncidentReport
from incident_report.extractors.heuristics.common import (
    clean_cell_content,
    is_checklist_table,
    is_trivial_value,
)
from incident_report.extractors.heuristics.tickets import (
    extract_clean_incident_id,
    is_primary_incident_id_key,
    is_secondary_incident_id_key,
)


def extract_timing(soup: BeautifulSoup, report: IncidentReport) -> None:
    """
    Extrae fechas de inicio, fin, duración y metadatos de tablas clave-valor.
    Prioriza siempre el ticket de la incidencia masiva sobre tickets relacionados o de problema.
    """
    text = soup.get_text(" ", strip=True)

    start_match = re.search(
        r"(?:Inicio|Fecha\s*de\s*inicio|Start)(?:\s*:\s*|\s+)([0-9]{2}/[0-9]{2}/[0-9]{4}(?:\s+[0-9]{2}:[0-9]{2}(?::[0-9]{2})?)?|[0-9]{4}-[0-9]{2}-[0-9]{2}(?:\s+[0-9]{2}:[0-9]{2})?)",
        text,
        re.IGNORECASE,
    )
    if start_match and (not report.start_time or is_trivial_value(report.start_time)):
        report.start_time = start_match.group(1).strip()

    end_match = re.search(
        r"(?:Fin|Fecha\s*de\s*(?:fin|resoluci[oó]n)|End)(?:\s*:\s*|\s+)([0-9]{2}/[0-9]{2}/[0-9]{4}(?:\s+[0-9]{2}:[0-9]{2}(?::[0-9]{2})?)?|[0-9]{4}-[0-9]{2}-[0-9]{2}(?:\s+[0-9]{2}:[0-9]{2})?)",
        text,
        re.IGNORECASE,
    )
    if end_match and (not report.end_time or is_trivial_value(report.end_time)):
        report.end_time = end_match.group(1).strip()

    dur_match = re.search(
        r"(?:Duraci[oó]n|Duration)(?:\s*:\s*|\s+)([0-9]+[hm]\s*(?:[0-9]+[m])?|[0-9]+(?:\.[0-9]+)?\s*(?:horas|h|minutos|min))",
        text,
        re.IGNORECASE,
    )
    if dur_match and (not report.duration or is_trivial_value(report.duration)):
        report.duration = dur_match.group(1).strip()

    found_primary_id = False
    for table in soup.find_all("table"):
        if is_checklist_table(table):
            continue
        for tr in table.find_all("tr"):
            cells = tr.find_all(["th", "td"])
            if len(cells) >= 2:
                k = cells[0].get_text(strip=True).lower()
                v = clean_cell_content(cells[1])
                if is_trivial_value(v):
                    continue
                if "inicio" in k and (not report.start_time or is_trivial_value(report.start_time)):
                    report.start_time = v
                elif ("fin" in k or "resoluci" in k) and (not report.end_time or is_trivial_value(report.end_time)):
                    report.end_time = v
                elif "duraci" in k and (not report.duration or is_trivial_value(report.duration)):
                    report.duration = v
                elif is_primary_incident_id_key(k):
                    clean_id = extract_clean_incident_id(v)
                    if clean_id:
                        report.incident_id = clean_id
                        found_primary_id = True
                elif is_secondary_incident_id_key(k) and not found_primary_id:
                    if (
                        not report.incident_id
                        or is_trivial_value(report.incident_id)
                        or report.incident_id.startswith("PROB-")
                    ):
                        clean_id = extract_clean_incident_id(v)
                        if clean_id:
                            report.incident_id = clean_id
                elif "título" in k or "titulo" in k:
                    if not report.title or report.title == "—" or is_trivial_value(report.title):
                        report.title = v

