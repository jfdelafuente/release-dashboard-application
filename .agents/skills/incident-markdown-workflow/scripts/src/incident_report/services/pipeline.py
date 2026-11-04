"""
Orquestador del flujo desacoplado en 2 etapas:
- Etapa 1: Ingesta (URL Confluence / Archivo HTML) -> Extracción -> Borrador Markdown estructurado.
- Etapa 2: Lectura de Markdown revisado (o directo) -> Validación -> Renderizado PowerPoint (.pptx).
"""

import os
from typing import Optional
from incident_report.domain.models import IncidentReport
from incident_report.domain.validators import apply_pending_placeholders
from incident_report.extractors.confluence.client import ConfluenceClient
from incident_report.extractors.html_parser import Extractor
from incident_report.renderers.markdown import dump_to_markdown, parse_from_markdown


class ReportPipeline:
    """
    Servicio de aplicación que coordina el ciclo de vida completo de generación del informe.
    """

    def __init__(
        self,
        use_llm: bool = False,
        verify_ssl: Optional[bool] = None,
        template_path: Optional[str] = None,
    ):
        self.use_llm = use_llm
        self.verify_ssl = verify_ssl
        self.template_path = template_path

    def fetch_html_from_url(self, url: str) -> str:
        client = ConfluenceClient(verify_ssl=self.verify_ssl)
        return client.fetch_page(url)

    def read_local_file(self, file_path: str) -> str:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    def extract_report(self, html_content: str) -> IncidentReport:
        extractor = Extractor(use_llm=self.use_llm)
        return extractor.extract_from_html(html_content)

    def save_markdown(self, report: IncidentReport, md_path: str) -> str:
        md_content = dump_to_markdown(report)
        os.makedirs(os.path.dirname(os.path.abspath(md_path)), exist_ok=True)
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)
        return md_path

    def load_from_markdown(self, md_path: str) -> IncidentReport:
        content = self.read_local_file(md_path)
        return parse_from_markdown(content)

    def render_pptx(self, report: IncidentReport, output_path: str) -> str:
        from incident_report.renderers.pptx import PPTXGenerator
        generator = PPTXGenerator(template_path=self.template_path)
        return generator.generate(report, output_path)

