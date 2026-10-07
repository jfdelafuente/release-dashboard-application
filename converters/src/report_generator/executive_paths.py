"""
Gestión de rutas y archivos para el informe ejecutivo de incidencias postmortem.
Feature 010: 010-incident-executive-report
"""

from pathlib import Path
from typing import Optional
from converters.src.report_generator.executive_models import sanitize_incident_ref

# Directorio base del proyecto release-dashboard-application
PROJECT_ROOT = Path(__file__).resolve().parents[3]


def get_executive_template_path() -> Path:
    """
    Retorna la ruta absoluta a la plantilla de referencia PowerPoint.
    Busca primero en assets del generador y como respaldo en la raíz del proyecto.
    """
    assets_path = Path(__file__).resolve().parent / "assets" / "executive_template.pptx"
    if assets_path.is_file():
        return assets_path

    root_template = PROJECT_ROOT / "20260609 Incidencia IVR ExMM.pptx"
    if root_template.is_file():
        return root_template

    raise FileNotFoundError(f"Plantilla PowerPoint no encontrada en {assets_path} ni en {root_template}")


def get_executive_reports_dir() -> Path:
    """
    Retorna la ruta al directorio de persistencia de informes ejecutivos, creándolo si no existe.
    """
    reports_dir = PROJECT_ROOT / "data" / "reports" / "executive"
    reports_dir.mkdir(parents=True, exist_ok=True)
    return reports_dir


def get_executive_report_filename(incident_ref: str) -> str:
    """
    Retorna el nombre del archivo de informe generado: RESUMEN_EJECUTIVO_{incidentRef}.pptx
    """
    clean_ref = sanitize_incident_ref(incident_ref)
    return f"RESUMEN_EJECUTIVO_{clean_ref}.pptx"


def get_executive_report_path(incident_ref: str) -> Path:
    """
    Retorna la ruta completa al archivo de informe para una incidencia dada.
    """
    return get_executive_reports_dir() / get_executive_report_filename(incident_ref)

