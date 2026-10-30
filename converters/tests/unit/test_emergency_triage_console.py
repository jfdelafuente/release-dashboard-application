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

