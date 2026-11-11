"""
Tests unitarios para converters/cli/sync_montmc_incidents.py.
Verifica el algoritmo de upsert incremental, conservación del histórico semestral,
manejo de fallos y recálculo de KPIs.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from converters.cli.sync_montmc_incidents import sync_remedy_incidents, resolve_active_massive_file
from converters.src.montmc_client import MonTMCClient, MonTMCError


@pytest.fixture
def mock_dataset(tmp_path):
    """Crea un dataset inicial simulando histórico semestral con 2 tickets."""
    data_dir = tmp_path / "data" / "output"
    data_dir.mkdir(parents=True, exist_ok=True)
    file_path = data_dir / "CS-Informe-test-massive.json"

    initial_content = {
        "_metadata": {
            "type": "massive",
            "version": "1.0",
            "record_count": 2,
            "kpis": {"total": 2, "pending": 1},
        },
        "data": [
            {
                "ID de incidencia": "INC000000000001",
                "Prioridad": "P1",
                "Descripción": "Ticket antiguo en curso",
                "Estatus": "Asignado",
                "Fecha de envío": "01/10/2026 10:00",
                "Grupo asignado": "N1 SOPORTE",
                "Urgencia": "Alta",
                "Impacto": "Masiva",
            },
            {
                "ID de incidencia": "INC000000000002",
                "Prioridad": "P3",
                "Descripción": "Ticket cerrado hace 2 meses",
                "Estatus": "Cerrado",
                "Fecha de envío": "15/08/2026 14:00",
                "Grupo asignado": "N2 BILLING",
                "Urgencia": "Baja",
                "Impacto": "Masiva",
            },
        ],
    }
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(initial_content, f)

    return file_path


def test_sync_inserts_new_incidents_and_preserves_history(mock_dataset, tmp_path):
    # Simular respuesta API con 1 ticket nuevo (INC3)
    mock_client = MagicMock(spec=MonTMCClient)
    mock_client.default_user = "testuser"
    mock_client.fetch_masivas.return_value = {
        "success": True,
        "incidencias": [
            {
                "idRemedy": "INC000000000003",
                "prioridadP": "P2",
                "resumen": "Nueva incidencia de hoy",
                "estadoDesc": "ASIGNADO",
                "fechaCreacion": "2026-11-11T09:00:00",
                "grupoAsignado": "SOPORTE FACTURACION",
                "urgencia": "Media",
            }
        ],
    }
    mock_client.normalize_mon_tmc_record.return_value = {
        "ID de incidencia": "INC000000000003",
        "Prioridad": "P2",
        "Descripción": "Nueva incidencia de hoy",
        "Estatus": "Asignado",
        "Fecha de envío": "11/11/2026 09:00",
        "Grupo asignado": "SOPORTE FACTURACION",
        "Urgencia": "Medio",
        "Impacto": "Masiva",
    }

    res = sync_remedy_incidents(
        dias=3,
        output_path=mock_dataset,
        skip_notifications=True,
        project_root=tmp_path,
        client=mock_client,
    )

    assert res["success"] is True
    assert res["nuevas"] == 1
    assert res["actualizadas"] == 0
    assert res["total_dataset"] == 3

    # Verificar contenido en disco
    with open(mock_dataset, "r", encoding="utf-8") as f:
        updated = json.load(f)

    # El histórico se conserva (total 3) y el ticket antiguo INC2 sigue estando presente
    ids = [r["ID de incidencia"] for r in updated["data"]]
    assert "INC000000000003" in ids
    assert "INC000000000001" in ids
    assert "INC000000000002" in ids
    assert updated["_metadata"]["kpis"]["total"] == 3
    # Pendientes: INC3 (Asignado) + INC1 (Asignado) = 2
    assert updated["_metadata"]["kpis"]["pending"] == 2


def test_sync_updates_modified_existing_incident(mock_dataset, tmp_path):
    # Simular que INC1 ahora viene como 'Resuelto'
    mock_client = MagicMock(spec=MonTMCClient)
    mock_client.default_user = "testuser"
    mock_client.fetch_masivas.return_value = {
        "success": True,
        "incidencias": [{"idRemedy": "INC000000000001"}],
    }
    mock_client.normalize_mon_tmc_record.return_value = {
        "ID de incidencia": "INC000000000001",
        "Prioridad": "P1",
        "Descripción": "Ticket antiguo en curso",
        "Estatus": "Resuelto",
        "Fecha de envío": "01/10/2026 10:00",
        "Fecha de última resolución": "11/11/2026 10:15",
        "Grupo asignado": "N1 SOPORTE",
        "Urgencia": "Alta",
        "Impacto": "Masiva",
    }

    res = sync_remedy_incidents(
        dias=1,
        output_path=mock_dataset,
        skip_notifications=True,
        project_root=tmp_path,
        client=mock_client,
    )

    assert res["success"] is True
    assert res["nuevas"] == 0
    assert res["actualizadas"] == 1
    assert res["total_dataset"] == 2

    with open(mock_dataset, "r", encoding="utf-8") as f:
        updated = json.load(f)

    inc1 = next(r for r in updated["data"] if r["ID de incidencia"] == "INC000000000001")
    assert inc1["Estatus"] == "Resuelto"
    assert inc1["Fecha de última resolución"] == "11/11/2026 10:15"
    # Pendientes ahora es 0 (INC1 Resuelto, INC2 Cerrado)
    assert updated["_metadata"]["kpis"]["pending"] == 0


def test_sync_mixed_insert_and_update_never_duplicates_or_overwrites_shifted_indices(mock_dataset, tmp_path):
    """
    Regresión crítica: verifica que al insertar tickets nuevos (que van al inicio)
    y actualizar tickets existentes en la misma llamada, NO se generen IDs duplicados
    ni se sobreescriban registros adyacentes por desplazamiento de índices de lista.
    """
    mock_client = MagicMock(spec=MonTMCClient)
    mock_client.default_user = "testuser"
    mock_client.fetch_masivas.return_value = {
        "success": True,
        "incidencias": [
            {"idRemedy": "INC_BRAND_NEW_1"},
            {"idRemedy": "INC000000000001"},  # Existente en mock_dataset
            {"idRemedy": "INC_BRAND_NEW_2"},
        ],
    }

    def mock_normalize(raw):
        id_val = raw["idRemedy"]
        if id_val == "INC000000000001":
            return {
                "ID de incidencia": "INC000000000001",
                "Prioridad": "P1",
                "Descripción": "Actualizado desde Remedy",
                "Estatus": "Resuelto",
                "Fecha de envío": "01/10/2026 10:00",
                "Grupo asignado": "N1 SOPORTE",
                "Urgencia": "Alta",
                "Impacto": "Masiva",
            }
        return {
            "ID de incidencia": id_val,
            "Prioridad": "P2",
            "Descripción": f"Nuevo ticket {id_val}",
            "Estatus": "Asignado",
            "Fecha de envío": "11/11/2026 11:00",
            "Grupo asignado": "N2",
            "Urgencia": "Media",
            "Impacto": "Masiva",
        }

    mock_client.normalize_mon_tmc_record.side_effect = mock_normalize

    res = sync_remedy_incidents(
        dias=3,
        output_path=mock_dataset,
        skip_notifications=True,
        project_root=tmp_path,
        client=mock_client,
    )

    assert res["success"] is True
    assert res["nuevas"] == 2
    assert res["actualizadas"] == 1
    # Había 2 originales + 2 nuevos = 4 en total
    assert res["total_dataset"] == 4

    with open(mock_dataset, "r", encoding="utf-8") as f:
        updated = json.load(f)

    data = updated["data"]
    ids = [r["ID de incidencia"] for r in data]
    assert len(ids) == 4
    # Comprobar unicidad absoluta: ningún ID duplicado
    assert len(set(ids)) == 4
    assert set(ids) == {"INC_BRAND_NEW_1", "INC_BRAND_NEW_2", "INC000000000001", "INC000004064075" if "INC000004064075" in ids else "INC000000000002"}

    # Comprobar que INC1 tiene la descripción actualizada
    inc1 = next(r for r in data if r["ID de incidencia"] == "INC000000000001")
    assert inc1["Descripción"] == "Actualizado desde Remedy"
    assert inc1["Estatus"] == "Resuelto"

    # Comprobar que el otro ticket original INC2 no fue sobreescrito ni destruido
    inc2 = next(r for r in data if r["ID de incidencia"] == "INC000000000002")
    assert inc2["Descripción"] == "Ticket cerrado hace 2 meses"
    assert inc2["Estatus"] == "Cerrado"


def test_sync_dry_run_does_not_modify_file(mock_dataset, tmp_path):
    mtime_before = mock_dataset.stat().st_mtime

    mock_client = MagicMock(spec=MonTMCClient)
    mock_client.default_user = "testuser"
    mock_client.fetch_masivas.return_value = {
        "success": True,
        "incidencias": [{"idRemedy": "INC999"}],
    }
    mock_client.normalize_mon_tmc_record.return_value = {
        "ID de incidencia": "INC999",
        "Prioridad": "P1",
        "Descripción": "Simulado",
        "Estatus": "Asignado",
        "Fecha de envío": "11/11/2026 10:00",
        "Grupo asignado": "N1",
        "Urgencia": "Alta",
        "Impacto": "Masiva",
    }

    res = sync_remedy_incidents(
        dias=3,
        output_path=mock_dataset,
        dry_run=True,
        skip_notifications=True,
        project_root=tmp_path,
        client=mock_client,
    )

    assert res["success"] is True
    assert res["dry_run"] is True
    assert res["nuevas"] == 1
    assert mock_dataset.stat().st_mtime == mtime_before

    with open(mock_dataset, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert len(data["data"]) == 2  # Sin cambios en disco


def test_sync_empty_response_does_not_corrupt_file(mock_dataset, tmp_path):
    mock_client = MagicMock(spec=MonTMCClient)
    mock_client.default_user = "testuser"
    mock_client.fetch_masivas.return_value = {"success": True, "incidencias": []}

    res = sync_remedy_incidents(
        dias=3,
        output_path=mock_dataset,
        skip_notifications=True,
        project_root=tmp_path,
        client=mock_client,
    )

    assert res["success"] is True
    assert res["total_consultadas"] == 0

    with open(mock_dataset, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert len(data["data"]) == 2


def test_sync_api_failure_returns_error_and_preserves_file(mock_dataset, tmp_path):
    mock_client = MagicMock(spec=MonTMCClient)
    mock_client.default_user = "testuser"
    mock_client.fetch_masivas.side_effect = MonTMCError("502 Bad Gateway")

    res = sync_remedy_incidents(
        dias=3,
        output_path=mock_dataset,
        skip_notifications=True,
        project_root=tmp_path,
        client=mock_client,
    )

    assert res["success"] is False
    assert "Fallo en consulta MonTMC" in res["error"]

    with open(mock_dataset, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert len(data["data"]) == 2
