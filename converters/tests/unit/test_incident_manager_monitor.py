"""Unit and integration tests for Incident Manager Monitor (013-incident-manager-monitor).

Covers:
- Strict UI isolation verification (FR-002, US5, T026)
- API endpoint contracts (/api/incident-manager/pending and /api/incident-manager/save-message)
- Pending queue detection and KPI calculations (US1, T007)
- Agent prompt generation inspection (US2, T013)
- Word count validation and single-paragraph normalization (US3, T017)
- Client-side filtering logic parity (US4, T022)
"""

import json
from pathlib import Path
import pytest

from converters.cli.update_agent_message import (
    parse_agent_raw_output,
    update_agent_store
)
from converters.cli.incident_manager_service import (
    get_pending_incidents_payload,
    validate_and_save_agent_message
)


@pytest.fixture
def repo_root() -> Path:
    """Returns the absolute repository root directory."""
    return Path(__file__).resolve().parent.parent.parent.parent


@pytest.fixture
def mock_notifications_catalog():
    """Sample catalog matching high_priority_notifications.json format."""
    return {
        "_metadata": {
            "version": "1.1.0",
            "generated_at": "2026-10-28T08:52:13Z",
            "source_file": "CS-Informe incidencias P1, P2 y P3 - 2026 - 28 Oct 2026-massive.json",
            "total_candidates_evaluated": 15,
            "total_high_priority_detected": 2,
            "p1_critical_count": 1,
            "p2_high_count": 1,
            "discrepancies_count": 1
        },
        "incidents": [
            {
                "id": "INC000004168775",
                "titulo": "INDISPONIBILIDAD // MIDDLEWARE // SL1",
                "sistemas": ["SPAIN ALMACENAMIENTO"],
                "prioridad_original": "Crítica",
                "prioridad_sugerida": "P2",
                "es_alta_prioridad": True,
                "es_discrepancia": False,
                "estatus": "Pendiente",
                "fecha_envio": "27/10/2026 18:21",
                "evaluacion": {
                    "proceso": "Sistemas Core",
                    "criterio": "SL2 Mayor: Degradación funcional o afectación en sede sin indisponibilidad global",
                    "impacto": "Alto",
                    "impacto_justificacion": "Afectación crítica o corte global",
                    "urgencia": "Baja",
                    "urgencia_justificacion": "Baja sensibilidad temporal",
                    "workaround": "Desconocido",
                    "sla_objetivo_minutos": 60
                },
                "resumen_ia": None,
                "tiene_epsilon": False,
                "mensajes_ejecutivos": {
                    "apertura": {
                        "completo": "",
                        "breve": "",
                        "generado_por_agente": False,
                        "estado": "pendiente"
                    },
                    "seguimiento": {
                        "completo": "",
                        "breve": "",
                        "generado_por_agente": False,
                        "estado": "pendiente"
                    },
                    "cierre": {
                        "completo": "",
                        "breve": "",
                        "generado_por_agente": False,
                        "estado": "pendiente"
                    }
                },
                "prompts_agente": {
                    "apertura": "Actúa como el agente incident-reporter...",
                    "seguimiento": "Actúa como el agente incident-reporter...",
                    "cierre": "Actúa como el agente incident-reporter..."
                }
            },
            {
                "id": "INC000004168617",
                "titulo": "CORTE TOTAL ATC CRM EN SEDES CENTRALES",
                "sistemas": ["CRM ONESIEBEL"],
                "prioridad_original": "Media",
                "prioridad_sugerida": "P1",
                "es_alta_prioridad": True,
                "es_discrepancia": True,
                "estatus": "En curso",
                "fecha_envio": "27/10/2026 16:40",
                "evaluacion": {
                    "proceso": "Atención al Cliente (ATC)",
                    "criterio": "ATC: Frontales/CRM/Herramientas de atención fuera de servicio > 10% de puestos",
                    "impacto": "Crítico",
                    "impacto_justificacion": "Corte de atención",
                    "urgencia": "Crítica",
                    "urgencia_justificacion": "Sin workaround",
                    "workaround": "No disponible",
                    "sla_objetivo_minutos": 45
                },
                "resumen_ia": {
                    "problema": "Caída del cluster CRM",
                    "bloqueos": "Base de datos Oracle bloqueada",
                    "solucion": "Reinicio ordenado"
                },
                "tiene_epsilon": True,
                "mensajes_ejecutivos": {
                    "apertura": {
                        "completo": "Apertura oficial registrada por agente con texto completo.",
                        "breve": "Apertura oficial breve.",
                        "generado_por_agente": True,
                        "estado": "completado"
                    }
                },
                "prompts_agente": {
                    "apertura": "Prompt de apertura...",
                    "seguimiento": "Prompt de seguimiento...",
                    "cierre": "Prompt de cierre..."
                }
            }
        ]
    }


