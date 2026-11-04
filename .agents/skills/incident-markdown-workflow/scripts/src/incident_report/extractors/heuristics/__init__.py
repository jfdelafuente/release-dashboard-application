"""
Submódulos de heurísticas especializadas de extracción HTML/Confluence.
"""

from incident_report.extractors.heuristics.cause import (
    SOLUTION_KEYS,
    is_cause_excluded,
    is_solution_excluded,
    set_cause,
    set_solution,
)
from incident_report.extractors.heuristics.common import (
    clean_block_text,
    clean_cell_content,
    collect_sibling_text,
    is_checklist_table,
    is_trivial_value,
)
from incident_report.extractors.heuristics.impact import (
    IMPACT_KEYS,
    format_business_impact,
    is_business_impact_key,
    set_impact,
)
from incident_report.extractors.heuristics.tables import (
    extract_chronology_from_sections,
    extract_tables,
    parse_action_table,
    parse_chronology_table,
)
from incident_report.extractors.heuristics.tickets import (
    extract_clean_incident_id,
    extract_title_and_id,
    is_primary_incident_id_key,
    is_secondary_incident_id_key,
)
from incident_report.extractors.heuristics.timing import extract_timing

__all__ = [
    "IMPACT_KEYS",
    "SOLUTION_KEYS",
    "clean_block_text",
    "clean_cell_content",
    "collect_sibling_text",
    "extract_chronology_from_sections",
    "extract_clean_incident_id",
    "extract_tables",
    "extract_timing",
    "extract_title_and_id",
    "format_business_impact",
    "is_business_impact_key",
    "is_cause_excluded",
    "is_checklist_table",
    "is_primary_incident_id_key",
    "is_secondary_incident_id_key",
    "is_solution_excluded",
    "is_trivial_value",
    "parse_action_table",
    "parse_chronology_table",
    "set_cause",
    "set_impact",
    "set_solution",
]
