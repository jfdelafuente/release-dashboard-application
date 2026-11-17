# -*- coding: utf-8 -*-
"""
test_fastapi_epsilon_router.py
------------------------------
Pruebas unitarias para el router FastAPI de Epsilon IA en producción.
"""

import json
from unittest.mock import patch
import pytest
from fastapi import HTTPException

from converters.src.fastapi_epsilon_router import (
    generate_summary,
    get_resumen_ia,
    clear_fastapi_cache,
    FASTAPI_EPSILON_CACHE,
)


@pytest.fixture(autouse=True)
def reset_cache():
    clear_fastapi_cache()
    yield
    clear_fastapi_cache()


def test_fastapi_generate_empty_payload():
    with pytest.raises(HTTPException) as exc_info:
        generate_summary(payload=None)
    assert exc_info.value.status_code == 400


def test_fastapi_generate_insufficient_data():
    with pytest.raises(HTTPException) as exc_info:
        generate_summary(payload={})
    assert exc_info.value.status_code == 400


def test_fastapi_generate_direct_mock():
    payload = {
        "ID de incidencia": "INC000004174655",
        "Descripción": "Error en sincronización Ficha Cliente",
        "Estatus": "Asignado",
        "Prioridad": "Crítica"
    }
    resp = generate_summary(payload=payload, mock=True)
    assert resp.status_code == 200
    data = json.loads(resp.body.decode("utf-8"))
    assert data["success"] is True
    assert "titulo" in data
    assert "problema" in data
    assert data["meta"]["mock"] is True


def test_fastapi_resumen_alias_wrapper_mock():
    payload = {
        "incident_data": {
            "ID de incidencia": "INC000004174655",
            "Descripción": "Error en sincronización Ficha Cliente",
            "Estatus": "Asignado",
            "Prioridad": "Crítica"
        },
        "mock": True
    }
    resp = generate_summary(payload=payload, mock=False)
    assert resp.status_code == 200
    data = json.loads(resp.body.decode("utf-8"))
    assert data["success"] is True
    assert data["meta"]["mock"] is True


def test_fastapi_generate_validation_failure_returns_422():
    with patch("converters.src.fastapi_epsilon_router.generate_epsilon_summary") as mock_gen:
        mock_gen.return_value = (
            False,
            {
                "error": "Error de validación de esquema Epsilon",
                "validation_errors": ["problema: excede 40 palabras"],
                "raw_output": {"problema": "demasiadas palabras " * 30}
            },
            {"provider": "mock"}
        )
        payload = {"ID de incidencia": "INC000004174655", "Descripción": "Test"}
        resp = generate_summary(payload=payload, mock=False)
        assert resp.status_code == 422
        data = json.loads(resp.body.decode("utf-8"))
        assert data["success"] is False
        assert "validation_errors" in data


def test_fastapi_generate_llm_failure_returns_502():
    with patch("converters.src.fastapi_epsilon_router.generate_epsilon_summary") as mock_gen:
        mock_gen.side_effect = RuntimeError("Conexión rechazada por proxy corporativo")
        payload = {"ID de incidencia": "INC000004174655", "Descripción": "Test"}
        resp = generate_summary(payload=payload, mock=False)
        assert resp.status_code == 502
        data = json.loads(resp.body.decode("utf-8"))
        assert data["success"] is False
        assert "Fallo en el servicio LLM" in data["error"]


def test_fastapi_get_resumen_ia_memory_cache():
    FASTAPI_EPSILON_CACHE["INC000009999999"] = (
        9999999999.0,
        {"success": True, "titulo": "En Memoria", "estadoActual": "Asignado"},
        200
    )
    resp = get_resumen_ia("INC000009999999")
    assert resp.status_code == 200
    assert resp.headers.get("X-Cache-Status") == "MEMORY_HIT"
    data = json.loads(resp.body.decode("utf-8"))
    assert data["titulo"] == "En Memoria"


def test_fastapi_get_resumen_ia_fallback_local_dumps():
    incident_mock = {
        "ID de incidencia": "INC000004174999",
        "Descripción": "Fallo en sincronización",
        "Estatus": "Asignado",
        "Prioridad": "Media"
    }
    with patch("converters.src.fastapi_epsilon_router.find_incident_in_local_dumps") as mock_find:
        # mtime = 0 -> > 2 horas -> is_stale_warning = True
        mock_find.return_value = (incident_mock, "2026-10-30-massive.json", 0.0)
        resp = get_resumen_ia("INC000004174999", force=True, mock=True)
        assert resp.status_code == 200
        assert resp.headers.get("X-Cache-Status") == "LOCAL_DUMP_FALLBACK"
        data = json.loads(resp.body.decode("utf-8"))
        assert data["success"] is True
        assert data["meta"]["is_stale_warning"] is True
        assert "horas de antigüedad" in data["meta"]["stale_reason"]


def test_fastapi_get_resumen_ia_not_found_returns_502():
    with patch("converters.src.fastapi_epsilon_router.find_incident_in_local_dumps", return_value=None):
        resp = get_resumen_ia("INC999999999999", force=True, mock=True)
        assert resp.status_code == 502
        data = json.loads(resp.body.decode("utf-8"))
        assert data["success"] is False


