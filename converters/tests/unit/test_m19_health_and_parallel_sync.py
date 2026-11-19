# -*- coding: utf-8 -*-
"""Tests unitarios M19: reconciliación paralela remedyG y endpoint /api/health/release-desk."""

import json
from pathlib import Path
import threading
import time

from converters.cli.sync_montmc_postmortem import sync_postmortem_release
from converters.src.montmc_client import MonTMCClient
from converters.src.storage_utils import build_release_desk_health


class _ParallelReconcileMockClient(MonTMCClient):
    def __init__(self):
        super().__init__(default_user="jdelat")
        self.thread_ids = set()
        self._lock = threading.Lock()

    def fetch_release(self, usuario=None):
        return {
            "incidencias": [
                {
                    "idRemedy": "INC_ACTIVE_01",
                    "resumen": "[2026R11] Activa",
                    "estadoDesc": "EN CURSO",
                    "prioridadP": "P3",
                    "urgencia": "Medio",
                    "grupoAsignado": "SOP_A",
                    "fechaCreacion": "2026-11-18T10:00:00.000+00:00",
                }
            ]
        }

    def fetch_remedy_detail(self, inc_id: str):
        with self._lock:
            self.thread_ids.add(threading.get_ident())
        time.sleep(0.02)
        if inc_id == "INC0000000002":
            raise TimeoutError("Simulated MonTMC timeout")
        return {
            "codigoResp": 0,
            "remedy": {
                "idRemedy": inc_id,
                "estadoDesc": "CERRADO",
                "prioridadP": "P2",
                "urgencia": "Alta",
                "resumen": f"[2026R11] Actualizado {inc_id}",
                "grupoAsignado": "DES_CRM4T",
                "fechaCreacion": "2026-10-09T14:03:00.000+00:00",
            },
        }


def test_sync_postmortem_reconciles_missing_tickets_in_parallel(tmp_path: Path):
    out_dir = tmp_path / "data" / "output"
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / "2026R11-postmortem.json"
    seed = {
        "_metadata": {"release_name": "2026R11", "type": "postmortem"},
        "data": [
            {"ID de incidencia": "INC0000000001", "Descripción": "[2026R11] Uno", "Estatus": "En curso", "Prioridad": "Alta"},
            {"ID de incidencia": "INC0000000002", "Descripción": "[2026R11] Dos", "Estatus": "En curso", "Prioridad": "Alta"},
            {"ID de incidencia": "INC0000000003", "Descripción": "[2026R11] Tres", "Estatus": "Asignado", "Prioridad": "Medio"},
        ],
    }
    target.write_text(json.dumps(seed, ensure_ascii=False), encoding="utf-8")

    client = _ParallelReconcileMockClient()
    res = sync_postmortem_release(
        release_name="2026R11",
        output_path=target,
        project_root=tmp_path,
        client=client,
    )

    assert res["success"] is True
    assert res["actualizadas"] == 2
    assert set(res["updated_ids"]) == {"INC0000000001", "INC0000000003"}
    saved = json.loads(target.read_text(encoding="utf-8"))
    by_id = {row["ID de incidencia"]: row for row in saved["data"]}
    assert by_id["INC0000000001"]["Estatus"] == "Cerrado"
    assert by_id["INC0000000002"]["Estatus"] == "En curso"
    assert by_id["INC0000000003"]["Estatus"] == "Cerrado"


def test_build_release_desk_health_reports_all_sections(tmp_path: Path):
    storage = tmp_path / "data"
    out_dir = storage / "output"
    out_dir.mkdir(parents=True, exist_ok=True)

    (out_dir / "2026R11-postmortem.json").write_text(
        json.dumps(
            {
                "_metadata": {
                    "release_name": "2026R11",
                    "last_sync_changes": {"timestamp": "2026-11-19T09:00:00"},
                },
                "data": [],
            }
        ),
        encoding="utf-8",
    )
    (out_dir / "high_priority_notifications.json").write_text("{}", encoding="utf-8")
    (storage / "projects_catalog.json").write_text(
        json.dumps({"releases": {"2026R11": {}}}),
        encoding="utf-8",
    )

    health = build_release_desk_health(storage, tmp_path)
    assert health["status"] == "ok"
    assert health["storage"]["ok"] is True
    assert health["postmortem"]["available"] is True
    assert health["postmortem"]["release"] == "2026R11"
    assert health["postmortem"]["last_sync"] == "2026-11-19T09:00:00"
    assert health["triage"]["available"] is True
    assert health["projects_catalog"]["available"] is True
    assert health["projects_catalog"]["releases_count"] == 1
    assert "montmc_configured" in health["integrations"]
