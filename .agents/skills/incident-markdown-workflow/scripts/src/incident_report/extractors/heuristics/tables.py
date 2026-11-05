"""
Heurísticas para extracción de tablas de Puntos de Acción y Cronología (tanto tablas como bloques Time Log).
"""

import copy
import re
from bs4 import BeautifulSoup
from incident_report.domain.models import ActionPoint, ChronologyEvent, IncidentReport
from incident_report.extractors.heuristics.common import (
    clean_cell_content,
    is_checklist_table,
    is_trivial_value,
)


def parse_action_table(table, report: IncidentReport) -> None:
    """Extrae la tabla de Puntos de Acción mapeando columnas dinámicamente."""
    rows = table.find_all("tr")
    if not rows:
        return

    header_cells = rows[0].find_all(["th", "td"])
    col_map = {"pp": 0, "desc": 1, "owner": 2, "forecast": 3}
    for idx, cell in enumerate(header_cells):
        txt = cell.get_text(strip=True).lower()
        if any(k in txt for k in ["pain", "punto", "tipo", "titulo", "título"]):
            col_map["pp"] = idx
        elif any(k in txt for k in ["desc", "acci", "tarea"]):
            col_map["desc"] = idx
        elif any(k in txt for k in ["owner", "responsable", "asignado"]):
            col_map["owner"] = idx
        elif any(k in txt for k in ["forecast", "fecha", "plazo", "estado"]):
            col_map["forecast"] = idx

    action_points = []
    for tr in rows[1:]:
        cells = tr.find_all(["td", "th"])
        if not cells or len(cells) < 2:
            continue

        def get_cell(col_idx):
            if col_idx < len(cells):
                val = clean_cell_content(cells[col_idx])
                return val if val else "—"
            return "—"

        pp = get_cell(col_map["pp"])
        desc = get_cell(col_map["desc"])
        owner = get_cell(col_map["owner"])
        forecast = get_cell(col_map["forecast"])

        if (desc != "—" and not is_trivial_value(desc)) or (pp != "—" and not is_trivial_value(pp)):
            action_points.append(
                ActionPoint(
                    pain_point=pp,
                    description=desc,
                    owner=owner,
                    forecast=forecast,
                )
            )
    if action_points:
        report.action_points = action_points


def parse_chronology_table(table, report: IncidentReport) -> None:
    """Extrae la tabla de Cronología de Hitos."""
    rows = table.find_all("tr")
    if not rows:
        return

    header_cells = rows[0].find_all(["th", "td"])
    time_idx, event_idx = 0, 1
    for idx, cell in enumerate(header_cells):
        txt = cell.get_text(strip=True).lower()
        if any(k in txt for k in ["hora", "time", "fecha"]):
            time_idx = idx
        elif any(k in txt for k in ["evento", "hito", "event", "desc"]):
            event_idx = idx

    events = []
    for tr in rows[1:]:
        cells = tr.find_all(["td", "th"])
        if not cells or len(cells) < 2:
            continue
        t = clean_cell_content(cells[time_idx]) if time_idx < len(cells) else ""
        e = clean_cell_content(cells[event_idx]) if event_idx < len(cells) else ""
        if (t and not is_trivial_value(t)) or (e and not is_trivial_value(e)):
            events.append(ChronologyEvent(time=t, event=e))

    if events:
        report.chronology = events


def extract_chronology_from_sections(soup: BeautifulSoup, report: IncidentReport) -> None:
    """
    Extrae la cronología cuando está redactada en párrafos o bloques con saltos de línea (<br/>)
    bajo encabezados como 'Time Log', 'Cronología' o 'Hitos'.
    """
    events = []

    for h in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
        h_text = h.get_text(strip=True).lower()
        if any(
            k in h_text
            for k in ["time log", "cronolog", "timeline", "hitos", "log de eventos", "registro de eventos"]
        ):
            for sib in h.find_next_siblings():
                if sib.name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
                    if sib.get_text(strip=True):
                        break
                if sib.name == "table":
                    parse_chronology_table(sib, report)
                    if report.chronology:
                        return
                    continue

                sib_copy = copy.copy(sib)
                for m in sib_copy.find_all(["ac:structured-macro", "structured-macro"]):
                    macro_name = m.get("ac:name") or m.get("name")
                    if macro_name == "jira":
                        key_tag = (
                            m.find(["ac:parameter", "parameter"], attrs={"ac:name": "key"})
                            or m.find(["ac:parameter", "parameter"], attrs={"name": "key"})
                        )
                        k_val = key_tag.get_text(strip=True) if key_tag else ""
                        m.replace_with(f" ({k_val})" if k_val else "")
                    else:
                        m.decompose()

                for t in sib_copy.find_all("time"):
                    dt = t.get("datetime", "")
                    if dt:
                        parts = dt.split("-")
                        if len(parts) == 3:
                            t.replace_with(f"{parts[2]}/{parts[1]}/{parts[0]}")
                        else:
                            t.replace_with(dt)
                    else:
                        t.decompose()

                for br in sib_copy.find_all(["br", "hr"]):
                    br.replace_with("\n")

                raw_text = sib_copy.get_text("\n", strip=True)
                lines = [l.strip() for l in raw_text.split("\n") if l.strip()]

                for line in lines:
                    clean_line = re.sub(r"^[\s\-\*\•\"\'“”«»]+", "", line).strip()
                    clean_line = re.sub(r"[\"\'“”«»]+$", "", clean_line).strip()
                    if not clean_line:
                        continue

                    # Ignore standalone date headers (e.g. '09/06' or 'Día 09/06')
                    if re.match(
                        r"^(?:d[ií]a\s+)?\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?$",
                        clean_line,
                        re.IGNORECASE,
                    ):
                        continue

                    m = re.match(
                        r"^((?:(?:\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?)\s+)?\d{1,2}[:.h]\d{2}(?::\d{2})?(?:\s*(?:CET|CEST|UTC|GMT|h\b))?)\s*[-–—:]?\s*(.+)$",
                        clean_line,
                        re.IGNORECASE,
                    )
                    if m:
                        t_val = m.group(1).strip()
                        e_val = m.group(2).strip()
                        if t_val and e_val:
                            events.append(ChronologyEvent(time=t_val, event=e_val))
                    elif events and clean_line:
                        events[-1].event = f"{events[-1].event} {clean_line}".strip()

            if events:
                report.chronology = events
                break


def extract_tables(soup: BeautifulSoup, report: IncidentReport) -> None:
    """Identifica y procesa las tablas de Puntos de Acción y Cronología en el documento HTML."""
    tables = soup.find_all("table")
    for table in tables:
        if is_checklist_table(table):
            continue
        rows = table.find_all("tr")
        if not rows:
            continue

        header_tr = (
            table.find("thead").find("tr")
            if table.find("thead") and table.find("thead").find("tr")
            else rows[0]
        )
        header_cells = header_tr.find_all(["th", "td"])
        headers = [c.get_text(strip=True).lower() for c in header_cells]
        headers_str = " ".join(headers)

        if any(k in headers_str for k in ["pain point", "punto", "acción", "accion"]) and any(
            k in headers_str for k in ["owner", "responsable", "forecast", "fecha", "plazo"]
        ):
            parse_action_table(table, report)

        elif ("cronolog" in headers_str or "timeline" in headers_str) or (
            any(any(k in h for k in ["hora", "time", "timestamp"]) for h in headers)
            and any(any(k in h for k in ["evento", "hito", "event", "descrip", "actividad"]) for h in headers)
        ):
            parse_chronology_table(table, report)

    if not report.chronology:
        extract_chronology_from_sections(soup, report)
