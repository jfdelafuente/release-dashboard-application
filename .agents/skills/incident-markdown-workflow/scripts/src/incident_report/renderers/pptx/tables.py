"""
Formateo, balanceo de columnas y población de tablas PowerPoint (Puntos de Acción y Cronología).
"""

import copy
from typing import List
from pptx.util import Inches, Pt
from incident_report.domain.models import ActionPoint, ChronologyEvent
from incident_report.renderers.pptx.styler import (
    BLACK_COLOR,
    MAX_CHRONO_ROWS,
    clean_executive_text,
    format_event_text,
)


def populate_action_table(shape, action_points: List[ActionPoint]) -> None:
    """
    Posiciona, equilibra anchos de columna y rellena la tabla de Puntos de Acción en la Diapositiva 1.
    """
    shape.left = Inches(0.33)
    shape.top = Inches(3.75)
    table = shape.table

    table.columns[0].width = Inches(1.40)
    table.columns[1].width = Inches(5.40)
    table.columns[2].width = Inches(1.40)
    table.columns[3].width = Inches(1.18)

    tbl = table._tbl
    tr_elements = tbl.xpath("./a:tr")
    if not tr_elements:
        return

    template_row_tr = tr_elements[1] if len(tr_elements) > 1 else tr_elements[0]

    items = (
        action_points
        if action_points
        else [
            ActionPoint(
                pain_point="—",
                description="No se definieron puntos de acción",
                owner="—",
                forecast="—",
            )
        ]
    )
    needed_rows = 1 + len(items)

    current_rows = len(table.rows)
    while current_rows < needed_rows:
        new_tr = copy.deepcopy(template_row_tr)
        tbl.append(new_tr)
        current_rows += 1
    while current_rows > needed_rows:
        tr_elements = tbl.xpath("./a:tr")
        tbl.remove(tr_elements[-1])
        current_rows -= 1

    font_size = Pt(7.5) if len(items) > 3 else Pt(8.0)

    for i, ap in enumerate(items):
        row = table.rows[1 + i]
        vals = [
            clean_executive_text(ap.pain_point or "—", 50),
            clean_executive_text(ap.description or "—", 220),
            clean_executive_text(ap.owner or "—", 30),
            clean_executive_text(ap.forecast or "—", 25),
        ]
        for col_idx, val in enumerate(vals):
            cell = row.cells[col_idx]
            cell.margin_top = Pt(1.5)
            cell.margin_bottom = Pt(1.5)
            cell.margin_left = Pt(3)
            cell.margin_right = Pt(3)
            cell.text_frame.clear()
            p = cell.text_frame.paragraphs[0]
            p.line_spacing = 1.05
            run = p.add_run()
            run.text = val
            run.font.size = font_size
            run.font.bold = False
            run.font.color.rgb = BLACK_COLOR


def populate_chronology_table(shape, raw_events: List[ChronologyEvent]) -> None:
    """
    Posiciona, equilibra columnas, limita a hitos ejecutivos y formatea la tabla de Cronología en Diapositiva 2.
    """
    shape.left = Inches(0.31)
    shape.top = Inches(0.68)
    table = shape.table

    table.columns[0].width = Inches(0.75)
    table.columns[1].width = Inches(8.63)

    events = list(raw_events)
    if len(events) > MAX_CHRONO_ROWS:
        first_chunk = events[:5]
        middle_candidates = events[5:-2]
        step = max(1, len(middle_candidates) // 6)
        selected_middle = middle_candidates[::step][:6]
        summary_marker = ChronologyEvent(
            time="...",
            event="[Hitos intermedios de verificación técnica omitidos para resumen ejecutivo]",
        )
        last_chunk = events[-2:]
        events = first_chunk + selected_middle + [summary_marker] + last_chunk
        if len(events) > MAX_CHRONO_ROWS:
            events = events[: MAX_CHRONO_ROWS - 1] + [events[-1]]
    elif not events:
        events = [ChronologyEvent(time="—", event="No hay eventos registrados en la cronología")]

    tbl = table._tbl
    tr_elements = tbl.xpath("./a:tr")
    if not tr_elements:
        return

    template_row_tr = tr_elements[1] if len(tr_elements) > 1 else tr_elements[0]

    needed_rows = 1 + len(events)
    current_rows = len(table.rows)

    while current_rows < needed_rows:
        new_tr = copy.deepcopy(template_row_tr)
        tbl.append(new_tr)
        current_rows += 1
    while current_rows > needed_rows:
        tr_elements = tbl.xpath("./a:tr")
        tbl.remove(tr_elements[-1])
        current_rows -= 1

    for i, ev in enumerate(events):
        row = table.rows[1 + i]
        c0 = row.cells[0]
        c0.margin_top = Pt(1.5)
        c0.margin_bottom = Pt(1.5)
        c0.margin_left = Pt(3)
        c0.margin_right = Pt(3)
        c0.text_frame.clear()
        p0 = c0.text_frame.paragraphs[0]
        r0 = p0.add_run()
        r0.text = ev.time or ""
        r0.font.size = Pt(7.5)

        c1 = row.cells[1]
        c1.margin_top = Pt(1.5)
        c1.margin_bottom = Pt(1.5)
        c1.margin_left = Pt(3)
        c1.margin_right = Pt(3)
        c1.text_frame.clear()
        p1 = c1.text_frame.paragraphs[0]
        p1.line_spacing = 1.05
        r1 = p1.add_run()
        r1.text = format_event_text(ev.event, 180)
        r1.font.size = Pt(7.5)