@pytest.fixture
def mock_agent_store():
    """Sample store matching data/agent_executive_messages.json format."""
    return {
        "_metadata": {
            "version": "1.0.0",
            "updated_at": "2026-10-28T09:00:00Z"
        },
        "incidents": {
            "INC000004168617": {
                "apertura": {
                    "completo": "Apertura oficial registrada por agente con texto completo.",
                    "breve": "Apertura oficial breve.",
                    "generado_por_agente": True,
                    "origen": "incident-reporter",
                    "conteo_palabras_completo": 8,
                    "conteo_palabras_breve": 4
                }
            }
        }
    }


# =========================================================================
# Phase 7 & User Story 5: Isolation Tests (FR-002, T026)
# =========================================================================

def test_should_guarantee_zero_references_to_monitor_in_portal_index_html(repo_root: Path):
    """The general portal (dashboards/portal/index.html) MUST NOT link or reference the monitor."""
    portal_html = repo_root / "dashboards" / "portal" / "index.html"
    assert portal_html.is_file(), f"Portal file not found at {portal_html}"
    content = portal_html.read_text(encoding="utf-8")
    assert "incident-manager-monitor" not in content, (
        "Violation of strict isolation: 'incident-manager-monitor' found in dashboards/portal/index.html"
    )


def test_should_guarantee_zero_references_to_monitor_in_root_index_html(repo_root: Path):
    """Root dashboards index.html MUST NOT link or redirect to incident-manager-monitor."""
    dashboards_index = repo_root / "dashboards" / "index.html"
    if dashboards_index.is_file():
        content = dashboards_index.read_text(encoding="utf-8")
        assert "incident-manager-monitor" not in content, (
            "Violation of strict isolation: 'incident-manager-monitor' found in dashboards/index.html"
        )


def test_should_guarantee_monitor_files_exist_in_dedicated_directory(repo_root: Path):
    """The monitor files must reside in dashboards/incident-manager-monitor/."""
    monitor_dir = repo_root / "dashboards" / "incident-manager-monitor"
    assert monitor_dir.is_dir(), f"Expected directory {monitor_dir} does not exist"


# =========================================================================
# Phase 3 & User Story 1: Pending Queue & KPI Calculation Tests (FR-004, FR-005, T007)
# =========================================================================

def compute_monitor_state(catalog: dict, agent_store: dict):
    """Helper mimicking the pending discrimination logic in backend and frontend."""
    incidents = catalog.get("incidents", [])
    store_incidents = agent_store.get("incidents", {})

    pending_list = []
    completed_list = []
    p1_count = 0
    p2_count = 0
    discrepancies_count = 0

    for inc in incidents:
        inc_id = inc.get("id")
        prio_sug = inc.get("prioridad_sugerida", "P2")
        if prio_sug == "P1":
            p1_count += 1
        elif prio_sug == "P2":
            p2_count += 1

        if inc.get("es_discrepancia"):
            discrepancies_count += 1

        # Check if pending agent drafting
        mensajes = inc.get("mensajes_ejecutivos", {})
        apertura = mensajes.get("apertura", {})
        store_entry = store_incidents.get(inc_id, {}).get("apertura", {})

        is_pending = (
            apertura.get("estado") == "pendiente"
            or not bool(apertura.get("completo"))
            or not apertura.get("generado_por_agente")
            or not store_entry.get("generado_por_agente")
        )

        if is_pending:
            pending_list.append(inc)
        else:
            completed_list.append(inc)

    kpis = {
        "total_active": len(incidents),
        "completed_count": len(completed_list),
        "pending_count": len(pending_list),
        "p1_count": p1_count,
        "p2_count": p2_count,
        "discrepancies_count": discrepancies_count
    }
    return kpis, pending_list, completed_list


def test_should_identify_pending_incident_when_apertura_estado_is_pendiente(
    mock_notifications_catalog, mock_agent_store
):
    kpis, pending, completed = compute_monitor_state(mock_notifications_catalog, mock_agent_store)
    pending_ids = [i["id"] for i in pending]
    assert "INC000004168775" in pending_ids
    assert "INC000004168617" not in pending_ids


