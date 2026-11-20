#!/usr/bin/env python3
"""
CLI de Sincronización Incremental de Incidencias Postmortem desde la API MonTMC / Epsilon.

Consulta GET /api/epsilon/release?usuario=<user>, realiza un upsert incremental no destructivo
sobre el dataset JSON de postmortem asociado a la release (conservando el histórico previo),
recalcula Despliegue (PAP/MESA) y KPIs, actualiza data/output/index.json (sección postmortem)
y registra la trazabilidad en auditoría de ingestas sin tocar massive-incidents ni
high_priority_notifications.json.

Uso:
    python sync_montmc_postmortem.py [--release 2026R11] [--usuario jdelat] [--dry-run]
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import json
import logging
import os
from pathlib import Path
import re
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(PROJECT_ROOT / "converters" / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "converters" / "src"))

from montmc_client import MonTMCClient, MonTMCError  # noqa: E402
from csv_to_json.postmortem_schemas import (  # noqa: E402
    PostmortemKPIMetrics,
    PostmortemRecord,
    derivateDespliegue,
)

try:
    from convert_postmortems import build_index_for_hub
except ImportError:
    try:
        from converters.cli.convert_postmortems import build_index_for_hub
    except ImportError:
        build_index_for_hub = None

try:
    from ingestion_logger import (
        append_to_log,
        log_conversion_result,
        log_upload_start,
    )
except ImportError:
    try:
        from converters.cli.ingestion_logger import (
            append_to_log,
            log_conversion_result,
            log_upload_start,
        )
    except ImportError:
        append_to_log = None
        log_conversion_result = None
        log_upload_start = None

logger = logging.getLogger("sync_montmc_postmortem")

_RELEASE_TAG_RE = re.compile(r"^\s*\[([^\]]+)\]")


def _sanitize_filename_part(name: str) -> str:
    """Convierte un nombre de release en un segmento seguro para nombre de archivo."""
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", (name or "").strip()).strip("-")
    return cleaned or "release"


def _infer_release_from_api(raw_incidencias: List[Dict[str, Any]]) -> Optional[str]:
    """Extrae el primer nombre de release entre corchetes del resumen si existe (ej. [Simulacro2026R11])."""
    for rec in raw_incidencias:
        if not isinstance(rec, dict):
            continue
        resumen = str(rec.get("resumen") or "")
        match = _RELEASE_TAG_RE.match(resumen)
        if match:
            tag = match.group(1).strip()
            if tag:
                return tag
    return None


def _filter_incidencias_by_release(
    raw_incidencias: List[Dict[str, Any]],
    release_name: Optional[str],
) -> List[Dict[str, Any]]:
    """Filtra las incidencias de MonTMC cuyo resumen/Descripción contiene el tag [<release_name>]."""
    if not release_name or not str(release_name).strip():
        return raw_incidencias
    pattern = re.compile(rf"\[{re.escape(str(release_name).strip())}\]", re.IGNORECASE)
    filtered: List[Dict[str, Any]] = []
    for rec in raw_incidencias:
        if not isinstance(rec, dict):
            continue
        text = f"{rec.get('resumen') or ''} {rec.get('detalle') or ''} {rec.get('Descripción') or ''}"
        if pattern.search(text):
            filtered.append(rec)
    return filtered


def resolve_active_postmortem_file(
    project_root: Optional[Path] = None,
    release_name: Optional[str] = None,
) -> Tuple[Path, Optional[str]]:
    """
    Localiza la ruta del archivo JSON de postmortem para la release indicada
    (o el más reciente en index.json si no se especifica).
    """
    root = Path(project_root) if project_root else PROJECT_ROOT
    output_dir = root / "data" / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    target_release = release_name.strip() if isinstance(release_name, str) and release_name.strip() else None

    index_file = output_dir / "index.json"
    if index_file.exists():
        try:
            with open(index_file, "r", encoding="utf-8") as f:
                idx = json.load(f)
            files = idx.get("postmortem", {}).get("files", [])
            if files:
                if target_release:
                    for entry in files:
                        if str(entry.get("release_name") or "").strip() == target_release:
                            rel_path = entry.get("path") or f"data/output/{entry.get('name')}"
                            candidate = root / rel_path if not Path(rel_path).is_absolute() else Path(rel_path)
                            return candidate, target_release
                else:
                    latest = files[0]
                    rel_path = latest.get("path") or f"data/output/{latest.get('name')}"
                    candidate = root / rel_path if not Path(rel_path).is_absolute() else Path(rel_path)
                    if candidate.exists():
                        return candidate, latest.get("release_name")
        except Exception:
            pass

    existing_files = sorted(
        [p for p in output_dir.glob("*-postmortem.json")],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if target_release:
        for file_path in existing_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = json.load(f)
                meta_rel = str(content.get("_metadata", {}).get("release_name") or "").strip()
                if meta_rel == target_release:
                    return file_path, target_release
            except Exception:
                continue
        safe_name = _sanitize_filename_part(target_release)
        return output_dir / f"{safe_name}-postmortem.json", target_release

    if existing_files:
        first_file = existing_files[0]
        meta_rel = None
        try:
            with open(first_file, "r", encoding="utf-8") as f:
                meta_rel = json.load(f).get("_metadata", {}).get("release_name")
        except Exception:
            pass
        return first_file, meta_rel

    return output_dir / "release-postmortem.json", None


def _recalculate_postmortem_dataset(
    data_list: List[Dict[str, Any]],
    release_name: Optional[str],
    existing_metadata: Dict[str, Any],
    last_sync_changes: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Recalcula Despliegue (PAP/MESA), KPIs y metadatos del dataset postmortem."""
    records = [PostmortemRecord(dict(item)) for item in data_list]
    despliegue_map = derivateDespliegue(records) if records else {}

    kpis = PostmortemKPIMetrics()
    enriched_data: List[Dict[str, Any]] = []
    for rec in records:
        inc_id = rec.data.get("ID de incidencia")
        if inc_id in despliegue_map:
            rec.data["Despliegue"] = despliegue_map[inc_id]
        kpis.add_record(rec)
        enriched_data.append(rec.to_dict())

    now_iso = datetime.now().isoformat()
    metadata = dict(existing_metadata) if isinstance(existing_metadata, dict) else {}
    metadata["type"] = "postmortem"
    metadata["version"] = metadata.get("version") or "1.0"
    metadata["created"] = metadata.get("created") or now_iso
    metadata["updated"] = now_iso
    metadata["last_sync_montmc"] = now_iso
    metadata["last_sync_source"] = "montmc_api"
    metadata["record_count"] = len(enriched_data)
    metadata["release_name"] = release_name
    metadata["kpis"] = kpis.to_dict()
    if last_sync_changes is not None:
        metadata["last_sync_changes"] = last_sync_changes

    return {
        "_metadata": metadata,
        "data": enriched_data,
    }


