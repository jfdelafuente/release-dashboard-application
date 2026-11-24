"""
Tests unitarios y de integración offline para converters/cli/sync_montmc_postmortem.py.
Verifica upsert incremental no destructivo, inferencia de release, index.json,
auditoría, casos límite y aislamiento estricto respecto a massive/notifications.
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from converters.cli.sync_montmc_postmortem import (
    _infer_release_from_api,
    resolve_active_postmortem_file,
    sync_postmortem_release,
)
from converters.src.montmc_client import MonTMCClient, MonTMCError


def _setup_workspace(tmp_path: Path) -> Path:
    output_dir = tmp_path / "data" / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def test_sync_postmortem_upsert_preserves_history_and_isolates_massive(tmp_path: Path):
    output_dir = _setup_workspace(tmp_path)

    # Massive y notifications existentes que NO deben tocarse ni modificarse
    massive_file = output_dir / "2026-massive.json"
    massive_payload = {"_metadata": {"type": "massive", "record_count": 1}, "data": [{"ID de incidencia": "INC999"}]}
    massive_file.write_text(json.dumps(massive_payload), encoding="utf-8")

    notif_file = output_dir / "high_priority_notifications.json"
    notif_payload = {"alerts": [{"id": "INC999", "priority": "P1"}]}
    notif_file.write_text(json.dumps(notif_payload), encoding="utf-8")

    # Postmortem previo con una incidencia ya resuelta (no vendrá en API) y una abierta (se actualizará)
    pm_file = output_dir / "Simulacro2026R11-postmortem.json"
    pm_initial = {
        "_metadata": {"type": "postmortem", "release_name": "Simulacro2026R11", "record_count": 2},
        "data": [
            {
                "ID de incidencia": "INC000004100001",
                "Descripción": "[Simulacro2026R11] Incidencia histórica cerrada",
                "Estatus": "Cerrado",
                "Fecha de envío": "15/11/2026 09:00",
                "Grupo asignado": "SOP_A",
                "Urgencia": "Medio",
                "Impacto": "TEIDE",
                "Prioridad": "P3",
            },
            {
                "ID de incidencia": "INC000004188718",
                "Descripción": "[Simulacro2026R11] - Genera orden vacía",
                "Estatus": "Asignado",
                "Fecha de envío": "18/11/2026 12:59",
                "Grupo asignado": "SOP_OLD",
                "Urgencia": "Medio",
                "Impacto": "TEIDE",
                "Prioridad": "P3",
            },
        ],
    }
    pm_file.write_text(json.dumps(pm_initial), encoding="utf-8")

    index_file = output_dir / "index.json"
    index_file.write_text(
        json.dumps(
            {
                "massive": {"type": "massive", "count": 1, "files": [{"name": "2026-massive.json", "path": "data/output/2026-massive.json"}]},
                "postmortem": {"type": "postmortem", "count": 1, "files": [{"name": "Simulacro2026R11-postmortem.json", "path": "data/output/Simulacro2026R11-postmortem.json", "release_name": "Simulacro2026R11"}]},
            }
        ),
        encoding="utf-8",
    )

    real_client = MonTMCClient()
    mock_client = MagicMock(spec=MonTMCClient)
    mock_client.default_user = "jdelat"
    mock_client.normalize_mon_tmc_postmortem_record.side_effect = real_client.normalize_mon_tmc_postmortem_record
    mock_client.fetch_release.return_value = {
        "total": 2,
        "success": True,
        "usuario": "jdelat",
        "incidencias": [
            {
                "idRemedy": "INC000004188718",
                "resumen": "[Simulacro2026R11] - Genera orden vacía",
                "estadoDesc": "EN CURSO",
                "prioridad": "Media",
                "prioridadP": "P3",
                "urgencia": "Alta",
                "producto": "TEIDE",
                "grupoAsignado": "SOP_SMC_TEIDE",
                "grupoResolutor": "SOP_TEIDE_N2",
                "fechaCreacion": "2026-11-18T11:59:30.000+00:00",
                "fechaResolucion": None,
            },
            {
                "idRemedy": "INC000004186382",
                "resumen": "[Simulacro2026R11] Error en provision en cambio de domicilio",
                "estadoDesc": "ASIGNADO",
                "prioridad": "Baja",
                "prioridadP": "P4",
                "urgencia": "Medio",
                "producto": "NABOO",
                "grupoAsignado": "SOP_CRMB2B",
                "grupoResolutor": None,
                "fechaCreacion": "2026-11-17T09:26:20.000+00:00",
                "fechaResolucion": None,
            },
        ],
    }

    res = sync_postmortem_release(
        release_name="Simulacro2026R11",
        project_root=tmp_path,
        client=mock_client,
    )

    assert res["success"] is True
    assert res["total_consultadas"] == 2
    assert res["nuevas"] == 1
    assert res["actualizadas"] == 1
    assert res["sin_cambios"] == 0
    assert res["total_dataset"] == 3

    saved = json.loads(pm_file.read_text(encoding="utf-8"))
    ids = {r["ID de incidencia"]: r for r in saved["data"]}
    assert "INC000004100001" in ids  # Histórico conservado
    assert ids["INC000004100001"]["Estatus"] == "Cerrado"
    assert ids["INC000004188718"]["Estatus"] == "En Curso"
    assert ids["INC000004188718"]["Grupo asignado"] == "SOP_SMC_TEIDE"
    assert ids["INC000004188718"]["Grupo Resolutor"] == "SOP_TEIDE_N2"
    assert "INC000004186382" in ids
    assert saved["_metadata"]["release_name"] == "Simulacro2026R11"
    assert saved["_metadata"]["last_sync_source"] == "montmc_api"
    assert "Despliegue" in ids["INC000004186382"]

    # Aislamiento estricto: massive y high_priority_notifications sin cambios
    assert json.loads(massive_file.read_text(encoding="utf-8")) == massive_payload
    assert json.loads(notif_file.read_text(encoding="utf-8")) == notif_payload

    # index.json conserva massive y mantiene postmortem actualizado
    idx = json.loads(index_file.read_text(encoding="utf-8"))
    assert idx["massive"]["count"] == 1
    assert idx["postmortem"]["count"] == 1
    assert idx["postmortem"]["files"][0]["release_name"] == "Simulacro2026R11"

    # Auditoría escrita en data/logs/ingestion_audit.log
    audit_log = tmp_path / "data" / "logs" / "ingestion_audit.log"
    assert audit_log.exists()
    log_text = audit_log.read_text(encoding="utf-8")
    assert "Tipo: postmortem" in log_text
    assert "[MON_TMC_RELEASE_SYNC]" in log_text
    assert "Simulacro2026R11" in log_text


def test_sync_postmortem_empty_response_preserves_local_data(tmp_path: Path):
    output_dir = _setup_workspace(tmp_path)
    pm_file = output_dir / "2026R11-postmortem.json"
    pm_initial = {
        "_metadata": {"type": "postmortem", "release_name": "2026R11", "record_count": 1},
        "data": [{"ID de incidencia": "INC1", "Estatus": "Cerrado"}],
    }
    pm_file.write_text(json.dumps(pm_initial), encoding="utf-8")

    mock_client = MagicMock(spec=MonTMCClient)
    mock_client.default_user = "jdelat"
    mock_client.fetch_release.return_value = {"total": 0, "success": True, "incidencias": []}

    res = sync_postmortem_release(release_name="2026R11", project_root=tmp_path, client=mock_client)
    assert res["success"] is True
    assert res["nuevas"] == 0
    assert res["actualizadas"] == 0
    assert res["total_dataset"] == 1
    assert json.loads(pm_file.read_text(encoding="utf-8")) == pm_initial


def test_sync_postmortem_api_error_does_not_overwrite_local_data(tmp_path: Path):
    output_dir = _setup_workspace(tmp_path)
    pm_file = output_dir / "2026R11-postmortem.json"
    pm_initial = {
        "_metadata": {"type": "postmortem", "release_name": "2026R11", "record_count": 1},
        "data": [{"ID de incidencia": "INC1", "Estatus": "Asignado"}],
    }
    pm_file.write_text(json.dumps(pm_initial), encoding="utf-8")

    mock_client = MagicMock(spec=MonTMCClient)
    mock_client.default_user = "jdelat"
    mock_client.fetch_release.side_effect = MonTMCError("502 Bad Gateway")

    res = sync_postmortem_release(release_name="2026R11", project_root=tmp_path, client=mock_client)
    assert res["success"] is False
    assert "502 Bad Gateway" in res["error"]
    assert json.loads(pm_file.read_text(encoding="utf-8")) == pm_initial


def test_resolve_active_postmortem_file_infers_or_creates_target(tmp_path: Path):
    _setup_workspace(tmp_path)
    path, rel = resolve_active_postmortem_file(tmp_path, "2026R11")
    assert path == tmp_path / "data" / "output" / "2026R11-postmortem.json"
    assert rel == "2026R11"


def test_sync_postmortem_filters_by_release_tag_in_descripcion(tmp_path: Path):
    output_dir = _setup_workspace(tmp_path)
    real_client = MonTMCClient()
    mock_client = MagicMock(spec=MonTMCClient)
    mock_client.default_user = "jdelat"
    mock_client.normalize_mon_tmc_postmortem_record.side_effect = real_client.normalize_mon_tmc_postmortem_record
    mock_client.fetch_release.return_value = {
        "total": 2,
        "success": True,
        "incidencias": [
            {
                "idRemedy": "INC_OTHER",
                "resumen": "[Simulacro2026R11] Incidencia de otra release",
                "estadoDesc": "ASIGNADO",
                "prioridadP": "P3",
                "urgencia": "Medio",
                "producto": "TEIDE",
                "grupoAsignado": "SOP_A",
                "fechaCreacion": "2026-11-18T11:00:00.000+00:00",
            },
            {
                "idRemedy": "INC_MATCH",
                "resumen": "[2026R11] Incidencia real de la release 2026R11",
                "estadoDesc": "ASIGNADO",
                "prioridadP": "P2",
                "urgencia": "Alta",
                "producto": "NABOO",
                "grupoAsignado": "SOP_B",
                "fechaCreacion": "2026-11-18T12:00:00.000+00:00",
            },
        ],
    }

    res = sync_postmortem_release(release_name="2026R11", project_root=tmp_path, client=mock_client)
    assert res["success"] is True
    assert res["total_consultadas"] == 1
    assert res["nuevas"] == 1

    saved = json.loads((output_dir / "2026R11-postmortem.json").read_text(encoding="utf-8"))
    ids = [r["ID de incidencia"] for r in saved["data"]]
    assert ids == ["INC_MATCH"]


def test_sync_postmortem_reconciles_missing_non_closed_tickets(tmp_path):
    output_dir = tmp_path / "data" / "output"
    output_dir.mkdir(parents=True)
    target_file = output_dir / "2026R9-postmortem.json"
    target_file.write_text(
        json.dumps(
            {
                "_metadata": {"type": "postmortem", "release_name": "2026R9"},
                "data": [
                    {
                        "ID de incidencia": "INC_MISSING_OPEN",
                        "Descripción": "[2026R9] Ticket antiguo",
                        "Estatus": "Asignado",
                        "Fecha de envío": "09/10/2026 14:03",
                        "Grupo asignado": "DES_CRM4T",
                    },
                    {
                        "ID de incidencia": "INC_ALREADY_CLOSED",
                        "Descripción": "[2026R9] Ya cerrado",
                        "Estatus": "Cerrado",
                        "Fecha de envío": "08/10/2026 10:00",
                        "Grupo asignado": "DES_CRM4T",
                    },
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    mock_client = MonTMCClient(default_user="jdelat")
    mock_client.fetch_release = MagicMock(
        return_value={
            "incidencias": [
                {
                    "idRemedy": "INC_ACTIVE",
                    "resumen": "[2026R9] Ticket activo",
                    "estadoDesc": "EN CURSO",
                    "prioridadP": "P3",
                    "urgencia": "Medio",
                    "grupoAsignado": "SOP_A",
                    "fechaCreacion": "2026-11-18T10:00:00.000+00:00",
                }
            ]
        }
    )
    mock_client.fetch_remedy_detail = MagicMock(
        return_value={
            "codigoResp": 0,
            "remedy": {
                "idRemedy": "INC_MISSING_OPEN",
                "resumen": "[2026R9] Ticket antiguo",
                "estadoDesc": "CERRADO",
                "prioridadP": "P3",
                "urgencia": "Medio",
                "grupoAsignado": "DES_CRM4T",
                "fechaCreacion": "2026-10-09T14:03:00.000+00:00",
                "fechaResolucion": "2026-10-15T12:00:00.000+00:00",
            },
        }
    )

    res = sync_postmortem_release(release_name="2026R9", project_root=tmp_path, client=mock_client)
    assert res["success"] is True
    assert res["nuevas"] == 1
    assert res["actualizadas"] == 1
    assert res["new_ids"] == ["INC_ACTIVE"]
    assert res["updated_ids"] == ["INC_MISSING_OPEN"]
    assert res["status_changed_ids"] == ["INC_MISSING_OPEN"]
    mock_client.fetch_remedy_detail.assert_called_once_with("INC_MISSING_OPEN")

    saved = json.loads(target_file.read_text(encoding="utf-8"))
    assert saved["_metadata"]["last_sync_changes"]["new_ids"] == ["INC_ACTIVE"]
    assert saved["_metadata"]["last_sync_changes"]["status_changed_ids"] == ["INC_MISSING_OPEN"]
    by_id = {r["ID de incidencia"]: r for r in saved["data"]}
    assert by_id["INC_MISSING_OPEN"]["Estatus"] == "Cerrado"
    assert by_id["INC_ALREADY_CLOSED"]["Estatus"] == "Cerrado"


def test_infer_release_from_api_ignores_simulacro_and_drill():
    incidencias = [
        {"resumen": "[Simulacro2026R11] Conversión a Convergente..."},
        {"resumen": "[DRILL2026R11] Prueba..."},
        {"resumen": "[2026R11] Incidencia real..."},
    ]
    assert _infer_release_from_api(incidencias) == "2026R11"

    only_simulacro = [
        {"resumen": "[Simulacro2026R11] Conversión a Convergente..."},
        {"resumen": "[Mock2026R11] Prueba..."},
    ]
    assert _infer_release_from_api(only_simulacro) is None


def test_sync_postmortem_prunes_untagged_or_dissociated_tickets(tmp_path: Path):
    """
    Verifica que si una incidencia previamente guardada pierde el tag de la release
    en Remedy (p. ej. corregida a [QuotaApigee] sin [2026R11]), se desvincula y purga
    del dataset postmortem de esa release.
    """
    output_dir = _setup_workspace(tmp_path)
    target_file = output_dir / "2026R11-postmortem.json"
    initial_data = {
        "_metadata": {"type": "postmortem", "release_name": "2026R11", "record_count": 2},
        "data": [
            {
                "ID de incidencia": "INC_VALID",
                "Descripción": "[2026R11] Ticket válido",
                "Estatus": "Asignado",
                "Fecha de envío": "22/11/2026 01:00",
                "Grupo asignado": "SOP_A",
                "Prioridad": "P3",
            },
            {
                "ID de incidencia": "INC_UNTAGGED",
                "Descripción": "[QuotaApigee] Alarma externa",
                "Estatus": "Asignado",
                "Fecha de envío": "22/11/2026 01:20",
                "Grupo asignado": "SOP_TMC",
                "Prioridad": "P2",
            },
        ],
    }
    target_file.write_text(json.dumps(initial_data), encoding="utf-8")

    real_client = MonTMCClient()
    mock_client = MagicMock(spec=MonTMCClient)
    mock_client.default_user = "jdelat"
    mock_client.normalize_mon_tmc_postmortem_record.side_effect = real_client.normalize_mon_tmc_postmortem_record
    mock_client.fetch_release.return_value = {
        "success": True,
        "incidencias": [
            {
                "idRemedy": "INC_VALID",
                "resumen": "[2026R11] Ticket válido",
                "estadoDesc": "ASIGNADO",
                "prioridadP": "P3",
                "urgencia": "Medio",
                "grupoAsignado": "SOP_A",
                "fechaCreacion": "2026-11-22T01:00:00.000+00:00",
            }
        ],
    }
    mock_client.fetch_remedy_detail.return_value = {
        "codigoResp": 0,
        "remedy": {
            "idRemedy": "INC_UNTAGGED",
            "resumen": "[QuotaApigee] Alarma externa sin tag",
            "estadoDesc": "ASIGNADO",
            "prioridadP": "P2",
            "urgencia": "Medio",
            "grupoAsignado": "SOP_TMC",
            "fechaCreacion": "2026-11-22T01:20:00.000+00:00",
        },
    }

    res = sync_postmortem_release(release_name="2026R11", project_root=tmp_path, client=mock_client)
    assert res["success"] is True
    assert res["total_dataset"] == 1

    saved = json.loads(target_file.read_text(encoding="utf-8"))
    ids = [r["ID de incidencia"] for r in saved["data"]]
    assert "INC_VALID" in ids
    assert "INC_UNTAGGED" not in ids


def test_sync_postmortem_preserves_grupo_remitente_if_not_empty(tmp_path: Path):
    output_dir = _setup_workspace(tmp_path)
    pm_file = output_dir / "2026R11-postmortem.json"
    pm_initial = {
        "_metadata": {"type": "postmortem", "release_name": "2026R11", "record_count": 2},
        "data": [
            {
                "ID de incidencia": "INC_WITH_REMITENTE",
                "Descripción": "[2026R11] Ticket con remitente existente",
                "Estatus": "Asignado",
                "Fecha de envío": "22/11/2026 01:00",
                "Grupo asignado": "SOP_OLD",
                "Grupo Remitente": "SLN Arvato Salamanca",
                "Urgencia": "Medio",
                "Impacto": "TEIDE",
                "Prioridad": "P3",
            },
            {
                "ID de incidencia": "INC_EMPTY_REMITENTE",
                "Descripción": "[2026R11] Ticket sin remitente inicial",
                "Estatus": "Asignado",
                "Fecha de envío": "22/11/2026 01:05",
                "Grupo asignado": "SOP_OLD",
                "Grupo Remitente": "",
                "Urgencia": "Medio",
                "Impacto": "TEIDE",
                "Prioridad": "P3",
            },
        ],
    }
    pm_file.write_text(json.dumps(pm_initial), encoding="utf-8")

    real_client = MonTMCClient()
    mock_client = MagicMock(spec=MonTMCClient)
    mock_client.default_user = "jdelat"
    mock_client.normalize_mon_tmc_postmortem_record.side_effect = real_client.normalize_mon_tmc_postmortem_record
    mock_client.fetch_release.return_value = {
        "success": True,
        "incidencias": [
            {
                "idRemedy": "INC_WITH_REMITENTE",
                "resumen": "[2026R11] Ticket con remitente existente modificado",
                "estadoDesc": "EN CURSO",
                "prioridadP": "P3",
                "urgencia": "Media",
                "grupoAsignado": "SOP_NEW",
                "peticionario": "OTRO_REMITENTE_EPSILON",
                "fechaCreacion": "2026-11-22T01:00:00.000+00:00",
            },
            {
                "idRemedy": "INC_EMPTY_REMITENTE",
                "resumen": "[2026R11] Ticket sin remitente inicial ahora con datos",
                "estadoDesc": "EN CURSO",
                "prioridadP": "P3",
                "urgencia": "Media",
                "grupoAsignado": "SOP_NEW",
                "peticionario": "NUEVO_REMITENTE_EPSILON",
                "fechaCreacion": "2026-11-22T01:05:00.000+00:00",
            },
        ],
    }

    res = sync_postmortem_release(release_name="2026R11", project_root=tmp_path, client=mock_client)
    assert res["success"] is True

    saved = json.loads(pm_file.read_text(encoding="utf-8"))
    records_by_id = {r["ID de incidencia"]: r for r in saved["data"]}

    # El registro que ya tenía Grupo Remitente debe conservar el valor previo
    assert records_by_id["INC_WITH_REMITENTE"]["Grupo Remitente"] == "SLN Arvato Salamanca"
    assert records_by_id["INC_WITH_REMITENTE"]["Grupo asignado"] == "SOP_NEW"

    # El registro que tenía Grupo Remitente vacío sí debe actualizarse con el valor de Epsilon
    assert records_by_id["INC_EMPTY_REMITENTE"]["Grupo Remitente"] == "NUEVO_REMITENTE_EPSILON"



