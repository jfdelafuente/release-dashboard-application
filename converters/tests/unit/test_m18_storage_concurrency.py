# -*- coding: utf-8 -*-
"""Tests unitarios M18: concurrencia segura, escritura atómica, backup .bak y retención de caché."""

from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import time

from converters.cli.update_agent_message import update_agent_store
from converters.src.release_desk_overrides import (
    get_overrides_for_release,
    set_fecha_prevista_override,
)
from converters.src.storage_utils import check_storage_writability, prune_cache_dir


def test_concurrent_release_desk_overrides_no_lost_updates(tmp_path: Path):
    total = 12

    def _save(idx: int) -> None:
        set_fecha_prevista_override(
            storage_dir=tmp_path,
            release_name="2026R11",
            incident_id=f"INC000000{idx:04d}",
            fecha_prevista=f"2026-11-{(idx % 28) + 1:02d}",
        )

    with ThreadPoolExecutor(max_workers=6) as pool:
        list(pool.map(_save, range(total)))

    saved = get_overrides_for_release(tmp_path, "2026R11")
    assert len(saved) == total
    for idx in range(total):
        assert f"INC000000{idx:04d}" in saved

    overrides_file = tmp_path / "release_desk_overrides.json"
    backup_file = tmp_path / "release_desk_overrides.json.bak"
    assert overrides_file.exists()
    assert backup_file.exists()
    assert json.loads(overrides_file.read_text(encoding="utf-8"))["by_release"]["2026R11"] == saved


def test_concurrent_agent_store_updates_no_lost_updates(tmp_path: Path):
    store_path = tmp_path / "agent_executive_messages.json"
    total = 12

    def _save(idx: int) -> None:
        update_agent_store(
            store_path=store_path,
            incident_id=f"INC999000{idx:04d}",
            phase="apertura",
            completo=f"Incidencia {idx} detectada en servicio de prueba sin afectación global.",
            breve=f"Incidencia {idx} en seguimiento.",
        )

    with ThreadPoolExecutor(max_workers=6) as pool:
        list(pool.map(_save, range(total)))

    payload = json.loads(store_path.read_text(encoding="utf-8"))
    assert len(payload["incidents"]) == total
    assert (tmp_path / "agent_executive_messages.json.bak").exists()


def test_prune_cache_dir_removes_expired_and_overflow(tmp_path: Path):
    cache_dir = tmp_path / ".epsilon_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    now = time.time()
    old_file = cache_dir / "INC_OLD.json"
    old_file.write_text('{"old": true}', encoding="utf-8")
    os.utime(old_file, (now - 40 * 86400, now - 40 * 86400))

    for idx in range(5):
        f = cache_dir / f"INC_NEW_{idx}.json"
        f.write_text(f'{{"idx": {idx}}}', encoding="utf-8")
        ts = now - (5 - idx) * 60
        os.utime(f, (ts, ts))

    stats = prune_cache_dir(cache_dir, max_age_days=30, max_files=3)
    assert stats["deleted_expired"] == 1
    assert stats["deleted_overflow"] == 2
    assert stats["remaining"] == 3
    assert not old_file.exists()
    remaining_names = sorted(p.name for p in cache_dir.glob("*.json"))
    assert remaining_names == ["INC_NEW_2.json", "INC_NEW_3.json", "INC_NEW_4.json"]


def test_check_storage_writability_ok(tmp_path: Path):
    target = tmp_path / "persistent_data"
    result = check_storage_writability(target)
    assert result["ok"] is True
    assert result["error"] is None
    assert target.is_dir()


def test_storage_utils_path_resolvers(tmp_path: Path):
    from converters.src.storage_utils import (
        resolve_projects_catalog_path,
        resolve_agents_catalog_path,
        resolve_executive_messages_path,
        resolve_cache_dir,
        resolve_release_overrides_path,
        resolve_index_path,
    )
    # Por defecto cuando ninguno existe, retorna canónico
    assert resolve_projects_catalog_path(tmp_path) == tmp_path / "config" / "projects_catalog.json"
    assert resolve_cache_dir(tmp_path, "remedy") == tmp_path / "cache" / "remedy"

    # Si existe legacy y no canónico, resuelve fallback legacy
    legacy_proj = tmp_path / "projects_catalog.json"
    legacy_proj.touch()
    assert resolve_projects_catalog_path(tmp_path) == legacy_proj

    legacy_cache = tmp_path / ".epsilon_cache"
    legacy_cache.mkdir()
    assert resolve_cache_dir(tmp_path, "epsilon") == legacy_cache

    # Con estructura modular creada, resuelve rutas canónicas
    (tmp_path / "config").mkdir(parents=True, exist_ok=True)
    canonical_proj = tmp_path / "config" / "projects_catalog.json"
    canonical_proj.touch()
    assert resolve_projects_catalog_path(tmp_path) == canonical_proj

    (tmp_path / "state").mkdir(parents=True, exist_ok=True)
    (tmp_path / "agents").mkdir(parents=True, exist_ok=True)
    (tmp_path / "storage").mkdir(parents=True, exist_ok=True)

    assert resolve_release_overrides_path(tmp_path) == tmp_path / "state" / "release_desk_overrides.json"
    assert resolve_agents_catalog_path(tmp_path) == tmp_path / "agents" / "catalog.json"
    assert resolve_executive_messages_path(tmp_path) == tmp_path / "agents" / "executive_messages.json"
    assert resolve_index_path(tmp_path) == tmp_path / "storage" / "index.json"


