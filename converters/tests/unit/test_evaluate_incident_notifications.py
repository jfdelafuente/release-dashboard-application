"""Unit tests for High Priority Incident Notifications Evaluator.

Follows Constitution Testing Standards:
- Descriptive names: `should_[action]_when_[condition]`
- Tests edge cases, fallback modes, and ITIL matrix rules.
"""

from datetime import datetime, timedelta
import json
from unittest.mock import MagicMock, patch
import pytest

from converters.cli.evaluate_incident_notifications import (
    SeverityEvaluator,
    EpsilonClient,
    ExecutiveMessageGenerator,
    evaluate_incidents_batch,
    detect_priority_discrepancy,
    compute_discrepancy_details,
    is_phrase_negated,
    extract_quantitative_metrics,
    normalize_priority,
    parse_incident_datetime,
    compute_emergency_sla_status,
    format_operational_duration,
)


@pytest.fixture
def sample_ticket_p3_nominal():
    """A ticket registered nominally as 'Media' / P3 in the original CSV."""
    return {
        "ID de incidencia": "INC000003884945",
        "Prioridad": "Media",
        "Descripción": "CAIDA GLOBAL DE FIBRA CLIENTES EMPRESAS // CORTE TOTAL",
        "Estatus": "Asignado",
        "Fecha de envío": "14/10/2026 10:00",
        "Grupo asignado": "SOPORTE FIBRA RED",
        "Urgencia": "Alta",
        "Impacto": "Masiva",
        "Grupo Resolutor": "SOPORTE FIBRA RED"
    }


@pytest.fixture
def sample_ticket_p4_minor():
    """A ticket registered nominally as 'Baja' / P4 with minor impact."""
    return {
        "ID de incidencia": "INC000003999999",
        "Prioridad": "Baja",
        "Descripción": "Error tipográfico en portal auto-consulta",
        "Estatus": "Cerrado",
        "Fecha de envío": "14/10/2026 12:00",
        "Grupo asignado": "WEB DEV",
        "Urgencia": "Baja",
        "Impacto": "Bajo",
        "Grupo Resolutor": "WEB DEV"
    }


@pytest.fixture
def sample_epsilon_critical_response():
    """Epsilon AI summary describing a total service outage with high impact."""
    return {
        "codigo": "INC000003884945",
        "titulo": "CAIDA GLOBAL DE FIBRA CLIENTES EMPRESAS // CORTE TOTAL",
        "estadoActual": "En curso",
        "sistemas": ["RED FTTH", "ROUTING CORE"],
        "problema": "Corte total en concentrador de fibra afectando a clientes empresariales.",
        "impacto": "Caída total del servicio sin alternativa viable, afectando a más del 50% de sedes corporativas.",
        "solucion": "Sustitución de tarjeta óptica averiada en nodo central.",
        "siguienteAccion": "Reinicio y convergencia de enlaces de fibra.",
        "bloqueos": ["Esperando acceso a sala técnica del nodo central"],
        "hitosTecnicos": ["10:00: Alarma detectada", "10:30: Técnico desplazado"]
    }


@pytest.fixture
def sample_epsilon_minor_response():
    """Epsilon AI summary describing an isolated cosmetic issue."""
    return {
        "codigo": "INC000003999999",
        "titulo": "Error tipográfico en portal auto-consulta",
        "estadoActual": "Cerrado",
        "sistemas": ["PORTAL WEB"],
        "problema": "Falta una tilde en la sección de preguntas frecuentes.",
        "impacto": "Problema cosmético sin afectación al servicio.",
        "solucion": "Corrección de texto en plantilla HTML.",
        "siguienteAccion": "Despliegue en ventana ordinaria.",
        "bloqueos": [],
        "hitosTecnicos": ["12:00: Solicitud recibida", "12:10: Corregido"]
    }


# ============================================================================
# Phase 3: User Story 1 (P1) Tests - Inferencia ITIL y Clasificación
# ============================================================================

def test_should_classify_p1_critical_when_high_impact_and_high_urgency(sample_ticket_p3_nominal, sample_epsilon_critical_response):
    evaluator = SeverityEvaluator()
    result = evaluator.evaluate(sample_ticket_p3_nominal, sample_epsilon_critical_response)

    assert result["prioridad_sugerida"] == "P1"
    assert result["es_alta_prioridad"] is True
    assert result["evaluacion"]["impacto"] == "Alto"
    assert result["evaluacion"]["urgencia"] == "Alta"
    assert result["evaluacion"]["sla_objetivo_minutos"] == 15


def test_should_classify_p2_high_when_high_impact_and_medium_urgency():
    evaluator = SeverityEvaluator()
    ticket = {
        "ID de incidencia": "INC000003884946",
        "Prioridad": "Media",
        "Descripción": "Degradación en enlaces secundarios",
        "Estatus": "Asignado",
        "Urgencia": "Media",
        "Impacto": "Alto"
    }
    epsilon_data = {
        "problema": "Degradación severa en enlaces secundarios.",
        "impacto": "Degradación en 30% del tráfico pero tráfico principal cursando.",
        "solucion": "",
        "siguienteAccion": "Reenrutar tráfico."
    }
    result = evaluator.evaluate(ticket, epsilon_data)

    assert result["prioridad_sugerida"] == "P2"
    assert result["es_alta_prioridad"] is True
    assert result["evaluacion"]["impacto"] in ["Alto", "Medio"]


def test_should_classify_p3_medium_when_low_impact_and_workaround_exists():
    evaluator = SeverityEvaluator()
    ticket = {
        "ID de incidencia": "INC000003884947",
        "Prioridad": "Media",
        "Descripción": "Incidencia menor con workaround",
        "Estatus": "En curso",
        "Urgencia": "Media",
        "Impacto": "Bajo"
    }
    epsilon_data = {
        "problema": "Retraso en generación de informe mensual.",
        "impacto": "Afecta a usuarios internos; se dispone de export alternativo.",
        "solucion": "Recalcular vista.",
        "siguienteAccion": "Validar datos."
    }
    result = evaluator.evaluate(ticket, epsilon_data)

    assert result["prioridad_sugerida"] in ["P3", "P4"]
    assert result["es_alta_prioridad"] is False


def test_should_classify_p4_low_when_low_impact_and_low_urgency(sample_ticket_p4_minor, sample_epsilon_minor_response):
    evaluator = SeverityEvaluator()
    result = evaluator.evaluate(sample_ticket_p4_minor, sample_epsilon_minor_response)

    assert result["prioridad_sugerida"] == "P4"
    assert result["es_alta_prioridad"] is False
    assert result["evaluacion"]["urgencia"] == "Baja"


