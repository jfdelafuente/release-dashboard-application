"""
Tests unitarios para converters/src/montmc_client.py.
Verifica la funcionalidad del cliente MonTMC, tratamiento de errores, retries y normalización de esquemas.
"""

import json
from unittest.mock import MagicMock, patch
import pytest

from converters.src.montmc_client import (
    MonTMCClient,
    MonTMCError,
    RemedyNotFoundError,
    _iso_to_dashboard_date,
    _normalize_priority,
    _normalize_status,
    _normalize_urgency,
)


def test_client_initialization_defaults(monkeypatch):
    monkeypatch.delenv("MON_TMC_BASE_URL", raising=False)
    monkeypatch.delenv("MON_TMC_USER", raising=False)

    client = MonTMCClient()
    assert client.base_url == "https://soptmc.si.orange.es/MonTMC"
    assert client.default_user == "jdelat"
    assert client.timeout == 15


def test_client_initialization_custom(monkeypatch):
    monkeypatch.setenv("MON_TMC_BASE_URL", "https://custom.tmc.org/MonTMC/")
    monkeypatch.setenv("MON_TMC_USER", "custom_user")

    client = MonTMCClient(timeout=30)
    assert client.base_url == "https://custom.tmc.org/MonTMC"
    assert client.default_user == "custom_user"
    assert client.timeout == 30


@patch("urllib.request.urlopen")
def test_fetch_masivas_success(mock_urlopen):
    sample_response = {
        "success": True,
        "total": 1,
        "incidencias": [
            {
                "idRemedy": "INC000004179897",
                "prioridadP": "P2",
                "prioridad": "Alta",
                "resumen": "ERROR EN FACTURACION",
                "estadoDesc": "ASIGNADO",
                "fechaCreacion": "2026-11-09T08:15:23",
                "grupoAsignado": "SOPORTE FACTURACION",
                "urgencia": "Media",
            }
        ],
    }
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = json.dumps(sample_response).encode("utf-8")
    mock_urlopen.return_value.__enter__.return_value = mock_resp

    client = MonTMCClient()
    result = client.fetch_masivas(dias=3, usuario="tester")

    assert result["success"] is True
    assert len(result["incidencias"]) == 1
    assert result["incidencias"][0]["idRemedy"] == "INC000004179897"
    assert mock_urlopen.call_count == 1

    # Verificar URL invocada
    req = mock_urlopen.call_args[0][0]
    assert "dias=3" in req.full_url
    assert "usuario=tester" in req.full_url


@patch("time.sleep", return_value=None)
@patch("urllib.request.urlopen")
def test_fetch_masivas_retry_on_network_error(mock_urlopen, mock_sleep):
    mock_resp_obj = MagicMock()
    mock_resp_obj.status = 200
    mock_resp_obj.read.return_value = json.dumps({"success": True, "incidencias": []}).encode("utf-8")

    mock_cm = MagicMock()
    mock_cm.__enter__.return_value = mock_resp_obj

    # Falla la primera vez con OSError, tiene éxito en el reintento
    mock_urlopen.side_effect = [OSError("Conexión abortada"), mock_cm]

    client = MonTMCClient()
    result = client.fetch_masivas(dias=1)

    assert result["success"] is True
    assert mock_urlopen.call_count == 2
    mock_sleep.assert_called_once_with(1.0)


@patch("time.sleep", return_value=None)
@patch("urllib.request.urlopen")
def test_fetch_masivas_persistent_failure_raises_montmc_error(mock_urlopen, mock_sleep):
    mock_urlopen.side_effect = [OSError("Conexión abortada"), OSError("Conexión abortada 2")]

    client = MonTMCClient()
    with pytest.raises(MonTMCError) as exc_info:
        client.fetch_masivas(dias=1)
    assert "Fallo al conectar con MonTMC" in str(exc_info.value)
    assert mock_urlopen.call_count == 2


@patch("urllib.request.urlopen")
def test_fetch_remedy_detail_success(mock_urlopen):
    sample_detail = {
        "codigoResp": 0,
        "descResp": "OK",
        "remedy": {
            "idRemedy": "INC000004179897",
            "detalle": "Texto apertura OTRS",
            "worklog": [
                {
                    "fecha": "2026-11-10 10:00:00",
                    "autor": "Carlos Morales",
                    "texto": "Se investiga timeout en servicio",
                }
            ],
            "paps": [],
        },
    }
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = json.dumps(sample_detail).encode("utf-8")
    mock_urlopen.return_value.__enter__.return_value = mock_resp

    client = MonTMCClient()
    detail = client.fetch_remedy_detail("INC000004179897")

    assert detail["codigoResp"] == 0
    assert detail["remedy"]["idRemedy"] == "INC000004179897"
    assert len(detail["remedy"]["worklog"]) == 1


