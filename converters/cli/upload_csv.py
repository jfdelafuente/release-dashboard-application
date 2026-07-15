#!/usr/bin/env python3
"""
Orquestación única de "CSV ya guardado -> conversor correcto -> resultado".

Este módulo es el único lugar que decide qué conversor le corresponde a un
CSV subido desde un dashboard, y el único que define la forma del
resultado (éxito/error). Antes esta lógica estaba duplicada, con
contratos de error distintos, en el backend FastAPI
(cso-incident-masivas-report/backend/main.py) y en el servidor de
desarrollo (serve_app.py).

Uso como librería (mismo repo, p. ej. serve_app.py):
    from converters.cli.upload_csv import run_upload
    result = run_upload(csv_path, dashboard_type, project_root, release_name)

Uso como CLI (otro repo/proceso, p. ej. el backend FastAPI):
    python upload_csv.py <csv_path> <dashboard_type> <project_root> [release_name]
    # Imprime el resultado como JSON en stdout.
"""

import json
import subprocess
import sys
from pathlib import Path

CONVERTER_SCRIPTS = {
    "massive": "convert_incidents.py",
    "postmortem": "convert_postmortems.py",
}


def run_upload(csv_path: Path, dashboard_type: str, project_root: Path, release_name: str = None) -> dict:
    """Ejecuta el conversor que corresponde a dashboard_type sobre csv_path.

    release_name solo se reenvía al conversor cuando dashboard_type es
    "postmortem" (ver specs/007-per-release-dashboards); se ignora para
    "massive", que no tiene el concepto de release.

    Devuelve siempre la misma forma de resultado, la usen dashboards de
    este repo (import directo) o de un repo hermano (vía subprocess):
        {"success": True, "message": str}
        {"success": False, "error": str, "details": str | None}
    """
    script_name = CONVERTER_SCRIPTS.get(dashboard_type, CONVERTER_SCRIPTS["massive"])
    script_path = Path(__file__).parent / script_name

    if not script_path.exists():
        return {"success": False, "error": f"Converter no encontrado: {script_path}"}

    command = [sys.executable, str(script_path), str(csv_path)]
    if dashboard_type == "postmortem" and release_name:
        command += ["--release-name", release_name]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        cwd=str(project_root),
    )

    if result.returncode != 0:
        return {
            "success": False,
            "error": "El CSV se guardó pero falló la conversión a JSON",
            "details": (result.stdout + result.stderr)[-4000:],
        }

    return {
        "success": True,
        "message": f"{csv_path.name} guardado en data/input/ y convertido correctamente",
    }


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"success": False, "error": "Uso: upload_csv.py <csv_path> [dashboard_type] [project_root]"}))
        return 1

    csv_path = Path(sys.argv[1])
    dashboard_type = sys.argv[2] if len(sys.argv) > 2 else "massive"
    project_root = Path(sys.argv[3]) if len(sys.argv) > 3 else Path.cwd()
    release_name = sys.argv[4] if len(sys.argv) > 4 else None

    result = run_upload(csv_path, dashboard_type, project_root, release_name)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