def test_should_fallback_to_ticket_metadata_when_epsilon_unreachable(sample_ticket_p3_nominal):
    evaluator = SeverityEvaluator()
    # When Epsilon returns None (offline / timeout)
    result = evaluator.evaluate(sample_ticket_p3_nominal, epsilon_data=None)

    assert result["prioridad_sugerida"] in ["P1", "P2", "P3"]
    assert "evaluacion" in result
    assert result["evaluacion"]["impacto"] is not None
    assert result["evaluacion"]["urgencia"] is not None


# ============================================================================
# Phase 4: User Story 2 (P2) Tests - Mensajes Ejecutivos (incident-reporter)
# ============================================================================

def test_should_generate_single_paragraph_under_90_words_when_full_message_requested(sample_ticket_p3_nominal, sample_epsilon_critical_response):
    evaluator = SeverityEvaluator()
    eval_result = evaluator.evaluate(sample_ticket_p3_nominal, sample_epsilon_critical_response)
    
    generator = ExecutiveMessageGenerator()
    messages = generator.generate(sample_ticket_p3_nominal, eval_result, sample_epsilon_critical_response)

    for phase in ["apertura", "seguimiento", "cierre"]:
        msg = messages[phase]
        full_text = msg["completo"]
        # Debe ser un único párrafo (sin saltos de línea dobles)
        assert "\n\n" not in full_text
        # Máximo 90 palabras
        words = full_text.split()
        assert len(words) <= 90
        assert msg["conteo_palabras_completo"] == len(words)


def test_should_generate_brief_message_under_30_words_when_brief_requested(sample_ticket_p3_nominal, sample_epsilon_critical_response):
    evaluator = SeverityEvaluator()
    eval_result = evaluator.evaluate(sample_ticket_p3_nominal, sample_epsilon_critical_response)
    
    generator = ExecutiveMessageGenerator()
    messages = generator.generate(sample_ticket_p3_nominal, eval_result, sample_epsilon_critical_response)

    for phase in ["apertura", "seguimiento", "cierre"]:
        msg = messages[phase]
        brief_text = msg["breve"]
        # Máximo 30 palabras
        words = brief_text.split()
        assert len(words) <= 30
        assert msg["conteo_palabras_breve"] == len(words)


def test_should_include_apertura_seguimiento_and_cierre_phases(sample_ticket_p3_nominal, sample_epsilon_critical_response):
    evaluator = SeverityEvaluator()
    eval_result = evaluator.evaluate(sample_ticket_p3_nominal, sample_epsilon_critical_response)
    
    generator = ExecutiveMessageGenerator()
    messages = generator.generate(sample_ticket_p3_nominal, eval_result, sample_epsilon_critical_response)

    assert "apertura" in messages
    assert "seguimiento" in messages
    assert "cierre" in messages


def test_should_synthesize_raw_ticket_title_into_clean_executive_phrasing():
    desc, scope, short = ExecutiveMessageGenerator.synthesize_ticket_title("ALTAIR // LA FINCA // ERROR FUNCIONAL")
    assert "ALTAIR" in scope
    assert "La Finca" in scope
    assert "error funcional" in desc
    assert "//" not in desc

    desc2, scope2, short2 = ExecutiveMessageGenerator.synthesize_ticket_title("Siebel 8 | Error funcional | OEST - Oviedo")
    assert "Siebel 8" in scope2
    assert "OEST - Oviedo" in scope2
    assert "|" not in desc2


def test_should_generate_incident_reporter_conforming_messages_without_epsilon(sample_ticket_p3_nominal):
    evaluator = SeverityEvaluator()
    eval_result = evaluator.evaluate(sample_ticket_p3_nominal, epsilon_data=None)

    generator = ExecutiveMessageGenerator()
    messages = generator.generate(sample_ticket_p3_nominal, eval_result, resumen_ia=None)

    for phase in ["apertura", "seguimiento", "cierre"]:
        msg = messages[phase]
        comp = msg["completo"]
        brev = msg["breve"]
        # Monopárrafo sin saltos
        assert "\n" not in comp
        assert "\n" not in brev
        # Límites estrictos de incident-reporter
        assert len(comp.split()) <= 90
        assert len(brev.split()) <= 30
        assert msg["conteo_palabras_completo"] == len(comp.split())
        assert msg["conteo_palabras_breve"] == len(brev.split())
        # Sin delimitadores crudos
        assert "//" not in comp
        assert "//" not in brev


# ============================================================================
# Phase 5: User Story 3 (P3) Tests - Discrepancias de Prioridad
# ============================================================================

def test_should_flag_discrepancy_when_ticket_is_p3_but_calculated_is_p1():
    is_disc = detect_priority_discrepancy(original_priority="Media", calculated_priority="P1")
    assert is_disc is True

    is_disc_p2 = detect_priority_discrepancy(original_priority="Baja", calculated_priority="P2")
    assert is_disc_p2 is True


def test_should_not_flag_discrepancy_when_ticket_matches_calculated():
    is_disc = detect_priority_discrepancy(original_priority="Crítica", calculated_priority="P1")
    assert is_disc is False

    is_disc_p3 = detect_priority_discrepancy(original_priority="Media", calculated_priority="P3")
    assert is_disc_p3 is False


# ============================================================================
# Batch & Catalog Generation Tests
# ============================================================================

def test_should_generate_valid_catalog_schema_when_batch_processed(sample_ticket_p3_nominal, sample_ticket_p4_minor, sample_epsilon_critical_response):
    client_mock = MagicMock()
    client_mock.get_resumen_ia.side_effect = lambda code: (
        sample_epsilon_critical_response if code == sample_ticket_p3_nominal["ID de incidencia"] else None
    )

    tickets = [sample_ticket_p3_nominal, sample_ticket_p4_minor]
    catalog = evaluate_incidents_batch(tickets, epsilon_client=client_mock)

    assert "_metadata" in catalog
    assert "data" in catalog
    assert catalog["_metadata"]["type"] == "high_priority_notifications"
    assert catalog["_metadata"]["kpis"]["total_scanned"] == 2
    assert catalog["_metadata"]["kpis"]["total_high_priority"] >= 1
    assert catalog["_metadata"]["kpis"]["discrepancies_count"] >= 1

    high_priority_items = catalog["data"]
    assert len(high_priority_items) >= 1
    p1_item = high_priority_items[0]
    assert p1_item["id"] == sample_ticket_p3_nominal["ID de incidencia"]
    assert p1_item["prioridad_sugerida"] == "P1"
    assert p1_item["es_discrepancia"] is True
    assert "mensajes_ejecutivos" in p1_item


