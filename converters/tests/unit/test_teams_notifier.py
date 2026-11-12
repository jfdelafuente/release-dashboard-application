"""
test_teams_notifier.py

Pruebas unitarias para el servicio converters/src/teams_notifier.py:
- Carga y persistencia de configuración de canales (data/teams_channels_config.json).
- Enrutamiento jerárquico de canales (override por grupo asignado > canal predeterminado de la acción).
- Construcción y validación estructural del Adaptive Card v1.4 de reclamación de Work Log.
- Despacho y auditoría de envíos a Teams (con mocks de red).
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from converters.src.teams_notifier import (
    load_teams_config,
    save_teams_config,
    resolve_channel,
    build_worklog_claim_card,
    send_to_teams,
    record_audit_entry,
    dispatch_teams_notification,
    get_default_config,
)


@pytest.fixture
def sample_config(tmp_path):
    cfg = {
        "_version": "1.0",
        "descripcion": "Test config",
        "remedy_base_url": "https://test.remedy.corp/console",
        "canales": {
            "canal_general": {
                "id": "canal_general",
                "nombre": "Canal General IT",
                "tipo": "power_automate_workflow",
                "webhook_url": "https://powerautomate.test/invoke?sig=valid123",
                "activo": True,
            },
            "canal_fibra": {
                "id": "canal_fibra",
                "nombre": "Soporte Red Fibra",
                "tipo": "power_automate_workflow",
                "webhook_url": "https://powerautomate.test/fibra?sig=fibra456",
                "activo": True,
            },
            "canal_inactivo": {
                "id": "canal_inactivo",
                "nombre": "Canal Inactivo",
                "tipo": "power_automate_workflow",
                "webhook_url": "https://powerautomate.test/inactive",
                "activo": False,
            },
        },
        "rutas_acciones": {
            "reclamacion_worklog": {
                "descripcion": "Reclamacion de Work Log",
                "canal_predeterminado": "canal_general",
                "mapeo_por_grupo": {
                    "RED FIBRA": "canal_fibra",
                },
            },
            "notificacion_direccion": {
                "descripcion": "Direccion",
                "canal_predeterminado": "canal_general",
                "mapeo_por_grupo": {},
            },
        },
    }
    cfg_file = tmp_path / "teams_channels_test.json"
    cfg_file.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    return cfg, cfg_file


def test_load_teams_config_loads_file(sample_config):
    _, cfg_file = sample_config
    loaded = load_teams_config(cfg_file)
    assert loaded["canales"]["canal_general"]["nombre"] == "Canal General IT"
    assert loaded["rutas_acciones"]["reclamacion_worklog"]["canal_predeterminado"] == "canal_general"


def test_load_teams_config_fallback_when_missing(tmp_path):
    missing_file = tmp_path / "non_existent.json"
    loaded = load_teams_config(missing_file)
    assert "canales" in loaded
    assert "rutas_acciones" in loaded


def test_save_teams_config(tmp_path):
    dest = tmp_path / "saved_config.json"
    custom_cfg = {"_version": "2.0", "canales": {}}
    assert save_teams_config(custom_cfg, dest) is True
    assert dest.exists()
    content = json.loads(dest.read_text(encoding="utf-8"))
    assert content["_version"] == "2.0"


def test_resolve_channel_explicit_channel_id(sample_config):
    cfg, _ = sample_config
    ch = resolve_channel(cfg, action="reclamacion_worklog", channel_id="canal_fibra")
    assert ch["id"] == "canal_fibra"
    assert ch["webhook_url"] == "https://powerautomate.test/fibra?sig=fibra456"


def test_resolve_channel_group_override(sample_config):
    cfg, _ = sample_config
    # When group is RED FIBRA, it should resolve to canal_fibra
    ch = resolve_channel(cfg, action="reclamacion_worklog", group="RED FIBRA")
    assert ch["id"] == "canal_fibra"
    assert ch["nombre"] == "Soporte Red Fibra"


def test_resolve_channel_action_default_when_group_not_overridden(sample_config):
    cfg, _ = sample_config
    # Group DES_DJINGO is not in mapeo_por_grupo, so it falls back to canal_predeterminado (canal_general)
    ch = resolve_channel(cfg, action="reclamacion_worklog", group="DES_DJINGO")
    assert ch["id"] == "canal_general"
    assert ch["nombre"] == "Canal General IT"


def test_resolve_channel_returns_none_when_channel_not_found(sample_config):
    cfg, _ = sample_config
    ch = resolve_channel(cfg, channel_id="canal_fantasma")
    assert ch is None


def test_resolve_channel_returns_none_when_channel_is_inactive(sample_config):
    cfg, _ = sample_config
    ch = resolve_channel(cfg, channel_id="canal_inactivo")
    assert ch is None


def test_build_worklog_claim_card():
    inc_data = {
        "incident_id": "INC000004181839",
        "resumen": "Degradación en pasarela de pagos B2B",
        "prioridad": "P1",
        "estado": "Asignado",
        "grupo_asignado": "RED FIBRA",
        "horas_sin_notas": 16.2,
        "limite_horas": 2.0,
        "urgencia": "CRITICO",
        "mensaje_reclamacion": "URGENCIA MÁXIMA: La incidencia P1 acumula 16.2h sin notas técnicas.",
    }
    remedy_url = "https://remedy.corp/view"
    card = build_worklog_claim_card(inc_data, remedy_url=remedy_url)

    assert card["type"] == "message"
    assert len(card["attachments"]) == 1
    content = card["attachments"][0]["content"]
    assert content["type"] == "AdaptiveCard"
    assert content["version"] == "1.4"

    # Validar que contenga el contenedor principal con el ID del ticket
    body = content["body"]
    container = body[0]
    assert container["type"] == "Container"

    # Verificar que el botón de Remedy esté configurado con Action.OpenUrl
    actions = content.get("actions", [])
    assert len(actions) >= 1
    remedy_action = actions[0]
    assert remedy_action["type"] == "Action.OpenUrl"
    assert remedy_action["url"] == remedy_url
    assert "BMC Remedy" in remedy_action["title"]


@patch("urllib.request.urlopen")
def test_send_to_teams_success(mock_urlopen):
    mock_resp = MagicMock()
    mock_resp.status = 202
    mock_resp.read.return_value = b'{"status": "accepted"}'
    mock_urlopen.return_value.__enter__.return_value = mock_resp

    payload = {"type": "message", "attachments": []}
    success, status_code, body = send_to_teams("https://powerautomate.test/invoke?sig=ok", payload)

    assert success is True
    assert status_code == 202


@patch("urllib.request.urlopen")
def test_dispatch_teams_notification_end_to_end(mock_urlopen, sample_config, tmp_path):
    mock_resp = MagicMock()
    mock_resp.status = 202
    mock_resp.read.return_value = b""
    mock_urlopen.return_value.__enter__.return_value = mock_resp

    cfg, cfg_file = sample_config
    audit_file = tmp_path / "teams_audit.json"

    with patch("converters.src.teams_notifier.CONFIG_FILE_PATH", cfg_file), \
         patch("converters.src.teams_notifier.AUDIT_LOG_PATH", audit_file):

        inc_data = {
            "incident_id": "INC000004181839",
            "resumen": "Incidencia de prueba",
            "prioridad": "P1",
            "grupo_asignado": "RED FIBRA",
            "horas_sin_notas": 14.5,
        }

        res = dispatch_teams_notification(
            action="reclamacion_worklog",
            incident=inc_data,
        )

        assert res["success"] is True
        assert res["channel"]["id"] == "canal_fibra"  # Group routing override
        assert audit_file.exists()

        audit_entries = json.loads(audit_file.read_text(encoding="utf-8"))
        assert len(audit_entries) == 1
        assert audit_entries[0]["incident_id"] == "INC000004181839"
        assert audit_entries[0]["channel_id"] == "canal_fibra"