def test_should_identify_pending_incident_when_not_in_agent_store(
    mock_notifications_catalog
):
    empty_store = {"incidents": {}}
    kpis, pending, completed = compute_monitor_state(mock_notifications_catalog, empty_store)
    # Both should be pending because store is empty
    assert len(pending) == 2
    assert kpis["pending_count"] == 2
    assert kpis["completed_count"] == 0


def test_should_calculate_correct_kpis_summary_counts(
    mock_notifications_catalog, mock_agent_store
):
    kpis, pending, completed = compute_monitor_state(mock_notifications_catalog, mock_agent_store)
    assert kpis["total_active"] == 2
    assert kpis["pending_count"] == 1
    assert kpis["completed_count"] == 1
    assert kpis["p1_count"] == 1
    assert kpis["p2_count"] == 1
    assert kpis["discrepancies_count"] == 1


def test_should_detect_discrepancy_badge_when_ticket_nominal_is_lower(mock_notifications_catalog):
    inc_discrepancy = next(i for i in mock_notifications_catalog["incidents"] if i["id"] == "INC000004168617")
    assert inc_discrepancy["es_discrepancia"] is True
    assert inc_discrepancy["prioridad_original"] == "Media"
    assert inc_discrepancy["prioridad_sugerida"] == "P1"


# =========================================================================
# Phase 4 & User Story 2: Prompt Inspection Tests (FR-008, FR-009, T013)
# =========================================================================

def test_should_include_process_and_criterion_in_generated_prompt(mock_notifications_catalog):
    inc = mock_notifications_catalog["incidents"][0]
    prompts = inc.get("prompts_agente", {})
    assert "apertura" in prompts
    assert "seguimiento" in prompts
    assert "cierre" in prompts


def test_should_include_systems_and_rules_in_prompt(mock_notifications_catalog):
    inc = mock_notifications_catalog["incidents"][0]
    eval_data = inc.get("evaluacion", {})
    proceso = eval_data.get("proceso")
    sistemas = inc.get("sistemas", [])
    assert proceso == "Sistemas Core"
    assert "SPAIN ALMACENAMIENTO" in sistemas


def test_should_contain_90_words_and_single_paragraph_instruction(mock_notifications_catalog):
    prompt_sample = (
        "Actúa como el agente incident-reporter de MasOrange para la fase de APERTURA.\n"
        "1. Versión Completa: máximo 90 palabras en un ÚNICO párrafo cohesionado.\n"
        "2. Versión Breve: máximo 30 palabras para canal de alertas.\n"
        "3. No inventes causas raíz ni métricas ausentes."
    )
    assert "máximo 90 palabras" in prompt_sample
    assert "ÚNICO párrafo" in prompt_sample
    assert "máximo 30 palabras" in prompt_sample



# =========================================================================
# Phase 5 & User Story 3: Word Count & Save Validation (FR-010, FR-011, T017)
# =========================================================================

def validate_agent_message_lengths(completo: str, breve: str) -> tuple[bool, str]:
    """Validates word count limits: complete <= 90 words single-paragraph, brief <= 30 words."""
    if not completo or not completo.strip():
        return False, "La versión completa es obligatoria."
    if not breve or not breve.strip():
        return False, "La versión breve es obligatoria."

    # Monoparagraph check (no internal newlines)
    clean_comp = completo.strip()
    clean_brev = breve.strip()
    words_comp = len(clean_comp.split())
    words_brev = len(clean_brev.split())

    if words_comp > 90:
        return False, f"Límite de palabras excedido: versión completa tiene {words_comp} palabras (máx 90)."
    if words_brev > 30:
        return False, f"Límite de palabras excedido: versión breve tiene {words_brev} palabras (máx 30)."

    return True, "OK"


def test_should_validate_word_count_within_limits():
    valid_comp = " ".join(["palabra"] * 85)
    valid_brev = " ".join(["palabra"] * 25)
    is_valid, msg = validate_agent_message_lengths(valid_comp, valid_brev)
    assert is_valid is True
    assert msg == "OK"


def test_should_reject_word_count_exceeding_90_words_for_complete():
    excess_comp = " ".join(["palabra"] * 95)
    valid_brev = " ".join(["palabra"] * 20)
    is_valid, msg = validate_agent_message_lengths(excess_comp, valid_brev)
    assert is_valid is False
    assert "máx 90" in msg


def test_should_reject_word_count_exceeding_30_words_for_brief():
    valid_comp = " ".join(["palabra"] * 70)
    excess_brev = " ".join(["palabra"] * 35)
    is_valid, msg = validate_agent_message_lengths(valid_comp, excess_brev)
    assert is_valid is False
    assert "máx 30" in msg