def test_should_skip_terminal_status_incidents_when_evaluating_batch():
    """Incidents with Cerrado, Resuelto or Cancelado status must not be notified."""
    client_mock = MagicMock()
    client_mock.get_resumen_ia.return_value = None
    tickets = [
        {"ID de incidencia": "INC001", "Prioridad": "Alta", "Impacto": "Masiva", "Urgencia": "Alta", "Estatus": "Cerrado"},
        {"ID de incidencia": "INC002", "Prioridad": "Alta", "Impacto": "Masiva", "Urgencia": "Alta", "Estatus": "Resuelto"},
        {"ID de incidencia": "INC003", "Prioridad": "Alta", "Impacto": "Masiva", "Urgencia": "Alta", "Estatus": "Cancelado"},
        {"ID de incidencia": "INC004", "Prioridad": "Alta", "Impacto": "Masiva", "Urgencia": "Alta", "Estatus": "Pendiente", "Descripción": "Corte de red"},
        {"ID de incidencia": "INC005", "Prioridad": "Alta", "Impacto": "Masiva", "Urgencia": "Alta", "Estatus": "Asignado", "Descripción": "Caída de servicio"},
    ]

    catalog = evaluate_incidents_batch(tickets, epsilon_client=client_mock)

    assert catalog["_metadata"]["kpis"]["total_scanned"] == 5
    assert catalog["_metadata"]["kpis"]["terminal_skipped_count"] == 3
    assert catalog["_metadata"]["kpis"]["active_evaluated_count"] == 2
    # Only active tickets (INC004, INC005) are included
    item_ids = [item["id"] for item in catalog["data"]]
    assert item_ids == ["INC004", "INC005"]
    # Epsilon should only have been called for active tickets
    assert client_mock.get_resumen_ia.call_count == 2


# ============================================================================
# Cache, CLI & Resolution Tests (Constitution Principle II: >= 80% Coverage)
# ============================================================================

def test_should_load_cached_data_when_cache_file_exists(tmp_path):
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    code = "INC000123"
    fake_data = {"codigo": code, "problema": "Cached problem"}
    (cache_dir / f"{code}.json").write_text(json.dumps(fake_data), encoding="utf-8")

    client = EpsilonClient(cache_dir=cache_dir)
    res = client.get_resumen_ia(code)

    assert res == fake_data


def test_should_save_cache_when_epsilon_responds_ok(tmp_path):
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    code = "INC000456"
    fake_response = {"data": {"codigo": code, "problema": "Network problem"}}

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = json.dumps(fake_response).encode("utf-8")

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        client = EpsilonClient(cache_dir=cache_dir)
        res = client.get_resumen_ia(code)

        assert res["codigo"] == code
        # Cache file should be saved
        saved = json.loads((cache_dir / f"{code}.json").read_text(encoding="utf-8"))
        assert saved["codigo"] == code


def test_should_set_server_offline_after_consecutive_failures(tmp_path):
    cache_dir = tmp_path / "cache"
    client = EpsilonClient(cache_dir=cache_dir)

    with patch("urllib.request.urlopen", side_effect=OSError("Network down")):
        for i in range(3):
            client.get_resumen_ia(f"INC000{i}")

        assert client._server_offline is True
        # Once offline, next call should return None immediately
        assert client.get_resumen_ia("INC999") is None


def test_should_resolve_default_input_file_from_index_json(tmp_path):
    from converters.cli.evaluate_incident_notifications import resolve_default_input_file
    
    data_dir = tmp_path / "data" / "output"
    data_dir.mkdir(parents=True)
    target_massive = data_dir / "target-massive.json"
    target_massive.write_text(json.dumps({"data": []}), encoding="utf-8")

    index_file = data_dir / "index.json"
    index_file.write_text(json.dumps({
        "massive": {
            "files": [{"path": "data/output/target-massive.json"}]
        }
    }), encoding="utf-8")

    resolved = resolve_default_input_file(tmp_path)
    assert resolved == target_massive


def test_should_run_main_dry_run_successfully(tmp_path, monkeypatch):
    from converters.cli.evaluate_incident_notifications import main

    test_input = tmp_path / "massive.json"
    test_input.write_text(json.dumps({
        "data": [{
            "ID de incidencia": "INC001",
            "Prioridad": "Media",
            "Descripción": "Test description",
            "Estatus": "Asignado"
        }]
    }), encoding="utf-8")

    monkeypatch.setattr("sys.argv", [
        "evaluate_incident_notifications.py",
        "--input", str(test_input),
        "--dry-run"
    ])

    exit_code = main()
    assert exit_code == 0


def test_should_generate_agent_prompt_with_epsilon_context():
    ticket = {
        "ID de incidencia": "INC000004103003",
        "Descripción": "Afectación masiva servicios de fibra",
        "Grupo asignado": "Sistemas Core"
    }
    evaluation = {
        "prioridad_sugerida": "P1",
        "evaluacion": {
            "impacto": "Crítico",
            "urgencia": "Alta"
        }
    }
    resumen_ia = {
        "problema": "Corte en enlace troncal de fibra óptica de la zona Este",
        "impacto": "45.000 clientes residenciales sin servicio de banda ancha",
        "solucion": "Despliegue de equipo de planta externa para empalme y sustitución de tramo",
        "siguienteAccion": "Fusión del cable principal y pruebas de reflectometría",
        "sistemas": ["FTTH", "Red Transporte"],
        "bloqueos": ["Acceso restringido a cámara subterránea por inundación"],
        "estadoActual": "En curso de resolución"
    }

    generator = ExecutiveMessageGenerator()
    messages = generator.generate(ticket, evaluation, resumen_ia)

    assert "apertura" in messages
    assert "prompt_agente" in messages["apertura"]
    prompt = messages["apertura"]["prompt_agente"]

    assert "incident-reporter" in prompt
    assert "INC000004103003" in prompt
    assert "Contexto extraído de Epsilon Resumen IA" in prompt
    assert "Corte en enlace troncal" in prompt
    assert "45.000 clientes" in prompt
    assert "Despliegue de equipo de planta externa" in prompt
    assert "Fusión del cable principal" in prompt
    assert "Acceso restringido a cámara" in prompt
    assert "90 palabras" in prompt
    assert "30 palabras" in prompt


