# -*- coding: utf-8 -*-
"""
test_fastapi_remedy_router.py
-----------------------------
Pruebas unitarias para el router FastAPI de integración con MonTMC Remedy en producción.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from fastapi import HTTPException

from converters.src.fastapi_remedy_router import (
    sync_remedy,
    get_remedy_detail,
    clear_fastapi_remedy_cache,
    FASTAPI_REMEDY_CACHE,
)
from converters.src.montmc_client import RemedyNotFoundError, MonTMCError


@pytest.fixture(autouse=True)
def reset_remedy_cache():
    clear_fastapi_remedy_cache()
    yield
    clear_fastapi_remedy_cache()


# =============================================================================
# Tests para POST /api/sync-remedy
# =============================================================================

def test_fastapi_sync_remedy_success():
    mock_result = {
        "success": True,
        "count": 15,
        "total_consultadas": 15,
        "nuevas": 2,
        "actualizadas": 5,
        "target_file": "/tmp/test.json",
    }
    with patch("converters.src.fastapi_remedy_router.sync_remedy_incidents", return_value=mock_result) as mock_sync:
        resp = sync_remedy(payload={"dias": 5, "usuario": "test_fastapi"})
        assert resp.status_code == 200
        data = json.loads(resp.body.decode("utf-8"))
        assert data["success"] is True
        assert data["count"] == 15
        assert data["nuevas"] == 2
        mock_sync.assert_called_once()
        _, kwargs = mock_sync.call_args
        assert kwargs["dias"] == 5
        assert kwargs["usuario"] == "test_fastapi"


def test_fastapi_sync_remedy_query_params_fallback():
    mock_result = {"success": True, "count": 8}
    with patch("converters.src.fastapi_remedy_router.sync_remedy_incidents", return_value=mock_result) as mock_sync:
        resp = sync_remedy(payload=None, dias=7, usuario="user_query")
        assert resp.status_code == 200
        _, kwargs = mock_sync.call_args
        assert kwargs["dias"] == 7
        assert kwargs["usuario"] == "user_query"


def test_fastapi_sync_remedy_failure_502():
    mock_result = {"success": False, "error": "Fallo de conexión con SOPTMC"}
    with patch("converters.src.fastapi_remedy_router.sync_remedy_incidents", return_value=mock_result):
        resp = sync_remedy(payload=None)
        assert resp.status_code == 502
        data = json.loads(resp.body.decode("utf-8"))
        assert data["success"] is False
        assert "Fallo de conexión" in data["error"]


def test_fastapi_sync_remedy_exception_502():
    with patch("converters.src.fastapi_remedy_router.sync_remedy_incidents", side_effect=RuntimeError("Error crítico")):
        resp = sync_remedy(payload={"dias": 3})
        assert resp.status_code == 502
        data = json.loads(resp.body.decode("utf-8"))
        assert data["success"] is False
        assert "Error crítico" in data["error"]


# =============================================================================
# Tests para GET /api/remedy/detail/{id_remedy}
# =============================================================================

def test_fastapi_remedy_detail_empty_id():
    with pytest.raises(HTTPException) as exc_info:
        get_remedy_detail(id_remedy="   ")
    assert exc_info.value.status_code == 400


def test_fastapi_remedy_detail_live_success_and_memory_cache():
    mock_raw = {
        "remedy": {
            "id": "INC000004179897",
            "detalle": "Incidencia en servicio FTTH",
            "detalleSolucion": "Reinicio de OLT",
            "estadoDesc": "En Curso",
            "worklog": [
                {"fecha": "2026-11-10 10:00", "texto": "Análisis inicial", "autor": "NOC"},
                {"fecha": "2026-11-10 10:30", "texto": "Reinicio ejecutado", "autor": "TMC"}
            ],
            "paps": ["PAP-001"]
        }
    }

    with patch("converters.src.fastapi_remedy_router.MonTMCClient") as mock_client_cls:
        instance = mock_client_cls.return_value
        instance.fetch_remedy_detail.return_value = mock_raw

        resp = get_remedy_detail(id_remedy="INC000004179897")
        assert resp.status_code == 200
        assert resp.headers.get("X-Cache-Status") == "LIVE_SOPTMC_HIT"
        data = json.loads(resp.body.decode("utf-8"))
        assert data["success"] is True
        assert data["idRemedy"] == "INC000004179897"
        assert len(data["worklogs"]) == 2
        assert data["_cached"] is False
        assert "INC000004179897" in FASTAPI_REMEDY_CACHE

        # Segunda llamada: memoria cache HIT
        resp_cached = get_remedy_detail(id_remedy="INC000004179897")
        assert resp_cached.status_code == 200
        assert resp_cached.headers.get("X-Cache-Status") == "MEMORY_HIT"
        data_cached = json.loads(resp_cached.body.decode("utf-8"))
        assert data_cached["_cached"] is True
        # Aseguramos que la llamada al cliente solo ocurrió una vez
        assert instance.fetch_remedy_detail.call_count == 1


def test_fastapi_remedy_detail_not_found_404():
    with patch("converters.src.fastapi_remedy_router.MonTMCClient") as mock_client_cls:
        instance = mock_client_cls.return_value
        instance.fetch_remedy_detail.side_effect = RemedyNotFoundError("Ticket no existe")

        resp = get_remedy_detail(id_remedy="INC999999999999")
        assert resp.status_code == 404
        data = json.loads(resp.body.decode("utf-8"))
        assert data["success"] is False
        assert data["idRemedy"] == "INC999999999999"


def test_fastapi_remedy_detail_disk_fallback(tmp_path):
    cache_dir = tmp_path / "data" / ".remedy_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / "INC000004179897.json"
    cache_file.write_text(json.dumps({
        "success": True,
        "idRemedy": "INC000004179897",
        "worklogs": [{"texto": "Nota guardada en disco"}],
    }), encoding="utf-8")

    with patch("converters.src.fastapi_remedy_router._get_cache_dir", return_value=cache_dir), \
         patch("converters.src.fastapi_remedy_router.MonTMCClient") as mock_client_cls:
        instance = mock_client_cls.return_value
        instance.fetch_remedy_detail.side_effect = MonTMCError("500 Server Error")

        resp = get_remedy_detail(id_remedy="INC000004179897")
        assert resp.status_code == 200
        assert resp.headers.get("X-Cache-Status") == "DISK_FALLBACK"
        data = json.loads(resp.body.decode("utf-8"))
        assert data["_cached"] is True
        assert data["_source"] == "disk_fallback"
        assert data["worklogs"][0]["texto"] == "Nota guardada en disco"


def test_fastapi_remedy_detail_no_disk_returns_502(tmp_path):
    empty_cache_dir = tmp_path / "data" / ".remedy_cache"
    empty_cache_dir.mkdir(parents=True, exist_ok=True)

    with patch("converters.src.fastapi_remedy_router._get_cache_dir", return_value=empty_cache_dir), \
         patch("converters.src.fastapi_remedy_router.MonTMCClient") as mock_client_cls:
        instance = mock_client_cls.return_value
        instance.fetch_remedy_detail.side_effect = MonTMCError("500 Server Error")

        resp = get_remedy_detail(id_remedy="INC000004179897")
        assert resp.status_code == 502
        data = json.loads(resp.body.decode("utf-8"))
        assert data["success"] is False
