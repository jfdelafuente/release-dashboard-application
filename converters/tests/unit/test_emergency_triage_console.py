"""
Tests unitarios para la Consola de Triaje y Reclasificación Automática (Módulo 1).
Valida las 3 funciones esenciales:
 1. Ingesta e Inspección Continua
 2. Evaluador de Umbrales Críticos
 3. Alertas de Reclasificación Inmediata
"""

import json
import re
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
CONSOLE_DIR = REPO_ROOT / "dashboards" / "emergency-triage-console"
NOTIFICATIONS_JSON_PATH = REPO_ROOT / "data" / "output" / "high_priority_notifications.json"


def test_emergency_triage_console_files_exist():
    """Valida que los archivos de la consola paralela existan."""
    assert CONSOLE_DIR.exists(), f"El directorio {CONSOLE_DIR} debe existir"
    assert (CONSOLE_DIR / "index.html").exists(), "index.html debe existir"
    assert (CONSOLE_DIR / "triage.css").exists(), "triage.css debe existir"
    assert (CONSOLE_DIR / "triage.js").exists(), "triage.js debe existir"


def test_index_html_contains_core_elements():
    """Valida que index.html contenga todos los elementos de las 3 funciones operativas."""
    html = (CONSOLE_DIR / "index.html").read_text(encoding="utf-8")

    # Título y badges
    assert "Consola de Triaje y Reclasificación Automática" in html
    assert "Módulo 1" in html

    # Función 1: Ingesta e Inspección Continua
    assert 'id="live-pill"' in html
    assert 'id="auto-refresh-select"' in html
    assert 'id="btn-refresh-now"' in html
    assert 'id="source-file-name"' in html
    assert 'id="last-scan-label"' in html
    assert 'id="kpi-scanned"' in html
    assert 'id="kpi-skipped"' in html
    assert 'id="kpi-active"' in html
    assert 'id="kpi-emergencies"' in html

    # Función 2: Evaluador de Umbrales Críticos
    assert 'id="filter-process"' in html
    assert 'id="filter-severity"' in html
    assert "Atención al Cliente (ATC)" in html
    assert "Facturación y Cobros" in html
    assert "Provisión y Cobertura" in html
    assert 'id="modal-criteria"' in html  # Cheat-sheet de umbrales oficiales
    assert 'id="btn-help-criteria"' in html
    assert "Criterios Oficiales" in html

    # Función 3: Alertas de Reclasificación Inmediata y Feed
    assert 'id="tab-reclass-only"' in html
    assert 'id="count-reclass"' in html
    assert 'id="triage-feed"' in html
    assert 'id="reclass-banner"' not in html  # Eliminado para dar más espacio vertical al dashboard

    # Accesibilidad
    assert 'id="sr-announcements"' in html
    assert 'role="status"' in html or 'aria-live="polite"' in html


def test_triage_css_contains_design_tokens():
    """Valida los tokens de estilo institucional y contraste de alertas."""
    css = (CONSOLE_DIR / "triage.css").read_text(encoding="utf-8")

    # Brand Colors
    assert "--triage-orange: #FF7900" in css
    assert "--triage-red-p1: #EF4444" in css
    assert "--triage-amber-p2: #F59E0B" in css

    # Classes for functions
    assert ".triage-reclass-alert-banner" in css
    assert ".triage-threshold-box" in css
    assert ".triage-btn-action-reclass" in css
    assert ".triage-kpi-grid" in css
    assert ".triage-sev-comparison-bar" in css


def test_triage_js_logic_and_contract():
    """Valida que triage.js implemente las funciones del Módulo 1 requeridas."""
    js = (CONSOLE_DIR / "triage.js").read_text(encoding="utf-8")

    # Función 1: Ingesta e inspección
    assert "performInspection" in js
    assert "processInspectionData" in js
    assert "updateRelativeTimeDisplay" in js
    assert "TERMINAL_STATUSES" in js
    assert "isTerminalStatus" in js

    # Función 2: Evaluador de umbrales
    assert "evaluacion.criterio" in js
    assert "evaluacion.impacto_justificacion" in js
    assert "metricas_cuantitativas" in js

    # Función 3: Alertas de reclasificación
    assert "buildFormalReclassificationText" in js
    assert "SOLICITUD URGENTE DE RECLASIFICACIÓN REMEDY" in js
    assert "es_discrepancia" in js
    assert "discrepancia_delta" in js
    assert "copyToClipboard" in js