def test_should_mark_pending_when_ticket_has_no_agent_messages_and_not_use_via_a():
    ticket = {
        "ID de incidencia": "INC_TOTALMENTE_NUEVA_999",
        "Descripción": "ERROR EN PASARELA NUEVA",
        "Impacto": "Alto",
        "Urgencia": "Alta"
    }
    evaluation = {"prioridad_sugerida": "P1", "es_alta_prioridad": True, "evaluacion": {}}
    generator = ExecutiveMessageGenerator()
    messages = generator.generate(ticket, evaluation, resumen_ia=None)

    for phase in ["apertura", "seguimiento", "cierre"]:
        msg = messages[phase]
        assert msg["generado_por_agente"] is False
        assert msg["estado"] == "pendiente"
        assert msg["completo"] is None
        assert msg["breve"] is None
        # Vía A descartada: No genera textos de plantilla falsa
        assert "Se ha declarado la apertura" not in str(msg["completo"])
        # El prompt estructurado debe estar listo para ejecutarse
        assert "prompt_agente" in msg
        assert "INC_TOTALMENTE_NUEVA_999" in msg["prompt_agente"]


def test_should_load_official_agent_messages_for_active_high_priority_incidents():
    generator = ExecutiveMessageGenerator()
    ticket_siebel = {
        "ID de incidencia": "INC000004159463",
        "Descripción": "Teide | Error funcional | Bosch - Vigo"
    }
    eval_p1 = {"prioridad_sugerida": "P1", "es_alta_prioridad": True, "evaluacion": {}}
    messages = generator.generate(ticket_siebel, eval_p1, resumen_ia=None)

    for phase in ["apertura", "seguimiento", "cierre"]:
        msg = messages[phase]
        assert msg["generado_por_agente"] is True
        assert msg["completo"] is not None
        assert msg["breve"] is not None
        assert len(msg["completo"].split()) <= 90
        assert len(msg["breve"].split()) <= 30
        assert "\n\n" not in msg["completo"]
        # Verifica contenido del agente para INC000004159463
        if phase == "apertura":
            assert "Siebel 8" in msg["completo"]
            assert "Bosch-Vigo" in msg["completo"]


def test_should_include_process_and_criterion_in_evaluation():
    evaluator = SeverityEvaluator()
    ticket_atc = {
        "ID de incidencia": "INC000004156790",
        "Descripción": "Ficha Cliente Orange | Error funcional | Madison - Valladolid",
        "Prioridad": "Media",
        "Impacto": "Masiva",
        "Urgencia": "Medio",
        "Grupo asignado": "DES_SOE_FICHA"
    }
    result = evaluator.evaluate(ticket_atc, epsilon_data=None)
    eval_block = result["evaluacion"]
    assert "proceso" in eval_block
    assert "criterio" in eval_block
    assert eval_block["proceso"] in ("Atención al Cliente (ATC)", "Ventas")
    assert len(eval_block["criterio"]) > 0


def test_should_classify_critical_processes_correctly():
    evaluator = SeverityEvaluator()
    
    # Facturación
    t_fact = {"Descripción": "BSCS Online tarificación batch con error", "Grupo asignado": "SOP_SMC_BSCS_ONLINE"}
    assert evaluator._classify_process(t_fact, None) == "Facturación y Cobros"
    
    # Prepago
    t_prepago = {"Descripción": "Fallo en recargas prepago canal web", "Grupo asignado": "PREPAGO_OPS"}
    assert evaluator._classify_process(t_prepago, None) == "Prepago"
    
    # Portabilidad
    t_porta = {"Descripción": "Retraso en portabilidad entidad de referencia", "Grupo asignado": "PORTA_CORE"}
    assert evaluator._classify_process(t_porta, None) == "Portabilidad"
    
    # Ventas
    t_ventas = {"Descripción": "Comprobantes de venta no descargan en televenta", "Grupo asignado": "NEG_CAMP_CERES"}
    assert evaluator._classify_process(t_ventas, None) == "Ventas"
    
    # Provisión
    t_prov = {"Descripción": "Siebel 8 órdenes de móvil en error", "Grupo asignado": "SOP_SMC_TEIDE"}
    assert evaluator._classify_process(t_prov, None) == "Provisión"
    
    # O&M
    t_om = {"Descripción": "ALTAIR test cortes CPE con caída", "Grupo asignado": "GNOC CAU"}
    assert evaluator._classify_process(t_om, None) == "Operación y Monitorización (O&M)"


def test_should_include_process_and_criterion_in_agent_prompt():
    generator = ExecutiveMessageGenerator()
    ticket = {
        "ID de incidencia": "INC000004156790",
        "Descripción": "Ficha Cliente Orange | Madison",
        "Grupo asignado": "DES_SOE_FICHA"
    }
    eval_block = {
        "prioridad_sugerida": "P1",
        "evaluacion": {
            "proceso": "Atención al Cliente (ATC)",
            "criterio": "ATC: Frontales/CRM (>20% desviación en 30m) o Regla de Oro N1"
        }
    }
    prompt = generator.generate_agent_prompt(ticket, eval_block, resumen_ia=None, phase="apertura")
    assert "Proceso de Negocio: Atención al Cliente (ATC)" in prompt
    assert "Criterio / Umbral: ATC: Frontales/CRM" in prompt


# ============================================================================
# Phase 6: Orange IT Emergency Management Tests (orange-it-emergency-management)
# ============================================================================

def test_should_parse_remedy_incident_datetime_formats():
    # Remedy export con indicador 'a'
    dt1 = parse_incident_datetime("14/10/2026 13:26 a")
    assert dt1 == datetime(2026, 10, 14, 13, 26)

    # Remedy export con indicador 'p'
    dt2 = parse_incident_datetime("20/10/2026 17:22 p")
    assert dt2 == datetime(2026, 10, 20, 17, 22)

    # Formato estándar DD/MM/YYYY HH:MM
    dt3 = parse_incident_datetime("14/10/2026 10:00")
    assert dt3 == datetime(2026, 10, 14, 10, 0)

    # Formato ISO
    dt4 = parse_incident_datetime("2026-10-14T10:00:00")
    assert dt4 == datetime(2026, 10, 14, 10, 0)

    # Valores inválidos o nulos
    assert parse_incident_datetime(None) is None
    assert parse_incident_datetime("") is None
    assert parse_incident_datetime("no-es-fecha") is None


