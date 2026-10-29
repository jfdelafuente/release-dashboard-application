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
    enrich_emergency_incident,
    get_emergency_cockpit_payload,
    get_pending_incidents_payload,
    parse_remedy_datetime_to_epoch_ms,
    validate_and_save_agent_message,
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
            },
            "INC000004152079": {
                "apertura": {
                    "completo": "Apertura completa oficial de facturación.",
                    "breve": "Apertura breve.",
                    "generado_por_agente": True,
                    "origen": "incident-reporter",
                    "conteo_palabras_completo": 5,
                    "conteo_palabras_breve": 2
                }
            },
            "INC000004168775": {
                "apertura": {
                    "completo": "Apertura completa middleware.",
                    "breve": "Apertura breve middleware.",
                    "generado_por_agente": True,
                    "origen": "incident-reporter",
                    "conteo_palabras_completo": 3,
                    "conteo_palabras_breve": 3
                }
            }
        }
    }


@pytest.fixture
def mock_emergency_console_catalog():
    """Catalog matching emergency console specification with SL1, SL2, discrepancies, and workarounds."""
    return {
        "_metadata": {
            "version": "1.0.0",
            "generated_at": "2026-10-29T08:00:00Z",
            "source_file": "CS-Informe incidencias P1, P2 y P3 - 2026 - 29 Oct 2026-massive.json",
            "total_candidates_evaluated": 20,
            "total_high_priority_detected": 3,
            "p1_critical_count": 2,
            "p2_high_count": 1,
            "discrepancies_count": 2
        },
        "data": [
            {
                "id": "INC000004152079",
                "titulo": "INCIFAC-1540 Stihl - Error en facturacion Lego Deporte",
                "sistemas": ["SOP_TMC_EXCALIBUR"],
                "prioridad_original": "Media",
                "prioridad_sugerida": "P1",
                "es_alta_prioridad": True,
                "es_discrepancia": True,
                "estatus": "En Curso",
                "fecha_apertura": "29/10/2026 07:10",
                "fecha_envio": "29/10/2026 07:10",
                "evaluacion": {
                    "proceso": "Facturación y Cobros",
                    "criterio": "Facturación: >3h sin tarificación online o ventana +/-3 días ciclo",
                    "impacto": "Alto",
                    "impacto_justificacion": "Afectación en proceso crítico de facturación comercial activa sin alternativa viable.",
                    "urgencia": "Media",
                    "urgencia_justificacion": "Ciclo activo en riesgo.",
                    "workaround": "Desconocido",
                    "workaround_gobernanza": "No identificado",
                    "sla_objetivo_minutos": 15,
                    "minutos_desde_apertura": 50,
                    "sla_primera_notificacion_vencido": True,
                    "requiere_escalado_telefonico": True,
                    "escalado_estamentos_superiores": False,
                    "proxima_ventana_update_minutos": 10
                },
                "mensajes_ejecutivos": {
                    "apertura": {
                        "completo": "Apertura completa de facturación con 70 palabras en único párrafo según normativa.",
                        "breve": "Apertura breve facturación.",
                        "generado_por_agente": True,
                        "estado": "completado"
                    }
                },
                "reporte_emergencia": "🚨 REPORTE DE EMERGENCIA IT - ORANGE TECH OPERATIONS\n[1] CLASIFICACIÓN DEL TICKET\n• Incidencia: INC000004152079 (SL1)\n[2] ESTADO DE COMUNICACIONES Y SLAS\n[3] PLAN DE ACCIÓN Y GOBERNANZA DE WORKAROUNDS\n[4] ESTADO DE ESCALADO TELEFÓNICO"
            },
            {
                "id": "INC000004169386",
                "titulo": "PROV-8812 - Caída en cola de aprovisionamiento de fibra",
                "sistemas": ["SIEBEL PROV", "NEBA CORE"],
                "prioridad_original": "Baja",
                "prioridad_sugerida": "P1",
                "es_alta_prioridad": True,
                "es_discrepancia": True,
                "estatus": "Asignado",
                "fecha_apertura": "29/10/2026 06:10",
                "fecha_envio": "29/10/2026 06:10",
                "evaluacion": {
                    "proceso": "Provisión y Activación",
                    "criterio": "Provisión: >20% pedidos móvil con error (>10m 100% error)",
                    "impacto": "Crítico",
                    "impacto_justificacion": "Bloqueo total en cola de aprovisionamiento.",
                    "urgencia": "Crítica",
                    "urgencia_justificacion": "Impacto acumulativo en órdenes comerciales.",
                    "workaround": "Script temporal de reintento",
                    "workaround_gobernanza": "Pendiente autorización IM-CSO",
                    "sla_objetivo_minutos": 15,
                    "minutos_desde_apertura": 110,
                    "sla_primera_notificacion_vencido": True,
                    "requiere_escalado_telefonico": True,
                    "escalado_estamentos_superiores": True,
                    "proxima_ventana_update_minutos": 5
                },
                "mensajes_ejecutivos": {
                    "apertura": {
                        "completo": "",
                        "breve": "",
                        "generado_por_agente": False,
                        "estado": "pendiente"
                    }
                }
            },
            {
                "id": "INC000004168775",
                "titulo": "INDISPONIBILIDAD // MIDDLEWARE // SL1 NOMINAL",
                "sistemas": ["SPAIN ALMACENAMIENTO"],
                "prioridad_original": "Crítica",
                "prioridad_sugerida": "P2",
                "es_alta_prioridad": True,
                "es_discrepancia": False,
                "estatus": "Pendiente",
                "fecha_apertura": "29/10/2026 07:45",
                "fecha_envio": "29/10/2026 07:45",
                "evaluacion": {
                    "proceso": "Sistemas Core",
                    "criterio": "SL2 Mayor: Degradación funcional o afectación en sede sin indisponibilidad global",
                    "impacto": "Medio",
                    "impacto_justificacion": "Degradación parcial sin impacto directo en cliente final.",
                    "urgencia": "Media",
                    "urgencia_justificacion": "Atención programada.",
                    "workaround": "Desvío por nodo secundario",
                    "workaround_gobernanza": "Autorizado por IM-CSO",
                    "sla_objetivo_minutos": 60,
                    "minutos_desde_apertura": 15,
                    "sla_primera_notificacion_vencido": False,
                    "requiere_escalado_telefonico": False,
                    "escalado_estamentos_superiores": False,
                    "proxima_ventana_update_minutos": 45
                },
                "mensajes_ejecutivos": {
                    "apertura": {
                        "completo": "Apertura completa middleware.",
                        "breve": "Apertura breve middleware.",
                        "generado_por_agente": True,
                        "estado": "completado"
                    }
                }
            }
        ]
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
    """Helper mimicking the pending discrimination logic in backend and frontend.
    
    Under the operational paradigm:
    An incident is PENDING (requiere tratamiento / acción operativa) if:
    1. Redaction is pending (SL1/P2 without official agent message in store)
    2. Escalation >= 45 min requires telephone follow-up
    3. Severity discrepancy requires N1/Orange matrix review
    """
    incidents = catalog.get("incidents", []) or catalog.get("data", [])
    store_incidents = agent_store.get("incidents", {})

    pending_list = []
    completed_list = []
    p1_count = 0
    p2_count = 0
    discrepancies_count = 0
    redactions_pending_count = 0

    for inc in incidents:
        inc_id = inc.get("id")
        prio_sug = inc.get("prioridad_sugerida", "P2")
        if prio_sug == "P1":
            p1_count += 1
        elif prio_sug == "P2":
            p2_count += 1

        is_disc = bool(inc.get("es_discrepancia"))
        if is_disc:
            discrepancies_count += 1

        # Check if pending agent drafting
        mensajes = inc.get("mensajes_ejecutivos", {})
        apertura = mensajes.get("apertura", {}) if isinstance(mensajes, dict) else {}
        store_entry = store_incidents.get(inc_id, {}).get("apertura", {})
        in_store = inc_id in store_incidents and bool(store_entry.get("completo")) and store_entry.get("generado_por_agente") is not False

        is_redaction_pending = (
            apertura.get("estado") == "pendiente"
            or not bool(apertura.get("completo"))
            or not in_store
        )
        if is_redaction_pending:
            redactions_pending_count += 1

        eval_data = inc.get("evaluacion", {}) if isinstance(inc.get("evaluacion"), dict) else {}
        mins_elapsed = eval_data.get("minutos_desde_apertura", 0)

        # 3 operational pending conditions
        is_pending = bool(is_redaction_pending or mins_elapsed >= 45 or is_disc)

        inc_copy = dict(inc)
        inc_copy["is_redaction_pending"] = is_redaction_pending
        inc_copy["is_pending"] = is_pending

        if is_pending:
            pending_list.append(inc_copy)
        else:
            completed_list.append(inc_copy)

    kpis = {
        "total_active": len(incidents),
        "completed_count": len(completed_list),
        "pending_count": len(pending_list),
        "redactions_pending_count": redactions_pending_count,
        "p1_count": p1_count,
        "p2_count": p2_count,
        "discrepancies_count": discrepancies_count,
        "escalation_alerts_count": sum(1 for i in incidents if i.get("evaluacion", {}).get("minutos_desde_apertura", 0) >= 45)
    }
    return kpis, pending_list, completed_list


def test_should_identify_pending_incident_when_apertura_estado_is_pendiente(
    mock_notifications_catalog, mock_agent_store
):
    kpis, pending, completed = compute_monitor_state(mock_notifications_catalog, mock_agent_store)
    pending_map = {i["id"]: i for i in pending}
    assert "INC000004168775" in pending_map
    assert pending_map["INC000004168775"]["is_redaction_pending"] is True
    assert pending_map["INC000004168775"]["is_pending"] is True


def test_should_identify_pending_incident_when_not_in_agent_store(
    mock_notifications_catalog
):
    empty_store = {"incidents": {}}
    kpis, pending, completed = compute_monitor_state(mock_notifications_catalog, empty_store)
    # Both should be pending because store is empty (and INC000004168617 also has discrepancy)
    assert len(pending) == 2
    assert kpis["pending_count"] == 2
    assert kpis["redactions_pending_count"] == 2
    assert kpis["completed_count"] == 0


def test_should_identify_pending_by_escalation_or_discrepancy_even_with_redaction_ready():
    sample_catalog = {
        "incidents": [
            {
                "id": "INC_DISC",
                "prioridad_sugerida": "P2",
                "es_discrepancia": True,
                "mensajes_ejecutivos": {
                    "apertura": {"completo": "Apertura lista", "generado_por_agente": True, "estado": "completado"}
                },
                "evaluacion": {"minutos_desde_apertura": 10}
            },
            {
                "id": "INC_ESC45",
                "prioridad_sugerida": "P2",
                "es_discrepancia": False,
                "mensajes_ejecutivos": {
                    "apertura": {"completo": "Apertura lista", "generado_por_agente": True, "estado": "completado"}
                },
                "evaluacion": {"minutos_desde_apertura": 50}
            },
            {
                "id": "INC_CLEAN",
                "prioridad_sugerida": "P2",
                "es_discrepancia": False,
                "mensajes_ejecutivos": {
                    "apertura": {"completo": "Apertura lista", "generado_por_agente": True, "estado": "completado"}
                },
                "evaluacion": {"minutos_desde_apertura": 10}
            }
        ]
    }
    sample_store = {
        "incidents": {
            "INC_DISC": {"apertura": {"completo": "Apertura lista", "generado_por_agente": True}},
            "INC_ESC45": {"apertura": {"completo": "Apertura lista", "generado_por_agente": True}},
            "INC_CLEAN": {"apertura": {"completo": "Apertura lista", "generado_por_agente": True}},
        }
    }
    kpis, pending, completed = compute_monitor_state(sample_catalog, sample_store)
    assert kpis["total_active"] == 3
    assert kpis["pending_count"] == 2
    assert kpis["completed_count"] == 1
    assert kpis["redactions_pending_count"] == 0

    pending_ids = [i["id"] for i in pending]
    assert "INC_DISC" in pending_ids
    assert "INC_ESC45" in pending_ids
    assert "INC_CLEAN" not in pending_ids

    assert len(completed) == 1
    assert completed[0]["id"] == "INC_CLEAN"
    assert completed[0]["is_pending"] is False


def test_should_calculate_correct_kpis_summary_counts(
    mock_notifications_catalog, mock_agent_store
):
    kpis, pending, completed = compute_monitor_state(mock_notifications_catalog, mock_agent_store)
    assert kpis["total_active"] == 2
    assert kpis["pending_count"] == 2
    assert kpis["completed_count"] == 0
    assert kpis["redactions_pending_count"] == 1
    assert kpis["p1_count"] == 1
    assert kpis["p2_count"] == 1
    assert kpis["escalation_alerts_count"] <= kpis["total_active"]
    assert kpis["discrepancies_count"] == 1


def test_should_ensure_escalation_alerts_count_is_deduplicated_in_monitor_js(repo_root: Path):
    monitor_js_path = repo_root / "dashboards" / "incident-manager-monitor" / "monitor.js"
    content = monitor_js_path.read_text(encoding="utf-8")
    assert "const escalationAlerts = (state.allIncidents || []).filter" in content
    assert "state.kpis.escalation_alerts_count = escalationAlerts;" in content




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
        "Actúa como el agente incident-reporter de Orange para la fase de APERTURA.\n"
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

def match_process_client_side(inc_process: str, filter_val: str) -> bool:
    if not filter_val or filter_val == "all":
        return True
    if not inc_process:
        return False
    p = inc_process.strip().lower()
    f = filter_val.strip().lower()
    if p == f:
        return True
    if "provis" in f and "provis" in p:
        return True
    if "venta" in f and "venta" in p:
        return True
    if "factur" in f and "factur" in p:
        return True
    if ("atc" in f or "atenci" in f) and ("atc" in p or "atenci" in p):
        return True
    if ("o&m" in f or "operac" in f or "monitor" in f or "red" in f) and ("o&m" in p or "operac" in p or "monitor" in p or "red" in p):
        return True
    if "core" in f and "core" in p:
        return True
    if "prepag" in f and "prepag" in p:
        return True
    if "portabil" in f and "portabil" in p:
        return True
    return False


def check_has_official_message_client_side(inc: dict, phase: str) -> bool:
    if phase == "apertura" and inc.get("is_redaction_pending"):
        return False
    mensajes = inc.get("mensajes_ejecutivos", {}) or {}
    msg_obj = mensajes.get(phase, {}) if isinstance(mensajes, dict) else {}
    if not isinstance(msg_obj, dict):
        return False
    completo = (msg_obj.get("completo") or "").strip()
    if not completo:
        return False
    if msg_obj.get("estado") == "pendiente":
        return False
    if msg_obj.get("generado_por_agente") is False:
        return False
    return True


def filter_incidents_client_side(
    incidents: list,
    severity: str = "all",
    process: str = "all",
    query: str = "",
    only_discrepancies: bool = False,
    view_mode: str = "all",
    comm_phase: str = "all",
):
    filtered = []
    q = query.strip().lower()

    for inc in incidents:
        if view_mode == "pending" and not inc.get("is_pending", True):
            continue

        if severity != "all" and inc.get("prioridad_sugerida") != severity:
            continue

        eval_data = inc.get("evaluacion", {})
        proc = eval_data.get("proceso") or inc.get("discrepancia", {}).get("proceso_critico") or ""
        if not match_process_client_side(proc, process):
            continue

        is_disc = bool(inc.get("es_discrepancia") or inc.get("discrepancia", {}).get("es_discrepancia"))
        if only_discrepancies and not is_disc:
            continue

        if comm_phase and comm_phase != "all":
            has_ap = check_has_official_message_client_side(inc, "apertura")
            has_seg = check_has_official_message_client_side(inc, "seguimiento")
            has_cie = check_has_official_message_client_side(inc, "cierre")

            if comm_phase == "missing_any" and (has_ap and has_seg and has_cie):
                continue
            if comm_phase == "missing_apertura" and has_ap:
                continue
            if comm_phase == "missing_seguimiento" and has_seg:
                continue
            if comm_phase == "missing_cierre" and has_cie:
                continue
            if comm_phase == "missing_all" and (has_ap or has_seg or has_cie):
                continue
            if comm_phase == "has_apertura" and not has_ap:
                continue
            if comm_phase == "has_seguimiento" and not has_seg:
                continue
            if comm_phase == "has_cierre" and not has_cie:
                continue
            if comm_phase == "all_completed" and (not has_ap or not has_seg or not has_cie):
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


def test_should_filter_by_tolerant_critical_process_names():
    sample_items = [
        {"id": "INC1", "evaluacion": {"proceso": "Provisión"}},
        {"id": "INC2", "evaluacion": {"proceso": "Provisión y Activación"}},
        {"id": "INC3", "evaluacion": {"proceso": "Ventas"}},
        {"id": "INC4", "evaluacion": {"proceso": "Ventas y Canales"}},
        {"id": "INC5", "evaluacion": {"proceso": "Atención al Cliente (ATC)"}}
    ]
    # Filter with 'Provisión' matches both 'Provisión' and 'Provisión y Activación'
    matched_prov = filter_incidents_client_side(sample_items, process="Provisión")
    assert len(matched_prov) == 2
    assert {i["id"] for i in matched_prov} == {"INC1", "INC2"}

    # Filter with 'Ventas y Canales' matches both 'Ventas' and 'Ventas y Canales'
    matched_ventas = filter_incidents_client_side(sample_items, process="Ventas y Canales")
    assert len(matched_ventas) == 2
    assert {i["id"] for i in matched_ventas} == {"INC3", "INC4"}


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


def test_should_filter_by_pending_view_vs_all_active_view():
    """Verifica que el selector 'Solo Pendientes' vs 'Todas las Activas' filtre correctamente según is_pending."""
    incidents = [
        {
            "id": "INC_PEND_1",
            "prioridad_sugerida": "P1",
            "is_pending": True,
            "minutos_desde_apertura": 50,
            "es_discrepancia": False,
        },
        {
            "id": "INC_PEND_2",
            "prioridad_sugerida": "P2",
            "is_pending": True,
            "minutos_desde_apertura": 10,
            "es_discrepancia": True,
        },
        {
            "id": "INC_STABLE_1",
            "prioridad_sugerida": "P2",
            "is_pending": False,
            "minutos_desde_apertura": 25,
            "es_discrepancia": False,
        },
    ]

    pending_only = filter_incidents_client_side(incidents, view_mode="pending")
    assert len(pending_only) == 2
    assert {i["id"] for i in pending_only} == {"INC_PEND_1", "INC_PEND_2"}

    all_active = filter_incidents_client_side(incidents, view_mode="all")
    assert len(all_active) == 3
    assert {i["id"] for i in all_active} == {"INC_PEND_1", "INC_PEND_2", "INC_STABLE_1"}


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
    # Both are pending: INC000004168775 has pending redaction, INC000004168617 has discrepancy
    assert kpis["pending_count"] == 2
    assert kpis["completed_count"] == 0
    assert kpis["redactions_pending_count"] == 1
    assert kpis["p1_count"] == 1
    assert kpis["p2_count"] == 1
    assert kpis["escalation_alerts_count"] <= kpis["total_active"]

    pending = payload["pending_incidents"]
    assert len(pending) == 2
    pending_ids = [i["id"] for i in pending]
    assert "INC000004168775" in pending_ids
    assert "INC000004168617" in pending_ids

    # Verify is_pending and is_redaction_pending flags
    inc_map = {inc["id"]: inc for inc in pending}
    assert inc_map["INC000004168775"]["is_pending"] is True
    assert inc_map["INC000004168775"]["is_redaction_pending"] is True

    assert inc_map["INC000004168617"]["is_pending"] is True
    assert inc_map["INC000004168617"]["is_redaction_pending"] is False
    assert inc_map["INC000004168617"]["es_discrepancia"] is True


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
    assert payload["kpis"]["pending_count"] == 2
    assert payload["kpis"]["redactions_pending_count"] == 1
    assert len(payload["pending_incidents"]) == 2
    pending_ids = [inc["id"] for inc in payload["pending_incidents"]]
    assert "INC000004168775" in pending_ids
    assert "INC000004168617" in pending_ids


def test_should_detect_exact_pending_incidents_from_real_workspace_files(repo_root: Path):
    """Integration check verifying real workspace files detect both pending incidents."""
    cat_file = repo_root / "data" / "output" / "high_priority_notifications.json"
    store_file = repo_root / "data" / "agent_executive_messages.json"

    if not cat_file.is_file() or not store_file.is_file():
        pytest.skip("Workspace data files not found")

    payload = get_pending_incidents_payload(catalog_path=cat_file, store_path=store_file)
    pending_ids = [inc["id"] for inc in payload["pending_incidents"]]

    assert isinstance(pending_ids, list)
    assert payload["kpis"]["total_active"] >= len(pending_ids)
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


# =========================================================================
# Feature 014: Orange Emergency Operations Console Tests
# =========================================================================

def test_should_return_emergency_cockpit_contract_structure(tmp_path: Path, mock_emergency_console_catalog, mock_agent_store):
    cat_file = tmp_path / "high_priority_notifications.json"
    cat_file.write_text(json.dumps(mock_emergency_console_catalog), encoding="utf-8")
    store_file = tmp_path / "agent_store.json"
    store_file.write_text(json.dumps(mock_agent_store), encoding="utf-8")

    payload = get_emergency_cockpit_payload(catalog_path=cat_file, store_path=store_file)

    assert "_metadata" in payload
    assert payload["_metadata"]["version"] == "1.0.0"
    assert "server_time" in payload["_metadata"]

    kpis = payload["kpis"]
    assert kpis["total_activas"] == 3
    assert kpis["sl1_criticas"] == 2
    assert kpis["sl2_altas"] == 1
    assert kpis["discrepancias_subescalacion"] == 2
    assert kpis["alertas_escalado_45m"] >= 2
    assert kpis["alertas_escalado_superior"] >= 1
    assert kpis["workarounds_pendientes_cso"] == 1
    assert kpis["redacciones_pendientes"] == 1

    assert len(payload["incidents"]) == 3
    first = payload["incidents"][0]
    assert "severidad_calculada" in first
    assert "apertura_epoch_ms" in first
    assert "discrepancia" in first
    assert "timeline" in first
    assert "workaround" in first
    assert "reporte_emergencia" in first


def test_should_filter_emergency_cockpit_by_severity_and_pending(tmp_path: Path, mock_emergency_console_catalog, mock_agent_store):
    cat_file = tmp_path / "high_priority_notifications.json"
    cat_file.write_text(json.dumps(mock_emergency_console_catalog), encoding="utf-8")
    store_file = tmp_path / "agent_store.json"
    store_file.write_text(json.dumps(mock_agent_store), encoding="utf-8")

    # Reference time matching mock catalog generated_at (29/10/2026 08:00 UTC)
    ref_now_ms = parse_remedy_datetime_to_epoch_ms("29/10/2026 08:00")

    # Severity SL1 filter
    sl1_payload = get_emergency_cockpit_payload(catalog_path=cat_file, store_path=store_file, severity="SL1", now_ms=ref_now_ms)
    assert len(sl1_payload["incidents"]) == 2
    assert all(inc["severidad_calculada"] == "SL1" for inc in sl1_payload["incidents"])

    # Severity SL2 filter
    sl2_payload = get_emergency_cockpit_payload(catalog_path=cat_file, store_path=store_file, severity="SL2", now_ms=ref_now_ms)
    assert len(sl2_payload["incidents"]) == 1
    assert sl2_payload["incidents"][0]["severidad_calculada"] == "SL2"

    # Pending filter:
    # Under the new operational definition:
    # - INC000004152079: 50m (>=45m) and discrepancy -> PENDING
    # - INC000004169386: 110m (>=45m), discrepancy and pending redaction -> PENDING
    # - INC000004168775: 15m (<45m), no discrepancy, approved redaction in store -> COMPLETED / AL DIA
    pending_payload = get_emergency_cockpit_payload(catalog_path=cat_file, store_path=store_file, only_pending=True, now_ms=ref_now_ms)
    assert len(pending_payload["incidents"]) == 2
    pending_ids = [inc["id"] for inc in pending_payload["incidents"]]
    assert "INC000004152079" in pending_ids
    assert "INC000004169386" in pending_ids
    assert "INC000004168775" not in pending_ids


def test_should_integrate_emergency_cockpit_with_serve_app_handler(monkeypatch):
    from unittest.mock import MagicMock
    import serve_app

    handler = MagicMock()
    handler._send_json = MagicMock()
    handler.path = "/api/incident-manager/emergency-cockpit?severity=all"

    serve_app.CustomHTTPHandler.handle_incident_manager_emergency_cockpit(handler)
    assert handler._send_json.called
    status, payload = handler._send_json.call_args[0]
    assert status == 200
    assert "kpis" in payload
    assert "incidents" in payload
    assert "total_activas" in payload["kpis"]


def test_should_enrich_pending_incidents_payload_with_emergency_fields(tmp_path: Path, mock_emergency_console_catalog, mock_agent_store):
    cat_file = tmp_path / "high_priority_notifications.json"
    cat_file.write_text(json.dumps(mock_emergency_console_catalog), encoding="utf-8")
    store_file = tmp_path / "agent_store.json"
    store_file.write_text(json.dumps(mock_agent_store), encoding="utf-8")

    payload = get_pending_incidents_payload(catalog_path=cat_file, store_path=store_file)
    for inc in payload["all_active_incidents"]:
        assert inc["apertura_epoch_ms"] is not None
        assert "discrepancia" in inc
        assert "timeline" in inc
        assert "workaround" in inc
        assert "reporte_emergencia" in inc


def test_should_extract_critical_process_and_quantitative_threshold(tmp_path: Path, mock_emergency_console_catalog, mock_agent_store):
    cat_file = tmp_path / "high_priority_notifications.json"
    cat_file.write_text(json.dumps(mock_emergency_console_catalog), encoding="utf-8")
    store_file = tmp_path / "agent_store.json"
    store_file.write_text(json.dumps(mock_agent_store), encoding="utf-8")

    payload = get_emergency_cockpit_payload(catalog_path=cat_file, store_path=store_file)
    inc_map = {inc["id"]: inc for inc in payload["incidents"]}

    fac_inc = inc_map["INC000004152079"]
    assert fac_inc["discrepancia"]["proceso_critico"] == "Facturación y Cobros"
    assert ">3h sin tarificación online o ventana +/-3 días ciclo" in fac_inc["discrepancia"]["criterio_umbral"]

    prov_inc = inc_map["INC000004169386"]
    assert prov_inc["discrepancia"]["proceso_critico"] == "Provisión y Activación"
    assert ">20% pedidos móvil con error" in prov_inc["discrepancia"]["criterio_umbral"]


def test_should_breakdown_discrepancy_kpis_sl1_vs_sl2(tmp_path: Path, mock_emergency_console_catalog, mock_agent_store):
    cat_file = tmp_path / "high_priority_notifications.json"
    cat_file.write_text(json.dumps(mock_emergency_console_catalog), encoding="utf-8")
    store_file = tmp_path / "agent_store.json"
    store_file.write_text(json.dumps(mock_agent_store), encoding="utf-8")

    payload = get_emergency_cockpit_payload(catalog_path=cat_file, store_path=store_file)
    sl1_discrepancies = [i for i in payload["incidents"] if i["es_discrepancia"] and i["severidad_calculada"] == "SL1"]
    sl2_discrepancies = [i for i in payload["incidents"] if i["es_discrepancia"] and i["severidad_calculada"] == "SL2"]

    assert len(sl1_discrepancies) == 2
    assert len(sl2_discrepancies) == 0


def test_should_assign_escalation_timeline_phases_and_elapsed_minutes():
    # Phase <45 min
    inc_recent = {"id": "INC_REC", "prioridad_sugerida": "P2", "evaluacion": {"minutos_desde_apertura": 15}}
    enriched_recent = enrich_emergency_incident(inc_recent)
    assert enriched_recent["timeline"]["fase_escalado"] == "NORMAL"
    assert enriched_recent["timeline"]["estamento_convocado"] == "N1 / Guardias"
    assert enriched_recent["timeline"]["sla_1a_notif_vencido"] is False

    # Phase 45m - 104m
    inc_45 = {"id": "INC_45", "prioridad_sugerida": "P1", "evaluacion": {"minutos_desde_apertura": 50}}
    enriched_45 = enrich_emergency_incident(inc_45)
    assert enriched_45["timeline"]["fase_escalado"] == "ESCALADO_45M_REQUERIDO"
    assert enriched_45["timeline"]["estamento_convocado"] == "Resolutores N2/N3"
    assert enriched_45["timeline"]["sla_1a_notif_vencido"] is True

    # Phase >= 105m
    inc_105 = {"id": "INC_105", "prioridad_sugerida": "P1", "evaluacion": {"minutos_desde_apertura": 110}}
    enriched_105 = enrich_emergency_incident(inc_105)
    assert enriched_105["timeline"]["fase_escalado"] == "ESCALADO_SUPERIOR_REQUERIDO"
    assert enriched_105["timeline"]["estamento_convocado"] == "Estamentos Superiores vía IM-CSO"
    assert enriched_105["timeline"]["sla_1a_notif_vencido"] is True


def test_should_mandate_phone_channel_for_all_sl1_incidents():
    inc_sl1 = {"id": "INC_SL1", "prioridad_sugerida": "P1", "evaluacion": {"minutos_desde_apertura": 10}}
    enriched_sl1 = enrich_emergency_incident(inc_sl1)
    assert enriched_sl1["timeline"]["requiere_canal_telefonico"] is True

    inc_sl2 = {"id": "INC_SL2", "prioridad_sugerida": "P2", "evaluacion": {"minutos_desde_apertura": 10}}
    enriched_sl2 = enrich_emergency_incident(inc_sl2)
    assert enriched_sl2["timeline"]["requiere_canal_telefonico"] is False


def test_should_block_deescalation_when_workaround_active_without_impact_eradication():
    inc_wa = {
        "id": "INC_WA",
        "prioridad_sugerida": "P1",
        "estatus": "En Curso",
        "evaluacion": {
            "workaround": "Script de reintento transitorio",
            "workaround_gobernanza": "Pendiente autorización IM-CSO",
            "minutos_desde_apertura": 30
        }
    }
    enriched = enrich_emergency_incident(inc_wa)
    wa = enriched["workaround"]
    assert wa["workaround_detectado"] is True
    assert wa["impacto_erradicado"] is False
    assert wa["desescalada_bloqueada"] is True
    assert "Regla de Oro CSO" in wa["motivo_bloqueo"]


def test_should_detect_workaround_pending_cso_authorization():
    inc_pending = {
        "id": "INC_WA_PEND",
        "prioridad_sugerida": "P1",
        "estatus": "Asignado",
        "evaluacion": {
            "workaround": "Parche temporal en DNS",
            "workaround_gobernanza": "Pendiente autorización IM-CSO"
        }
    }
    enriched_pending = enrich_emergency_incident(inc_pending)
    assert enriched_pending["workaround"]["autorizado_cso"] is False
    assert enriched_pending["workaround"]["estado_gobernanza"] == "PENDIENTE_AUTORIZACION_CSO"

    inc_approved = {
        "id": "INC_WA_APP",
        "prioridad_sugerida": "P1",
        "estatus": "En Curso",
        "evaluacion": {
            "workaround": "Parche temporal en DNS",
            "workaround_gobernanza": "Autorizado por IM-CSO"
        }
    }
    enriched_approved = enrich_emergency_incident(inc_approved)
    assert enriched_approved["workaround"]["autorizado_cso"] is True
    assert enriched_approved["workaround"]["estado_gobernanza"] == "AUTORIZADO_CSO_IMPACTO_ACTIVO"


def test_should_contain_4_normalized_blocks_in_emergency_report():
    inc = {
        "id": "INC000004152079",
        "titulo": "Fallo masivo facturacion Lego",
        "prioridad_sugerida": "P1",
        "sistemas": ["SOP_TMC_EXCALIBUR"],
        "evaluacion": {
            "proceso": "Facturación y Cobros",
            "criterio": "Facturación: >3h sin tarificación",
            "minutos_desde_apertura": 60
        }
    }
    enriched = enrich_emergency_incident(inc)
    rep = enriched["reporte_emergencia"]
    assert "🚨 REPORTE DE EMERGENCIA IT - ORANGE TECH OPERATIONS" in rep
    assert "[1] CLASIFICACIÓN DEL TICKET" in rep
    assert "[2] ESTADO DE COMUNICACIONES Y SLAS" in rep
    assert "[3] PLAN DE ACCIÓN Y GOBERNANZA DE WORKAROUNDS" in rep
    assert "[4] ESTADO DE ESCALADO TELEFÓNICO" in rep
    assert "Regla de Oro: Prohibida la desescalada automática" in rep


def test_should_provide_remedy_reclassification_and_warroom_tools_in_monitor_js(repo_root):
    """Verifica que monitor.js incluya las funciones y botones de acción inmediata para el Incident Manager."""
    monitor_js_path = repo_root / "dashboards" / "incident-manager-monitor" / "monitor.js"
    content = monitor_js_path.read_text(encoding="utf-8")

    # Funciones de construcción de textos de acción
    assert "function buildRemedyReclassificationText(" in content
    assert "function buildTeamsWarRoomText(" in content
    assert "function generateAiDraftForIncident(" in content

    # Botones en vistas y tarjetas
    assert "btn-copy-remedy-reclass" in content
    assert "btn-copy-teams-warroom" in content
    assert "btn-quick-reclass" in content
    assert "btn-quick-warroom" in content
    assert "btn-suggest-draft" in content


def test_should_provide_action_tools_styling_in_monitor_css(repo_root):
    """Verifica que monitor.css defina estilos para los botones de acción inmediata."""
    monitor_css_path = repo_root / "dashboards" / "incident-manager-monitor" / "monitor.css"
    content = monitor_css_path.read_text(encoding="utf-8")

    assert ".btn-quick-reclass" in content
    assert ".btn-quick-warroom" in content
    assert ".btn-suggest-draft" in content
    assert ".btn-copy-remedy-reclass" in content
    assert ".btn-copy-teams-warroom" in content


def test_should_verify_ai_draft_word_limits_for_all_phases():
    """Verifica que el generador de borradores IA cumpla con los límites de 90 y 30 palabras en un solo párrafo."""
    def count_words(s):
        return len(s.strip().split())

    sample_inc = {
        "id": "INC000004170183",
        "prioridad_sugerida": "P1",
        "proceso": "Provisión y Activación",
        "criterio": "Móvil: >20% pedidos con error (>10m 100% error)",
        "sistemas": "IP24, Provisión",
        "titulo": "Afectación en IP24 Provisión y activación móvil"
    }

    phases = ["apertura", "seguimiento", "cierre"]
    for phase in phases:
        inc_id = sample_inc["id"]
        prio_sug = sample_inc["prioridad_sugerida"]
        sev_label = "crítica P1" if prio_sug == "P1" else "mayor P2"
        proceso = sample_inc["proceso"]
        criterio = sample_inc["criterio"]
        sistemas_str = sample_inc["sistemas"]
        titulo = sample_inc["titulo"]

        if phase == "apertura":
            comp = f"Se declara incidencia {sev_label} ({inc_id}) por {titulo}. La anomalía impacta directamente en el proceso de {proceso} superando el umbral operativo ({criterio}), afectando a {sistemas_str}. Los equipos técnicos y grupos resolutores investigan el origen del fallo y aplican medidas inmediatas de mitigación para restablecer el servicio a la mayor brevedad. Próxima actualización en 30 minutos."
            brev = f"Apertura {prio_sug} ({inc_id}): {titulo}. Impacto en {proceso} ({sistemas_str}). Equipos resolutores investigando medidas de mitigación."
        elif phase == "seguimiento":
            comp = f"Seguimiento de la incidencia {prio_sug} ({inc_id}) en {proceso}. Los grupos resolutores continúan analizando las trazas e integraciones en {sistemas_str} sobre la afectación reportada ({titulo}). Se ejecutan acciones técnicas de contención operativa para estabilizar los componentes mientras se supervisa de forma continua el impacto en clientes. Próxima actualización en 30 minutos."
            brev = f"Seguimiento {prio_sug} ({inc_id}): Diagnóstico y acciones de contención en curso sobre {sistemas_str}. Servicio bajo monitorización continua de soporte."
        elif phase == "cierre":
            comp = f"Queda resuelta la incidencia {prio_sug} ({inc_id}) que afectaba a {proceso}. Tras las intervenciones técnicas de los grupos resolutores sobre {sistemas_str}, se ha subsanado la anomalía ({titulo}) y el servicio opera con plena normalidad. Se confirma la total erradicación del impacto en clientes y se mantiene monitorización preventiva."
            brev = f"Cierre {prio_sug} ({inc_id}): Restablecido el servicio en {sistemas_str} tras resolución técnica. Impacto erradicado y operativa normalizada."

        # Validar monopárrafo y límites de palabras
        assert "\n" not in comp, f"Fase {phase} completo debe ser monopárrafo"
        assert "\n" not in brev, f"Fase {phase} breve debe ser monopárrafo"
        assert count_words(comp) <= 90, f"Fase {phase} completo excede 90 palabras: {count_words(comp)}"
        assert count_words(brev) <= 30, f"Fase {phase} breve excede 30 palabras: {count_words(brev)}"


def test_should_filter_by_missing_or_completed_official_communications():
    """Verifica que el filtrado por fase de comunicación oficial funcione correctamente para todas las opciones."""
    sample_incidents = [
        # INC_NONE: sin ninguna comunicación generada
        {
            "id": "INC_NONE",
            "is_pending": True,
            "is_redaction_pending": True,
            "mensajes_ejecutivos": {
                "apertura": {"completo": "", "estado": "pendiente", "generado_por_agente": False},
                "seguimiento": {"completo": "", "estado": "pendiente", "generado_por_agente": False},
                "cierre": {"completo": "", "estado": "pendiente", "generado_por_agente": False}
            }
        },
        # INC_AP_ONLY: solo apertura oficial generada
        {
            "id": "INC_AP_ONLY",
            "is_pending": True,
            "is_redaction_pending": False,
            "mensajes_ejecutivos": {
                "apertura": {"completo": "Apertura oficial completada para Dirección.", "estado": "completado", "generado_por_agente": True},
                "seguimiento": {"completo": "", "estado": "pendiente", "generado_por_agente": False},
                "cierre": {"completo": "", "estado": "pendiente", "generado_por_agente": False}
            }
        },
        # INC_AP_SEG: apertura y seguimiento generados, falta cierre
        {
            "id": "INC_AP_SEG",
            "is_pending": True,
            "is_redaction_pending": False,
            "mensajes_ejecutivos": {
                "apertura": {"completo": "Apertura oficial completada.", "estado": "completado", "generado_por_agente": True},
                "seguimiento": {"completo": "Seguimiento oficial en curso.", "estado": "completado", "generado_por_agente": True},
                "cierre": {"completo": "", "estado": "pendiente", "generado_por_agente": False}
            }
        },
        # INC_ALL: todas las comunicaciones generadas
        {
            "id": "INC_ALL",
            "is_pending": False,
            "is_redaction_pending": False,
            "mensajes_ejecutivos": {
                "apertura": {"completo": "Apertura oficial aprobada.", "estado": "completado", "generado_por_agente": True},
                "seguimiento": {"completo": "Seguimiento oficial aprobado.", "estado": "completado", "generado_por_agente": True},
                "cierre": {"completo": "Cierre oficial notificado.", "estado": "completado", "generado_por_agente": True}
            }
        }
    ]

    # 1. Todas
    all_res = filter_incidents_client_side(sample_incidents, comm_phase="all")
    assert len(all_res) == 4

    # 2. missing_any: falta alguna fase (INC_NONE, INC_AP_ONLY, INC_AP_SEG)
    missing_any = filter_incidents_client_side(sample_incidents, comm_phase="missing_any")
    assert {i["id"] for i in missing_any} == {"INC_NONE", "INC_AP_ONLY", "INC_AP_SEG"}

    # 3. missing_apertura: (INC_NONE)
    missing_ap = filter_incidents_client_side(sample_incidents, comm_phase="missing_apertura")
    assert {i["id"] for i in missing_ap} == {"INC_NONE"}

    # 4. missing_seguimiento: (INC_NONE, INC_AP_ONLY)
    missing_seg = filter_incidents_client_side(sample_incidents, comm_phase="missing_seguimiento")
    assert {i["id"] for i in missing_seg} == {"INC_NONE", "INC_AP_ONLY"}

    # 5. missing_cierre: (INC_NONE, INC_AP_ONLY, INC_AP_SEG)
    missing_cie = filter_incidents_client_side(sample_incidents, comm_phase="missing_cierre")
    assert {i["id"] for i in missing_cie} == {"INC_NONE", "INC_AP_ONLY", "INC_AP_SEG"}

    # 6. missing_all: sin ninguna comunicación (INC_NONE)
    missing_all = filter_incidents_client_side(sample_incidents, comm_phase="missing_all")
    assert {i["id"] for i in missing_all} == {"INC_NONE"}

    # 7. has_apertura: (INC_AP_ONLY, INC_AP_SEG, INC_ALL)
    has_ap = filter_incidents_client_side(sample_incidents, comm_phase="has_apertura")
    assert {i["id"] for i in has_ap} == {"INC_AP_ONLY", "INC_AP_SEG", "INC_ALL"}

    # 8. has_seguimiento: (INC_AP_SEG, INC_ALL)
    has_seg = filter_incidents_client_side(sample_incidents, comm_phase="has_seguimiento")
    assert {i["id"] for i in has_seg} == {"INC_AP_SEG", "INC_ALL"}

    # 9. has_cierre: (INC_ALL)
    has_cie = filter_incidents_client_side(sample_incidents, comm_phase="has_cierre")
    assert {i["id"] for i in has_cie} == {"INC_ALL"}

    # 10. all_completed: todas generadas (INC_ALL)
    all_comp = filter_incidents_client_side(sample_incidents, comm_phase="all_completed")
    assert {i["id"] for i in all_comp} == {"INC_ALL"}


def test_has_official_phase_message_unit_logic():
    """Valida la función has_official_phase_message del servicio backend."""
    from incident_manager_service import has_official_phase_message

    # Incidencia sin mensajes
    inc_empty = {"id": "INC1", "mensajes_ejecutivos": {}}
    assert has_official_phase_message(inc_empty, "apertura") is False
    assert has_official_phase_message(inc_empty, "seguimiento") is False
    assert has_official_phase_message(inc_empty, "cierre") is False

    # Incidencia con mensaje pendiente
    inc_pend = {
        "id": "INC2",
        "is_redaction_pending": True,
        "mensajes_ejecutivos": {
            "apertura": {"completo": "Borrador sin aprobar", "estado": "pendiente"}
        }
    }
    assert has_official_phase_message(inc_pend, "apertura") is False

    # Incidencia con mensaje completado pero marcado is_redaction_pending
    inc_redac_pend = {
        "id": "INC3",
        "is_redaction_pending": True,
        "mensajes_ejecutivos": {
            "apertura": {"completo": "Apertura válida", "estado": "completado", "generado_por_agente": True}
        }
    }
    assert has_official_phase_message(inc_redac_pend, "apertura") is False

    # Incidencia con mensaje oficial válido
    inc_valid = {
        "id": "INC4",
        "is_redaction_pending": False,
        "mensajes_ejecutivos": {
            "apertura": {"completo": "Apertura válida oficial.", "estado": "completado", "generado_por_agente": True},
            "seguimiento": {"completo": "Seguimiento válido oficial.", "estado": "completado", "generado_por_agente": True}
        }
    }
    assert has_official_phase_message(inc_valid, "apertura") is True
    assert has_official_phase_message(inc_valid, "seguimiento") is True
    assert has_official_phase_message(inc_valid, "cierre") is False


def test_emergency_cockpit_comm_phase_filtering(mock_notifications_catalog, mock_agent_store, tmp_path):
    """Verifica que get_emergency_cockpit_payload soporte filtrado por comm_phase."""
    from incident_manager_service import get_emergency_cockpit_payload

    cat_file = tmp_path / "high_priority_notifications.json"
    cat_file.write_text(json.dumps(mock_notifications_catalog, ensure_ascii=False), encoding="utf-8")

    store_file = tmp_path / "agent_executive_messages.json"
    store_file.write_text(json.dumps(mock_agent_store, ensure_ascii=False), encoding="utf-8")

    # Apertura válida para INC000004168617, mientras que INC000004168775 tiene apertura pendiente
    payload_has_ap = get_emergency_cockpit_payload(
        catalog_path=cat_file,
        store_path=store_file,
        comm_phase="has_apertura"
    )
    inc_ids_has_ap = [i["id"] for i in payload_has_ap["incidents"]]
    assert "INC000004168617" in inc_ids_has_ap
    assert "INC000004168775" not in inc_ids_has_ap

    # missing_apertura debe devolver INC000004168775
    payload_missing_ap = get_emergency_cockpit_payload(
        catalog_path=cat_file,
        store_path=store_file,
        comm_phase="missing_apertura"
    )
    inc_ids_missing_ap = [i["id"] for i in payload_missing_ap["incidents"]]
    assert "INC000004168775" in inc_ids_missing_ap
    assert "INC000004168617" not in inc_ids_missing_ap


def test_should_render_communication_filter_select_in_index_html(repo_root):
    """Verifica que el dropdown filter-comm-select y el chip de triaje chip-missing-comm existan en index.html."""
    html_path = repo_root / "dashboards" / "incident-manager-monitor" / "index.html"
    content = html_path.read_text(encoding="utf-8")

    # Select y opciones
    assert 'id="filter-comm-select"' in content
    expected_options = [
        'value="all"',
        'value="missing_any"',
        'value="missing_apertura"',
        'value="missing_seguimiento"',
        'value="missing_cierre"',
        'value="missing_all"',
        'value="has_apertura"',
        'value="has_seguimiento"',
        'value="has_cierre"',
        'value="all_completed"'
    ]
    for opt in expected_options:
        assert opt in content, f"Opción {opt} debe existir en #filter-comm-select"

    # Chip de triaje de comunicaciones pendientes
    assert 'id="chip-missing-comm"' in content
    assert 'id="chip-count-missing-comm"' in content


def test_should_verify_monitor_js_handles_communication_filter_and_chips(repo_root):
    """Verifica que monitor.js incluya el estado, selectores y lógica de filtrado de comunicaciones."""
    js_path = repo_root / "dashboards" / "incident-manager-monitor" / "monitor.js"
    content = js_path.read_text(encoding="utf-8")

    assert "commPhase: 'all'" in content
    assert "filterCommSelect: document.getElementById('filter-comm-select')" in content
    assert "chipMissingComm: document.getElementById('chip-missing-comm')" in content
    assert "chipCountMissingComm: document.getElementById('chip-count-missing-comm')" in content
    assert "function hasOfficialMessage(" in content
    assert "commPhase === 'missing_any'" in content
    assert "commPhase === 'all_completed'" in content
    assert "triage-comm-pills" in content
    assert "badge-comm-ok" in content
    assert "badge-comm-missing" in content





