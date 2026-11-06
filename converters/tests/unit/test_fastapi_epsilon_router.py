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