def test_should_compute_emergency_sla_triggers_correctly():
    ref = datetime(2026, 10, 14, 12, 0)

    # 1. Menos de 20 min (Apertura reciente a las 11:50) -> Todo en plazo
    sla_10m = compute_emergency_sla_status(ref - timedelta(minutes=10), reference_time=ref)
    assert sla_10m["minutos_desde_apertura"] == 10
    assert sla_10m["sla_primera_notificacion_vencido"] is False
    assert sla_10m["requiere_escalado_telefonico"] is False
    assert sla_10m["escalado_estamentos_superiores"] is False
    assert sla_10m["proxima_ventana_update_minutos"] == 50

    # 2. 25 min -> SLA 1ª Notificación vencido (>20 min), pero sin escalado telefónico todavía
    sla_25m = compute_emergency_sla_status(ref - timedelta(minutes=25), reference_time=ref)
    assert sla_25m["minutos_desde_apertura"] == 25
    assert sla_25m["sla_primera_notificacion_vencido"] is True
    assert sla_25m["requiere_escalado_telefonico"] is False
    assert sla_25m["escalado_estamentos_superiores"] is False

    # 3. 50 min -> 1er Escalado telefónico requerido (>=45 min)
    sla_50m = compute_emergency_sla_status(ref - timedelta(minutes=50), reference_time=ref)
    assert sla_50m["minutos_desde_apertura"] == 50
    assert sla_50m["sla_primera_notificacion_vencido"] is True
    assert sla_50m["requiere_escalado_telefonico"] is True
    assert sla_50m["escalado_estamentos_superiores"] is False

    # 4. 110 min -> 2º Escalado requerido a Estamentos Superiores (>=105 min, 45m + 1h)
    sla_110m = compute_emergency_sla_status(ref - timedelta(minutes=110), reference_time=ref)
    assert sla_110m["minutos_desde_apertura"] == 110
    assert sla_110m["sla_primera_notificacion_vencido"] is True
    assert sla_110m["requiere_escalado_telefonico"] is True
    assert sla_110m["escalado_estamentos_superiores"] is True


def test_should_keep_p1_and_require_cso_validation_when_high_impact_and_workaround_applied():
    """Reglas de Oro 2 y 3: Un workaround NO desescala automáticamente una Emergencia SL1/P1."""
    evaluator = SeverityEvaluator()
    ticket = {
        "ID de incidencia": "INC000004199999",
        "Descripción": "CORTE TOTAL FIBRA EMPRESAS // Solución temporal workaround mediante export alternativo",
        "Prioridad": "Media",
        "Estatus": "Asignado",
        "Impacto": "Masiva",
        "Urgencia": "Media",
        "Grupo asignado": "SOPORTE FIBRA RED"
    }
    result = evaluator.evaluate(ticket, epsilon_data=None)

    # Debe mantenerse como P1 a pesar del workaround
    assert result["prioridad_sugerida"] == "P1"
    assert result["es_alta_prioridad"] is True
    eval_data = result["evaluacion"]
    assert eval_data["impacto"] == "Alto"
    assert eval_data["workaround"] == "Sí"
    assert "Pendiente autorización IM-CSO" in eval_data["workaround_gobernanza"]


def test_should_generate_emergency_4blocks_report_with_all_sections():
    generator = ExecutiveMessageGenerator()
    ticket = {
        "ID de incidencia": "INC000004156790",
        "Descripción": "Ficha Cliente Orange | Error funcional | Madison - Valladolid",
        "Grupo asignado": "DES_SOE_FICHA"
    }
    eval_result = {
        "prioridad_sugerida": "P1",
        "evaluacion": {
            "proceso": "Atención al Cliente (ATC)",
            "criterio": "ATC: Frontales/CRM (>20% desviación en 30m) o Regla de Oro N1",
            "impacto": "Alto",
            "impacto_justificacion": "Corte en servicio principal",
            "urgencia": "Alta",
            "urgencia_justificacion": "Afectación activa",
            "workaround": "Sí",
            "workaround_gobernanza": "Pendiente autorización IM-CSO (SL1 activa)"
        }
    }
    sla_status = {
        "minutos_desde_apertura": 55,
        "sla_primera_notificacion_vencido": True,
        "requiere_escalado_telefonico": True,
        "escalado_estamentos_superiores": False
    }

    report = generator.generate_emergency_4blocks_report(ticket, eval_result, resumen_ia=None, sla_status=sla_status)

    assert "REPORTE DE EMERGENCIA IT - ORANGE TECH OPERATIONS" in report
    assert "[1] CLASIFICACIÓN DEL TICKET" in report
    assert "[2] ESTADO DE COMUNICACIONES Y SLAS" in report
    assert "[3] PLAN DE ACCIÓN Y GOBERNANZA DE WORKAROUNDS" in report
    assert "[4] ESTADO DE ESCALADO TELEFÓNICO" in report
    assert "INC000004156790" in report
    assert "SL1 (Emergencia Crítica)" in report
    assert "Atención al Cliente (ATC)" in report
    assert "SLA 1ª Notificación VENCIDO" in report
    assert "Escalado Telefónico Requerido" in report
    assert "Pendiente autorización IM-CSO" in report
    assert "Vía Telefónica obligatoria" in report


def test_should_include_emergency_kpis_and_reports_in_batch_evaluation(sample_ticket_p3_nominal, sample_epsilon_critical_response):
    client_mock = MagicMock()
    client_mock.get_resumen_ia.return_value = sample_epsilon_critical_response

    ref_time = datetime(2026, 10, 14, 11, 0) # 60 minutos después de las 10:00 del ticket
    catalog = evaluate_incidents_batch(
        [sample_ticket_p3_nominal],
        epsilon_client=client_mock,
        reference_time=ref_time
    )

    kpis = catalog["_metadata"]["kpis"]
    assert "sla_primera_notificacion_vencidos_count" in kpis
    assert "requiere_escalado_telefonico_count" in kpis
    assert "workaround_pendientes_cso_count" in kpis
    assert kpis["sla_primera_notificacion_vencidos_count"] >= 1
    assert kpis["requiere_escalado_telefonico_count"] >= 1

    item = catalog["data"][0]
    assert "reporte_emergencia" in item
    assert "[1] CLASIFICACIÓN DEL TICKET" in item["reporte_emergencia"]
    assert "reporte_emergencia" not in item["mensajes_ejecutivos"]
    assert set(item["mensajes_ejecutivos"].keys()) == {"apertura", "seguimiento", "cierre"}
    assert item["evaluacion"]["minutos_desde_apertura"] == 60
    assert item["evaluacion"]["requiere_escalado_telefonico"] is True