@patch("urllib.request.urlopen")
def test_fetch_remedy_detail_not_found_raises_remedy_not_found(mock_urlopen):
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = json.dumps({"codigoResp": 1, "descResp": "No existe registro"}).encode("utf-8")
    mock_urlopen.return_value.__enter__.return_value = mock_resp

    client = MonTMCClient()
    with pytest.raises(RemedyNotFoundError) as exc_info:
        client.fetch_remedy_detail("INC999999999999")
    assert "no encontrada en Remedy" in str(exc_info.value)


def test_fetch_remedy_detail_empty_id_raises():
    client = MonTMCClient()
    with pytest.raises(ValueError):
        client.fetch_remedy_detail("")


def test_normalize_mon_tmc_record_all_fields():
    client = MonTMCClient()
    raw = {
        "idRemedy": "INC000004179897",
        "prioridadP": "P1",
        "prioridad": "Crítica",
        "resumen": "CORP - CAIDA SERVICIO FACTURACION",
        "estadoDesc": "EN CURSO",
        "fechaCreacion": "2026-11-09T08:15:23",
        "fechaResolucion": "2026-11-09T10:30:00",
        "grupoAsignado": "SOPORTE FACTURACION N2",
        "grupoResolutor": "CORE SYSTEMS",
        "urgencia": "Alta",
        "peticionarioNombre": "Mesa de Ayuda",
        "fechaUltimaModificacion": "2026-11-09T10:35:00",
        "solucion": "Reinicio de pods de tarificación",
        "producto": "BSCS",
    }

    norm = client.normalize_mon_tmc_record(raw)

    assert norm["ID de incidencia"] == "INC000004179897"
    assert norm["Prioridad"] == "P1"
    assert norm["Descripción"] == "CORP - CAIDA SERVICIO FACTURACION"
    assert norm["Estatus"] == "En Curso"
    assert norm["Fecha de envío"] == "09/11/2026 08:15"
    assert norm["Fecha de última resolución"] == "09/11/2026 10:30"
    assert norm["Grupo asignado"] == "SOPORTE FACTURACION N2"
    assert norm["Grupo Resolutor"] == "CORE SYSTEMS"
    assert norm["Urgencia"] == "Alta"
    assert norm["Impacto"] == "Masiva"
    assert norm["Grupo Remitente"] == "Mesa de Ayuda"
    assert norm["detalleSolucion"] == "Reinicio de pods de tarificación"
    assert norm["producto"] == "BSCS"


def test_normalize_mon_tmc_record_minimal_and_nulls():
    client = MonTMCClient()
    raw = {
        "idRemedy": "INC000004199999",
        "resumen": "Error puntual",
        "estadoDesc": "ASIGNADO",
        "fechaCreacion": None,
        "fechaResolucion": None,
        "grupoAsignado": None,
        "urgencia": None,
    }

    norm = client.normalize_mon_tmc_record(raw)
    assert norm["ID de incidencia"] == "INC000004199999"
    assert norm["Prioridad"] == "P3"
    assert norm["Estatus"] == "Asignado"
    assert norm["Urgencia"] == "Medio"
    assert norm["Impacto"] == "Masiva"
    assert "Fecha de última resolución" not in norm
    assert "Grupo Resolutor" not in norm


def test_helpers_normalization():
    assert _normalize_priority("P1", "Alta") == "P1"
    assert _normalize_priority(None, "Crítica") == "P1"
    assert _normalize_priority(None, "Alta") == "P2"
    assert _normalize_priority(None, "Media") == "P3"
    assert _normalize_priority(None, "Baja") == "P4"

    assert _normalize_status("ASIGNADO") == "Asignado"
    assert _normalize_status("RESUELTO") == "Resuelto"
    assert _normalize_status("PENDIENTE") == "Pendiente"

    assert _normalize_urgency("1-Crítica") == "Crítica"
    assert _normalize_urgency("2-Alta") == "Alta"
    assert _normalize_urgency("Media") == "Medio"

    assert _iso_to_dashboard_date("2026-11-09T08:15:23") == "09/11/2026 08:15"
    assert _iso_to_dashboard_date("2026-11-09 14:30:00") == "09/11/2026 14:30"
    assert _iso_to_dashboard_date(None) is None
