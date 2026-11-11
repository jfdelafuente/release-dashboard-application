#!/usr/bin/env python3
"""
CLI de Sincronización Incremental de Incidencias desde la API MonTMC / Epsilon.

Recupera las incidencias masivas recientes desde MonTMC, realiza un upsert no destructivo
sobre el dataset JSON masivo local (conservando los registros semestrales históricos fuera
de la ventana consultada), actualiza los KPIs y dispara la reevaluación de alertas ejecutivas.

Uso:
    python sync_montmc_incidents.py [--dias 3] [--usuario jdelat] [--dry-run]
"""

from __future__ import annotations

import argparse
from datetime import datetime
import json
import logging
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

# Asegurar import de converters/src
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "converters" / "src"))

from montmc_client import MonTMCClient, MonTMCError

try:
    from build_index import build_index
except ImportError:
    try:
        from converters.cli.build_index import build_index
    except ImportError:
        build_index = None

try:
    from ingestion_logger import (
        append_to_log,
        get_log_file_path,
        log_conversion_result,
        log_upload_start,
    )
except ImportError:
    try:
        from converters.cli.ingestion_logger import (
            append_to_log,
            get_log_file_path,
            log_conversion_result,
            log_upload_start,
        )
    except ImportError:
        append_to_log = None
        get_log_file_path = None
        log_conversion_result = None
        log_upload_start = None

logger = logging.getLogger("sync_montmc")


