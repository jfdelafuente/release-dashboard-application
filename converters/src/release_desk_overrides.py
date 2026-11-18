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
    """Devuelve el mapa `{incident_id: {fecha_prevista, updated_at}}` para una release."""
    rel = (release_name or "").strip()
    if not rel:
        return {}
    raw = _load_raw(Path(storage_dir) / OVERRIDES_FILENAME)
    bucket = raw.get("by_release", {}).get(rel, {})
    return bucket if isinstance(bucket, dict) else {}


def set_fecha_prevista_override(
    storage_dir: Path,
    release_name: str,
    incident_id: str,
    fecha_prevista: str,
) -> Dict[str, Any]:
    """Guarda o limpia la fecha prevista acordada de `incident_id` en `release_name`."""
    rel = (release_name or "").strip()
    inc_id = (incident_id or "").strip()
    if not rel:
        raise ValueError("release_name es obligatorio")
    if not inc_id:
        raise ValueError("incident_id es obligatorio")

    overrides_path = Path(storage_dir) / OVERRIDES_FILENAME
    raw = _load_raw(overrides_path)
    by_release = raw.setdefault("by_release", {})
    bucket = by_release.setdefault(rel, {})
    if not isinstance(bucket, dict):
        bucket = {}
        by_release[rel] = bucket

    clean_date = (fecha_prevista or "").strip()
    if clean_date:
        bucket[inc_id] = {
            "fecha_prevista": clean_date,
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        }
    else:
        bucket.pop(inc_id, None)

    raw["updated_at"] = datetime.now().isoformat(timespec="seconds")
    overrides_path.parent.mkdir(parents=True, exist_ok=True)
    overrides_path.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "success": True,
        "release_name": rel,
        "incident_id": inc_id,
        "fecha_prevista": clean_date,
        "overrides": bucket,
    }


def load_cached_epsilon_summaries(
    storage_dir: Path,
    incident_ids: Iterable[str],
) -> Dict[str, Any]:
    """Lee únicamente resúmenes ya cacheados en `<storage_dir>/.epsilon_cache/` (coste 0)."""
    cache_dir = Path(storage_dir) / ".epsilon_cache"
    summaries: Dict[str, Any] = {}
    if not cache_dir.is_dir():
        return summaries

    for raw_id in incident_ids:
        clean_id = (raw_id or "").strip()
        if not clean_id or not _SAFE_ID_RE.match(clean_id):
            continue
        cache_file = cache_dir / f"{clean_id}.json"
        if not cache_file.is_file():
            continue
        try:
            payload = json.loads(cache_file.read_text(encoding="utf-8"))
            if isinstance(payload, dict) and payload.get("success") is not False:
                payload["_cached_at_ms"] = int(cache_file.stat().st_mtime * 1000)
                payload["_from_disk_cache"] = True
                summaries[clean_id] = payload
        except Exception:
            continue
    return summaries
