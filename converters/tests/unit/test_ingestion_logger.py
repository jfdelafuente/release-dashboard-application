import json
from pathlib import Path
import sys
from unittest.mock import MagicMock, patch

# Ensure converters/cli/ is in sys.path
cli_path = Path(__file__).resolve().parent.parent.parent / "cli"
if str(cli_path) not in sys.path:
    sys.path.insert(0, str(cli_path))

from converters.cli.ingestion_logger import (
    audit_incident_completeness,
    write_batch_audit,
    get_log_file_path,
    get_summary_file_path,
    log_upload_start,
    log_conversion_result,
)
from converters.cli.evaluate_incident_notifications import evaluate_incidents_batch


def test_audit_incident_completeness_completa():
    item = {
        "id": "INC001",
        "Descripción": "Caída BD Oracle",
        "Estatus": "Asignado",
        "Prioridad": "Crítica",
    }
    epsilon_data = {
        "problema": "Bloqueo de sesiones",
        "impacto": "Corte de servicio",
        "solucion": "Reinicio de instancia",
    }
    agent_msgs = {
        "apertura": {
            "completo": "Mensaje de apertura oficial.",
            "breve": "Apertura oficial.",
            "estado": "publicado",
            "generado_por_agente": True,
        }
    }
    res = audit_incident_completeness(
        item=item,
        epsilon_data=epsilon_data,
        epsilon_reason="Cache local válida (HIT)",
        agent_msgs=agent_msgs,
        evaluation={"prioridad_sugerida": "P1", "es_discrepancia": False},
        is_terminal=False,
    )
    assert res["estado_informacion"] == "COMPLETA"
    assert res["resumen_ia"]["disponible"] is True
    assert res["mensajes_ejecutivos"]["disponible"] is True
    assert "apertura" in res["mensajes_ejecutivos"]["fases_aprobadas"]
    assert res["is_terminal"] is False


def test_audit_incident_completeness_parcial_sin_resumen_ia():
    item = {
        "id": "INC002",
        "Descripción": "Degradación API",
        "Estatus": "En curso",
        "Prioridad": "Media",
    }
    agent_msgs = {
        "seguimiento": {
            "completo": "Mensaje de seguimiento oficial.",
            "breve": "Seguimiento oficial.",
            "estado": "publicado",
            "generado_por_agente": True,
        }
    }
    res = audit_incident_completeness(
        item=item,
        epsilon_data=None,
        epsilon_reason="HTTP 404 (incidencia no indexada en telemetría Epsilon)",
        agent_msgs=agent_msgs,
        evaluation={"prioridad_sugerida": "P2", "es_discrepancia": True},
        is_terminal=False,
    )
    assert res["estado_informacion"] == "PARCIAL"
    assert res["resumen_ia"]["disponible"] is False
    assert "404" in res["resumen_ia"]["causa_falta"]
    assert res["mensajes_ejecutivos"]["disponible"] is True


def test_audit_incident_completeness_incompleta():
    item = {
        "id": "INC003",
        "Descripción": "Avería switch sede",
        "Estatus": "Asignado",
        "Prioridad": "Baja",
    }
    res = audit_incident_completeness(
        item=item,
        epsilon_data=None,
        epsilon_reason="Epsilon no disponible: Connection refused",
        agent_msgs=None,
        evaluation={"prioridad_sugerida": "P3", "es_discrepancia": False},
        is_terminal=False,
    )
    assert res["estado_informacion"] == "INCOMPLETA"
    assert res["resumen_ia"]["disponible"] is False
    assert res["mensajes_ejecutivos"]["disponible"] is False
    assert "Connection refused" in res["resumen_ia"]["causa_falta"]
    assert "incident-reporter" in res["mensajes_ejecutivos"]["causa_falta"]


