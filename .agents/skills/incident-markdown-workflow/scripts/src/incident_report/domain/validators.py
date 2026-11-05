"""
Reglas de validación de dominio y marcadores de campos pendientes para informes de incidencias.
"""

from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from incident_report.domain.models import IncidentReport

PENDING_IMPACT_MARKER = "[PENDIENTE DE COMPLETAR: Impacto no detectado en la fuente]"
PENDING_CAUSE_MARKER = "[PENDIENTE DE COMPLETAR: Causa raíz no detectada en la fuente]"


def is_empty_or_pending(value: str) -> bool:
    """
    Determina si un campo obligatorio está vacío, contiene solo un guión ('—')
    o tiene un marcador pendiente de completar.
    """
    if not value or not value.strip():
        return True
    cleaned = value.strip()
    if cleaned == "—":
        return True
    if "PENDIENTE DE COMPLETAR" in cleaned.upper():
        return True
    return False


def validate_incident_report(report: "IncidentReport") -> List[str]:
    """
    Valida que el informe disponga de los campos críticos obligatorios (Impacto y Causa raíz).
    Devuelve una lista de errores descriptivos o una lista vacía si es válido.
    """
    errors: List[str] = []
    if is_empty_or_pending(report.impact):
        errors.append("Impacto (campo obligatorio ausente o vacío)")
    if is_empty_or_pending(report.cause):
        errors.append("Causa raíz (campo obligatorio ausente o vacío)")
    return errors


def apply_pending_placeholders(report: "IncidentReport") -> None:
    """
    Inserta los marcadores literales oficiales cuando faltan campos obligatorios en Etapa 1 (--only-md).
    """
    if is_empty_or_pending(report.impact):
        report.impact = PENDING_IMPACT_MARKER
    if is_empty_or_pending(report.cause):
        report.cause = PENDING_CAUSE_MARKER