def test_should_avoid_false_positive_substring_matches():
    evaluator = SeverityEvaluator()
    # 1. "operaciones" should not classify as O&M via "rac"
    ticket_operaciones = {
        "ID de incidencia": "INC000004999901",
        "Prioridad": "Media",
        "Descripción": "Consulta de operaciones financieras del cliente",
        "Grupo Resolutor": "SOPORTE GENERAL",
    }
    top_cat, top_bus, top_tech = evaluator._classify_process_multi_domain(ticket_operaciones, None)
    assert top_cat != "Operación y Monitorización (O&M)"

    # 2. "pasaporte" should not classify as Facturación via "sap"
    ticket_pasaporte = {
        "ID de incidencia": "INC000004999902",
        "Prioridad": "Media",
        "Descripción": "Subida de foto de pasaporte en portal",
        "Grupo Resolutor": "SOPORTE DOCUMENTAL",
    }
    top_cat, top_bus, top_tech = evaluator._classify_process_multi_domain(ticket_pasaporte, None)
    assert top_cat != "Facturación y Cobros"

    # 3. "comunicación" should not classify as O&M via "uca"
    ticket_comunicacion = {
        "ID de incidencia": "INC000004999903",
        "Prioridad": "Media",
        "Descripción": "Envío de carta de comunicación de bienvenida",
        "Grupo Resolutor": "SOPORTE GENERAL",
    }
    top_cat, top_bus, top_tech = evaluator._classify_process_multi_domain(ticket_comunicacion, None)
    assert top_cat != "Operación y Monitorización (O&M)"

    # 4. "precaución" should not classify as O&M via "cau"
    ticket_precaucion = {
        "ID de incidencia": "INC000004999904",
        "Prioridad": "Media",
        "Descripción": "Nota de precaución sobre uso de contraseñas",
        "Grupo Resolutor": "SOPORTE GENERAL",
    }
    top_cat, top_bus, top_tech = evaluator._classify_process_multi_domain(ticket_precaucion, None)
    assert top_cat != "Operación y Monitorización (O&M)"


def test_should_not_elevate_impact_when_critical_phrase_is_syntactically_negated():
    evaluator = SeverityEvaluator()

    # Negated scenario: "se descarta caída total"
    ticket_negated = {
        "ID de incidencia": "INC000004999910",
        "Prioridad": "Baja",
        "Descripción": "Revisión preventiva de routers. Se descarta caída total del servicio.",
        "Urgencia": "Baja",
        "Impacto": "Bajo"
    }
    eval_negated = evaluator.evaluate(ticket_negated, None)
    assert eval_negated["evaluacion"]["impacto"] != "Alto"
    assert eval_negated["prioridad_sugerida"] in ("P3", "P4")

    # Positive (non-negated) scenario: "caída total del servicio"
    ticket_positive = {
        "ID de incidencia": "INC000004999911",
        "Prioridad": "Media",
        "Descripción": "Caída total del servicio sin alternativa viable.",
        "Urgencia": "Alta",
        "Impacto": "Medio"
    }
    eval_positive = evaluator.evaluate(ticket_positive, None)
    assert eval_positive["evaluacion"]["impacto"] == "Alto"
    assert eval_positive["prioridad_sugerida"] == "P1"


def test_should_extract_quantitative_magnitude_metrics():
    # Sedes
    m1 = extract_quantitative_metrics("Incidencia que afecta a 4 sedes operativas de Madrid")
    assert m1["sedes"] == 4

    # Usuarios
    m2 = extract_quantitative_metrics("Afectación en 1.500 clientes de fibra fija")
    assert m2["usuarios"] == 1500

    # Desviación %
    m3 = extract_quantitative_metrics("Desviación del 25% en tramitación de portabilidad")
    assert m3["desviacion_pct"] == 25.0

    # Texto sin métricas cuantitativas
    m4 = extract_quantitative_metrics("Incidencia menor en interfaz visual")
    assert m4["sedes"] is None
    assert m4["usuarios"] is None
    assert m4["desviacion_pct"] is None


def test_should_escalate_impact_to_high_when_quantitative_thresholds_exceeded():
    evaluator = SeverityEvaluator()

    # Threshold sedes >= 3
    ticket_sedes = {
        "ID de incidencia": "INC000004999920",
        "Prioridad": "Media",
        "Descripción": "Incidencia de conectividad con impacto en 3 tiendas físicas de Barcelona",
        "Urgencia": "Alta",
        "Impacto": "Medio"
    }
    res_sedes = evaluator.evaluate(ticket_sedes, None)
    assert res_sedes["evaluacion"]["impacto"] == "Alto"
    assert "Umbral Cuantitativo (>=3 sedes: 3)" in res_sedes["evaluacion"]["criterio"]
    assert res_sedes["prioridad_sugerida"] == "P1"

    # Threshold usuarios >= 500
    ticket_users = {
        "ID de incidencia": "INC000004999921",
        "Prioridad": "Media",
        "Descripción": "Problema en frontal web afectando a 650 usuarios concurrentes",
        "Urgencia": "Alta",
        "Impacto": "Bajo"
    }
    res_users = evaluator.evaluate(ticket_users, None)
    assert res_users["evaluacion"]["impacto"] == "Alto"
    assert "Umbral Cuantitativo (>=500 usuarios: 650)" in res_users["evaluacion"]["criterio"]
    assert res_users["prioridad_sugerida"] == "P1"


def test_should_classify_with_multi_domain_weighted_scoring_and_dual_itil_labeling():
    evaluator = SeverityEvaluator()

    ticket = {
        "ID de incidencia": "INC000004999930",
        "Prioridad": "Media",
        "Descripción": "Fallo en motor Oracle BBDD afectando a consultas",
        "Grupo Resolutor": "DES_SOE_FICHA",  # ATC pattern in resolver group (4x weight)
        "Urgencia": "Alta",
        "Impacto": "Alto"
    }
    epsilon_data = {
        "sistemas": ["DES_SOE_FICHA", "FICHA CLIENTE"],
        "problema": "Carga lenta de fichas de clientes comerciales.",
        "impacto": "Consultas lentas.",
    }
    result = evaluator.evaluate(ticket, epsilon_data)

    eval_data = result["evaluacion"]
    # ATC should outvote BBDD because Grupo Resolutor (weight 4) and Epsilon (weight 3) point to ATC
    assert eval_data["proceso"] == "Atención al Cliente (ATC)"
    assert eval_data["proceso_negocio"] == "Atención al Cliente (ATC)"
    assert "dominio_tecnico" in eval_data


