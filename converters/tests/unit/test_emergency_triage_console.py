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
    if not catalog.get("data"):
        pytest.skip("Workspace limpio: sin incidencias cargadas en high_priority_notifications.json")
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


def test_collapsible_footer_and_shortcuts():
    """Valida la implementación del footer plegable/desplegable, accesibilidad y atajos de teclado de consola."""
    html = (CONSOLE_DIR / "index.html").read_text(encoding="utf-8")
    css = (CONSOLE_DIR / "triage.css").read_text(encoding="utf-8")
    js = (CONSOLE_DIR / "triage.js").read_text(encoding="utf-8")

    # 1. Validación en index.html
    assert 'id="triage-footer"' in html
    assert 'id="triage-footer-header"' in html
    assert 'id="footer-btn-toggle"' in html
    assert 'id="triage-footer-expandable"' in html
    assert 'id="footer-btn-scroll-top"' in html
    assert "triage-footer-shortcuts-card" in html
    assert "<kbd>F</kbd>" in html
    assert "<kbd>Shift+H</kbd>" in html
    assert "<kbd>Shift+M</kbd>" in html
    assert "<kbd>Shift+U</kbd>" in html

    # 2. Validación de estilos en triage.css
    assert ".triage-footer" in css
    assert ".triage-footer.is-expanded" in css
    assert ".triage-footer-btn-toggle" in css
    assert ".triage-footer-expandable" in css
    assert ".triage-footer-shortcuts-card" in css

    # 3. Validación de lógica operativa en triage.js
    assert "initFooterCollapse" in js
    assert "toggleFooter" in js
    assert "setFooterExpanded" in js
    assert "triage_footer_expanded" in js
    assert "footerBtnToggle" in js
    assert "triageFooterExpandable" in js or "triage-footer-expandable" in js
    assert "Shift+H" in js or "shiftKey" in js


def test_enrichment_indicators_ia_and_executive_comms():
    """Valida la presencia y consistencia de las marcas discretas de Resumen IA y Mensajes Ejecutivos en la tabla de triaje."""
    css = (CONSOLE_DIR / "triage.css").read_text(encoding="utf-8")
    js = (CONSOLE_DIR / "triage.js").read_text(encoding="utf-8")

    # 1. Validación de clases y estilos CSS para marcas discretas
    assert ".triage-micro-marks" in css, "Debe existir contenedor .triage-micro-marks en triage.css"
    assert ".triage-micro-mark" in css, "Debe existir clase .triage-micro-mark en triage.css"
    assert ".triage-micro-mark.is-ia" in css, "Debe existir estilo para .triage-micro-mark.is-ia en triage.css"
    assert ".triage-micro-mark.is-comms" in css, "Debe existir estilo para .triage-micro-mark.is-comms en triage.css"
    assert "#F3E8FF" in css or "purple" in css, "Debe incluir color suave lavanda/índigo para Resumen IA"
    assert "#ECFDF5" in css or "green" in css, "Debe incluir color suave verde esmeralda para Comunicaciones Ejecutivas"

    # 2. Validación de lógica en triage.js
    assert "hasResumenIa" in js, "triage.js debe computar hasResumenIa para cada incidencia"
    assert "hasMensajesEjecutivos" in js, "triage.js debe computar hasMensajesEjecutivos para cada incidencia"
    assert "triage-micro-marks" in js, "triage.js debe renderizar el bloque triage-micro-marks en la celda de incidencia"
    assert "is-ia" in js, "triage.js debe aplicar clase is-ia en la marca de IA"
    assert "is-comms" in js, "triage.js debe aplicar clase is-comms en la marca de comunicaciones"
    assert "btn-open-exec-comm" in js, "triage.js debe soportar botón interactivo para abrir comunicaciones ejecutivas"
    assert "triage-detail-enrichment-bar" in js, "triage.js debe mostrar el estado de redacción oficial en el detalle expandido"

    # 3. Validación contra el dataset real de notificaciones
    with open(NOTIFICATIONS_JSON_PATH, "r", encoding="utf-8") as f:
        notif_data = json.load(f)

    incidents = notif_data.get("data", [])
    if not incidents:
        pytest.skip("Workspace limpio: sin incidencias cargadas en high_priority_notifications.json")
    inc_with_both = 0
    inc_with_neither = 0

    for inc in incidents:
        res = inc.get("resumen_ia") or {}
        has_ia = bool(res.get("problema") or res.get("impacto") or res.get("solucion") or res.get("causa_raiz"))
        
        msgs = inc.get("mensajes_ejecutivos") or {}
        has_exec = False
        for phase in ("apertura", "seguimiento", "cierre"):
            p = msgs.get(phase) or {}
            if (p.get("completo") or p.get("generado_por_agente")) and p.get("estado") != "pendiente":
                has_exec = True
                break

        if has_ia and has_exec:
            inc_with_both += 1
        elif not has_ia and not has_exec:
            inc_with_neither += 1

    assert inc_with_both >= 15, "La mayoría de las incidencias activas deben tener Resumen IA y Comms completos"


