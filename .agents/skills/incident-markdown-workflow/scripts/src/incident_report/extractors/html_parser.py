"""
Orquestador de extracción HTML/Confluence basado en heurísticas modulares.
"""

import re
from bs4 import BeautifulSoup
from incident_report.domain.models import IncidentReport
from incident_report.extractors.base import BaseExtractor
from incident_report.extractors.heuristics import (
    IMPACT_KEYS,
    SOLUTION_KEYS,
    clean_block_text,
    clean_cell_content,
    collect_sibling_text,
    extract_chronology_from_sections,
    extract_clean_incident_id,
    extract_tables,
    extract_timing,
    extract_title_and_id,
    format_business_impact,
    is_business_impact_key,
    is_cause_excluded,
    is_checklist_table,
    is_primary_incident_id_key,
    is_secondary_incident_id_key,
    is_solution_excluded,
    is_trivial_value,
    parse_action_table,
    parse_chronology_table,
    set_cause,
    set_impact,
    set_solution,
)


class Extractor(BaseExtractor):
    """
    Adaptador de extracción desde HTML de Confluence / exportaciones locales.
    Coordina los submódulos heurísticos de `incident_report.extractors.heuristics`.
    """

    def __init__(self, use_llm: bool = False):
        self.use_llm = use_llm

    def extract(self, raw_content: str) -> IncidentReport:
        return self.extract_from_html(raw_content)

    def extract_from_html(self, html_content: str) -> IncidentReport:
        soup = BeautifulSoup(html_content, "html.parser")
        report = IncidentReport()

        # 1. Título e identificador inicial
        extract_title_and_id(soup, report)

        # 2. Secciones clave (Impacto, Impacto de Negocio, Causa Raíz, Solución)
        self._extract_sections(soup, report)

        # 3. Tablas (Puntos de Acción y Cronología)
        extract_tables(soup, report)

        # 4. Tiempos y metadatos de tablas resumen (Inicio, Fin, Duración, ID Incidencia Masiva)
        extract_timing(soup, report)

        # 5. Refinamiento opcional con LLM
        if self.use_llm:
            from incident_report.services.llm_service import refine_report_with_llm
            refine_report_with_llm(html_content, report)

        return report

    def _extract_sections(self, soup: BeautifulSoup, report: IncidentReport) -> None:
        is_primary_cause = [-1]
        is_primary_solution = [-1]

        # Estrategia 1: Encabezados (h1 a h6)
        headings = soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])
        for h in headings:
            h_text = h.get_text(" ", strip=True).lower()
            if len(h_text) > 80:
                continue

            if is_business_impact_key(h_text):
                content = collect_sibling_text(h)
                if content and not is_trivial_value(content):
                    report.business_impact = format_business_impact(content)
            elif any(k in h_text for k in IMPACT_KEYS):
                content = collect_sibling_text(h)
                if content and not is_trivial_value(content):
                    set_impact(report, content)

            if not is_cause_excluded(h_text):
                content = collect_sibling_text(h)
                if content and not is_trivial_value(content):
                    set_cause(report, h_text, content, is_primary_cause)

            if not is_solution_excluded(h_text) and any(k in h_text for k in SOLUTION_KEYS):
                content = collect_sibling_text(h)
                if content and not is_trivial_value(content):
                    set_solution(report, h_text, content, is_primary_solution)

        # Estrategia 2: Macros estructuradas de Confluence / Paneles
        self._extract_from_confluence_macros(
            soup, report, IMPACT_KEYS, is_primary_cause, SOLUTION_KEYS, is_primary_solution
        )

        # Estrategia 3: Tablas resumen clave-valor
        self._extract_from_summary_tables(
            soup, report, IMPACT_KEYS, is_primary_cause, SOLUTION_KEYS, is_primary_solution
        )

        # Estrategia 4: Párrafos en línea con etiqueta en negrita (<p><strong>Causa:</strong> ...</p>)
        self._extract_from_inline_paragraphs(
            soup, report, IMPACT_KEYS, is_primary_cause, SOLUTION_KEYS, is_primary_solution
        )

    def _extract_from_confluence_macros(
        self,
        soup: BeautifulSoup,
        report: IncidentReport,
        impact_keys,
        is_primary_cause,
        solution_keys,
        is_primary_solution=None,
    ) -> None:
        for macro in soup.find_all(["ac:structured-macro", "structured-macro", "div"]):
            title_text = ""
            body = None
            if macro.name in ["ac:structured-macro", "structured-macro"]:
                macro_name = (macro.get("ac:name") or macro.get("name") or "").lower()
                if macro_name == "jira":
                    continue
                param = (
                    macro.find(["ac:parameter", "parameter"], attrs={"ac:name": "title"}, recursive=False)
                    or macro.find(["ac:parameter", "parameter"], recursive=False)
                )
                if param:
                    title_text = param.get_text(" ", strip=True).lower()
                body = macro.find(["ac:rich-text-body", "rich-text-body"], recursive=False)
            elif macro.name == "div" and any(
                c in (macro.get("class") or []) for c in ["panel", "confluence-information-macro"]
            ):
                header = macro.find(class_=re.compile(r"header|title", re.I))
                if header:
                    title_text = header.get_text(" ", strip=True).lower()
                body = macro.find(class_=re.compile(r"body|content", re.I)) or macro

            if not title_text or not body:
                continue

            body_text = clean_block_text(body)
            if not body_text or is_trivial_value(body_text):
                continue

            if is_business_impact_key(title_text):
                if (
                    not report.business_impact
                    or report.business_impact == "—"
                    or is_trivial_value(report.business_impact)
                ):
                    report.business_impact = format_business_impact(body_text)
            elif any(k in title_text for k in impact_keys):
                set_impact(report, body_text)
            set_cause(report, title_text, body_text, is_primary_cause)
            if any(k in title_text for k in solution_keys):
                set_solution(report, title_text, body_text, is_primary_solution)

    def _extract_from_summary_tables(
        self,
        soup: BeautifulSoup,
        report: IncidentReport,
        impact_keys,
        is_primary_cause,
        solution_keys,
        is_primary_solution=None,
    ) -> None:
        for table in soup.find_all("table"):
            if is_checklist_table(table):
                continue
            for tr in table.find_all("tr"):
                cells = tr.find_all(["th", "td"])
                if len(cells) >= 2:
                    k_text = cells[0].get_text(" ", strip=True).lower()
                    if len(k_text) > 300 or k_text.startswith("resumen"):
                        continue
                    v_text = clean_block_text(cells[1])
                    if not v_text or is_trivial_value(v_text):
                        continue

                    if is_business_impact_key(k_text):
                        if (
                            not report.business_impact
                            or report.business_impact == "—"
                            or is_trivial_value(report.business_impact)
                        ):
                            report.business_impact = format_business_impact(v_text)
                    elif any(k in k_text for k in impact_keys):
                        set_impact(report, v_text)
                    set_cause(report, k_text, v_text, is_primary_cause)
                    if any(k in k_text for k in solution_keys):
                        set_solution(report, k_text, v_text, is_primary_solution)

    def _extract_from_inline_paragraphs(
        self,
        soup: BeautifulSoup,
        report: IncidentReport,
        impact_keys,
        is_primary_cause,
        solution_keys,
        is_primary_solution=None,
    ) -> None:
        for elem in soup.find_all(["p", "li", "div"]):
            if elem.find_parent("table"):
                continue

            strong = elem.find(["strong", "b"])
            if not strong:
                continue

            prefix = strong.get_text(" ", strip=True).lower().rstrip(":- ")
            if not prefix or len(prefix) > 60:
                continue

            full_text = clean_cell_content(elem)
            content = re.sub(
                rf"^{re.escape(strong.get_text(' ', strip=True))}\s*[:-]?\s*",
                "",
                full_text,
                flags=re.I,
            ).strip()
            if not content or is_trivial_value(content):
                continue

            if is_business_impact_key(prefix):
                if (
                    not report.business_impact
                    or report.business_impact == "—"
                    or is_trivial_value(report.business_impact)
                ):
                    report.business_impact = format_business_impact(content)
            elif any(k == prefix or prefix.startswith(k) for k in impact_keys):
                set_impact(report, content)
            set_cause(report, prefix, content, is_primary_cause)
            if any(k == prefix or prefix.startswith(k) for k in solution_keys):
                set_solution(report, prefix, content, is_primary_solution)

    # Delegaciones de métodos privados para retrocompatibilidad completa
    _is_checklist_table = staticmethod(is_checklist_table)
    _is_trivial_value = staticmethod(is_trivial_value)
    _clean_cell_content = staticmethod(clean_cell_content)
    _clean_block_text = staticmethod(clean_block_text)
    _collect_sibling_text = staticmethod(collect_sibling_text)
    _extract_title_and_id = staticmethod(extract_title_and_id)
    _is_primary_incident_id_key = staticmethod(is_primary_incident_id_key)
    _is_secondary_incident_id_key = staticmethod(is_secondary_incident_id_key)
    _extract_clean_incident_id = staticmethod(extract_clean_incident_id)
    _extract_timing = staticmethod(extract_timing)
    _is_cause_excluded = staticmethod(is_cause_excluded)
    _set_cause = staticmethod(set_cause)
    _set_solution = staticmethod(set_solution)
    _is_business_impact_key = staticmethod(is_business_impact_key)
    _format_business_impact = staticmethod(format_business_impact)
    _set_impact = staticmethod(set_impact)
    _extract_tables = staticmethod(extract_tables)
    _parse_action_table = staticmethod(parse_action_table)
    _parse_chronology_table = staticmethod(parse_chronology_table)
    _extract_chronology_from_sections = staticmethod(extract_chronology_from_sections)