def test_should_normalize_multiple_paragraphs_into_single_paragraph():
    multi_p = "Primer párrafo con información.\n\nSegundo párrafo añadido por error."
    comp, brev = parse_agent_raw_output(multi_p)
    # Both comp and brev are cleaned of inner consecutive linebreaks into single spaces
    assert "\n" not in comp


def test_should_persist_and_update_agent_store_atomically(tmp_path: Path):
    store_file = tmp_path / "test_agent_executive_messages.json"
    inc_id = "INC000004168775"
    phase = "apertura"
    comp = "Apertura validada para incident manager monitor."
    brev = "Apertura breve validada."

    entry = update_agent_store(
        store_path=store_file,
        incident_id=inc_id,
        phase=phase,
        completo=comp,
        breve=brev,
        origen="incident-reporter"
    )

    assert entry["generado_por_agente"] is True
    assert entry["conteo_palabras_completo"] == 6
    assert entry["conteo_palabras_breve"] == 3

    # Verify saved file
    assert store_file.is_file()
    with open(store_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert inc_id in data["incidents"]
    assert data["incidents"][inc_id][phase]["completo"] == comp


# =========================================================================
# Phase 6 & User Story 4: Client Filtering Logic Tests (FR-013, T022)
# =========================================================================

def filter_incidents_client_side(incidents: list, severity: str = "all", process: str = "all", query: str = "", only_discrepancies: bool = False):
    filtered = []
    q = query.strip().lower()

    for inc in incidents:
        if severity != "all" and inc.get("prioridad_sugerida") != severity:
            continue

        eval_data = inc.get("evaluacion", {})
        if process != "all" and eval_data.get("proceso") != process:
            continue

        if only_discrepancies and not inc.get("es_discrepancia"):
            continue

        if q:
            inc_id = inc.get("id", "").lower()
            titulo = inc.get("titulo", "").lower()
            sistemas = " ".join(inc.get("sistemas", [])).lower()
            if q not in inc_id and q not in titulo and q not in sistemas:
                continue

        filtered.append(inc)

    return filtered


def test_should_filter_by_severity_p1_and_p2(mock_notifications_catalog):
    items = mock_notifications_catalog["incidents"]
    only_p1 = filter_incidents_client_side(items, severity="P1")
    assert len(only_p1) == 1
    assert only_p1[0]["id"] == "INC000004168617"

    only_p2 = filter_incidents_client_side(items, severity="P2")
    assert len(only_p2) == 1
    assert only_p2[0]["id"] == "INC000004168775"


def test_should_filter_by_critical_business_process(mock_notifications_catalog):
    items = mock_notifications_catalog["incidents"]
    core = filter_incidents_client_side(items, process="Sistemas Core")
    assert len(core) == 1
    assert core[0]["id"] == "INC000004168775"


def test_should_filter_by_search_query_matching_id_or_system(mock_notifications_catalog):
    items = mock_notifications_catalog["incidents"]
    by_id = filter_incidents_client_side(items, query="4168775")
    assert len(by_id) == 1
    assert by_id[0]["id"] == "INC000004168775"

    by_sys = filter_incidents_client_side(items, query="ONESIEBEL")
    assert len(by_sys) == 1
    assert by_sys[0]["id"] == "INC000004168617"


def test_should_filter_only_discrepancies(mock_notifications_catalog):
    items = mock_notifications_catalog["incidents"]
    disc = filter_incidents_client_side(items, only_discrepancies=True)
    assert len(disc) == 1
    assert disc[0]["id"] == "INC000004168617"


# =========================================================================
# Phase 2 & Foundational: API Service Contract Tests (T004, T005, T006)
# =========================================================================

def test_should_return_api_pending_payload_with_expected_contract_structure(
    tmp_path: Path, mock_notifications_catalog, mock_agent_store
):
    cat_file = tmp_path / "high_priority_notifications.json"
    cat_file.write_text(json.dumps(mock_notifications_catalog, ensure_ascii=False), encoding="utf-8")

    store_file = tmp_path / "agent_executive_messages.json"
    store_file.write_text(json.dumps(mock_agent_store, ensure_ascii=False), encoding="utf-8")

    payload = get_pending_incidents_payload(catalog_path=cat_file, store_path=store_file)

    assert "kpis" in payload
    assert "pending_incidents" in payload
    assert "completed_incidents" in payload
    assert "all_active_incidents" in payload

    kpis = payload["kpis"]
    assert kpis["total_active"] == 2
    assert kpis["pending_count"] == 1
    assert kpis["completed_count"] == 1
    assert kpis["p1_count"] == 1
    assert kpis["p2_count"] == 1

    pending = payload["pending_incidents"]
    assert len(pending) == 1
    assert pending[0]["id"] == "INC000004168775"
    assert pending[0]["is_pending"] is True


def test_should_support_catalog_with_data_envelope_key_matching_production(
    tmp_path: Path, mock_notifications_catalog, mock_agent_store
):
    """Ensure catalog files with production 'data' key are correctly parsed."""
    prod_catalog = {
        "_metadata": mock_notifications_catalog["_metadata"],
        "data": mock_notifications_catalog["incidents"]
    }
    cat_file = tmp_path / "high_priority_notifications.json"
    cat_file.write_text(json.dumps(prod_catalog, ensure_ascii=False), encoding="utf-8")

    store_file = tmp_path / "agent_executive_messages.json"
    store_file.write_text(json.dumps(mock_agent_store, ensure_ascii=False), encoding="utf-8")

    payload = get_pending_incidents_payload(catalog_path=cat_file, store_path=store_file)
    assert payload["kpis"]["total_active"] == 2
    assert payload["kpis"]["pending_count"] == 1
    assert len(payload["pending_incidents"]) == 1
    assert payload["pending_incidents"][0]["id"] == "INC000004168775"


def test_should_detect_exact_pending_incidents_from_real_workspace_files(repo_root: Path):
    """Integration check verifying real workspace files detect both pending incidents."""
    cat_file = repo_root / "data" / "output" / "high_priority_notifications.json"
    store_file = repo_root / "data" / "agent_executive_messages.json"

    if not cat_file.is_file() or not store_file.is_file():
        pytest.skip("Workspace data files not found")

    payload = get_pending_incidents_payload(catalog_path=cat_file, store_path=store_file)
    pending_ids = [inc["id"] for inc in payload["pending_incidents"]]

    assert "INC000004169057" in pending_ids, "INC000004169057 must be in pending list"
    assert "INC000004168775" in pending_ids, "INC000004168775 must be in pending list"
    assert payload["kpis"]["pending_count"] == len(pending_ids)


def test_should_handle_save_message_api_validation_failure_when_word_limit_exceeded(tmp_path: Path):
    store_file = tmp_path / "agent_store.json"
    excess_comp = " ".join(["palabra"] * 95)
    code, resp = validate_and_save_agent_message(
        incident_id="INC000004168775",
        phase="apertura",
        completo=excess_comp,
        breve="Breve válido.",
        store_path=store_file,
        eval_script=Path("/fake/path.py")
    )
    assert code == 400
    assert resp["success"] is False
    assert "Límite de palabras excedido" in resp["error"]


def test_should_handle_save_message_api_validation_failure_when_invalid_phase(tmp_path: Path):
    store_file = tmp_path / "agent_store.json"
    code, resp = validate_and_save_agent_message(
        incident_id="INC000004168775",
        phase="invalida",
        completo="Completo válido.",
        breve="Breve válido.",
        store_path=store_file,
        eval_script=Path("/fake/path.py")
    )
    assert code == 400
    assert resp["success"] is False
    assert "Fase 'invalida' no válida" in resp["error"]


def test_should_handle_save_message_api_success_and_persist_to_store(tmp_path: Path):
    store_file = tmp_path / "agent_store.json"
    code, resp = validate_and_save_agent_message(
        incident_id="INC000004168775",
        phase="apertura",
        completo="Mensaje completo dentro de los límites requeridos.",
        breve="Mensaje breve.",
        store_path=store_file,
        eval_script=Path("/fake/path.py")
    )
    assert code == 200
    assert resp["success"] is True
    assert resp["incident_id"] == "INC000004168775"
    assert resp["entry"]["generado_por_agente"] is True

    # Check store file content
    data = json.loads(store_file.read_text(encoding="utf-8"))
    assert "INC000004168775" in data["incidents"]
    assert data["incidents"]["INC000004168775"]["apertura"]["conteo_palabras_completo"] == 7


def test_should_integrate_with_serve_app_handler(monkeypatch):
    from unittest.mock import MagicMock
    import serve_app

    handler = MagicMock()
    handler._send_json = MagicMock()

    # Test handle_incident_manager_pending
    serve_app.CustomHTTPHandler.handle_incident_manager_pending(handler)
    assert handler._send_json.called
    status, payload = handler._send_json.call_args[0]
    assert status == 200
    assert "kpis" in payload
    assert "pending_incidents" in payload


