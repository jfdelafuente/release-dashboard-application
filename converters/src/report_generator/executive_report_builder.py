"""
Generador de informes ejecutivos PowerPoint basados en la plantilla corporativa Orange.
Feature 010: 010-incident-executive-report
"""

from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

import pptx
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor

from converters.src.report_generator.executive_models import (
    ExecutiveIncidentData,
    ExecutiveActionPoint,
    ExecutiveTimelineEvent,
    ReportMetadata,
)
from converters.src.report_generator.executive_paths import (
    get_executive_template_path,
    get_executive_report_path,
    get_executive_report_filename,
)


def _set_run_text_preserving_style(paragraph, text: str):
    """Establece texto en un párrafo preservando la tipografía, tamaño y color del primer run."""
    if not paragraph.runs:
        paragraph.text = text
        return

    first_run = paragraph.runs[0]
    font_name = first_run.font.name
    font_size = first_run.font.size
    bold = first_run.font.bold
    italic = first_run.font.italic
    color_rgb = None
    try:
        if first_run.font.color and first_run.font.color.type == 1:
            color_rgb = first_run.font.color.rgb
    except Exception:
        pass

    # Reemplazar texto
    paragraph.text = text
    if paragraph.runs:
        r = paragraph.runs[0]
        if font_name:
            r.font.name = font_name
        if font_size:
            r.font.size = font_size
        if bold is not None:
            r.font.bold = bold
        if italic is not None:
            r.font.italic = italic
        if color_rgb:
            r.font.color.rgb = color_rgb


def _set_cell_text(cell, text: str, font_size_pt: Optional[float] = None, bold: Optional[bool] = None):
    """Escribe texto en una celda de tabla preservando el estilo base del formato."""
    p = cell.text_frame.paragraphs[0] if cell.text_frame.paragraphs else cell.text_frame.add_paragraph()
    _set_run_text_preserving_style(p, text)
    if font_size_pt and p.runs:
        p.runs[0].font.size = Pt(font_size_pt)
    if bold is not None and p.runs:
        p.runs[0].font.bold = bold