def _record_audit(
    root: Path,
    target_file: Path,
    elapsed: float,
    total_consultadas: int,
    nuevas: int,
    actualizadas: int,
    sin_cambios: int,
    total_dataset: int,
    release_name: Optional[str],
) -> None:
    """Registra la ejecución en ingestion_summary.json e ingestion.log."""
    file_size = target_file.stat().st_size if target_file.exists() else 0
    if log_upload_start:
        log_upload_start("montmc_api", file_size, "postmortem", root)
    if log_conversion_result:
        rel_out = str(target_file.relative_to(root) if target_file.is_relative_to(root) else target_file)
        log_conversion_result(
            "montmc_api",
            True,
            elapsed,
            output_file=rel_out,
            project_root=root,
        )
    if append_to_log:
        append_to_log(
            f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [MON_TMC_RELEASE_SYNC] "
            f"Release: {release_name or 'N/A'} | Consultadas: {total_consultadas} | "
            f"Nuevas: {nuevas} | Actualizadas: {actualizadas} | Sin cambios: {sin_cambios} | "
            f"Total dataset: {total_dataset}\n",
            root,
        )


def sync_postmortem_release(
    release_name: Optional[str] = None,
    usuario: Optional[str] = None,
    output_path: Optional[Path | str] = None,
    dry_run: bool = False,
    project_root: Optional[Path | str] = None,
    client: Optional[MonTMCClient] = None,
) -> Dict[str, Any]:
    """
    Orquesta la sincronización incremental del dashboard Postmortem desde
    GET /api/epsilon/release?usuario=<user>.
    """
    start_time = time.time()
    root = Path(project_root) if project_root else PROJECT_ROOT
    api_client = client or MonTMCClient(default_user=usuario)
    active_user = usuario or api_client.default_user

    # 1. Consultar API MonTMC
    try:
        api_data = api_client.fetch_release(usuario=active_user)
    except Exception as e:
        err_msg = f"Fallo en consulta MonTMC release: {e}"
        logger.error(err_msg)
        if append_to_log:
            append_to_log(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] {err_msg}\n", root)
        return {
            "success": False,
            "error": err_msg,
            "release_name": release_name,
            "total_consultadas": 0,
            "nuevas": 0,
            "actualizadas": 0,
            "sin_cambios": 0,
            "total_dataset": 0,
            "target_file": str(output_path or ""),
            "timestamp": datetime.now().isoformat(),
        }

    raw_incidencias = api_data.get("incidencias") or []
    if not isinstance(raw_incidencias, list):
        raw_incidencias = []

    inferred_release = release_name or _infer_release_from_api(raw_incidencias)
    if output_path:
        target_file = Path(output_path)
        active_release = inferred_release
    else:
        target_file, resolved_release = resolve_active_postmortem_file(root, inferred_release)
        active_release = inferred_release or resolved_release

    total_api = len(raw_incidencias)
    raw_incidencias = _filter_incidencias_by_release(raw_incidencias, active_release)

    # Caso límite: API devuelve 0 incidencias (o 0 tras filtrar por release)
    if len(raw_incidencias) == 0:
        existing_count = 0
        if target_file.exists():
            try:
                with open(target_file, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                if isinstance(loaded, dict) and isinstance(loaded.get("data"), list):
                    existing_count = len(loaded["data"])
            except Exception:
                pass

        msg = (
            f"MonTMC release API devolvió {total_api} incidencias, 0 con tag [{active_release}]. Se conserva intacto el dataset local."
            if active_release and total_api > 0
            else "MonTMC release API devolvió 0 incidencias. Se conserva intacto el dataset local."
        )
        logger.warning(msg)
        elapsed = time.time() - start_time
        if not dry_run:
            _record_audit(root, target_file, elapsed, 0, 0, 0, 0, existing_count, active_release)
        return {
            "success": True,
            "message": msg,
            "release_name": active_release,
            "total_consultadas": 0,
            "nuevas": 0,
            "actualizadas": 0,
            "sin_cambios": 0,
            "total_dataset": existing_count,
            "target_file": str(target_file),
            "timestamp": datetime.now().isoformat(),
        }

    # 2. Cargar dataset local persistente
    existing_metadata: Dict[str, Any] = {}
    data_list: List[Dict[str, Any]] = []
    if target_file.exists():
        try:
            with open(target_file, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            if isinstance(loaded, dict) and isinstance(loaded.get("data"), list):
                data_list = loaded["data"]
                existing_metadata = loaded.get("_metadata") or {}
        except Exception as e:
            logger.warning("Error leyendo dataset postmortem existente %s: %s", target_file, e)

    records_by_id: Dict[str, Dict[str, Any]] = {}
    ordered_ids: List[str] = []
    for item in data_list:
        inc_id = str(item.get("ID de incidencia") or "").strip()
        if inc_id and inc_id not in records_by_id:
            records_by_id[inc_id] = item
            ordered_ids.append(inc_id)

    # 3. Upsert incremental no destructivo
    nuevas = 0
    actualizadas = 0
    sin_cambios = 0
    new_ids: List[str] = []
    updated_ids: List[str] = []
    status_changed_ids: List[str] = []
    compare_fields = (
        "Estatus",
        "Grupo asignado",
        "Grupo Resolutor",
        "Fecha de última resolución",
        "Urgencia",
        "Prioridad",
        "Descripción",
        "Impacto",
        "detalleSolucion",
        "fechaUltimaModificacion",
        "fechaPrevista",
    )

    seen_api_ids: set[str] = set()
    for raw_rec in raw_incidencias:
        norm_rec = api_client.normalize_mon_tmc_postmortem_record(raw_rec)
        inc_id = str(norm_rec.get("ID de incidencia") or "").strip()
        if not inc_id:
            continue
        seen_api_ids.add(inc_id)

        if inc_id in records_by_id:
            old_rec = records_by_id[inc_id]
            has_changes = any(norm_rec.get(k) != old_rec.get(k) for k in compare_fields)
            if has_changes:
                if norm_rec.get("Estatus") != old_rec.get("Estatus"):
                    status_changed_ids.append(inc_id)
                updated_ids.append(inc_id)
                updated_rec = dict(old_rec)
                updated_rec.update(norm_rec)
                records_by_id[inc_id] = updated_rec
                actualizadas += 1
            else:
                sin_cambios += 1
        else:
            records_by_id[inc_id] = norm_rec
            new_ids.append(inc_id)
            nuevas += 1

    # 3b. Reconciliar en paralelo (con límite y timeout) tickets locales no cerrados que ya no vienen en /api/epsilon/release
    if hasattr(api_client, "fetch_remedy_detail"):
        pending_reconcile = [
            inc_id
            for inc_id in ordered_ids
            if inc_id not in seen_api_ids
            and str(records_by_id[inc_id].get("Estatus") or "").strip().lower() != "cerrado"
        ]
        max_reconcile = int(os.environ.get("MONTMC_RECONCILE_MAX", "50") or 50)
        reconcile_batch = pending_reconcile[:max(0, max_reconcile)]
        if reconcile_batch:
            max_workers = min(5, len(reconcile_batch))
            details_by_id: Dict[str, Any] = {}
            with ThreadPoolExecutor(max_workers=max_workers) as pool:
                futures = {
                    inc_id: pool.submit(api_client.fetch_remedy_detail, inc_id)
                    for inc_id in reconcile_batch
                }
                for inc_id, future in futures.items():
                    try:
                        details_by_id[inc_id] = future.result(timeout=15)
                    except Exception as err:
                        logger.debug("No se pudo reconciliar detalle Remedy para %s: %s", inc_id, err)

            for inc_id in reconcile_batch:
                detail = details_by_id.get(inc_id)
                remedy_node = detail.get("remedy") if isinstance(detail, dict) else None
                if not isinstance(remedy_node, dict):
                    continue
                old_rec = records_by_id[inc_id]
                norm_detail = api_client.normalize_mon_tmc_postmortem_record(remedy_node)
                if not remedy_node.get("fechaCreacion") and old_rec.get("Fecha de envío"):
                    norm_detail["Fecha de envío"] = old_rec["Fecha de envío"]
                has_changes = any(norm_detail.get(k) != old_rec.get(k) for k in compare_fields)
                if has_changes:
                    if norm_detail.get("Estatus") != old_rec.get("Estatus"):
                        status_changed_ids.append(inc_id)
                    updated_ids.append(inc_id)
                    updated_rec = dict(old_rec)
                    updated_rec.update(norm_detail)
                    records_by_id[inc_id] = updated_rec
                    actualizadas += 1

    final_data_list = [records_by_id[i] for i in new_ids] + [
        records_by_id[i] for i in ordered_ids if i not in set(new_ids)
    ]

    # 4. Recalcular Despliegue (PAP/MESA), KPIs y Metadatos
    last_sync_changes = {
        "new_ids": new_ids,
        "updated_ids": updated_ids,
        "status_changed_ids": status_changed_ids,
        "timestamp": datetime.now().isoformat(),
    }
    final_dataset = _recalculate_postmortem_dataset(
        final_data_list,
        active_release,
        existing_metadata,
        last_sync_changes=last_sync_changes,
    )
    total_records = len(final_dataset["data"])
    elapsed = time.time() - start_time

    # 5. Persistencia atómica en disco + index.json (solo sección postmortem) + auditoría
    if not dry_run:
        target_file.parent.mkdir(parents=True, exist_ok=True)
        tmp_file = target_file.with_name(f"{target_file.stem}.tmp_{os.getpid()}")
        try:
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(final_dataset, f, ensure_ascii=False, indent=2)
            tmp_file.replace(target_file)
        except Exception as e:
            if tmp_file.exists():
                tmp_file.unlink(missing_ok=True)
            raise IOError(f"Error escribiendo dataset postmortem de forma atómica: {e}") from e

        if build_index_for_hub:
            try:
                build_index_for_hub(str(target_file.parent))
            except Exception as e:
                logger.warning("Aviso actualizando index.json de postmortem: %s", e)

        _record_audit(
            root,
            target_file,
            elapsed,
            len(raw_incidencias),
            nuevas,
            actualizadas,
            sin_cambios,
            total_records,
            active_release,
        )

    return {
        "success": True,
        "release_name": active_release,
        "total_consultadas": len(raw_incidencias),
        "nuevas": nuevas,
        "actualizadas": actualizadas,
        "sin_cambios": sin_cambios,
        "new_ids": new_ids,
        "updated_ids": updated_ids,
        "status_changed_ids": status_changed_ids,
        "total_dataset": total_records,
        "target_file": str(target_file),
        "dry_run": dry_run,
        "elapsed_seconds": round(elapsed, 3),
        "timestamp": datetime.now().isoformat(),
    }


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    parser = argparse.ArgumentParser(description="Sincronización incremental de Postmortem desde MonTMC /api/epsilon/release")
    parser.add_argument("--release", default=None, help="Nombre de la release a actualizar (ej. 2026R11)")
    parser.add_argument("--usuario", default=None, help="Usuario MonTMC (por defecto MON_TMC_USER o 'jdelat')")
    parser.add_argument("--output", default=None, help="Ruta de archivo JSON destino explícita")
    parser.add_argument("--dry-run", action="store_true", help="Simula la sincronización sin escribir en disco")
    parser.add_argument("--project-root", default=None, help="Raíz del proyecto")
    args = parser.parse_args()

    result = sync_postmortem_release(
        release_name=args.release,
        usuario=args.usuario,
        output_path=args.output,
        dry_run=args.dry_run,
        project_root=args.project_root,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    sys.exit(main())
