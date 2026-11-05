"""
Orquestador de construcción de diapositivas PowerPoint (PPTXGenerator).
"""

import os
from pptx import Presentation
from pptx.util import Pt
from incident_report.config import resolve_template_path
from incident_report.domain.models import IncidentReport
from incident_report.renderers.base import BaseRenderer
from incident_report.renderers.pptx.styler import (
    style_cause_textbox,
    style_impact_textbox,
    style_solution_textbox,
)
from incident_report.renderers.pptx.tables import (
    populate_action_table,
    populate_chronology_table,
)


class PPTXGenerator(BaseRenderer):
    """
    Adaptador de renderizado PowerPoint (.pptx) en 2 diapositivas ejecutivas.
    Soporta resolución de plantillas desde `assets/templates/` o rutas directas.
    """

    def __init__(self, template_path: str = None):
        self.template_path = resolve_template_path(template_path)

    def render(self, report: IncidentReport, output_path: str) -> str:
        return self.generate(report, output_path)

    def generate(self, report: IncidentReport, output_path: str) -> str:
        """
        Genera una presentación ejecutiva de 2 diapositivas a partir de un IncidentReport.
        Devuelve la ruta final donde se guardó el archivo.
        """
        validation_errors = report.validate()
        if validation_errors:
            raise ValueError(
                f"Faltan campos obligatorios para generar el informe: {', '.join(validation_errors)}"
            )

        if not os.path.exists(self.template_path):
            raise FileNotFoundError(
                f"Plantilla base de PowerPoint no encontrada: {self.template_path}"
            )

        prs = Presentation(self.template_path)

        # 1. Actualizar Diapositiva 1
        self._update_slide_1(prs.slides[0], report)

        # 2. Actualizar Diapositiva 2
        if len(prs.slides) > 1:
            self._update_slide_2(prs.slides[1], report)

        # 3. Asegurar exactamente 2 diapositivas
        self._trim_to_two_slides(prs)

        # 4. Guardar presentación de forma segura (manejando bloqueo de archivo en Windows)
        final_output_path = output_path
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        try:
            prs.save(final_output_path)
        except PermissionError:
            base, ext = os.path.splitext(output_path)
            final_output_path = f"{base}_actualizado{ext}"
            prs.save(final_output_path)
            print(
                f"[Aviso] El archivo '{output_path}' está abierto en otra aplicación. Se guardó como '{final_output_path}'."
            )

        return final_output_path

    def _update_slide_1(self, slide, report: IncidentReport) -> None:
        formatted_title = report.get_formatted_title()

        for shape in slide.shapes:
            if (
                shape.name.startswith("Título")
                or shape.name.startswith("Ttulo")
                or (shape.has_text_frame and "RESUMEN EJECUTIVO" in shape.text_frame.text)
            ):
                shape.text_frame.clear()
                p = shape.text_frame.paragraphs[0]
                run = p.add_run()
                run.text = formatted_title
                run.font.size = Pt(12)
                run.font.bold = True
                break

        for shape in slide.shapes:
            if shape.name.startswith("Subtítulo") or shape.name.startswith("Subttulo"):
                if shape.has_text_frame and "Inicio:" in shape.text_frame.text:
                    shape.text_frame.clear()
                    p0 = shape.text_frame.paragraphs[0]
                    r0_label = p0.add_run()
                    r0_label.text = "Inicio: "
                    r0_label.font.bold = True
                    r0_label.font.size = Pt(9)
                    r0_val = p0.add_run()
                    r0_val.text = report.start_time or "No disponible"
                    r0_val.font.bold = False
                    r0_val.font.size = Pt(9)

                    p1 = shape.text_frame.add_paragraph()
                    r1_label = p1.add_run()
                    r1_label.text = "Duración: "
                    r1_label.font.bold = True
                    r1_label.font.size = Pt(9)
                    r1_val = p1.add_run()
                    r1_val.text = report.duration or "No disponible"
                    r1_val.font.bold = False
                    r1_val.font.size = Pt(9)
                    break

        for shape in slide.shapes:
            if shape.name == "CuadroTexto 10":
                self._update_impact_textbox(shape, report.impact or "", report.business_impact or "")
            elif shape.name == "TextBox 11" and shape.has_text_frame:
                shape.text_frame.clear()
            elif shape.name == "CuadroTexto 21":
                self._update_cause_textbox(shape, report.cause)
            elif shape.name == "CuadroTexto 22":
                self._update_solution_textbox(shape, report.solution)

        table_shape = next(
            (s for s in slide.shapes if s.has_table and len(s.table.columns) == 4), None
        )
        if table_shape:
            self._update_action_table(table_shape, report.action_points)

    def _update_slide_2(self, slide, report: IncidentReport) -> None:
        formatted_title = report.get_formatted_title()

        for shape in slide.shapes:
            if (
                shape.name.startswith("Título")
                or shape.name.startswith("Ttulo")
                or (shape.has_text_frame and "RESUMEN EJECUTIVO" in shape.text_frame.text)
            ):
                shape.text_frame.clear()
                p = shape.text_frame.paragraphs[0]
                run = p.add_run()
                run.text = formatted_title
                run.font.size = Pt(12)
                run.font.bold = True
                break

        table_shape = next(
            (s for s in slide.shapes if s.has_table and len(s.table.columns) == 2), None
        )
        if table_shape:
            self._update_chronology_table(table_shape, report.chronology)

    def _trim_to_two_slides(self, prs: Presentation) -> None:
        while len(prs.slides) > 2:
            slide_id_list = prs.slides._sldIdLst
            slide_elem = slide_id_list[2]
            rId = slide_elem.attrib[
                "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
            ]
            prs.part.drop_rel(rId)
            slide_id_list.remove(slide_elem)

    _update_impact_textbox = staticmethod(style_impact_textbox)
    _update_cause_textbox = staticmethod(style_cause_textbox)
    _update_solution_textbox = staticmethod(style_solution_textbox)
    _update_action_table = staticmethod(populate_action_table)
    _update_chronology_table = staticmethod(populate_chronology_table)