def test_fastapi_get_resumen_ia_live_soptmc_hit(tmp_path, monkeypatch):
    monkeypatch.setenv("EPSILON_PROVIDER_MODE", "soptmc")
    mock_payload = {
        "success": True,
        "titulo": "SOPTMC Live",
        "problema": "Corte de fibra",
        "estadoActual": "Asignado",
    }

    class DummyResponse:
        def __init__(self):
            self.status = 200

        def read(self):
            return json.dumps(mock_payload).encode("utf-8")

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

    cache_dir = tmp_path / "epsilon_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    with patch("urllib.request.urlopen", return_value=DummyResponse()), \
         patch("converters.src.fastapi_epsilon_router._get_cache_dir", return_value=cache_dir):
        resp = get_resumen_ia("INC000004183530", force=True, mock=False)
        assert resp.status_code == 200
        assert resp.headers.get("X-Cache-Status") == "LIVE_SOPTMC_HIT"
        data = json.loads(resp.body.decode("utf-8"))
        assert data["titulo"] == "SOPTMC Live"
        assert (cache_dir / "INC000004183530.json").exists()


def test_fastapi_get_resumen_ia_internal_engine_default_and_fingerprint_hit(tmp_path, monkeypatch):
    monkeypatch.setenv("EPSILON_PROVIDER_MODE", "internal")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-internal-key")

    cache_dir = tmp_path / "data" / ".epsilon_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    remedy_payload = {
        "codigoResp": 0,
        "remedy": {
            "idRemedy": "INC000004186294",
            "resumen": "Fallo en sincronización OTRS",
            "estadoDesc": "Asignado",
            "fechaUltimaModificacion": "2026-11-17T08:30:46.000+00:00",
            "worklog": [
                {"idWorklog": "WL1", "fecha": "2026-11-17T08:30:46.000+00:00", "detalle": "Apunte inicial"}
            ],
        },
    }
    valid_llm = {
        "success": True,
        "titulo": "Fallo en sincronización OTRS",
        "estadoActual": "Asignado",
        "problema": "Incidencia de comunicación entre pasarela OTRS y backend.",
        "impacto": "Afecta al envío automático de tickets. Sin método alternativo disponible.",
        "sistemas": ["OTRS", "Remedy"],
        "hitosTecnicos": ["[17/11/2026 09:30:46]: Apunte inicial de diagnóstico en pasarela."],
        "bloqueos": [],
    }

    with patch("converters.src.montmc_client.MonTMCClient.fetch_remedy_detail", return_value=remedy_payload), \
         patch("converters.src.epsilon_service.call_anthropic", return_value=(valid_llm, 210, 0.4)) as mock_llm, \
         patch("converters.src.fastapi_epsilon_router._get_cache_dir", return_value=cache_dir), \
         patch("converters.src.fastapi_epsilon_router._get_candidate_roots", return_value=[tmp_path]):
        # 1ª petición: genera con nuestro motor interno
        resp1 = get_resumen_ia("INC000004186294", force=False, mock=False)
        assert resp1.status_code == 200
        assert resp1.headers.get("X-Cache-Status") == "INTERNAL_LLM_GENERATED"
        assert mock_llm.call_count == 1
        body1 = json.loads(resp1.body.decode("utf-8"))
        assert body1["meta"]["source"] == "internal_epsilon_engine"

        # Limpiar caché en memoria: 2ª petición debe dar FINGERPRINT_HIT sin invocar al LLM
        clear_fastapi_cache()
        resp2 = get_resumen_ia("INC000004186294", force=False, mock=False)
        assert resp2.status_code == 200
        assert resp2.headers.get("X-Cache-Status") == "FINGERPRINT_HIT"
        assert mock_llm.call_count == 1


def test_fastapi_get_resumen_ia_disk_hit(tmp_path):
    cache_dir = tmp_path / "epsilon_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    disk_file = cache_dir / "INC000004183530.json"
    disk_file.write_text(json.dumps({
        "success": True,
        "titulo": "From Disk Cache",
        "problema": "Problema guardado",
    }), encoding="utf-8")

    with patch("converters.src.fastapi_epsilon_router._get_cache_dir", return_value=cache_dir):
        resp = get_resumen_ia("INC000004183530", force=False, mock=True)
        assert resp.status_code == 200
        assert resp.headers.get("X-Cache-Status") == "DISK_HIT"
        data = json.loads(resp.body.decode("utf-8"))
        assert data["titulo"] == "From Disk Cache"


def test_fastapi_get_resumen_ia_fallback_local_dumps_fresh():
    incident_mock = {
        "ID de incidencia": "INC000004174998",
        "Descripción": "Fallo reciente",
        "Estatus": "Asignado",
        "Prioridad": "Alta"
    }
    import time
    with patch("converters.src.fastapi_epsilon_router.find_incident_in_local_dumps") as mock_find:
        mock_find.return_value = (incident_mock, "2026-11-13-massive.json", time.time())
        resp = get_resumen_ia("INC000004174998", force=True, mock=True)
        assert resp.status_code == 200
        assert resp.headers.get("X-Cache-Status") == "LOCAL_DUMP_FALLBACK"
        data = json.loads(resp.body.decode("utf-8"))
        assert data["success"] is True
        assert data["meta"]["is_stale_warning"] is False
