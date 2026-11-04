"""
Parser de documentos Markdown estructurados hacia objetos IncidentReport (Etapa 2).
"""

import re
from typing import List
from incident_report.domain.models import ActionPoint, ChronologyEvent, IncidentReport


def parse_markdown_table(text: str) -> List[List[str]]:
    """
    Parsea una tabla Markdown en una lista de filas de celdas (excluyendo cabecera y separador).
    """
    rows = []
    lines = [line.strip() for line in text.strip().split("\n") if line.strip().startswith("|")]
    if len(lines) < 2:
        return rows

    data_lines = lines[2:]
    for line in data_lines:
        cells = [c.strip() for c in line.strip("|").split("|")]
        if any(c and not set(c).issubset({"-", ":", " "}) for c in cells):
            rows.append(cells)
    return rows


def parse_from_markdown(content: str) -> IncidentReport:
    """
    Parsea un documento Markdown estructurado en un objeto IncidentReport.
    """
    report = IncidentReport()

    sections = {}
    current_section = None
    current_lines = []

    for line in content.splitlines():
        h2_match = re.match(r"^##\s+(.+)$", line.strip())
        if h2_match:
            if current_section:
                sections[current_section] = "\n".join(current_lines).strip()
            current_section = h2_match.group(1).strip().lower()
            current_lines = []
        else:
            if current_section:
                current_lines.append(line)

    if current_section:
        sections[current_section] = "\n".join(current_lines).strip()

    # 1. Metadatos
    meta_text = sections.get("metadatos", "")
    for line in meta_text.splitlines():
        match = re.search(r"-\s*\*\*([^:]+)\*\*:\s*(.*)", line)
        if match:
            k = match.group(1).strip().lower()
            v = match.group(2).strip()
            if v == "—":
                v = ""
            if "id" in k or "tt" in k:
                report.incident_id = v
            elif "título" in k or "titulo" in k:
                report.title = v
            elif "inicio" in k:
                report.start_time = v
            elif "fin" in k:
                report.end_time = v
            elif "duración" in k or "duracion" in k:
                report.duration = v

    # 2. Impacto de Negocio
    biz_key = next(
        (
            k
            for k in sections
            if ("impacto" in k and "negocio" in k)
            or "business" in k
            or k in ["impacto de negocio", "impacto en negocio"]
        ),
        None,
    )
    if biz_key:
        report.business_impact = sections[biz_key].strip()

    # 3. Impacto General
    impact_key = next((k for k in sections if "impacto" in k and "negocio" not in k), None)
    if impact_key:
        impact_val = sections[impact_key].strip()
        if not report.business_impact or report.business_impact == "—":
            split_m = re.split(
                r"(?:###?\s*)?(?:Impacto\s+(?:en|de|al|a|para)\s+(?:el\s+)?Negocio|Business\s+Impact)\s*[:\n]?",
                impact_val,
                flags=re.I,
            )
            if len(split_m) > 1:
                report.impact = split_m[0].strip()
                report.business_impact = split_m[1].strip()
            else:
                report.impact = impact_val
        else:
            report.impact = impact_val

    # 4. Causa Raíz
    cause_key = next((k for k in sections if "causa" in k), None)
    if cause_key:
        report.cause = sections[cause_key].strip()

    # 5. Solución
    sol_key = next((k for k in sections if "solución" in k or "solucion" in k), None)
    if sol_key:
        report.solution = sections[sol_key].strip()

    # 6. Puntos de Acción
    action_key = next((k for k in sections if "acción" in k or "accion" in k or "puntos" in k), None)
    if action_key:
        raw_table = parse_markdown_table(sections[action_key])
        action_points = []
        for row in raw_table:
            pp = row[0] if len(row) > 0 and row[0] != "—" else "—"
            desc = row[1] if len(row) > 1 and row[1] != "—" else "—"
            owner = row[2] if len(row) > 2 and row[2] != "—" else "—"
            fc = row[3] if len(row) > 3 and row[3] != "—" else "—"
            if desc != "—" or pp != "—":
                action_points.append(
                    ActionPoint(pain_point=pp, description=desc, owner=owner, forecast=fc)
                )
        report.action_points = action_points

    # 7. Cronología
    crono_key = next((k for k in sections if "cronología" in k or "cronologia" in k or "hitos" in k), None)
    if crono_key:
        raw_crono = parse_markdown_table(sections[crono_key])
        chronology = []
        for row in raw_crono:
            t = row[0] if len(row) > 0 and row[0] != "—" else ""
            ev = row[1] if len(row) > 1 and row[1] != "—" else ""
            if t or ev:
                chronology.append(ChronologyEvent(time=t, event=ev))
        report.chronology = chronology

    return report

