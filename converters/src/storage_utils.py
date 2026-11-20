# -*- coding: utf-8 -*-
"""
Utilidades compartidas de almacenamiento seguro para Mesa de Release y Consola de Triaje:
- Locks por fichero (`threading.Lock`) para evitar condiciones de carrera en escrituras concurrentes.
- Escritura atómica de JSON (`tempfile` + `fsync` + `os.replace`) con copia `.bak` opcional.
- Política de retención y limpieza (TTL + máximo de ficheros) para cachés en disco.
- Verificación de permisos de escritura en el directorio de almacenamiento persistente.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import tempfile
import threading
import time
from typing import Any, Dict


_LOCKS_GUARD = threading.Lock()
_PATH_LOCKS: Dict[str, threading.Lock] = {}


def get_path_lock(path: Path) -> threading.Lock:
    """Devuelve un `threading.Lock` estable asociado a la ruta resuelta."""
    key = str(Path(path).resolve())
    with _LOCKS_GUARD:
        lock = _PATH_LOCKS.get(key)
        if lock is None:
            lock = threading.Lock()
            _PATH_LOCKS[key] = lock
        return lock


def atomic_write_json(
    path: Path,
    payload: Any,
    *,
    create_backup: bool = True,
    indent: int = 2,
) -> None:
    """Escribe `payload` como JSON de forma atómica, creando `.bak` previo si existe."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)

    if create_backup and target.exists():
        backup_path = target.with_name(target.name + ".bak")
        try:
            shutil.copy2(target, backup_path)
        except OSError:
            pass

    serialized = json.dumps(payload, ensure_ascii=False, indent=indent)
    tmp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=str(target.parent),
            prefix=f".{target.name}.",
            suffix=".tmp",
            delete=False,
        ) as tmp_file:
            tmp_path = tmp_file.name
            tmp_file.write(serialized)
            tmp_file.flush()
            os.fsync(tmp_file.fileno())
        for attempt in range(5):
            try:
                os.replace(tmp_path, target)
                break
            except PermissionError:
                if attempt == 4:
                    raise
                time.sleep(0.01 * (attempt + 1))
    except Exception:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
        raise


def prune_cache_dir(
    cache_dir: Path,
    max_age_days: int = 30,
    max_files: int = 2000,
) -> Dict[str, int]:
    """Limpia ficheros `.json` caducados o excedentes en un directorio de caché."""
    target = Path(cache_dir)
    if not target.is_dir():
        return {"deleted_expired": 0, "deleted_overflow": 0, "remaining": 0}

    now = time.time()
    cutoff = now - max(0, max_age_days) * 86400
    entries = []
    deleted_expired = 0

    for item in target.glob("*.json"):
        try:
            mtime = item.stat().st_mtime
        except OSError:
            continue
        if max_age_days >= 0 and mtime < cutoff:
            try:
                item.unlink()
                deleted_expired += 1
            except OSError:
                pass
        else:
            entries.append((mtime, item))

    deleted_overflow = 0
    if max_files >= 0 and len(entries) > max_files:
        entries.sort(key=lambda pair: pair[0])
        excess = len(entries) - max_files
        for _, item in entries[:excess]:
            try:
                item.unlink()
                deleted_overflow += 1
            except OSError:
                pass
        entries = entries[excess:]

    return {
        "deleted_expired": deleted_expired,
        "deleted_overflow": deleted_overflow,
        "remaining": len(entries),
    }


def check_storage_writability(storage_dir: Path) -> Dict[str, Any]:
    """Comprueba que `storage_dir` existe y permite crear/borrar ficheros."""
    target = Path(storage_dir)
    probe = target / f".write_probe_{os.getpid()}_{threading.get_ident()}"
    try:
        target.mkdir(parents=True, exist_ok=True)
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return {"ok": True, "path": str(target), "error": None}
    except Exception as exc:
        return {"ok": False, "path": str(target), "error": str(exc)}


def build_release_desk_health(storage_dir: Path, project_root: Path) -> Dict[str, Any]:
    """Construye el diagnóstico de salud para Mesa de Release y Consola de Triaje."""
    storage = Path(storage_dir)
    root = Path(project_root)
    storage_status = check_storage_writability(storage)

    output_dir = storage / "output"
    if not output_dir.is_dir():
        output_dir = root / "data" / "output"

    latest_pm_info: Dict[str, Any] = {"available": False, "file": None, "release": None, "last_sync": None}
    if output_dir.is_dir():
        pm_files = sorted(
            output_dir.glob("*postmortem*.json"),
            key=lambda p: p.stat().st_mtime if p.exists() else 0,
            reverse=True,
        )
        if pm_files:
            latest = pm_files[0]
            latest_pm_info["available"] = True
            latest_pm_info["file"] = latest.name
            try:
                pm_data = json.loads(latest.read_text(encoding="utf-8"))
                meta = (
                    (pm_data.get("_metadata") or pm_data.get("metadata"))
                    if isinstance(pm_data, dict)
                    else {}
                )
                if isinstance(meta, dict):
                    latest_pm_info["release"] = meta.get("release_name") or meta.get("release")
                    sync_changes = meta.get("last_sync_changes") or {}
                    latest_pm_info["last_sync"] = (
                        sync_changes.get("timestamp")
                        or meta.get("ultima_actualizacion")
                        or meta.get("last_updated")
                    )
            except Exception:
                pass

    triage_file = output_dir / "high_priority_notifications.json"
    triage_info: Dict[str, Any] = {
        "available": triage_file.is_file(),
        "updated_at": (
            datetime.fromtimestamp(triage_file.stat().st_mtime, tz=timezone.utc).isoformat()
            if triage_file.is_file()
            else None
        ),
    }

    catalog_file = storage / "projects_catalog.json"
    if not catalog_file.is_file():
        catalog_file = root / "data" / "projects_catalog.json"
    catalog_info: Dict[str, Any] = {"available": catalog_file.is_file(), "releases_count": 0}
    if catalog_file.is_file():
        try:
            cat_data = json.loads(catalog_file.read_text(encoding="utf-8"))
            releases = cat_data.get("releases") if isinstance(cat_data, dict) else {}
            if isinstance(releases, dict):
                catalog_info["releases_count"] = len(releases)
        except Exception:
            pass

    montmc_url = os.environ.get("MON_TMC_BASE_URL", "https://montmc.orange.es").strip()
    epsilon_url = os.environ.get("EPSILON_API_URL", "https://epsilon.orange.es").strip()
    integrations = {
        "montmc_configured": bool(montmc_url),
        "montmc_base_url": montmc_url,
        "epsilon_configured": bool(epsilon_url),
        "epsilon_token_present": bool(os.environ.get("EPSILON_BEARER_TOKEN", "").strip()),
    }

    return {
        "status": "ok" if storage_status["ok"] else "degraded",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "storage": storage_status,
        "postmortem": latest_pm_info,
        "triage": triage_info,
        "projects_catalog": catalog_info,
        "integrations": integrations,
    }
