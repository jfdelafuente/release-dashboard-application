"""Carga de los datos de postmortem de una release concreta.

Usa el mismo criterio de agrupación por `_metadata.release_name` que
`converters/cli/cleanup_output.py`, para que "una release" signifique lo
mismo en toda la aplicación.
"""
import json
from pathlib import Path

DEFAULT_OUTPUT_DIR = Path("data") / "output"


class ReleaseNotFoundError(Exception):
    """No hay ningún fichero -postmortem.json con el release_name pedido."""


def find_postmortem_file(release_name, output_dir=None):
    """Devuelve el Path del -postmortem.json más reciente para release_name.

    Si hay varios ficheros para la misma release (no debería, ya que
    convert_postmortems.py archiva la versión anterior en cada subida), se
    queda con el más reciente por fecha de modificación.
    """
    output_dir = Path(output_dir) if output_dir else DEFAULT_OUTPUT_DIR
    if not output_dir.exists():
        return None

    candidates = []
    for file_path in output_dir.glob("*-postmortem.json"):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = json.load(f)
        except (json.JSONDecodeError, IOError, OSError):
            continue
        existing_release = content.get("_metadata", {}).get("release_name")
        if existing_release and existing_release.strip() == release_name.strip():
            candidates.append(file_path)

    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def load_postmortem_records(release_name, output_dir=None):
    """Devuelve la lista de registros (list[dict]) de postmortem de una release.

    Lanza ReleaseNotFoundError con un mensaje claro si no hay datos cargados
    para esa release (FR-009) — nunca debe generarse un informe con ceros.
    """
    file_path = find_postmortem_file(release_name, output_dir)
    if file_path is None:
        raise ReleaseNotFoundError(
            f"No hay datos de postmortem cargados para la release '{release_name}'"
        )

    with open(file_path, "r", encoding="utf-8") as f:
        content = json.load(f)
    return content.get("data", [])


def list_available_release_names(output_dir=None):
    """Nombres de todas las releases con -postmortem.json disponible (para --all)."""
    output_dir = Path(output_dir) if output_dir else DEFAULT_OUTPUT_DIR
    if not output_dir.exists():
        return []

    names = set()
    for file_path in output_dir.glob("*-postmortem.json"):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = json.load(f)
        except (json.JSONDecodeError, IOError, OSError):
            continue
        release_name = content.get("_metadata", {}).get("release_name")
        if release_name:
            names.add(release_name.strip())
    return sorted(names)