class ExecutiveReportBuilder:
    """Construye y rellena la presentación ejecutiva .pptx a partir de datos estructurados."""

    def __init__(self, template_path: Optional[Path] = None):
        self.template_path = Path(template_path) if template_path else get_executive_template_path()

    def generate(self, data: ExecutiveIncidentData, output_path: Optional[Path] = None) -> ReportMetadata:
        """
        Carga la plantilla PowerPoint, rellena las diapositivas con los datos del postmortem
        y guarda el informe en la ruta especificada.
        """
        if not self.template_path.is_file():
            raise FileNotFoundError(f"Plantilla base PowerPoint no encontrada: {self.template_path}")

        prs = pptx.Presentation(str(self.template_path))

        # Título estándar reutilizado en todas las diapositivas
        title_text = f"RESUMEN EJECUTIVO INCIDENCIA- TT {data.incident_ref} - {data.title}"

        # 1. Rellenar Diapositiva 1 (Resumen, impacto, causa, solución y acciones)
        self._populate_slide_1(prs.slides[0], data, title_text)

        # 2. Rellenar Diapositivas 2 y 3+ (Cronología de eventos)
        self._populate_timeline_slides(prs, data.timeline_events, title_text)

        # Guardar archivo
        dest_path = Path(output_path) if output_path else get_executive_report_path(data.incident_ref)
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        prs.save(str(dest_path))

        size_bytes = dest_path.stat().st_size
        generated_at = datetime.now(timezone.utc).isoformat()

        return ReportMetadata(
            incident_ref=data.incident_ref,
            filename=dest_path.name,
            file_path=str(dest_path),
            generated_at=generated_at,
            size_bytes=size_bytes,
            slide_count=len(prs.slides),
        )

    def _populate_slide_1(self, slide, data: ExecutiveIncidentData, title_text: str):
        """Cumplimenta las formas de texto y la tabla de acciones en la primera diapositiva."""
        for shape in slide.shapes:
            # 1. Título principal
            if shape.shape_id == 4 or (shape.has_text_frame and "RESUMEN EJECUTIVO INCIDENCIA" in shape.text_frame.text):
                _set_run_text_preserving_style(shape.text_frame.paragraphs[0], title_text)

            # 2. Subtítulo (Inicio y Duración)
            elif shape.shape_id == 3 or (shape.has_text_frame and "Inicio:" in shape.text_frame.text):
                sub_text = f"Inicio: {data.start_time or 'No especificado'}\nDuración: {data.duration or 'No especificada'}"
                _set_run_text_preserving_style(shape.text_frame.paragraphs[0], sub_text)

            # 3. IMPACTO (shape_id 11 o texto explicativo de impacto)
            elif shape.shape_id == 11:
                txt = data.impact_text or "Detalle de impacto no disponible."
                _set_run_text_preserving_style(shape.text_frame.paragraphs[0], txt)

            # 4. CAUSA (shape_id 22)
            elif shape.shape_id == 22:
                txt = data.cause_text or "Detalle de causa raíz no disponible."
                _set_run_text_preserving_style(shape.text_frame.paragraphs[0], txt)

            # 5. SOLUCION (shape_id 23)
            elif shape.shape_id == 23:
                txt = data.solution_text or "Detalle de solución aplicada no disponible."
                _set_run_text_preserving_style(shape.text_frame.paragraphs[0], txt)

            # 6. TABLA DE PUNTOS DE ACCION (4 columnas: Pain Point | Description | Owner | Forecast)
            elif shape.has_table and len(shape.table.columns) == 4:
                table = shape.table
                actions = data.action_points
                # Fila 0 es la cabecera. Filas de datos a partir de índice 1
                target_count = len(actions)

                # Ajustar cantidad de filas de la tabla si hay menos o más
                while len(table.rows) - 1 < target_count:
                    # Clonar la última fila existente
                    sample_tr = deepcopy(table.rows[len(table.rows) - 1]._tr)
                    table._tbl.append(sample_tr)

                while len(table.rows) - 1 > target_count and len(table.rows) > 2:
                    # Eliminar fila sobrante
                    last_tr = table.rows[len(table.rows) - 1]._tr
                    last_tr.getparent().remove(last_tr)

                # Si no hay acciones, dejamos 1 fila indicativa
                if not actions and len(table.rows) > 1:
                    _set_cell_text(table.rows[1].cells[0], "—")
                    _set_cell_text(table.rows[1].cells[1], "Sin puntos de acción registrados")
                    _set_cell_text(table.rows[1].cells[2], "—")
                    _set_cell_text(table.rows[1].cells[3], "—")
                else:
                    for i, ap in enumerate(actions):
                        r_idx = i + 1
                        if r_idx < len(table.rows):
                            _set_cell_text(table.rows[r_idx].cells[0], ap.pain_point or "Otros")
                            _set_cell_text(table.rows[r_idx].cells[1], ap.description or "")
                            _set_cell_text(table.rows[r_idx].cells[2], ap.owner or "—")
                            _set_cell_text(table.rows[r_idx].cells[3], ap.forecast or "—")

    def _populate_timeline_slides(self, prs, events: List[ExecutiveTimelineEvent], title_text: str):
        """
        Rellena las diapositivas de cronología (Slide 2 y Slide 3) distribuyendo los eventos.
        Si hay más de 37 eventos, clona diapositivas adicionales.
        """
        if len(prs.slides) < 2:
            return

        # Capacidad estimada por diapositiva: ~18 filas para slide 2, ~19 para slide 3
        # Repartición de eventos
        chunk_size = 18
        chunks: List[List[ExecutiveTimelineEvent]] = []
        if not events:
            chunks = [[]]
        else:
            for i in range(0, len(events), chunk_size):
                chunks.append(events[i:i + chunk_size])

        # Asegurar al menos 2 diapositivas de cronología si venían en la plantilla
        timeline_slides = [prs.slides[1]]
        if len(prs.slides) >= 3:
            timeline_slides.append(prs.slides[2])

        # Si hay más chunks que diapositivas disponibles, clonamos la última diapositiva
        while len(timeline_slides) < len(chunks):
            # Clonar la última diapositiva
            slide_layout = prs.slide_layouts[6] if len(prs.slide_layouts) > 6 else prs.slide_layouts[0]
            new_slide = prs.slides.add_slide(slide_layout)
            # Copiar formas de la diapositiva de referencia
            ref_slide = timeline_slides[-1]
            for shape in ref_slide.shapes:
                if shape.has_table:
                    # Copiar tabla
                    t = shape.table
                    rows = len(t.rows)
                    cols = len(t.columns)
                    new_table_shape = new_slide.shapes.add_table(rows, cols, shape.left, shape.top, shape.width, shape.height)
                    for r_idx in range(rows):
                        for c_idx in range(cols):
                            new_table_shape.table.cell(r_idx, c_idx).text = t.cell(r_idx, c_idx).text
                elif shape.has_text_frame:
                    new_tx = new_slide.shapes.add_textbox(shape.left, shape.top, shape.width, shape.height)
                    new_tx.text_frame.text = shape.text_frame.text
            timeline_slides.append(new_slide)

        # Rellenar cada diapositiva con su respectivo chunk de eventos
        for idx, slide in enumerate(timeline_slides):
            # Actualizar título
            for shape in slide.shapes:
                if shape.shape_id == 4 or (shape.has_text_frame and "RESUMEN EJECUTIVO INCIDENCIA" in shape.text_frame.text):
                    _set_run_text_preserving_style(shape.text_frame.paragraphs[0], title_text)

            chunk = chunks[idx] if idx < len(chunks) else []

            # Encontrar tabla de cronología (2 columnas: Hora | Evento)
            for shape in slide.shapes:
                if shape.has_table and len(shape.table.columns) == 2:
                    table = shape.table
                    # Fila 0 es cabecera ("Hora", "Evento")
                    target_rows = max(len(chunk), 1)

                    # Ajustar número de filas
                    while len(table.rows) - 1 < target_rows:
                        sample_tr = deepcopy(table.rows[len(table.rows) - 1]._tr)
                        table._tbl.append(sample_tr)

                    while len(table.rows) - 1 > target_rows and len(table.rows) > 2:
                        last_tr = table.rows[len(table.rows) - 1]._tr
                        last_tr.getparent().remove(last_tr)

                    if not chunk:
                        if len(table.rows) > 1:
                            _set_cell_text(table.rows[1].cells[0], "—")
                            _set_cell_text(table.rows[1].cells[1], "Sin eventos cronológicos registrados")
                    else:
                        for e_idx, event in enumerate(chunk):
                            r_idx = e_idx + 1
                            if r_idx < len(table.rows):
                                _set_cell_text(table.rows[r_idx].cells[0], event.time or "")
                                _set_cell_text(table.rows[r_idx].cells[1], event.event or "")
