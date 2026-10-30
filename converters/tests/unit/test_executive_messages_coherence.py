import pytest
from converters.cli.audit_executive_messages_coherence import (
    audit_incident_messages,
    count_words,
    run_audit
)


def test_count_words():
    assert count_words("") == 0
    assert count_words("   ") == 0
    assert count_words("Hola mundo") == 2
    assert count_words("Se declara incidencia P1 (INC000004171670)") == 5


def test_audit_valid_conforming_incident():
    stored = {
        "apertura": {
            "completo": "Se declara incidencia mayor P2 (INC000004171670) en CRM4TELCO por fallo en escaparate de terminales debido a parámetro clusterID en GestorCatalogoDisponibleWS. Afecta a 15 operadores en sede Andes de Teleperformance Medellín sin impedir venta de terminales en promoción. Equipos de desarrollo corrigen el mapeo. Próxima actualización en 60 minutos.",
            "breve": "Apertura P2 (INC000004171670): Fallo de escaparate en CRM4TELCO por parámetro clusterID; afecta a 15 operadores en Medellín. En resolución."
        }
    }
    eps_data = {
        "problema": "Escaparate no carga en CRM4TELCO. Error: parámetro clusterID erróneo (valor 0) en GestorCatalogoDisponibleWS.",
        "impacto": "Afecta 15 usuarios de Teleperformance Medellín (sede Andes)",
        "sistemas": ["CRM4TELCO"]
    }
    issues = audit_incident_messages("INC000004171670", stored, eps_data, "DEGRADACION/BSS JAZZTEL/SL2")
    assert len(issues) == 0


def test_audit_detects_word_count_exceeded():
    long_msg = "palabra " * 95
    stored = {
        "apertura": {
            "completo": long_msg.strip(),
            "breve": "palabra " * 35
        }
    }
    issues = audit_incident_messages("INCTEST01", stored)
    rules = [i.rule for i in issues]
    assert "WORD_COUNT_COMPLETO" in rules
    assert "WORD_COUNT_BREVE" in rules


def test_audit_detects_multiparagraph_violation():
    stored = {
        "apertura": {
            "completo": "Primer párrafo de apertura.\n\nSegundo párrafo prohibido en versión monopárrafo.",
            "breve": "Versión breve correcta."
        }
    }
    issues = audit_incident_messages("INCTEST02", stored)
    assert any(i.rule == "MONOPARRAFO_COMPLETO" for i in issues)


def test_audit_detects_ungrounded_hallucinations():
    # Hallucinated database bottleneck when telemetry says nothing about DB
    stored = {
        "apertura": {
            "completo": "Se declara incidencia P2 (INCTEST03) en CRM4TELCO. Los técnicos analizan un cuello de botella en consultas a base de datos para restablecer las latencias estándar.",
            "breve": "Apertura P2 (INCTEST03): Análisis de base de datos."
        }
    }
    eps_data = {
        "problema": "Fallo en validación de parámetro clusterID en catálogo web.",
        "impacto": "10 usuarios",
        "sistemas": ["CRM4TELCO"]
    }
    issues = audit_incident_messages("INCTEST03", stored, eps_data)
    rules = [i.rule for i in issues]
    assert "UNGROUNDED_TECHNICAL_CLAIM" in rules


def test_audit_detects_missing_key_telemetry():
    # Epsilon explicitly highlights clusterID=0 as the sole error, but message is vague
    stored = {
        "apertura": {
            "completo": "Se declara incidencia P2 (INCTEST04) en CRM4TELCO. Se registra una degradación general en el escaparate. Soporte investiga el problema.",
            "breve": "Apertura P2 (INCTEST04): Degradación en escaparate."
        }
    }
    eps_data = {
        "problema": "Error crítico por parámetro clusterID=0 en catálogo.",
        "sistemas": ["CRM4TELCO"]
    }
    issues = audit_incident_messages("INCTEST04", stored, eps_data)
    assert any(i.rule == "MISSING_KEY_TELEMETRY" for i in issues)


def test_audit_detects_unconverted_remote_timezone():
    # Message quotes local Colombian morning time 05:37 without converting to Madrid CET
    stored = {
        "apertura": {
            "completo": "Se declara incidencia P2 (INCTEST05) en CRM4TELCO detectada a las 05:37 en la sede de Medellín. Soporte investiga clusterID.",
            "breve": "Apertura P2 (INCTEST05): Detección 05:37 en Medellín."
        }
    }
    eps_data = {
        "problema": "Error clusterID",
        "impacto": "Sede Medellín",
        "hitosTecnicos": ["Detección 05:37 en Medellín"]
    }
    issues = audit_incident_messages("INCTEST05", stored, eps_data)
    assert any(i.rule == "UNCONVERTED_REMOTE_TIMEZONE" for i in issues)


def test_run_audit_on_live_inc000004171670():
    res = run_audit(target_id="INC000004171670")
    assert res["success"] is True
    assert res["error_count"] == 0
    assert res["warning_count"] == 0