def test_high_priority_notifications_dataset_compliance():
    """Valida que los datos de high_priority_notifications.json cumplan el contrato y generen reclasificaciones correctas."""
    assert NOTIFICATIONS_JSON_PATH.exists(), f"El archivo {NOTIFICATIONS_JSON_PATH} debe existir"

    with open(NOTIFICATIONS_JSON_PATH, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    # Validar metadata e inspección continua
    meta = catalog.get("_metadata", {})
    assert "kpis" in meta, "Debe contener KPIs de ingesta"
    kpis = meta["kpis"]
    assert kpis.get("total_scanned", 0) > 0
    assert kpis.get("total_high_priority", 0) > 0
    assert kpis.get("discrepancies_count", 0) > 0

    # Validar tickets
    incidents = catalog.get("data", [])
    assert len(incidents) > 0

    reclass_count = 0
    delta2_count = 0
    delta1_count = 0

    for inc in incidents:
        assert "id" in inc
        assert "titulo" in inc
        assert "evaluacion" in inc
        evaluacion = inc["evaluacion"]
        assert "proceso" in evaluacion or "proceso_negocio" in evaluacion
        assert "criterio" in evaluacion

        if inc.get("es_discrepancia"):
            reclass_count += 1
            delta = inc.get("discrepancia_delta", 0)
            if delta == 2:
                delta2_count += 1
            elif delta == 1:
                delta1_count += 1

            # Comprobar que podemos construir el texto formal de reclasificación
            titulo = inc.get("titulo", "")
            nominal = inc.get("prioridad_original", "")
            sugerida = inc.get("prioridad_sugerida", "")
            proceso = evaluacion.get("proceso") or evaluacion.get("proceso_negocio")
            umbral = evaluacion.get("criterio")

            reclass_text = f"""[SOLICITUD URGENTE DE RECLASIFICACIÓN REMEDY - CRITERIO PROCESO OPERATIVO GESTIÓN EMERGENCIAS IT ORANGE]
INCIDENCIA: {inc['id']}
TÍTULO: {titulo}
PRIORIDAD REMEDY ACTUAL: {nominal}
PRIORIDAD REQUERIDA: {sugerida} (SL1 / P1 - Emergencia Crítica)
PROCESO CRÍTICO AFECTADO: {proceso}
UMBRAL DE EMERGENCIA SUPERADO: {umbral}"""

            assert inc["id"] in reclass_text
            assert nominal in reclass_text
            assert sugerida in reclass_text

    assert reclass_count == kpis.get("discrepancies_count")
    assert delta2_count == kpis.get("discrepancias_delta2_mayor_count")
    assert delta1_count == kpis.get("discrepancias_delta1_moderada_count")


# ==============================================================================
# PRUEBAS UNITARIAS PARA EL MÓDULO 2: ORQUESTADOR DEL PROCESO OPERATIVO
# ==============================================================================

PAPS_JSON_PATH = REPO_ROOT / "data" / "scheduled_changes_pap.json"


def test_module_2_scheduled_changes_pap_dataset():
    """Valida la integridad del catálogo de Trabajos Programados (PaP) recientes para detección de Rollback."""
    assert PAPS_JSON_PATH.exists(), f"El archivo {PAPS_JSON_PATH} debe existir"

    with open(PAPS_JSON_PATH, "r", encoding="utf-8") as f:
        pap_data = json.load(f)

    meta = pap_data.get("_metadata", {})
    assert "total_changes" in meta
    assert meta["total_changes"] >= 5
    assert meta.get("filter_window_hours") == 6
    assert meta.get("is_mock") is True, "El catálogo sintético debe estar marcado con is_mock=True"
    assert meta.get("data_source_mode") == "SIMULATED_MOCK_DATA"
    assert "target_api_spec" in meta

    changes = pap_data.get("changes", [])
    assert len(changes) == meta["total_changes"]

    # Validar campos obligatorios de cada PaP para permitir la orden formal de Rollback
    for pap in changes:
        assert pap.get("crq", "").startswith("CRQ"), "Debe tener un código CRQ válido"
        assert len(pap.get("titulo", "")) > 0
        assert isinstance(pap.get("sistemas", []), list) and len(pap["sistemas"]) > 0
        assert len(pap.get("proceso_relacionado", "")) > 0
        assert len(pap.get("rollback_plan", "")) > 0, "Debe tener un plan de rollback documentado"
        assert len(pap.get("tiempo_rollback_estimado", "")) > 0
        assert len(pap.get("contacto_guardia", "")) > 0
        assert pap.get("is_mock") is True, "Cada registro simulado debe indicar is_mock=True"
        assert pap.get("data_source") == "SIMULATED_MOCK"
        assert "[MOCK" in pap.get("mock_tag", "")

    # Validar que existe al menos el cambio de CRM4TELCO y bffclientdashboard
    crqs = [p["crq"] for p in changes]
    assert "CRQ000000190422" in crqs
    assert "CRQ000000190311" in crqs


def test_module_2_index_html_orchestrator_elements():
    """Valida que index.html contenga todos los componentes del Módulo 2 (War Room, Relojes, PaP, Bitácora)."""
    html = (CONSOLE_DIR / "index.html").read_text(encoding="utf-8")

    # 1. Pestaña y contador del Orquestador
    assert 'id="tab-orchestrator"' in html
    assert 'id="count-orchestrator"' in html

    # 2. Modal Principal del Orquestador Operativo
    assert 'id="modal-orchestrator"' in html
    assert 'id="btn-orch-close"' in html
    assert 'id="orch-inc-id"' in html
    assert 'id="orch-im-name"' in html
    assert 'id="orch-sev-badge"' in html
    assert 'id="orch-global-aging-tag"' in html

    # 3. Cuatro Relojes de Escalado Controlados
    assert 'id="orch-clock-20m"' in html
    assert 'id="clock-20m-timer"' in html
    assert 'id="btn-action-20m"' in html

    assert 'id="orch-clock-45m"' in html
    assert 'id="clock-45m-timer"' in html
    assert 'id="btn-action-45m"' in html

    assert 'id="orch-clock-105m"' in html
    assert 'id="clock-105m-timer"' in html
    assert 'id="btn-action-105m"' in html

    assert 'id="orch-clock-120m"' in html
    assert 'id="clock-120m-timer"' in html
    assert 'id="btn-action-120m"' in html

    # 4. War Room & Microsoft Teams
    assert 'id="orch-warroom-state"' in html
    assert 'id="orch-teams-url-preview"' in html
    assert 'id="orch-btn-join-teams"' in html
    assert 'id="orch-btn-copy-teams"' in html

    # 5. Monitor PaP
    assert 'id="orch-pap-status-badge"' in html
    assert 'id="orch-pap-container"' in html

    # 6. Bitácora Interactiva (Live Incident Log)
    assert 'id="orch-timeline-container"' in html
    assert 'id="orch-log-form"' in html
    assert 'id="orch-log-role"' in html
    assert 'id="orch-log-text"' in html
    assert 'id="btn-copy-full-log"' in html
    assert 'id="btn-clear-log"' in html

    # 7. Modales de Orden de Rollback y Notificación Ejecutiva
    assert 'id="modal-rollback-order"' in html
    assert 'id="rollback-order-text"' in html
    assert 'id="btn-rollback-confirm-copy"' in html

    assert 'id="modal-executive-comm"' in html
    assert 'id="exec-comm-completo"' in html
    assert 'id="exec-comm-breve"' in html
    assert 'id="btn-copy-exec-completo"' in html


def test_module_2_triage_css_orchestrator_styles():
    """Valida las clases y reglas de estilo para los componentes del Módulo 2."""
    css = (CONSOLE_DIR / "triage.css").read_text(encoding="utf-8")

    # Diálogo modal y grid
    assert ".orch-modal-dialog" in css
    assert ".orch-clocks-grid" in css
    assert ".orch-clock-card" in css
    assert ".orch-clock-alarm-zone" in css
    assert ".orch-clock-alarm-zone.is-alarm" in css

    # War Room y Monitor PaP
    assert ".orch-war-room-box" in css
    assert ".orch-pap-box" in css
    assert ".orch-btn-rollback" in css

    # Bitácora
    assert ".orch-timeline-container" in css
    assert ".orch-timeline-entry" in css
    assert ".orch-log-form" in css

    # Botones de acción en tabla y footer
    assert ".triage-btn-table-orchestrator" in css
    assert ".triage-btn-action-orchestrator" in css


def test_module_2_triage_js_orchestrator_logic():
    """Valida la presencia y consistencia de las funciones operativas del Módulo 2 en triage.js."""
    js = (CONSOLE_DIR / "triage.js").read_text(encoding="utf-8")

    # Módulo 2 header y estado
    assert "MÓDULO 2: ORQUESTADOR DEL PROCESO OPERATIVO DE EMERGENCIAS" in js
    assert "Carlos Morales · Incident Manager de Guardia" in js
    assert "loadScheduledChangesPaP" in js
    assert "findMatchingPaP" in js

    # Teams War Room
    assert "generateTeamsWarRoomUrl" in js
    assert "teams.microsoft.com" in js
    assert "buildTeamsWarRoomCallText" in js

    # Bitácora
    assert "getOrInitLog" in js
    assert "saveLog" in js
    assert "addLogEntry" in js
    assert "renderTimelineEntries" in js
    assert "formatFullLogForClipboard" in js
    assert "getRoleMeta" in js

    # PaP y Rollback
    assert "renderPapSection" in js
    assert "openRollbackOrderModal" in js
    assert "ORDEN FORMAL DE ROLLBACK INMEDIATO" in js

    # Relojes y Escalados
    assert "startOrchestratorClocks" in js
    assert "updateOrchestratorClocks" in js
    assert "openExecutiveCommModal" in js
    assert "openEmergencyOrchestrator" in js
    assert "closeEmergencyOrchestrator" in js


def test_mock_data_flags_badges_and_api_spec():
    """Valida que los datos inventados estén explícitamente marcados y que exista la especificación de API REST."""
    # 1. Validar marcas en index.html
    html = (CONSOLE_DIR / "index.html").read_text(encoding="utf-8")
    assert "triage-mock-badge" in html
    assert "🧪 Mock On-Call · Pendiente API Guardias" in html
    assert "🧪 Mock Puente · Pendiente Graph API" in html
    assert "🧪 Mock Data · Pendiente API CMDB" in html
    assert "AVISO DE DATOS SIMULADOS (MOCK)" in html

    # 2. Validar estilos en triage.css
    css = (CONSOLE_DIR / "triage.css").read_text(encoding="utf-8")
    assert ".triage-mock-badge" in css
    assert ".triage-mock-banner" in css
    assert "#6B21A8" in css or "purple" in css or "#F3E8FF" in css

    # 3. Validar especificación de API REST
    api_spec_path = REPO_ROOT / "docs" / "api" / "remedy_cmdb_pap_spec.md"
    assert api_spec_path.exists(), f"El documento de API spec {api_spec_path} debe existir"

    spec_content = api_spec_path.read_text(encoding="utf-8")
    assert "/api/v1/cmdb/scheduled-changes" in spec_content
    assert "/api/v1/cmdb/scheduled-changes/{crq}/rollback-order" in spec_content
    assert "is_mock" in spec_content
    assert "BMC Remedy ITSM" in spec_content