def test_ingestion_audit_console_and_shortcuts():
    """Valida la presencia del modal de auditoría de carga, atajo Shift+I y endpoints correspondientes."""
    html = (CONSOLE_DIR / "index.html").read_text(encoding="utf-8")
    css = (CONSOLE_DIR / "triage.css").read_text(encoding="utf-8")
    js = (CONSOLE_DIR / "triage.js").read_text(encoding="utf-8")

    # 1. Validación en index.html
    assert 'id="modal-ingestion-audit"' in html, "Debe existir modal-ingestion-audit en index.html"
    assert "<kbd>Shift+I</kbd>" in html, "Debe existir atajo Shift+I en la tarjeta de atajos de consola"
    assert "btn-audit-force-all" in html, "Debe existir botón para forzar refresco general de IA"
    assert "btn-audit-retry-missing" in html, "Debe existir botón para reintentar incidencias sin IA"
    assert "audit-tickets-tbody" in html, "Debe existir tabla de incidencias de auditoría"
    assert "audit-log-terminal" in html, "Debe existir visor de terminal de logs"

    # 2. Validación de estilos en triage.css
    assert ".audit-modal-dialog" in css, "Debe existir clase .audit-modal-dialog en triage.css"
    assert ".audit-actions-toolbar" in css, "Debe existir barra de acciones en triage.css"
    assert ".audit-kpis-grid" in css, "Debe existir grid de KPIs de auditoría en triage.css"
    assert ".audit-log-terminal" in css, "Debe existir estilo para el terminal de log en triage.css"

    # 3. Validación en triage.js
    assert "openIngestionAuditModal" in js, "Debe existir función openIngestionAuditModal en triage.js"
    assert "closeIngestionAuditModal" in js, "Debe existir función closeIngestionAuditModal en triage.js"
    assert "triggerEpsilonRetry" in js, "Debe existir función triggerEpsilonRetry en triage.js"
    assert "Shift+I" in js or "key === 'I'" in js or "key === 'i'" in js, "Debe interceptar tecla I con Shift"
    assert "/api/ingestion/retry-ia" in js, "Debe llamar al endpoint de relanzamiento de IA"

    # 4. Validación de serve_app.py
    serve_py = (CONSOLE_DIR.parent.parent / "serve_app.py").read_text(encoding="utf-8")
    assert "/api/ingestion/retry-ia" in serve_py, "serve_app.py debe soportar /api/ingestion/retry-ia"
    assert "handle_ingestion_retry_ia" in serve_py, "serve_app.py debe implementar handle_ingestion_retry_ia"
    assert "/api/logs/ingestion" in serve_py, "serve_app.py debe soportar /api/logs/ingestion"
    assert "handle_ingestion_logs" in serve_py, "serve_app.py debe implementar handle_ingestion_logs"

    # 5. Validación de resiliencia y fallback estático ante servidores no reiniciados
    assert "ingestion_audit_summary.json" in js, "triage.js debe tener fallback a ingestion_audit_summary.json"
    assert "is-warning" in css, "triage.css debe contemplar estado is-warning para avisos no bloqueantes"


def test_triage_table_6_columns_layout_and_date_sorting():
    """Valida la reestructuración de la tabla a 6 columnas funcionales y la ordenación cronológica por Fecha de Apertura."""
    css = (CONSOLE_DIR / "triage.css").read_text(encoding="utf-8")
    js = (CONSOLE_DIR / "triage.js").read_text(encoding="utf-8")

    # 1. Validación de cabecera de 6 columnas
    assert "Incidencia / Apertura" in js, "Columna 1: Incidencia, Fecha Apertura y tiempo activa"
    assert "Título / Resumen IA / Mensajes" in js, "Columna 2: Título e iconos de Resumen IA y Mensajes"
    assert "Proceso Crítico y Sistemas" in js, "Columna 3: Proceso Crítico y Sistemas"
    assert "Remedy INI" in js, "Columna 4: Remedy INI"
    assert "Severidad ITIL" in js, "Columna 5: Severidad ITIL"
    assert "Acciones" in js, "Columna 6: Acciones"

    # 2. Validación de fila expandible ajustada a 6 columnas
    assert 'colspan="6"' in js, "La fila de detalle plegable debe tener colspan=6"

    # 3. Validación de función de parseo y ordenación por fecha de apertura descendente
    assert "parseIncidentEpoch" in js, "Debe existir parseIncidentEpoch para convertir fecha_apertura"
    assert "formatFechaApertura" in js, "Debe existir formatFechaApertura para formatear la fecha mostrada"
    assert "epochB - epochA" in js, "getFilteredIncidents debe ordenar de más reciente a más antigua (descendente)"

    # 4. Validación de clases CSS para la nueva distribución
    assert ".triage-cell-incident" in css
    assert ".triage-datetime-row" in css
    assert ".triage-date-label" in css
    assert ".triage-aging-badge" in css
    assert ".triage-cell-title-comms" in css
    assert ".triage-title-indicators" in css
    assert ".triage-cell-process-systems" in css
    assert ".triage-cell-remedy" in css
    assert ".triage-cell-itil" in css
    assert ".triage-itil-delta-sub" in css



