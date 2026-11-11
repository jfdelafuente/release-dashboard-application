"""
Pruebas unitarias para los endpoints de sincronización y detalle de Remedy en serve_app.py:
  - POST /api/sync-remedy
  - GET /api/remedy/detail/{idRemedy}
"""
import io
import json
import time
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

import serve_app
from converters.src.montmc_client import RemedyNotFoundError, MonTMCError


@pytest.fixture(autouse=True)
def clean_remedy_cache():
    """Limpia la caché de Remedy antes y después de cada test."""
    serve_app.REMEDY_DETAIL_CACHE.clear()
    yield
    serve_app.REMEDY_DETAIL_CACHE.clear()


# =========================================================================
# Tests para POST /api/sync-remedy
# =========================================================================

def test_handle_sync_remedy_success():
    handler = MagicMock()
    body = json.dumps({"dias": 5, "usuario": "test_user"}).encode("utf-8")
    handler.headers = {"Content-Length": str(len(body))}
    handler.rfile = io.BytesIO(body)
    handler.path = "/api/sync-remedy"
    handler._send_json = MagicMock()

    mock_result = {
        "success": True,
        "count": 12,
        "stats": {"inserted": 2, "updated": 10, "historical_kept": 450},
        "target_file": "2026-11-11-massive.json",
    }

    with patch("serve_app.sync_remedy_incidents", return_value=mock_result) as mock_sync:
        serve_app.CustomHTTPHandler.handle_sync_remedy(handler)
        mock_sync.assert_called_once_with(dias=5, usuario="test_user", project_root=serve_app.PROJECT_ROOT)

    assert handler._send_json.called
    status, payload = handler._send_json.call_args[0]
    assert status == 200
    assert payload["success"] is True
    assert payload["count"] == 12


def test_handle_sync_remedy_query_params_fallback():
    handler = MagicMock()
    handler.headers = {"Content-Length": "0"}
    handler.rfile = io.BytesIO(b"")
    handler.path = "/api/sync-remedy?dias=7&usuario=param_user"
    handler._send_json = MagicMock()

    mock_result = {"success": True, "count": 5}

    with patch("serve_app.sync_remedy_incidents", return_value=mock_result) as mock_sync:
        serve_app.CustomHTTPHandler.handle_sync_remedy(handler)
        mock_sync.assert_called_once_with(dias=7, usuario="param_user", project_root=serve_app.PROJECT_ROOT)

    status, _ = handler._send_json.call_args[0]
    assert status == 200


def test_handle_sync_remedy_failure_502():
    handler = MagicMock()
    handler.headers = {"Content-Length": "0"}
    handler.rfile = io.BytesIO(b"")
    handler.path = "/api/sync-remedy"
    handler._send_json = MagicMock()

    mock_result = {"success": False, "error": "Fallo de conexión con SOPTMC"}

    with patch("serve_app.sync_remedy_incidents", return_value=mock_result):
        serve_app.CustomHTTPHandler.handle_sync_remedy(handler)

    status, payload = handler._send_json.call_args[0]
    assert status == 502
    assert payload["success"] is False


def test_do_post_routes_to_sync_remedy():
    handler = MagicMock()
    handler.path = "/api/sync-remedy"
    handler.handle_sync_remedy = MagicMock()

    serve_app.CustomHTTPHandler.do_POST(handler)
    assert handler.handle_sync_remedy.called


# =========================================================================
# Tests para GET /api/remedy/detail/{idRemedy}
# =========================================================================

def test_handle_remedy_detail_missing_id():
    handler = MagicMock()
    handler.path = "/api/remedy/detail/"
    handler.headers = {}
    handler._send_json = MagicMock()

    serve_app.CustomHTTPHandler.handle_remedy_detail(handler, "")

    status, payload = handler._send_json.call_args[0]
    assert status == 400
    assert payload["success"] is False


