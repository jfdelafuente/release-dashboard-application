import json
import pytest
from pathlib import Path
from converters.cli.update_agent_message import (
    parse_agent_raw_output,
    update_agent_store
)


def test_should_parse_standard_agent_markdown_output():
    raw = """
**Mensaje para Dirección (versión completa):** (único párrafo, máx 90 palabras)
Se declara incidencia crítica P1 (INC000004159463) en Siebel 8 por fallo en tramitaciones logísticas. Afecta a 10 operadores y pedidos de clientes sin alternativa de desvío. Soporte e infraestructura analizan interfaces. Próxima actualización en 30 minutos.

**Versión aún más breve:** (máx 30 palabras)
Apertura P1 (INC000004159463): Bloqueo logístico en Siebel 8. Afecta a 10 operadores. Diagnóstico en curso sin alternativa operativa.
"""
    comp, brev = parse_agent_raw_output(raw)
    assert "Se declara incidencia crítica P1" in comp
    assert "\n" not in comp  # Monopárrafo sin saltos de línea
    assert "(único párrafo, máx 90 palabras)" not in comp
    assert "Apertura P1 (INC000004159463): Bloqueo logístico en Siebel 8" in brev
    assert "(máx 30 palabras)" not in brev


def test_should_parse_alternative_headers():
    raw = """
**Versión Completa Dirección:**
Incidencia en Siebel 8 restablecida.

**Versión Breve:**
Cierre P1: Resuelto en Siebel 8.
"""
    comp, brev = parse_agent_raw_output(raw)
    assert comp == "Incidencia en Siebel 8 restablecida."
    assert brev == "Cierre P1: Resuelto en Siebel 8."


def test_should_fallback_to_paragraphs_when_no_headers():
    raw = """
Primer párrafo con la explicación completa para la dirección general de operaciones.

Segundo párrafo con el resumen breve.
"""
    comp, brev = parse_agent_raw_output(raw)
    assert comp == "Primer párrafo con la explicación completa para la dirección general de operaciones."
    assert brev == "Segundo párrafo con el resumen breve."


def test_should_update_store_and_preserve_existing_incidents(tmp_path: Path):
    store_file = tmp_path / "test_store.json"
    initial_data = {
        "_metadata": {"version": "1.0.0"},
        "incidents": {
            "INC000004065609": {
                "apertura": {
                    "completo": "Existente",
                    "breve": "Existente breve",
                    "conteo_palabras_completo": 1,
                    "conteo_palabras_breve": 2
                }
            }
        }
    }
    with open(store_file, "w", encoding="utf-8") as f:
        json.dump(initial_data, f)

    entry = update_agent_store(
        store_path=store_file,
        incident_id="inc000004159463",
        phase="seguimiento",
        completo="Texto de seguimiento detallado para dirección.",
        breve="Seguimiento breve."
    )

    assert entry["conteo_palabras_completo"] == 6
    assert entry["conteo_palabras_breve"] == 2
    assert entry["generado_por_agente"] is True

    # Verificar persistencia en disco
    with open(store_file, "r", encoding="utf-8") as f:
        saved = json.load(f)

    # Conserva la previa
    assert "INC000004065609" in saved["incidents"]
    # Añade la nueva en mayúsculas
    assert "INC000004159463" in saved["incidents"]
    assert "seguimiento" in saved["incidents"]["INC000004159463"]
    assert saved["incidents"]["INC000004159463"]["seguimiento"]["completo"] == "Texto de seguimiento detallado para dirección."


def test_should_raise_value_error_on_invalid_phase(tmp_path: Path):
    store_file = tmp_path / "test_store.json"
    with pytest.raises(ValueError, match="Fase no válida"):
        update_agent_store(
            store_path=store_file,
            incident_id="INC000004159463",
            phase="fase_inventada",
            completo="A",
            breve="B"
        )