def test_orchestrator_sections_folded_by_default_phase1():
    """Valida que las secciones de Bitácora, WarRoom y Monitor de Trabajos estén plegadas por defecto en el Módulo 2."""
    html = (CONSOLE_DIR / "index.html").read_text(encoding="utf-8")
    css = (CONSOLE_DIR / "triage.css").read_text(encoding="utf-8")
    js = (CONSOLE_DIR / "triage.js").read_text(encoding="utf-8")

    # 1. Validación en index.html: existencia de clases is-collapsed y botones de conmutación
    assert 'id="orch-war-room-section" class="orch-card-box orch-war-room-box is-collapsed"' in html or (
        'id="orch-war-room-section"' in html and 'orch-war-room-box is-collapsed' in html
    )
    assert 'id="orch-pap-section"' in html and 'orch-pap-box is-collapsed' in html
    assert 'id="orch-log-section"' in html and 'orch-log-section is-collapsed' in html

    # Cabeceras interactivas y botones de toggle
    assert 'id="orch-war-room-header"' in html
    assert 'id="btn-toggle-war-room"' in html
    assert 'id="orch-pap-header"' in html
    assert 'id="btn-toggle-pap"' in html
    assert 'id="orch-log-header"' in html
    assert 'id="btn-toggle-log"' in html
    assert 'class="orch-log-body"' in html

    # Atributos de accesibilidad iniciales (plegado = aria-expanded="false")
    assert 'aria-expanded="false"' in html

    # 2. Validación en triage.css: estilos de colapso, rotación del chevron y ocultación de contenido
    assert ".orch-box-collapsible-header" in css
    assert ".orch-box-toggle-btn" in css
    assert ".orch-box-chevron" in css
    assert ".orch-card-box.is-collapsed" in css
    assert ".orch-card-box.is-collapsed .orch-warroom-content" in css
    assert ".orch-card-box.is-collapsed .orch-pap-content" in css
    assert ".orch-card-box.is-collapsed .orch-log-body" in css
    assert "transform: rotate(-90deg)" in css

    # 3. Validación en triage.js: métodos de gestión y restablecimiento a plegado por defecto
    assert "initOrchestratorCollapsibleSections" in js
    assert "setOrchSectionCollapsed" in js
    assert "toggleOrchSection" in js
    assert "setOrchSectionCollapsed('warroom', true)" in js
    assert "setOrchSectionCollapsed('pap', true)" in js
    assert "setOrchSectionCollapsed('log', true)" in js


def test_topbar_and_portal_navigation_integration():
    """Valida que la Consola de Triaje esté integrada en la barra superior unificada y en el panel general del portal."""
    topbar_js = (REPO_ROOT / "dashboards" / "assets" / "topbar.js").read_text(encoding="utf-8")
    portal_html = (REPO_ROOT / "dashboards" / "portal" / "index.html").read_text(encoding="utf-8")
    triage_html = (CONSOLE_DIR / "index.html").read_text(encoding="utf-8")

    # 1. Validación en topbar.js: Consola de Triaje presente y Agentes IA reemplazado
    assert "emergency-triage" in topbar_js
    assert "Consola de Triaje" in topbar_js
    assert "/dashboards/emergency-triage-console/" in topbar_js
    assert "agents-catalog" not in topbar_js

    # 2. Validación en portal/index.html: Card 4 enlazada a la Consola de Triaje
    assert 'href="/dashboards/emergency-triage-console/"' in portal_html
    assert "Consola de Triaje" in portal_html
    assert "tag-emergency" in portal_html
    assert 'href="/dashboards/agents-catalog/"' in portal_html
    assert "Biblioteca de Agentes IA y Automatización" in portal_html

    # 3. Validación de data-active en emergency-triage-console/index.html para sincronía con topbar.js
    assert 'id="mo-topbar-root" data-active="emergency-triage"' in triage_html
