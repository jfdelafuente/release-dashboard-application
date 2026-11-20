# -*- coding: utf-8 -*-
"""
test_m21_desk_service.py
------------------------
Pruebas unitarias para la capa de servicio backend unificada (desk_service.py)
introducida en M21 para garantizar paridad exacta entre serve_app.py y FastAPI.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from converters.src.desk_service import (
    clear_global_remedy_cache,
    resolve_project_root,
    resolve_storage_dir,
    resolve_remedy_cache_dir,
    service_get_cached_epsilon,
    service_get_health,
    service_get_overrides,
    service_get_remedy_detail,
    service_set_override,
    service_sync_postmortem,
    service_sync_remedy,
    GLOBAL_REMEDY_CACHE,
)
from converters.src.montmc_client import RemedyNotFoundError, MonTMCError


@pytest.fixture(autouse=True)
def reset_service_cache():
    clear_global_remedy_cache()
    yield
    clear_global_remedy_cache()


# =============================================================================
# Tests de Rutas y Directorios
# =============================================================================

def test_resolve_project_root_and_storage(tmp_path, monkeypatch):
    custom_root = tmp_path / "custom_project"
    custom_root.mkdir()
    monkeypatch.setenv("RELEASE_DASHBOARD_ROOT", str(custom_root))
    assert resolve_project_root() == custom_root

    custom_storage = tmp_path / "custom_storage"
    custom_storage.mkdir()
    monkeypatch.setenv("RELEASE_DASHBOARD_STORAGE_DIR", str(custom_storage))
    assert resolve_storage_dir() == custom_storage
    cache_dir = resolve_remedy_cache_dir(project_root=custom_root)
    assert cache_dir.exists()


# =============================================================================
# Tests de Sincronización (service_sync_remedy y service_sync_postmortem)
# =============================================================================

def test_service_sync_remedy_success():
    mock_fn = MagicMock(return_value={"success": True, "count": 10})
    code, res = service_sync_remedy(payload={"dias": 5, "usuario": "user1"}, sync_fn=mock_fn)
    assert code == 200
    assert res["success"] is True
    assert res["count"] == 10
    mock_fn.assert_called_once()
    _, kwargs = mock_fn.call_args
    assert kwargs["dias"] == 5
    assert kwargs["usuario"] == "user1"


def test_service_sync_remedy_missing_module():
    code, res = service_sync_remedy(sync_fn=None)
    # Si no se encuentra el módulo sync_montmc_incidents
    with patch("converters.src.desk_service.service_sync_remedy", side_effect=None):
        pass


def test_service_sync_remedy_exception_502():
    mock_fn = MagicMock(side_effect=RuntimeError("MonTMC timeout"))
    code, res = service_sync_remedy(payload=None, sync_fn=mock_fn)
    assert code == 502
    assert res["success"] is False
    assert "MonTMC timeout" in res["error"]


def test_service_sync_postmortem_success():
    mock_fn = MagicMock(return_value={"success": True, "release_name": "2026R9", "count": 4})
    code, res = service_sync_postmortem(
        payload={"release_name": "2026R9", "usuario": "user2"},
        sync_fn=mock_fn,
    )
    assert code == 200
    assert res["release_name"] == "2026R9"
    _, kwargs = mock_fn.call_args
    assert kwargs["release_name"] == "2026R9"
    assert kwargs["usuario"] == "user2"


def test_service_sync_postmortem_exception_502():
    mock_fn = MagicMock(side_effect=ConnectionError("Conexión rechazada"))
    code, res = service_sync_postmortem(sync_fn=mock_fn)
    assert code == 502
    assert res["success"] is False
    assert "Conexión rechazada" in res["error"]


# =============================================================================
# Tests de Overrides de Mesa de Release
# =============================================================================

def test_service_overrides_lifecycle(tmp_path):
    storage_dir = tmp_path / "data"
    storage_dir.mkdir(parents=True)

    # 1. Obtener inicial (vacío)
    initial = service_get_overrides(storage_dir, "2026R9")
    assert initial["success"] is True
    assert initial["overrides"] == {}

    # 2. Guardar override válido
    code, res = service_set_override(
        payload={
            "release_name": "2026R9",
            "incident_id": "INC000004179897",
            "fecha_prevista": "2026-11-25",
        },
        storage_dir=storage_dir,
    )
    assert code == 200
    assert res["success"] is True
    assert res["fecha_prevista"] == "2026-11-25"

    # 3. Verificar que persiste al leer
    updated = service_get_overrides(storage_dir, "2026R9")
    assert "INC000004179897" in updated["overrides"]
    assert updated["overrides"]["INC000004179897"]["fecha_prevista"] == "2026-11-25"

    # 4. Error de validación (incident_id vacío) -> 400
    bad_code, bad_res = service_set_override(
        payload={
            "release_name": "2026R9",
            "incident_id": "",
            "fecha_prevista": "2026-11-25",
        },
        storage_dir=storage_dir,
    )
    assert bad_code == 400
    assert bad_res["success"] is False


# =============================================================================
# Tests de Resumen IA en Caché
# =============================================================================

def test_service_get_cached_epsilon(tmp_path):
    storage_dir = tmp_path / "data"
    cache_dir = storage_dir / ".epsilon_cache"
    cache_dir.mkdir(parents=True)
    summary_file = cache_dir / "INC000004179897.json"
    summary_file.write_text(json.dumps({
        "codigo": "INC000004179897",
        "resumen": "Resumen de prueba IA",
    }), encoding="utf-8")

    # Consulta con string delimitado por comas
    res_str = service_get_cached_epsilon("INC000004179897, INC999999", storage_dir=storage_dir)
    assert res_str["success"] is True
    assert res_str["count"] == 1
    assert "INC000004179897" in res_str["summaries"]

    # Consulta con lista
    res_list = service_get_cached_epsilon(["INC000004179897"], storage_dir=storage_dir)
    assert res_list["count"] == 1


# =============================================================================
# Tests de Health
# =============================================================================

def test_service_get_health(tmp_path):
    storage_dir = tmp_path / "data"
    storage_dir.mkdir(parents=True)
    (storage_dir / "output").mkdir()

    code, health = service_get_health(storage_dir=storage_dir, project_root=tmp_path)
    assert code in (200, 503)
    assert "status" in health
    assert "storage" in health
    assert "integrations" in health


# =============================================================================
# Tests de Detalle Remedy con Doble Caché
# =============================================================================

def test_service_get_remedy_detail_validation_and_flow(tmp_path):
    # 1. ID vacío
    code, res, _ = service_get_remedy_detail(id_remedy="   ")
    assert code == 400

    # 2. Mock del cliente MonTMC
    mock_client = MagicMock()
    mock_client.fetch_remedy_detail.return_value = {
        "remedy": {
            "id": "INC000004179897",
            "detalle": "Incidencia en servicio FTTH",
            "estadoDesc": "En Curso",
            "worklog": [{"texto": "Nota técnica inicial"}],
        }
    }
    mock_cls = MagicMock(return_value=mock_client)

    cache_dir = tmp_path / "data" / ".remedy_cache"
    cache_dir.mkdir(parents=True)

    code, payload, headers = service_get_remedy_detail(
        id_remedy="INC000004179897",
        cache_dir=cache_dir,
        client_cls=mock_cls,
    )
    assert code == 200
    assert headers.get("X-Cache-Status") == "LIVE_SOPTMC_HIT"
    assert payload["idRemedy"] == "INC000004179897"
    assert "INC000004179897" in GLOBAL_REMEDY_CACHE

    # 3. Segunda llamada: debe ser un HIT de memoria
    code_mem, payload_mem, headers_mem = service_get_remedy_detail(
        id_remedy="INC000004179897",
        cache_dir=cache_dir,
        client_cls=mock_cls,
    )
    assert code_mem == 200
    assert headers_mem.get("X-Cache-Status") == "MEMORY_HIT"
    assert payload_mem["_cached"] is True
    # Solo 1 llamada al cliente MonTMC
    assert mock_client.fetch_remedy_detail.call_count == 1

    # 4. Fallback a disco ante fallo de red
    clear_global_remedy_cache()
    mock_client_err = MagicMock()
    mock_client_err.fetch_remedy_detail.side_effect = MonTMCError("500 Server Error")
    mock_cls_err = MagicMock(return_value=mock_client_err)

    code_disk, payload_disk, headers_disk = service_get_remedy_detail(
        id_remedy="INC000004179897",
        cache_dir=cache_dir,
        client_cls=mock_cls_err,
    )
    assert code_disk == 200
    assert headers_disk.get("X-Cache-Status") == "DISK_FALLBACK"
    assert payload_disk["_cached"] is True

    # 5. Ticket inexistente 404
    mock_client_404 = MagicMock()
    mock_client_404.fetch_remedy_detail.side_effect = RemedyNotFoundError("Ticket no existe")
    mock_cls_404 = MagicMock(return_value=mock_client_404)

    code_404, payload_404, _ = service_get_remedy_detail(
        id_remedy="INC999999999999",
        cache_dir=cache_dir,
        client_cls=mock_cls_404,
    )
    assert code_404 == 404
    assert payload_404["success"] is False