def test_should_compute_discrepancy_delta_and_severity_levels():
    # Delta 0: Aligned
    d0 = compute_discrepancy_details("Media", "P3")
    assert d0["es_discrepancia"] is False
    assert d0["delta"] == 0
    assert d0["gravedad"] == "Sin discrepancia"

    # Delta 1: Moderada (P3 -> P2)
    d1 = compute_discrepancy_details("Media", "P2")
    assert d1["es_discrepancia"] is True
    assert d1["delta"] == 1
    assert d1["gravedad"] == "Moderada"
    assert "Subescalación moderada (+1 nivel)" in d1["motivo"]

    # Delta 2: Mayor Severa (P3 -> P1)
    d2 = compute_discrepancy_details("Media", "P1", reasons=["Afectación de 3 tiendas"])
    assert d2["es_discrepancia"] is True
    assert d2["delta"] == 2
    assert d2["gravedad"] == "Mayor Severa"
    assert "Subescalación severa (+2 niveles)" in d2["motivo"]
    assert "Afectación de 3 tiendas" in d2["motivo"]

    # Delta 3: Crítica Extrema (P4 -> P1)
    d3 = compute_discrepancy_details("Baja", "P1")
    assert d3["es_discrepancia"] is True
    assert d3["delta"] == 3
    assert d3["gravedad"] == "Crítica Extrema"
    assert "Subescalación crítica extrema" in d3["motivo"]


def test_should_apply_operational_aging_escalation_when_p2_open_over_120_min_without_workaround():
    evaluator = SeverityEvaluator()

    # Ticket P2 naturally: Impacto Medio + Urgencia Media sin workaround
    ticket_aging = {
        "ID de incidencia": "INC000004999940",
        "Prioridad": "Media",
        "Descripción": "Degradación en enlace de sede sin corte total",
        "Estatus": "Asignado",
        "Fecha de envío": "14/10/2026 10:00",
        "Urgencia": "Media",
        "Impacto": "Medio"
    }

    # Case A: Open for 130 min without workaround -> escalates to P1
    ref_time_130m = datetime(2026, 10, 14, 12, 10)
    result_aging = evaluator.evaluate(ticket_aging, None, reference_time=ref_time_130m)
    assert result_aging["prioridad_sugerida"] == "P1"
    assert result_aging["evaluacion"]["aging_escalated"] is True
    assert "Aging Escalation" in result_aging["evaluacion"]["criterio"]

    # Case B: Open for only 60 min -> stays P2
    ref_time_60m = datetime(2026, 10, 14, 11, 0)
    result_normal = evaluator.evaluate(ticket_aging, None, reference_time=ref_time_60m)
    assert result_normal["prioridad_sugerida"] == "P2"
    assert result_normal["evaluacion"]["aging_escalated"] is False

    # Case C: Open for 140 min WITH workaround -> stays P2 (not escalated by aging)
    ticket_with_workaround = dict(ticket_aging)
    ticket_with_workaround["Descripción"] = "Degradación en enlace de sede con workaround activo"
    ref_time_140m = datetime(2026, 10, 14, 12, 20)
    result_wa = evaluator.evaluate(ticket_with_workaround, None, reference_time=ref_time_140m)
    assert result_wa["evaluacion"]["aging_escalated"] is False


def test_should_include_new_discrepancy_and_aging_kpis_in_batch_catalog():
    ticket_p3 = {
        "ID de incidencia": "INC000004999950",
        "Prioridad": "Media",
        "Descripción": "Corte de fibra afectando a 5 tiendas",
        "Estatus": "Asignado",
        "Fecha de envío": "14/10/2026 10:00",
        "Urgencia": "Alta",
        "Impacto": "Alto"
    }
    # Evaluates to P1 with discrepancy Delta = 2 (Media -> P1)
    ref_time = datetime(2026, 10, 14, 10, 15)
    catalog = evaluate_incidents_batch([ticket_p3], epsilon_client=None, reference_time=ref_time)

    kpis = catalog["_metadata"]["kpis"]
    assert "discrepancias_delta1_moderada_count" in kpis
    assert "discrepancias_delta2_mayor_count" in kpis
    assert "discrepancias_delta3_critica_count" in kpis
    assert "aging_escaladas_p1_count" in kpis
    assert kpis["discrepancias_delta2_mayor_count"] == 1

    item = catalog["data"][0]
    assert item["discrepancia_delta"] == 2
    assert item["discrepancia_gravedad"] == "Mayor Severa"
    assert "+2 niveles" in item["discrepancia_motivo"]


def test_should_discriminate_impact_when_remedy_impacto_is_masiva_without_total_outage():
    """Remedy exports every row with 'Impacto': 'Masiva'. The engine must discriminate real impact."""
    evaluator = SeverityEvaluator()

    # Ticket with Remedy 'Masiva' but affecting only 5 customers with localized TV defect
    ticket_masiva_acotado = {
        "ID de incidencia": "INC000004161012",
        "Prioridad": "Media",
        "Descripción": "IP24 | Error funcional | ATAC Jazzplat - Guadalajara",
        "Estatus": "Asignado",
        "Fecha de envío": "30/10/2026 09:00",
        "Urgencia": "Media",
        "Impacto": "Masiva",
        "Grupo Resolutor": "SOP_SMC_TEIDE"
    }
    epsilon_data = {
        "problema": "Activación automática de TV libre en líneas multisede sin solicitud.",
        "impacto": "5 clientes reclamando activación no solicitada de TV libre.",
        "solucion": "Desactivación manual y depuración de script de activación."
    }

    ref_time = datetime(2026, 10, 30, 9, 30) # 30 min open
    result = evaluator.evaluate(ticket_masiva_acotado, epsilon_data, reference_time=ref_time)

    eval_data = result["evaluacion"]
    # Must NOT blindly assign Alto just because Remedy says 'Masiva'
    assert eval_data["impacto"] == "Medio"
    assert "5 clientes reclamando" in eval_data["impacto_justificacion"]
    assert eval_data["impacto_justificacion"].startswith("Epsilon IA:")
    # Matrix: Medio + Media -> P2 (Incidencia Mayor)
    assert result["prioridad_sugerida"] == "P2"


