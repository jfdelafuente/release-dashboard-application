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
import os
import subprocess
import sys
import time
from pathlib import Path

try:
    from converters.cli.ingestion_logger import (
        get_log_file_path,
        log_background_start,
        log_conversion_result,
        log_upload_start,
    )
except ImportError:
    try:
        from ingestion_logger import (
            get_log_file_path,
            log_background_start,
            log_conversion_result,
            log_upload_start,
        )
    except ImportError:
        get_log_file_path = None
        log_background_start = None
        log_conversion_result = None
        log_upload_start = None

CONVERTER_SCRIPTS = {
    "massive": "convert_incidents.py",
    "postmortem": "convert_postmortems.py",
}


def run_upload(
    csv_path: Path,
    dashboard_type: str,
    project_root: Path = None,
    release_name: str = None,
    wait_eval: bool = False,
) -> dict:
    """Ejecuta el conversor que corresponde a dashboard_type sobre csv_path.

    release_name solo se reenvía al conversor cuando dashboard_type es
    "postmortem" (ver specs/007-per-release-dashboards); se ignora para
    "massive", que no tiene el concepto de release.

    Devuelve siempre la misma forma de resultado, la usen dashboards de
    este repo (import directo) o de un repo hermano (vía subprocess):
        {"success": True, "message": str}
        {"success": False, "error": str, "details": str | None}
    """
    csv_path = Path(csv_path)
    project_root = Path(project_root) if project_root else Path.cwd()
    script_name = CONVERTER_SCRIPTS.get(dashboard_type, CONVERTER_SCRIPTS["massive"])

    start_time = time.time()
    file_size = csv_path.stat().st_size if csv_path.exists() else 0
    if log_upload_start:
        log_upload_start(csv_path.name, file_size, dashboard_type, project_root)

    # Priorizar el conversor dentro de project_root (p. ej. .../current/converters/cli/...)
    # para soportar cambios de symlink/rotación en procesos persistentes que conserven el módulo en memoria.
    candidate_paths = [
        project_root / "converters" / "cli" / script_name,
        Path(__file__).resolve().parent / script_name,
        Path(__file__).parent / script_name,
    ]
    script_path = next((p for p in candidate_paths if p.exists()), candidate_paths[0])

    if not script_path.exists():
        err_msg = f"Converter no encontrado: {script_path}"
        if log_conversion_result:
            log_conversion_result(csv_path.name, False, time.time() - start_time, error_details=err_msg, project_root=project_root)
        return {"success": False, "error": err_msg}

    command = [sys.executable, str(script_path), str(csv_path)]
    if dashboard_type == "postmortem" and release_name:
        command += ["--release-name", release_name]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        cwd=str(project_root),
    )

    elapsed = time.time() - start_time

    if result.returncode != 0:
        if log_conversion_result:
            log_conversion_result(
                csv_path.name,
                False,
                elapsed,
                error_details=(result.stdout + result.stderr)[-4000:],
                project_root=project_root,
            )
        return {
            "success": False,
            "error": "El CSV se guardó pero falló la conversión a JSON",
            "details": (result.stdout + result.stderr)[-4000:],
        }

    if log_conversion_result:
        log_conversion_result(
            csv_path.name,
            True,
            elapsed,
            output_file=f"data/output/{csv_path.stem}.json",
            project_root=project_root,
        )

    bg_tasks = []
    if dashboard_type == "massive":
        proc = _trigger_notifications_evaluation(project_root, wait=wait_eval)
        if proc is not None:
            bg_tasks.append("incident_notifications_evaluation")

    response_payload = {
        "success": True,
        "message": f"{csv_path.name} guardado en data/input/ y convertido correctamente",
    }
    if bg_tasks:
        response_payload["background_tasks"] = bg_tasks

    return response_payload


def _trigger_notifications_evaluation(project_root: Path, wait: bool = False):
    """Dispara en segundo plano la regeneración del catálogo de alertas de alta prioridad.

    Si wait=False (por defecto), lanza el proceso en segundo plano asíncrono
    vía subprocess.Popen desacoplado del ciclo HTTP para respuesta inmediata en < 0.5s.
    Si wait=True, espera síncronamente a que finalice.
    Las trazas de stdout y stderr se vuelcan a data/logs/ingestion_audit.log.
    """
    candidate_paths = [
        project_root / "converters" / "cli" / "evaluate_incident_notifications.py",
        Path(__file__).resolve().parent / "evaluate_incident_notifications.py",
        Path(__file__).parent / "evaluate_incident_notifications.py",
    ]
    eval_script = next((p for p in candidate_paths if p.exists()), None)
    if not eval_script:
        return None

    try:
        env = dict(os.environ)
        env["PYTHONIOENCODING"] = "utf-8"
        kwargs = {
            "cwd": str(project_root),
            "env": env,
        }
        log_file = None
        if get_log_file_path:
            try:
                log_p = get_log_file_path(project_root)
                log_file = open(log_p, "a", encoding="utf-8")
                kwargs["stdout"] = log_file
                kwargs["stderr"] = subprocess.STDOUT
            except Exception:
                kwargs["stdout"] = subprocess.DEVNULL
                kwargs["stderr"] = subprocess.DEVNULL
        else:
            kwargs["stdout"] = subprocess.DEVNULL
            kwargs["stderr"] = subprocess.DEVNULL

        if sys.platform == "win32":
            flags = 0
            if hasattr(subprocess, "CREATE_NO_WINDOW"):
                flags |= subprocess.CREATE_NO_WINDOW
            if hasattr(subprocess, "DETACHED_PROCESS"):
                flags |= subprocess.DETACHED_PROCESS
            if flags:
                kwargs["creationflags"] = flags
        else:
            kwargs["start_new_session"] = True

        proc = subprocess.Popen([sys.executable, str(eval_script)], **kwargs)
        if log_background_start:
            log_background_start("evaluate_incident_notifications.py", proc.pid, project_root)

        if wait:
            proc.wait(timeout=60)
        return proc
    except Exception:
        return None


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"success": False, "error": "Uso: upload_csv.py <csv_path> [dashboard_type] [project_root] [release_name] [--wait-eval]"}))
        return 1

    csv_path = Path(sys.argv[1])
    dashboard_type = sys.argv[2] if len(sys.argv) > 2 else "massive"
    project_root = Path(sys.argv[3]) if len(sys.argv) > 3 else Path.cwd()
    release_name = sys.argv[4] if len(sys.argv) > 4 and not sys.argv[4].startswith("--") else None
    wait_eval = "--wait-eval" in sys.argv

    result = run_upload(csv_path, dashboard_type, project_root, release_name, wait_eval=wait_eval)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
