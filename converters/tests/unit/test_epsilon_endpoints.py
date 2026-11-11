"""
Pruebas unitarias e integración para los endpoints HTTP de Epsilon Resumen IA en serve_app.py.
"""
import io
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

import serve_app


@pytest.fixture(autouse=True)
def clean_cache():
    """Limpia la caché de Epsilon antes y después de cada test."""
    serve_app.EPSILON_CACHE.clear()
    yield
    serve_app.EPSILON_CACHE.clear()


# =========================================================================
# Tests para POST /api/epsilon/generate y POST /api/epsilon/resumen
# =========================================================================

def test_handle_epsilon_generate_empty_body():
    handler = MagicMock()
    handler.headers = {"Content-Length": "0"}
    handler.rfile = io.BytesIO(b"")
    handler.path = "/api/epsilon/generate"
    handler._send_json = MagicMock()

    serve_app.CustomHTTPHandler.handle_epsilon_generate(handler)

    assert handler._send_json.called
    status, payload = handler._send_json.call_args[0]
    assert status == 400
    assert payload["success"] is False
    assert "vacío" in payload["error"]


def test_handle_epsilon_generate_invalid_json():
    handler = MagicMock()
    bad_bytes = b"{invalid-json"
    handler.headers = {"Content-Length": str(len(bad_bytes))}
    handler.rfile = io.BytesIO(bad_bytes)
    handler.path = "/api/epsilon/generate"
    handler._send_json = MagicMock()

    serve_app.CustomHTTPHandler.handle_epsilon_generate(handler)

    assert handler._send_json.called
    status, payload = handler._send_json.call_args[0]
    assert status == 400
    assert payload["success"] is False


def test_handle_epsilon_generate_insufficient_incident_data():
    handler = MagicMock()
    raw_body = json.dumps({"incident_data": {}}).encode("utf-8")
    handler.headers = {"Content-Length": str(len(raw_body))}
    handler.rfile = io.BytesIO(raw_body)
    handler.path = "/api/epsilon/generate"
    handler._send_json = MagicMock()

    serve_app.CustomHTTPHandler.handle_epsilon_generate(handler)

    assert handler._send_json.called
    status, payload = handler._send_json.call_args[0]
    assert status == 400
    assert "insuficientes" in payload["error"]


def test_handle_epsilon_generate_direct_payload_mock_success(tmp_path):
    handler = MagicMock()
    incident_payload = {
        "codigo": "INC000004174655",
        "Descripción": "Caída del servicio B2B",
        "Estatus": "Asignado",
        "Prioridad": "Crítica"
    }
    raw_body = json.dumps(incident_payload).encode("utf-8")
    handler.headers = {"Content-Length": str(len(raw_body))}
    handler.rfile = io.BytesIO(raw_body)
    handler.path = "/api/epsilon/generate?mock=true"
    handler._send_json = MagicMock()

    with patch("serve_app.PROJECT_ROOT", tmp_path):
        serve_app.CustomHTTPHandler.handle_epsilon_generate(handler)

    assert handler._send_json.called
    status, payload = handler._send_json.call_args[0]
    assert status == 200
    assert payload["success"] is True
    assert "data" in payload
    assert payload["data"]["problema"]
    assert "INC000004174655" in serve_app.EPSILON_CACHE


def test_handle_epsilon_generate_wrapper_payload_mock_success(tmp_path):
    handler = MagicMock()
    request_body = {
        "incident_data": {
            "ID de incidencia": "INC000004179999",
            "Descripción": "Degradación en Pasarela de Pago",
            "Estatus": "Pendiente",
            "Prioridad": "Alta"
        },
        "mock": True
    }
    raw_body = json.dumps(request_body).encode("utf-8")
    handler.headers = {"Content-Length": str(len(raw_body))}
    handler.rfile = io.BytesIO(raw_body)
    handler.path = "/api/epsilon/generate"
    handler._send_json = MagicMock()

    with patch("serve_app.PROJECT_ROOT", tmp_path):
        serve_app.CustomHTTPHandler.handle_epsilon_generate(handler)

    assert handler._send_json.called
    status, payload = handler._send_json.call_args[0]
    assert status == 200
    assert payload["success"] is True
    assert "INC000004179999" in serve_app.EPSILON_CACHE