def test_audit_incident_completeness_terminal_no_aplica():
    item = {
        "id": "INC004",
        "Descripción": "Incidencia resuelta",
        "Estatus": "Cerrado",
        "Prioridad": "Media",
    }
    res = audit_incident_completeness(
        item=item,
        epsilon_data=None,
        epsilon_reason=None,
        agent_msgs=None,
        evaluation=None,
        is_terminal=True,
    )
    assert res["estado_informacion"] == "NO_APLICA"
    assert res["is_terminal"] is True
    assert "terminal" in res["causa_global"].lower()


def test_write_batch_audit_creates_files(tmp_path):
    audit_records = [
        {
            "id": "INC001",
            "titulo": "Ticket Uno",
            "estatus": "Asignado",
            "is_terminal": False,
            "sistemas": "Sistemas Core",
            "prioridad_nominal": "Media",
            "prioridad_sugerida": "P1",
            "es_discrepancia": True,
            "discrepancia_delta": 2,
            "discrepancia_motivo": "Afectación masiva",
            "proceso_critico": "Core CRM",
            "resumen_ia": {"disponible": True, "origen": "Caché", "causa_falta": None},
            "mensajes_ejecutivos": {"disponible": True, "fases_aprobadas": ["apertura"], "causa_falta": None},
            "estado_informacion": "COMPLETA",
            "causa_global": "Información completa",
        },
        {
            "id": "INC002",
            "titulo": "Ticket Dos",
            "estatus": "Asignado",
            "is_terminal": False,
            "sistemas": "Red",
            "prioridad_nominal": "Baja",
            "prioridad_sugerida": "P3",
            "es_discrepancia": False,
            "discrepancia_delta": 0,
            "discrepancia_motivo": "",
            "proceso_critico": "General",
            "resumen_ia": {"disponible": False, "origen": None, "causa_falta": "HTTP 404"},
            "mensajes_ejecutivos": {"disponible": False, "fases_aprobadas": [], "causa_falta": "Sin redacción"},
            "estado_informacion": "INCOMPLETA",
            "causa_global": "Faltan ambos",
        },
    ]

    log_path = get_log_file_path(tmp_path)
    summary_path = get_summary_file_path(tmp_path)

    log_upload_start("test_incidents.csv", 1024, "massive", project_root=tmp_path)
    log_conversion_result("test_incidents.csv", True, 0.123, project_root=tmp_path)

    written_summary = write_batch_audit(
        source_file="test_incidents.csv",
        audit_records=audit_records,
        elapsed_sec=1.5,
        project_root=tmp_path,
    )

    assert written_summary.exists()
    assert log_path.exists()

    log_content = log_path.read_text(encoding="utf-8")
    assert "PROCESO DE INGESTA DE INCIDENCIAS" in log_content
    assert "[CONVERT_OK]" in log_content
    assert "INC001" in log_content
    assert "COMPLETA" in log_content
    assert "INC002" in log_content
    assert "INCOMPLETA" in log_content
    assert "HTTP 404" in log_content

    with open(summary_path, "r", encoding="utf-8") as f:
        summary_json = json.load(f)
    assert summary_json["_metadata"]["kpis"]["total_tickets"] == 2
    assert summary_json["_metadata"]["kpis"]["completas_count"] == 1
    assert summary_json["_metadata"]["kpis"]["incompletas_count"] == 1
    assert summary_json["_metadata"]["kpis"]["discrepancias_count"] == 1


def test_evaluate_incidents_batch_includes_audit_completeness(tmp_path):
    ticket = {
        "ID de incidencia": "INC999",
        "Descripción": "Caída del servicio de facturación masiva",
        "Estatus": "Asignado",
        "Prioridad": "Crítica",
        "Fecha de envío": "01/11/2026 10:00:00",
    }
    catalog = evaluate_incidents_batch([ticket], epsilon_client=None, project_root=tmp_path)
    assert "_metadata" in catalog
    assert "audit_completeness" in catalog["_metadata"]
    audit_stats = catalog["_metadata"]["audit_completeness"]
    assert "completas" in audit_stats
    assert "parciales" in audit_stats
    assert "incompletas" in audit_stats
    assert "terminales_omitidas" in audit_stats