def resolve_active_massive_file(project_root: Optional[Path] = None) -> Path:
    """
    Localiza la ruta del archivo JSON masivo activo.
    Prioriza index.json, luego el archivo *-massive.json más reciente, o genera uno estándar.
    """
    root = Path(project_root) if project_root else PROJECT_ROOT
    output_dir = root / "data" / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    index_file = output_dir / "index.json"
    if index_file.exists():
        try:
            with open(index_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            files = data.get("massive", {}).get("files", [])
            if files and isinstance(files, list):
                first_path = files[0].get("path")
                if first_path:
                    p = root / first_path if not Path(first_path).is_absolute() else Path(first_path)
                    if p.exists():
                        return p
        except Exception as e:
            logger.warning("No se pudo leer index.json: %s", e)

    # Buscar archivos *-massive.json existentes
    massive_candidates = sorted(
        output_dir.glob("*-massive.json"),
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )
    if massive_candidates:
        return massive_candidates[0]

    # Fallback predeterminado con fecha del día
    today_str = datetime.now().strftime("%d %b %Y")
    return output_dir / f"CS-Informe incidencias P1,  P2 y P3 - 2026S2 - {today_str}-massive.json"


def _trigger_notifications_evaluation(project_root: Path, wait: bool = True) -> Optional[int]:
    """Ejecuta la regeneración del catálogo de alertas de alta prioridad tras la ingesta."""
    candidate_paths = [
        project_root / "converters" / "cli" / "evaluate_incident_notifications.py",
        CURRENT_DIR / "evaluate_incident_notifications.py",
    ]
    eval_script = next((p for p in candidate_paths if p.exists()), None)
    if not eval_script:
        return None

    try:
        env = dict(os.environ)
        env["PYTHONIOENCODING"] = "utf-8"
        cmd = [sys.executable, str(eval_script)]
        if wait:
            res = subprocess.run(cmd, cwd=str(project_root), env=env, capture_output=True, text=True, timeout=60)
            return res.returncode
        else:
            subprocess.Popen(cmd, cwd=str(project_root), env=env)
            return 0
    except Exception as e:
        logger.error("Error disparando evaluate_incident_notifications: %s", e)
        return -1


def sync_remedy_incidents(
    dias: int = 3,
    usuario: Optional[str] = None,
    output_path: Optional[Path | str] = None,
    dry_run: bool = False,
    skip_notifications: bool = False,
    project_root: Optional[Path | str] = None,
    client: Optional[MonTMCClient] = None,
) -> Dict[str, Any]:
    """
    Función orquestadora principal para la sincronización incremental de Remedy.
    Retorna resumen con estadísticas del balance de sincronización.
    """
    start_time = time.time()
    root = Path(project_root) if project_root else PROJECT_ROOT
    target_file = Path(output_path) if output_path else resolve_active_massive_file(root)

    api_client = client or MonTMCClient(default_user=usuario)
    active_user = usuario or api_client.default_user

    logger.info("Iniciando sincronización MonTMC: dias=%d, usuario=%s, target=%s, dry_run=%s",
                dias, active_user, target_file, dry_run)

    # 1. Consultar API MonTMC
    try:
        api_data = api_client.fetch_masivas(dias=dias, usuario=active_user)
    except Exception as e:
        err_msg = f"Fallo en consulta MonTMC masivas: {e}"
        logger.error(err_msg)
        if append_to_log:
            append_to_log(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] {err_msg}", root)
        return {
            "success": False,
            "error": err_msg,
            "total_consultadas": 0,
            "nuevas": 0,
            "actualizadas": 0,
            "sin_cambios": 0,
            "total_dataset": 0,
            "target_file": str(target_file),
            "timestamp": datetime.now().isoformat(),
        }

    raw_incidencias = api_data.get("incidencias") or []
    if not isinstance(raw_incidencias, list):
        raw_incidencias = []

    # Caso límite: API devuelve 0 incidencias
    if len(raw_incidencias) == 0:
        msg = f"MonTMC API devolvió 0 incidencias en ventana de {dias} días. No se modifica el dataset local."
        logger.warning(msg)
        if append_to_log:
            append_to_log(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [WARN] {msg}", root)
        return {
            "success": True,
            "message": msg,
            "total_consultadas": 0,
            "nuevas": 0,
            "actualizadas": 0,
            "sin_cambios": 0,
            "total_dataset": 0,
            "target_file": str(target_file),
            "timestamp": datetime.now().isoformat(),
        }

    # 2. Cargar dataset local persistente
    existing_dataset: Dict[str, Any] = {
        "_metadata": {
            "type": "massive",
            "version": "1.0",
            "created": datetime.now().isoformat(),
            "record_count": 0,
            "kpis": {"total": 0, "pending": 0, "trend_7d": None, "trend_15d": None, "trend_30d": None},
        },
        "data": [],
    }

    if target_file.exists():
        try:
            with open(target_file, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict) and "data" in loaded and isinstance(loaded["data"], list):
                    existing_dataset = loaded
        except Exception as e:
            logger.warning("Error leyendo dataset existente %s: %s", target_file, e)

    data_list: List[Dict[str, Any]] = existing_dataset.get("data", [])

    # Indexar registros existentes preservando el orden original y deduplicando si existieran
    records_by_id: Dict[str, Dict[str, Any]] = {}
    ordered_ids: List[str] = []
    for item in data_list:
        inc_id = str(item.get("ID de incidencia") or "").strip()
        if inc_id and inc_id not in records_by_id:
            records_by_id[inc_id] = item
            ordered_ids.append(inc_id)

    # 3. Aplicar Upsert Incremental
    nuevas = 0
    actualizadas = 0
    sin_cambios = 0
    new_ids: List[str] = []

    incoming_normalized: List[Dict[str, Any]] = []
    for raw_rec in raw_incidencias:
        norm_rec = api_client.normalize_mon_tmc_record(raw_rec)
        inc_id = str(norm_rec.get("ID de incidencia") or "").strip()
        if not inc_id:
            continue

        incoming_normalized.append(norm_rec)

        if inc_id in records_by_id:
            old_rec = records_by_id[inc_id]
            # Evaluar si ha cambiado algún campo clave
            has_changes = False
            for k in ("Estatus", "Grupo asignado", "Grupo Resolutor", "Fecha de última resolución",
                      "Urgencia", "Prioridad", "Descripción", "detalleSolucion", "fechaUltimaModificacion"):
                if norm_rec.get(k) != old_rec.get(k):
                    has_changes = True
                    break

            if has_changes:
                # Actualizar campos conservando atributos locales previos
                updated_rec = dict(old_rec)
                updated_rec.update(norm_rec)
                records_by_id[inc_id] = updated_rec
                actualizadas += 1
            else:
                sin_cambios += 1
        else:
            # Nuevo registro: registrar en mapa y al frente de la cola de nuevos IDs
            records_by_id[inc_id] = norm_rec
            new_ids.append(inc_id)
            nuevas += 1

    # Reconstruir listado ordenado: nuevos al inicio (más recientes), seguidos de los existentes
    final_data_list = [records_by_id[i] for i in new_ids] + [records_by_id[i] for i in ordered_ids if i not in set(new_ids)]
    existing_dataset["data"] = final_data_list
    data_list = final_data_list

    # 4. Recalcular KPIs y Metadatos
    total_records = len(data_list)
    pending_statuses = {"Abierto", "Pendiente", "En Progreso", "En Curso", "Asignado"}
    pending_count = sum(1 for r in data_list if r.get("Estatus") in pending_statuses)

    metadata = existing_dataset.setdefault("_metadata", {})
    metadata["type"] = "massive"
    metadata["version"] = "1.0"
    metadata["record_count"] = total_records
    metadata["updated"] = datetime.now().isoformat()
    metadata["last_sync_montmc"] = datetime.now().isoformat()
    metadata["last_sync_source"] = "montmc_api"

    kpis = metadata.setdefault("kpis", {})
    kpis["total"] = total_records
    kpis["pending"] = pending_count

    elapsed = time.time() - start_time

    # 5. Persistencia Atómica en Disco
    if not dry_run:
        target_file.parent.mkdir(parents=True, exist_ok=True)
        tmp_file = target_file.with_name(f"{target_file.stem}.tmp_{os.getpid()}")
        try:
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(existing_dataset, f, ensure_ascii=False, indent=2)
            tmp_file.replace(target_file)
        except Exception as e:
            if tmp_file.exists():
                tmp_file.unlink(missing_ok=True)
            raise IOError(f"Error escribiendo dataset de forma atómica: {e}") from e

        # Actualizar index.json
        if build_index:
            try:
                build_index(str(target_file.parent))
            except Exception as e:
                logger.warning("Aviso actualizando index.json: %s", e)

        # Registrar trazabilidad en auditoría
        if log_upload_start:
            log_upload_start("montmc_api", target_file.stat().st_size, "massive", root)
        if log_conversion_result:
            log_conversion_result(
                "montmc_api",
                True,
                elapsed,
                output_file=str(target_file.relative_to(root) if target_file.is_relative_to(root) else target_file),
                project_root=root,
            )
        if append_to_log:
            append_to_log(
                f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [MON_TMC_SYNC] "
                f"Consultadas: {len(raw_incidencias)} | Nuevas: {nuevas} | "
                f"Actualizadas: {actualizadas} | Sin cambios: {sin_cambios} | Total dataset: {total_records}\n",
                root,
            )

        # Disparar reevaluación de notificaciones de alta prioridad
        if not skip_notifications:
            _trigger_notifications_evaluation(root, wait=True)

    return {
        "success": True,
        "total_consultadas": len(raw_incidencias),
        "nuevas": nuevas,
        "actualizadas": actualizadas,
        "sin_cambios": sin_cambios,
        "total_dataset": total_records,
        "target_file": str(target_file),
        "dry_run": dry_run,
        "elapsed_sec": round(elapsed, 2),
        "timestamp": datetime.now().isoformat(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sincronizador incremental de incidencias Remedy desde API MonTMC",
    )
    parser.add_argument("--dias", type=int, default=3, help="Días de histórico a solicitar (default: 3)")
    parser.add_argument("--usuario", type=str, default=None, help="Usuario para consulta MonTMC (default: env o jdelat)")
    parser.add_argument("-o", "--output", type=str, default=None, help="Ruta del fichero JSON masivo de salida")
    parser.add_argument("--dry-run", action="store_true", help="Simular consulta y balance sin escribir en disco")
    parser.add_argument("--skip-notifications", action="store_true", help="Omitir reevaluación de catálogo de alta prioridad")
    parser.add_argument("-v", "--verbose", action="store_true", help="Salida detallada de logs")

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    try:
        res = sync_remedy_incidents(
            dias=args.dias,
            usuario=args.usuario,
            output_path=args.output,
            dry_run=args.dry_run,
            skip_notifications=args.skip_notifications,
        )
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return 0 if res.get("success") else 1
    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}, indent=2))
        return 1


if __name__ == "__main__":
    sys.exit(main())