def test_handle_epsilon_generate_pydantic_validation_failure_returns_422():
    handler = MagicMock()
    request_body = {
        "incident_data": {"codigo": "INC123456"},
        "mock": False
    }
    raw_body = json.dumps(request_body).encode("utf-8")
    handler.headers = {"Content-Length": str(len(raw_body))}
    handler.rfile = io.BytesIO(raw_body)
    handler.path = "/api/epsilon/generate"
    handler._send_json = MagicMock()

    with patch("serve_app.generate_epsilon_summary") as mock_gen:
        mock_gen.return_value = (
            False,
            {
                "error": "Error de validación de esquema Epsilon",
                "validation_errors": ["problema: excede 40 palabras"],
                "raw_output": {}
            },
            {"mock": False}
        )
        serve_app.CustomHTTPHandler.handle_epsilon_generate(handler)

    assert handler._send_json.called
    status, payload = handler._send_json.call_args[0]
    assert status == 422
    assert payload["success"] is False
    assert "validation_errors" in payload


def test_handle_epsilon_generate_llm_exception_returns_502():
    handler = MagicMock()
    request_body = {
        "incident_data": {"codigo": "INC123456"},
        "mock": False
    }
    raw_body = json.dumps(request_body).encode("utf-8")
    handler.headers = {"Content-Length": str(len(raw_body))}
    handler.rfile = io.BytesIO(raw_body)
    handler.path = "/api/epsilon/generate"
    handler._send_json = MagicMock()

    with patch("serve_app.generate_epsilon_summary", side_effect=Exception("Anthropic API timeout")):
        serve_app.CustomHTTPHandler.handle_epsilon_generate(handler)

    assert handler._send_json.called
    status, payload = handler._send_json.call_args[0]
    assert status == 502
    assert payload["success"] is False
    assert "Anthropic API timeout" in payload["error"]


def test_do_post_routing_epsilon_endpoints():
    handler = MagicMock()
    handler.path = "/api/epsilon/generate"
    handler.handle_epsilon_generate = MagicMock()

    serve_app.CustomHTTPHandler.do_POST(handler)
    assert handler.handle_epsilon_generate.called

    handler_resumen = MagicMock()
    handler_resumen.path = "/api/epsilon/resumen?mock=true"
    handler_resumen.handle_epsilon_generate = MagicMock()

    serve_app.CustomHTTPHandler.do_POST(handler_resumen)
    assert handler_resumen.handle_epsilon_generate.called


# =========================================================================
# Tests para GET /api/epsilon/resumenIA/{codigo} y contingencia local
# =========================================================================

def test_proxy_to_epsilon_ia_uses_cached_in_memory():
    handler = MagicMock()
    handler.path = "/api/epsilon/resumenIA/INC000004174655"
    handler.headers = {}
    handler.wfile = io.BytesIO()

    # Pre-cargar en EPSILON_CACHE
    cached_content = json.dumps({"problema": "Cached summary"}).encode("utf-8")
    import time
    serve_app.EPSILON_CACHE["INC000004174655"] = (time.time(), cached_content, 200)

    serve_app.CustomHTTPHandler.proxy_to_epsilon_ia(handler, "INC000004174655")

    assert handler.send_response.called
    assert handler.send_response.call_args[0][0] == 200
    written = handler.wfile.getvalue().decode("utf-8")
    assert "Cached summary" in written


def test_proxy_to_epsilon_ia_fallback_to_local_dumps_when_soptmc_fails(tmp_path):
    output_dir = tmp_path / "data" / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    massive_dump = output_dir / "2026-10-30-massive.json"
    massive_dump.write_text(json.dumps([
        {
            "ID de incidencia": "INC000004174655",
            "Descripción": "Fallo crítico en Facturación",
            "Estatus": "Asignado",
            "Prioridad": "Crítica"
        }
    ]), encoding="utf-8")

    handler = MagicMock()
    handler.path = "/api/epsilon/resumenIA/INC000004174655?mock=true"
    handler.headers = {}
    handler.wfile = io.BytesIO()

    with patch("serve_app.PROJECT_ROOT", tmp_path), \
         patch("urllib.request.urlopen", side_effect=Exception("SOPTMC network unreachable")):
        serve_app.CustomHTTPHandler.proxy_to_epsilon_ia(handler, "INC000004174655")

    assert handler.send_response.called
    assert handler.send_response.call_args[0][0] == 200
    written = handler.wfile.getvalue().decode("utf-8")
    data = json.loads(written)
    assert data["meta"]["source"] == "local_dump_fallback"
    assert "2026-10-30-massive.json" in data["meta"]["dump_file"]
    assert "is_stale_warning" in data["meta"]


