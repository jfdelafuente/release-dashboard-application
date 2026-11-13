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
    build_executive_notification_card,
    build_warroom_card,
    build_zombie_closure_card,
    build_shift_handover_card,
    generate_default_warroom_url,
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


def test_build_executive_notification_card():
    incident = {
        "id": "INC000004181999",
        "prioridad_sugerida": "P2",
        "prioridad_nominal": "P3",
        "estatus": "En Gestión",
        "grupo_asignado": "SOPORTE B2B",
        "titulo": "Degradación en pasarela de pagos B2B",
        "evaluacion": {
            "proceso_negocio": "Facturación y Cobros",
            "minutos_desde_apertura": 90,
            "impacto_justificacion": "Afectación en cobros recurrentes de empresas.",
        },
        "resumen_ia": {
            "problema": "Timeouts intermitentes en la pasarela de pagos B2B.",
            "impacto": "450 empresas con reintentos pendientes.",
            "solucion_recomendada": "Reinicio preventivo del clúster de workers.",
        },
        "guia_operador": {
            "accion_recomendada": "Ejecutar balanceo de tráfico hacia el nodo pasivo.",
        },
    }
    remedy_url = "https://remedy.corp/view/INC000004181999"
    card = build_executive_notification_card(
        incident,
        remedy_url=remedy_url,
        executive_text="Texto ejecutivo customizado para Dirección."
    )

    assert card["type"] == "message"
    content = card["attachments"][0]["content"]
    assert content["type"] == "AdaptiveCard"
    assert content["version"] == "1.4"

    # Verificar encabezado y texto ejecutivo
    body = content["body"]
    header = body[0]["items"][0]["text"]
    assert "COMUNICACIÓN EJECUTIVA" in header

    # Verificar botón de Remedy
    actions = content.get("actions", [])
    assert len(actions) == 1
    assert actions[0]["url"] == remedy_url

    # Verificar que el texto ejecutivo personalizado se incluye en el cuerpo
    body_str = json.dumps(body, ensure_ascii=False)
    assert "Texto ejecutivo customizado para Dirección." in body_str


def test_build_warroom_card():
    incident = {
        "id": "INC000004199999",
        "prioridad_sugerida": "P1",
        "titulo": "Caída total nodo core Madrid",
        "grupo_asignado": "OPERACIONES RED IP",
        "sistemas": ["ROUTER-MAD-01", "FIREWALL-CORE"],
        "evaluacion": {
            "proceso_negocio": "Core Routing",
        },
        "resumen_ia": {
            "problema": "BGP flapping continuo en nodo perimetral.",
        },
    }
    remedy_url = "https://remedy.corp/view"
    teams_meet_url = "https://teams.microsoft.com/l/meetup-join/test-warroom"
    card = build_warroom_card(incident, remedy_url=remedy_url, teams_meeting_url=teams_meet_url)

    assert card["type"] == "message"
    content = card["attachments"][0]["content"]
    assert content["type"] == "AdaptiveCard"

    # Verificar que hay 2 botones: Unirse a War Room y Remedy
    actions = content.get("actions", [])
    assert len(actions) == 2
    assert actions[0]["title"] == "📞 Unirse a Sesión War Room (Teams)"
    assert actions[0]["url"] == teams_meet_url
    assert actions[1]["title"] == "🔗 Abrir Incidencia en BMC Remedy"
    assert actions[1]["url"] == remedy_url


def test_build_zombie_closure_card():
    incident = {
        "id": "INC000004189003",
        "prioridad_sugerida": "P3",
        "prioridad_nominal": "P2",
        "titulo": "Ticket residual sin impacto",
        "grupo_asignado": "SOPORTE LOCAL",
        "estatus": "Asignado",
        "horas_sin_notas": 360,
        "detalle_zombi": "Sin actividad durante más de 15 días tras resolución técnica.",
    }
    remedy_url = "https://remedy.corp/view"
    card = build_zombie_closure_card(incident, remedy_url=remedy_url)

    assert card["type"] == "message"
    content = card["attachments"][0]["content"]
    assert content["type"] == "AdaptiveCard"

    body_str = json.dumps(content["body"], ensure_ascii=False)
    assert "SOLICITUD DE CIERRE ADMINISTRATIVO" in body_str
    assert "INC000004189003" in body_str


@patch("urllib.request.urlopen")
def test_dispatch_teams_notification_action_routing(mock_urlopen, sample_config, tmp_path):
    mock_resp = MagicMock()
    mock_resp.status = 202
    mock_resp.read.return_value = b""
    mock_urlopen.return_value.__enter__.return_value = mock_resp

    cfg, cfg_file = sample_config
    audit_file = tmp_path / "teams_audit2.json"

    with patch("converters.src.teams_notifier.CONFIG_FILE_PATH", cfg_file), \
         patch("converters.src.teams_notifier.AUDIT_LOG_PATH", audit_file):

        inc = {
            "id": "INC000004199999",
            "prioridad_sugerida": "P1",
            "titulo": "Crisis crítica",
            "grupo_asignado": "RED FIBRA",
        }

        # Despacho acción convocatoria_warroom
        res_warroom = dispatch_teams_notification(
            action="convocatoria_warroom",
            incident=inc,
            teams_meeting_url="https://teams.microsoft.com/meet/test"
        )
        assert res_warroom["success"] is True

        # Despacho acción notificacion_direccion
        res_exec = dispatch_teams_notification(
            action="notificacion_direccion",
            incident=inc,
            executive_text="Aviso dirección"
        )
        assert res_exec["success"] is True


def test_build_shift_handover_card():
    card = build_shift_handover_card(
        report_text="Informe de relevo del turno de tarde: sin incidencias graves abiertas.",
        meta_summary="10 incidencias activas · 0 SL1",
        remedy_url="https://test.remedy.corp"
    )
    assert card["type"] == "message"
    att = card["attachments"][0]["content"]
    assert att["type"] == "AdaptiveCard"
    body_str = json.dumps(att["body"], ensure_ascii=False)
    assert "RELEVO / TRASPASO DE GUARDIA ITIL" in body_str
    assert "Informe de relevo del turno de tarde" in body_str
    assert "10 incidencias activas" in body_str


