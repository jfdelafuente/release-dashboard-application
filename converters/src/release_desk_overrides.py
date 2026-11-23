# -*- coding: utf-8 -*-
"""
Persistencia ligera de overrides operativos para Mesa de Release
(por ahora: Fecha Prevista acordada por incidencia y release) en
`<storage_dir>/release_desk_overrides.json` sin alterar los datos crudos de MonTMC.
"""

from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
import re
from typing import Any, Dict, Iterable

from converters.src.storage_utils import (
    atomic_write_json,
    get_path_lock,
    resolve_cache_dir,
    resolve_release_overrides_path,
)


import time
import uuid

OVERRIDES_FILENAME = "release_desk_overrides.json"
_SAFE_ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def _load_raw(overrides_path: Path) -> Dict[str, Any]:
    if not overrides_path.exists():
        return {"by_release": {}}
    try:
        data = json.loads(overrides_path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("by_release"), dict):
            return data
    except Exception:
        pass
    return {"by_release": {}}


def get_overrides_for_release(storage_dir: Path, release_name: str) -> Dict[str, Any]:
    """Devuelve el mapa `{incident_id: {fecha_prevista, notas, updated_at}}` para una release."""
    rel = (release_name or "").strip()
    if not rel:
        return {}
    overrides_path = resolve_release_overrides_path(Path(storage_dir))
    raw = _load_raw(overrides_path)
    bucket = raw.get("by_release", {}).get(rel, {})
    return bucket if isinstance(bucket, dict) else {}


def set_fecha_prevista_override(
    storage_dir: Path,
    release_name: str,
    incident_id: str,
    fecha_prevista: str,
) -> Dict[str, Any]:
    """Guarda o limpia la fecha prevista acordada de `incident_id` en `release_name`, preservando notas."""
    rel = (release_name or "").strip()
    inc_id = (incident_id or "").strip()
    if not rel:
        raise ValueError("release_name es obligatorio")
    if not inc_id:
        raise ValueError("incident_id es obligatorio")

    overrides_path = resolve_release_overrides_path(Path(storage_dir))
    clean_date = (fecha_prevista or "").strip()

    with get_path_lock(overrides_path):
        raw = _load_raw(overrides_path)
        by_release = raw.setdefault("by_release", {})
        bucket = by_release.setdefault(rel, {})
        if not isinstance(bucket, dict):
            bucket = {}
            by_release[rel] = bucket

        now_iso = datetime.now().isoformat(timespec="seconds")
        existing_entry = bucket.get(inc_id)
        entry = dict(existing_entry) if isinstance(existing_entry, dict) else {}

        if clean_date:
            entry["fecha_prevista"] = clean_date
            entry["updated_at"] = now_iso
            bucket[inc_id] = entry
        else:
            entry.pop("fecha_prevista", None)
            if entry.get("notas"):
                entry["updated_at"] = now_iso
                bucket[inc_id] = entry
            else:
                bucket.pop(inc_id, None)

        raw["updated_at"] = now_iso
        atomic_write_json(overrides_path, raw, create_backup=True, indent=2)

    return {
        "success": True,
        "release_name": rel,
        "incident_id": inc_id,
        "fecha_prevista": clean_date,
        "overrides": bucket,
    }


def add_nota_override(
    storage_dir: Path,
    release_name: str,
    incident_id: str,
    texto: str,
    fecha: Optional[str] = None,
) -> Dict[str, Any]:
    """Añade una nota con marca de tiempo al historial cronológico de `incident_id` en `release_name`."""
    rel = (release_name or "").strip()
    inc_id = (incident_id or "").strip()
    clean_text = (texto or "").strip()
    if not rel:
        raise ValueError("release_name es obligatorio")
    if not inc_id:
        raise ValueError("incident_id es obligatorio")
    if not clean_text:
        raise ValueError("El texto de la nota no puede estar vacío")

    overrides_path = resolve_release_overrides_path(Path(storage_dir))
    now_iso = datetime.now().isoformat(timespec="seconds")
    note_date = (fecha or "").strip() or now_iso
    note_id = f"{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}"

    note_obj = {
        "id": note_id,
        "fecha": note_date,
        "texto": clean_text,
    }

    with get_path_lock(overrides_path):
        raw = _load_raw(overrides_path)
        by_release = raw.setdefault("by_release", {})
        bucket = by_release.setdefault(rel, {})
        if not isinstance(bucket, dict):
            bucket = {}
            by_release[rel] = bucket

        existing_entry = bucket.get(inc_id)
        entry = dict(existing_entry) if isinstance(existing_entry, dict) else {}
        notas_list = list(entry.get("notas", [])) if isinstance(entry.get("notas"), list) else []

        # Insertar la nota más reciente al principio
        notas_list.insert(0, note_obj)
        entry["notas"] = notas_list
        entry["updated_at"] = now_iso
        bucket[inc_id] = entry

        raw["updated_at"] = now_iso
        atomic_write_json(overrides_path, raw, create_backup=True, indent=2)

    return {
        "success": True,
        "release_name": rel,
        "incident_id": inc_id,
        "nota": note_obj,
        "notas": bucket[inc_id]["notas"],
        "overrides": bucket,
    }