def test_proxy_to_epsilon_ia_not_found_anywhere_returns_502(tmp_path):
    output_dir = tmp_path / "data" / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    handler = MagicMock()
    handler.path = "/api/epsilon/resumenIA/INC999999999999"
    handler.headers = {}
    handler.wfile = io.BytesIO()

    with patch("serve_app.PROJECT_ROOT", tmp_path), \
         patch("urllib.request.urlopen", side_effect=Exception("SOPTMC unreachable")):
        serve_app.CustomHTTPHandler.proxy_to_epsilon_ia(handler, "INC999999999999")

    assert handler.send_response.called
    assert handler.send_response.call_args[0][0] == 502
    written = handler.wfile.getvalue().decode("utf-8")
    assert "no disponible en SOPTMC corporativo ni en los volcados locales" in written


def test_cache_invalidation_on_upload():
    """Verifica que EPSILON_CACHE se vacía tras una carga exitosa en handle_upload."""
    serve_app.EPSILON_CACHE["INC000004174655"] = (123456789.0, b'{"test": 1}', 200)
    assert len(serve_app.EPSILON_CACHE) == 1

    handler = MagicMock()
    handler.headers = {"Content-Type": "multipart/form-data; boundary=---boundary", "Content-Length": "100"}
    handler._send_json = MagicMock()

    # Simulamos el flujo de handle_upload parcheando run_upload para retornar success
    fake_multipart_body = (
        b"-----boundary\r\n"
        b'Content-Disposition: form-data; name="file"; filename="test.csv"\r\n\r\n'
        b"col1,col2\r\n"
        b"-----boundary--\r\n"
    )
    handler.headers["Content-Length"] = str(len(fake_multipart_body))
    handler.rfile = io.BytesIO(fake_multipart_body)

    with patch("upload_csv.run_upload", return_value={"success": True, "details": "ok"}):
        serve_app.CustomHTTPHandler.handle_upload(handler)

    assert handler._send_json.called
    status, res = handler._send_json.call_args[0]
    assert status == 200
    # La caché en memoria debió haber sido limpiada
    assert len(serve_app.EPSILON_CACHE) == 0


def test_proxy_to_epsilon_ia_client_connection_aborted_handled_cleanly():
    """Verifica que si el cliente cancela la conexión (WinError 10053), proxy_to_epsilon_ia no lanza excepción ni genera cascada."""
    handler = MagicMock()
    handler.path = "/api/epsilon/resumenIA/INC000004122710"
    handler.headers = {}
    handler.wfile = MagicMock()
    handler.wfile.write.side_effect = ConnectionAbortedError(10053, "Se ha anulado una conexión establecida")

    fake_resp = MagicMock()
    fake_resp.status = 200
    fake_resp.read.return_value = json.dumps({"problema": "OK"}).encode("utf-8")
    fake_resp.__enter__.return_value = fake_resp
    fake_resp.__exit__.return_value = None

    with patch("urllib.request.urlopen", return_value=fake_resp):
        # No debe lanzar excepción
        serve_app.CustomHTTPHandler.proxy_to_epsilon_ia(handler, "INC000004122710")

    # Debe haber intentado escribir una vez y capturado la desconexión sin lanzar error
    assert handler.send_response.called
    assert handler.send_response.call_args[0][0] == 200


def test_send_json_client_connection_aborted_handled_cleanly():
    """Verifica que _send_json y _send_raw_response absorben desconexiones abruptas del cliente."""
    handler = MagicMock()
    handler.wfile = MagicMock()
    handler.wfile.write.side_effect = ConnectionAbortedError(10053, "Aborted")

    # Ejecutar real _send_json llamándolo sobre handler mockeado
    serve_app.CustomHTTPHandler._send_json(handler, 200, {"data": "test"})
    assert handler.send_response.called
    assert handler.send_response.call_args[0][0] == 200

