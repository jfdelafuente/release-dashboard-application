"""Unit tests for Ingestion Delta Analyzer (ingestion_delta.py)."""

from pathlib import Path
import pytest
from src.csv_to_json.ingestion_delta import (
    compute_ingestion_delta,
    extract_incident_id,
    extract_incident_status,
    find_latest_archived_massive_file,
    is_status_terminal,
    mark_reopened_tickets,
)


def test_is_status_terminal():
    assert is_status_terminal("Resuelto") is True
    assert is_status_terminal("resuelta") is True
    assert is_status_terminal("Cerrado") is True
    assert is_status_terminal("Cancelado") is True
    assert is_status_terminal("Asignado") is False
    assert is_status_terminal("En Curso") is False
    assert is_status_terminal("Pendiente") is False
    assert is_status_terminal(None) is False
    assert is_status_terminal("") is False


def test_extract_incident_id_and_status():
    t1 = {"ID de incidencia": "INC123", "Estatus": "Asignado"}
    assert extract_incident_id(t1) == "INC123"
    assert extract_incident_status(t1) == "Asignado"

    t2 = {"id": "INC456", "status": "Resuelto"}
    assert extract_incident_id(t2) == "INC456"
    assert extract_incident_status(t2) == "Resuelto"


def test_compute_ingestion_delta_detects_new_resolved_and_reopened():
    previous = [
        {"ID de incidencia": "INC001", "Estatus": "Asignado"},
        {"ID de incidencia": "INC002", "Estatus": "Resuelto"},
        {"ID de incidencia": "INC003", "Estatus": "En Curso"},
    ]
    current = [
        {"ID de incidencia": "INC001", "Estatus": "Resuelto"},  # Activo -> Terminal (Resuelto)
        {"ID de incidencia": "INC002", "Estatus": "Asignado"},  # Terminal -> Activo (Reabierto)
        {"ID de incidencia": "INC003", "Estatus": "En Curso"},  # Sin cambio
        {"ID de incidencia": "INC004", "Estatus": "Asignado"},  # Nuevo
    ]

    delta = compute_ingestion_delta(current, previous, previous_file_name="prev_batch.json")

    assert delta["fichero_anterior"] == "prev_batch.json"
    assert delta["total_actual"] == 4
    assert delta["total_anterior"] == 3
    assert delta["conteo_nuevos"] == 1
    assert delta["tickets_nuevos"] == ["INC004"]
    assert delta["conteo_resueltos"] == 1
    assert delta["tickets_resueltos"] == ["INC001"]
    assert delta["conteo_reabiertos"] == 1
    assert delta["tickets_reabiertos"] == ["INC002"]


def test_mark_reopened_tickets_both_delta_and_intrinsic():
    tickets = [
        {"ID de incidencia": "INC001", "Estatus": "Asignado"},
        {"ID de incidencia": "INC002", "Estatus": "Asignado"},
        {
            "ID de incidencia": "INC003",
            "Estatus": "Asignado",
            "Fecha de última resolución": "04/11/2026 10:00",
        },
        {"ID de incidencia": "INC004", "Estatus": "Resuelto", "Fecha de última resolución": "04/11/2026 10:00"},
    ]

    count = mark_reopened_tickets(tickets, reabiertos_ids={"INC001"})

    assert count == 2  # INC001 (by delta) and INC003 (by intrinsic resolution date on active status)
    assert tickets[0].get("es_reapertura") is True
    assert tickets[1].get("es_reapertura") is None or not tickets[1].get("es_reapertura")
    assert tickets[2].get("es_reapertura") is True
    assert tickets[3].get("es_reapertura") is None or not tickets[3].get("es_reapertura")


def test_find_latest_archived_massive_file(tmp_path):
    arch_dir = tmp_path / "archive"
    arch_dir.mkdir()

    f1 = arch_dir / "CS-massive_20261104100000.json"
    f1.write_text("{}", encoding="utf-8")

    f2 = arch_dir / "CS-massive_20261104120000.json"
    f2.write_text("{}", encoding="utf-8")

    latest = find_latest_archived_massive_file(arch_dir)
    assert latest == f2

    # Excluding f2 should yield f1
    second = find_latest_archived_massive_file(arch_dir, exclude_file=f2)
    assert second == f1