def test_handle_remedy_detail_live_success_and_memory_cache(tmp_path):
    handler = MagicMock()
    handler.path = "/api/remedy/detail/INC000004179897"
    handler.headers = {}
    handler._send_json = MagicMock()

    mock_raw_detail = {
        "remedy": {
            "id": "INC000004179897",
            "detalle": "Incidencia masiva routers B2B",
            "detalleSolucion": "Reinicio de interfaces",
            "worklog": [
                {"fecha": "2026-11-10 14:00", "texto": "Investigando", "autor": "TMC"},
                {"fecha": "2026-11-10 14:30", "texto": "Solución aplicada", "autor": "NOC"}
            ],
            "paps": ["PAP-1234"]
        }
    }

    with patch("serve_app.PROJECT_ROOT", tmp_path), \
         patch.object(serve_app.MonTMCClient, "fetch_remedy_detail", return_value=mock_raw_detail):
        serve_app.CustomHTTPHandler.handle_remedy_detail(handler, "INC000004179897")

    status, payload = handler._send_json.call_args[0]
    assert status == 200
    assert payload["success"] is True
    assert payload["idRemedy"] == "INC000004179897"
    assert len(payload["worklogs"]) == 2
    assert payload["_cached"] is False
    assert "INC000004179897" in serve_app.REMEDY_DETAIL_CACHE

    # Segunda llamada: debe responder desde la caché en memoria
    handler_cache = MagicMock()
    handler_cache.path = "/api/remedy/detail/INC000004179897"
    handler_cache.headers = {}
    handler_cache._send_json = MagicMock()

    with patch.object(serve_app.MonTMCClient, "fetch_remedy_detail", side_effect=Exception("No debe llamarse")):
        serve_app.CustomHTTPHandler.handle_remedy_detail(handler_cache, "INC000004179897")

    cache_status, cache_payload = handler_cache._send_json.call_args[0]
    assert cache_status == 200
    assert cache_payload["_cached"] is True


def test_handle_remedy_detail_not_found_404():
    handler = MagicMock()
    handler.path = "/api/remedy/detail/INC999999999999"
    handler.headers = {}
    handler._send_json = MagicMock()

    with patch.object(serve_app.MonTMCClient, "fetch_remedy_detail", side_effect=RemedyNotFoundError("404 Not Found")):
        serve_app.CustomHTTPHandler.handle_remedy_detail(handler, "INC999999999999")

    status, payload = handler._send_json.call_args[0]
    assert status == 404
    assert payload["success"] is False
    assert payload["idRemedy"] == "INC999999999999"


def test_handle_remedy_detail_network_error_disk_fallback(tmp_path):
    handler = MagicMock()
    handler.path = "/api/remedy/detail/INC000004179897"
    handler.headers = {}
    handler._send_json = MagicMock()

    # Preparamos fichero en disco
    cache_dir = tmp_path / "data" / ".remedy_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    disk_file = cache_dir / "INC000004179897.json"
    disk_file.write_text(json.dumps({
        "success": True,
        "idRemedy": "INC000004179897",
        "worklogs": [{"texto": "Nota recuperada de disco"}],
    }), encoding="utf-8")

    with patch("serve_app.PROJECT_ROOT", tmp_path), \
         patch.object(serve_app.MonTMCClient, "fetch_remedy_detail", side_effect=MonTMCError("500 Server Error")):
        serve_app.CustomHTTPHandler.handle_remedy_detail(handler, "INC000004179897")

    status, payload = handler._send_json.call_args[0]
    assert status == 200
    assert payload["_cached"] is True
    assert payload["_source"] == "disk_fallback"
    assert payload["worklogs"][0]["texto"] == "Nota recuperada de disco"


def test_handle_remedy_detail_network_error_no_disk_502(tmp_path):
    handler = MagicMock()
    handler.path = "/api/remedy/detail/INC000004179897"
    handler.headers = {}
    handler._send_json = MagicMock()

    with patch("serve_app.PROJECT_ROOT", tmp_path), \
         patch.object(serve_app.MonTMCClient, "fetch_remedy_detail", side_effect=MonTMCError("500 Server Error")):
        serve_app.CustomHTTPHandler.handle_remedy_detail(handler, "INC000004179897")

    status, payload = handler._send_json.call_args[0]
    assert status == 502
    assert payload["success"] is False


def test_do_get_routes_to_remedy_detail():
    handler = MagicMock()
    handler.path = "/api/remedy/detail/INC000004179897"
    handler.handle_remedy_detail = MagicMock()

    serve_app.CustomHTTPHandler.do_GET(handler)
    handler.handle_remedy_detail.assert_called_once_with("INC000004179897")
