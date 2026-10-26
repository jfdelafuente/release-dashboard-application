"""Unit tests for High Priority Incident Notifications Evaluator.

Follows Constitution Testing Standards:
- Descriptive names: `should_[action]_when_[condition]`
- Tests edge cases, fallback modes, and ITIL matrix rules.
"""

import json
from unittest.mock import MagicMock, patch
import pytest

from converters.cli.evaluate_incident_notifications import (
    SeverityEvaluator,
    EpsilonClient,
    ExecutiveMessageGenerator,
    evaluate_incidents_batch,
    detect_priority_discrepancy,
    normalize_priority
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


