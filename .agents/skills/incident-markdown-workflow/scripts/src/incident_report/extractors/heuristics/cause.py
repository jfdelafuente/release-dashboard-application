"""
Heurísticas para extracción jerárquica de Causa Raíz y Solución.
"""

from incident_report.domain.models import IncidentReport
from incident_report.extractors.heuristics.common import is_trivial_value

SOLUTION_PRIMARY_KEYS = [
    "solución técnica",
    "solucion tecnica",
    "solución aplicada",
    "solucion aplicada",
    "solución",
    "solucion",
    "resolución técnica",
    "resolucion tecnica",
]

SOLUTION_SECONDARY_KEYS = [
    "resolución",
    "resolucion",
    "mitigación",
    "mitigacion",
    "workaround",
    "acciones tomadas",
    "medidas adoptadas",
    "restablecimiento",
    "recuperación",
    "recuperacion",
    "normalización",
    "normalizacion",
    "acciones correctivas inmediatas",
]

SOLUTION_KEYS = SOLUTION_PRIMARY_KEYS + SOLUTION_SECONDARY_KEYS

SOLUTION_EXCLUDED_TERMS = [
    "tiempo de resolución",
    "tiempo de resolucion",
    "canal de teams",
    "procedimiento documentado",
    "con workaround",
    "autorrecuperación",
    "autorrecuperacion",
    "marcar con",
]

CAUSE_EXCLUDED_TERMS = [
    "no se detect",
    "monitoriz",
    "detecci",
    "aviso",
    "notificaci",
    "detectada",
]

CAUSE_DETAIL_KEYS = [
    "detalle causa raíz",
    "detalle causa raiz",
    "detalle de la causa raíz",
    "detalle de la causa raiz",
    "explicación técnica",
    "explicacion tecnica",
    "detalle técnico",
    "detalle tecnico",
]

CAUSE_PRIMARY_KEYS = [
    "causa raíz",
    "causa raiz",
    "root cause",
    "rca",
]

CAUSE_SECONDARY_KEYS = [
    "origen de la avería",
    "origen de la averia",
    "origen de la incidencia",
    "origen del problema",
    "origen del corte",
    "origen del fallo",
    "motivo de la incidencia",
    "motivo de la avería",
    "evento desencadenante",
    "detonante",
    "trigger",
    "por qué ocurrió",
    "por que ocurrio",
    "origen",
    "causa",
    "causas",
]


def is_cause_excluded(text: str) -> bool:
    """Descarta claves de causa referidas a monitorización o falta de detección."""
    t = text.lower()
    return any(neg in t for neg in CAUSE_EXCLUDED_TERMS)


def is_solution_excluded(text: str) -> bool:
    """Descarta claves de checklist o proceso que contienen palabras como 'resolución' o 'workaround'."""
    t = text.lower()
    return any(neg in t for neg in SOLUTION_EXCLUDED_TERMS)


def set_cause(
    report: IncidentReport,
    key_text: str,
    content: str,
    is_primary_cause: list,
) -> None:
    """
    Asigna la causa raíz aplicando prioridad jerárquica:
    Nivel 2 (Detalle causa raíz) > Nivel 1 (Causa raíz / RCA) > Nivel 0 (Origen / detonante).
    """
    if is_cause_excluded(key_text) or is_trivial_value(content):
        return
    k = key_text.lower()

    if any(dk in k for dk in CAUSE_DETAIL_KEYS):
        level = 2
    elif any(pk in k for pk in CAUSE_PRIMARY_KEYS):
        level = 1
    elif any(sk in k for sk in CAUSE_SECONDARY_KEYS):
        level = 0
    else:
        return

    current_level = is_primary_cause[0]
    if level > current_level or (
        level == current_level and (not report.cause or is_trivial_value(report.cause))
    ):
        report.cause = content
        is_primary_cause[0] = level


def set_solution(
    report: IncidentReport,
    key_text: str,
    content: str,
    is_primary_solution: list = None,
) -> None:
    """
    Asigna la solución aplicando prioridad jerárquica:
    Nivel 1 (Solución / Solución técnica / Solución aplicada) > Nivel 0 (Mitigación / Workaround / Recuperación).
    """
    if is_solution_excluded(key_text) or is_trivial_value(content):
        return
    k = key_text.lower()

    if any(pk in k for pk in SOLUTION_PRIMARY_KEYS):
        level = 1
    elif any(sk in k for sk in SOLUTION_SECONDARY_KEYS):
        level = 0
    else:
        return

    if is_primary_solution is not None:
        current_level = is_primary_solution[0]
        if level > current_level or (
            level == current_level and (not report.solution or report.solution == "—" or is_trivial_value(report.solution))
        ):
            report.solution = content
            is_primary_solution[0] = level
    else:
        if not report.solution or report.solution == "—" or is_trivial_value(report.solution) or level == 1:
            report.solution = content
