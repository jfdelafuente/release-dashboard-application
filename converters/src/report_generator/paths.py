"""Rutas y saneado de nombres de fichero para los informes PPT de postmortem."""
import os
import re
from pathlib import Path

def get_default_reports_dir() -> Path:
    env_dir = os.environ.get("RELEASE_DASHBOARD_STORAGE_DIR", "").strip()
    if env_dir:
        return Path(env_dir) / "reports"
    prod_storage = Path("/infocodes/var/storage/release-dashboard/reports")
    if os.name != "nt" and prod_storage.parent.is_dir():
        return prod_storage
    return Path("data") / "reports"


DEFAULT_REPORTS_DIR = get_default_reports_dir()


def sanitize_release_name(release_name):
    """Convierte un nombre de release en un nombre de fichero seguro.

    Sustituye cualquier carácter que no sea letra/número/guion/guion bajo por
    "_", y colapsa guiones bajos repetidos, para evitar problemas de path
    traversal o caracteres no válidos en el sistema de ficheros (FR-008).
    """
    if not release_name or not release_name.strip():
        raise ValueError("release_name no puede estar vacío")

    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", release_name.strip())
    safe = re.sub(r"_+", "_", safe).strip("_")
    if not safe:
        raise ValueError(f"release_name '{release_name}' no produce un nombre de fichero válido")
    return safe


def report_output_path(release_name, output_dir=None):
    """Ruta por defecto (o dentro de output_dir) para el informe de una release."""
    output_dir = Path(output_dir) if output_dir else DEFAULT_REPORTS_DIR
    filename = f"{sanitize_release_name(release_name)}-postmortem-report.pptx"
    return output_dir / filename