def delete_nota_override(
    storage_dir: Path,
    release_name: str,
    incident_id: str,
    nota_id: str,
) -> Dict[str, Any]:
    """Elimina una nota específica del historial de `incident_id` en `release_name`."""
    rel = (release_name or "").strip()
    inc_id = (incident_id or "").strip()
    clean_nota_id = (nota_id or "").strip()
    if not rel:
        raise ValueError("release_name es obligatorio")
    if not inc_id:
        raise ValueError("incident_id es obligatorio")
    if not clean_nota_id:
        raise ValueError("nota_id es obligatorio")

    overrides_path = resolve_release_overrides_path(Path(storage_dir))
    now_iso = datetime.now().isoformat(timespec="seconds")

    with get_path_lock(overrides_path):
        raw = _load_raw(overrides_path)
        by_release = raw.setdefault("by_release", {})
        bucket = by_release.setdefault(rel, {})
        if not isinstance(bucket, dict):
            bucket = {}
            by_release[rel] = bucket

        existing_entry = bucket.get(inc_id)
        if isinstance(existing_entry, dict):
            entry = dict(existing_entry)
            notas_list = [
                n for n in entry.get("notas", [])
                if isinstance(n, dict) and str(n.get("id")) != clean_nota_id
            ]
            if notas_list:
                entry["notas"] = notas_list
                entry["updated_at"] = now_iso
                bucket[inc_id] = entry
            else:
                entry.pop("notas", None)
                if entry.get("fecha_prevista"):
                    entry["updated_at"] = now_iso
                    bucket[inc_id] = entry
                else:
                    bucket.pop(inc_id, None)

        raw["updated_at"] = now_iso
        atomic_write_json(overrides_path, raw, create_backup=True, indent=2)

    current_entry = bucket.get(inc_id, {})
    return {
        "success": True,
        "release_name": rel,
        "incident_id": inc_id,
        "nota_id": clean_nota_id,
        "notas": current_entry.get("notas", []) if isinstance(current_entry, dict) else [],
        "overrides": bucket,
    }


def load_cached_epsilon_summaries(
    storage_dir: Path,
    incident_ids: Iterable[str],
) -> Dict[str, Any]:
    """Lee únicamente resúmenes ya cacheados en `<storage_dir>/cache/epsilon/` o `.epsilon_cache/` (coste 0)."""
    st = Path(storage_dir)
    candidate_dirs: List[Path] = []
    for d in [
        resolve_cache_dir(st, "epsilon"),
        st / ".epsilon_cache",
        st / "data" / ".epsilon_cache",
        st / "cache" / "epsilon",
        Path("/infocodes/var/storage/release-dashboard/cache/epsilon"),
        Path("/infocodes/var/storage/release-dashboard/.epsilon_cache"),
        Path("/infocodes/var/storage/release-dashboard/data/.epsilon_cache"),
    ]:
        if d.is_dir() and d not in candidate_dirs:
            candidate_dirs.append(d)

    summaries: Dict[str, Any] = {}
    if not candidate_dirs:
        return summaries

    for raw_id in incident_ids:
        clean_id = (raw_id or "").strip()
        if not clean_id or not _SAFE_ID_RE.match(clean_id):
            continue
        for cdir in candidate_dirs:
            cache_file = cdir / f"{clean_id}.json"
            if cache_file.is_file():
                try:
                    payload = json.loads(cache_file.read_text(encoding="utf-8"))
                    if isinstance(payload, dict) and payload.get("success") is not False:
                        payload["_cached_at_ms"] = int(cache_file.stat().st_mtime * 1000)
                        payload["_from_disk_cache"] = True
                        summaries[clean_id] = payload
                        break
                except Exception:
                    continue
    return summaries
