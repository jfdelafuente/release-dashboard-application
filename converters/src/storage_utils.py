# -*- coding: utf-8 -*-
"""
Utilidades compartidas de almacenamiento seguro para Mesa de Release y Consola de Triaje:
- Locks por fichero (`threading.Lock`) para evitar condiciones de carrera en escrituras concurrentes.
- Escritura atómica de JSON (`tempfile` + `fsync` + `os.replace`) con copia `.bak` opcional.
- Política de retención y limpieza (TTL + máximo de ficheros) para cachés en disco.
- Verificación de permisos de escritura en el directorio de almacenamiento persistente.
"""

from __future__ import annotations

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
        os.replace(tmp_path, target)
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