def test_should_populate_dynamic_impact_justification_with_actual_evidence():
    """Impact justification must be dynamic and reflective of real evidence, not a generic static string."""
    evaluator = SeverityEvaluator()

    # Case A: Quantitative threshold exceeded
    ticket_quant = {
        "ID de incidencia": "INC000004170500",
        "Prioridad": "Media",
        "Descripción": "Error funcional en Ficha Cliente Orange",
        "Impacto": "Masiva",
        "Urgencia": "Alta"
    }
    epsilon_quant = {
        "problema": "Error al consultar permanencias.",
        "impacto": "Impacto alto: 100% de errores en operativa, afecta a 4 sedes.",
    }
    res_quant = evaluator.evaluate(ticket_quant, epsilon_quant)
    assert res_quant["evaluacion"]["impacto"] == "Alto"
    assert "Umbral cuantitativo superado" in res_quant["evaluacion"]["impacto_justificacion"]
    assert "4 sedes/tiendas afectadas" in res_quant["evaluacion"]["impacto_justificacion"]

    # Case B: Ticket without Epsilon or critical keyword, but with Remedy 'Masiva'
    ticket_remedy_only = {
        "ID de incidencia": "INC000004171427",
        "Prioridad": "Media",
        "Descripción": "DJINGO | Consulta de operativa nocturna",
        "Impacto": "Masiva",
        "Urgencia": "Media"
    }
    res_remedy = evaluator.evaluate(ticket_remedy_only, None)
    assert res_remedy["evaluacion"]["impacto"] == "Medio"
    assert "Incidencia catalogada Masiva en Remedy" in res_remedy["evaluacion"]["impacto_justificacion"]


def test_should_format_operational_duration_correctly():
    """Validates human-readable formatting of minutes into days, hours, and minutes."""
    assert format_operational_duration(None) == "En curso (reciente)"
    assert format_operational_duration(-5) == "0m"
    assert format_operational_duration(0) == "0m"
    assert format_operational_duration(15) == "15m"
    assert format_operational_duration(59) == "59m"
    assert format_operational_duration(60) == "1h 0m (60m)"
    assert format_operational_duration(105) == "1h 45m (105m)"
    assert format_operational_duration(1440) == "1d 0h (1440m)"
    assert format_operational_duration(74616) == "51d 19h (74616m)"


def test_should_adapt_emergency_report_when_incident_is_resolved_or_closed():
    """Emergency report for resolved/closed tickets must not emit pending escalation alarms."""
    generator = ExecutiveMessageGenerator()
    ticket_resolved = {
        "ID de incidencia": "INC000004122710",
        "Descripción": "Ficha Cliente Orange - Interfaz de teléfono",
        "Estatus": "Resuelto",
        "Grupo asignado": "FIJO APL Soporte PS",
    }
    eval_result = {
        "prioridad_sugerida": "P1",
        "evaluacion": {
            "proceso": "Atención al Cliente (ATC)",
            "criterio": "ATC (3.1): Frontales/CRM",
            "impacto": "Alto",
            "impacto_justificacion": "Afectación en recogida de equipos",
            "urgencia": "Alta",
            "urgencia_justificacion": "Impacto activo",
            "workaround": "No",
        }
    }
    sla_status = {
        "minutos_desde_apertura": 74616,
        "sla_primera_notificacion_vencido": True,
        "requiere_escalado_telefonico": True,
        "escalado_estamentos_superiores": True,
    }

    report = generator.generate_emergency_4blocks_report(ticket_resolved, eval_result, sla_status=sla_status)

    assert "INCIDENCIA RESUELTA / ESTABILIZADA" in report
    assert "Duración Total: 51d 19h (74616m) hasta restablecimiento" in report
    assert "Proceso de escalado concluido por resolución" in report
    assert "Paso a Post-Incident Review (PIR) / Problem Management" in report
    assert "SLA 1ª Notificación VENCIDO" not in report
    assert "2º Escalado Requerido" not in report


def test_should_activate_parallel_escalation_for_middleware_and_core_infrastructure():
    """Structural components (Middleware / Cloud / Core IT) must mandate Parallel Escalation in emergency report."""
    generator = ExecutiveMessageGenerator()
    ticket_middleware = {
        "ID de incidencia": "INC000004100001",
        "Descripción": "TIBCO Bus Transversal // TIMEOUT GENERAL",
        "Estatus": "En Curso",
        "Grupo asignado": "SOP_INTEGRACION_TIBCO",
    }
    eval_result = {
        "prioridad_sugerida": "P1",
        "evaluacion": {
            "proceso": "Middleware e Integración Transversal",
            "dominio_tecnico": "Middleware e Integración Transversal",
            "criterio": "Middleware (3.7): Caída o bloqueo transversal en bus/API",
            "impacto": "Alto",
            "impacto_justificacion": "Corte total de APIs core",
            "urgencia": "Alta",
            "urgencia_justificacion": "Impacto activo",
            "workaround": "No",
        }
    }
    sla_status = {
        "minutos_desde_apertura": 50,
        "sla_primera_notificacion_vencido": True,
        "requiere_escalado_telefonico": True,
        "escalado_estamentos_superiores": False,
    }

    report = generator.generate_emergency_4blocks_report(ticket_middleware, eval_result, sla_status=sla_status)

    assert "⚡ ESCALADO EN PARALELO ACTIVADO" in report
    assert "Matrices de Contacto: GRIAL (entornos Orange/Jazztel) | Confluence (entornos MasMóvil/KRT)" in report
    assert "Incident Manager (R) / Customer & Service Ops IM-CSO (A)" in report


def test_should_escalate_stagnant_incident_over_2h_in_emergency_report():
    """Active P1 incidents open for > 120 minutes must trigger Stagnation Alarm in emergency report."""
    generator = ExecutiveMessageGenerator()
    ticket_active = {
        "ID de incidencia": "INC000004199999",
        "Descripción": "Caída Pasarela Pagos OCS",
        "Estatus": "Asignado",
        "Grupo asignado": "SOPORTE_OCS_PAGOS",
    }
    eval_result = {
        "prioridad_sugerida": "P1",
        "evaluacion": {
            "proceso": "Prepago",
            "criterio": "Prepago (3.3): >10% errores",
            "impacto": "Alto",
            "impacto_justificacion": "Imposibilidad de cobro",
            "urgencia": "Alta",
            "urgencia_justificacion": "Impacto en vivo",
            "workaround": "No",
        }
    }
    sla_status = {
        "minutos_desde_apertura": 130,
        "sla_primera_notificacion_vencido": True,
        "requiere_escalado_telefonico": True,
        "escalado_estamentos_superiores": True,
    }

    report = generator.generate_emergency_4blocks_report(ticket_active, eval_result, sla_status=sla_status)

    assert "🚨 ALARMA POR ESTANCAMIENTO (>2h): Escalado a Dirección IM-CSO" in report
    assert "2h 10m (130m)" in report







