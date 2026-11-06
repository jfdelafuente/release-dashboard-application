"""
Pruebas unitarias para el servicio desacoplado Epsilon Resumen IA (epsilon_service.py).
"""
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from converters.src.epsilon_service import (
    generate_epsilon_summary,
    find_incident_in_local_dumps,
    evaluate_contract,
    count_words,
    parse_timestamp_dt,
    load_project_env,
    EpsilonResumenModel,
)


def test_generate_epsilon_summary_mock_mode():
    sample_incident = {
        "ID de incidencia": "INC000004174655",
        "Descripción": "Caída del servicio B2B por fallo en microservicio de cobros.",
        "Prioridad": "Crítica",
        "Estatus": "Asignado",
        "Notas": "2026-10-30 08:30:00 - Reinicio del pod completado con éxito.",
    }

    is_valid, data, meta = generate_epsilon_summary(sample_incident, mock=True)

    assert is_valid is True
    assert meta["mock"] is True
    assert "problema" in data
    assert "impacto" in data
    assert "sistemas" in data
    assert "hitosTecnicos" in data
    assert isinstance(data["hitosTecnicos"], list)
    assert len(data["hitosTecnicos"]) >= 1
    # Verificar que el payload generado supera el modelo estricto
    model_obj = EpsilonResumenModel(**data)
    assert model_obj.problema == data["problema"]


def test_generate_epsilon_summary_llm_valid_response():
    sample_incident = {
        "codigo": "INC000009999999",
        "resumen": "Latencia en base de datos PostgreSQL",
    }
    valid_llm_dict = {
        "success": True,
        "titulo": "Latencia en base de datos PostgreSQL",
        "estadoActual": "Asignado",
        "problema": "Latencia crítica en cluster PostgreSQL afectando checkout.",
        "impacto": "Proceso afectado: Checkout web. Sin workaround disponible.",
        "sistemas": ["PostgreSQL", "API Checkout"],
        "solucion": "",
        "hitosTecnicos": ["[30/10/2026 09:00]: Alerta de contención", "[30/10/2026 09:30]: Escalado a DBA"],
        "bloqueos": [],
        "siguienteAccion": "Optimización de índices"
    }

    with patch("converters.src.epsilon_service.call_anthropic", return_value=(valid_llm_dict, 150, 0.45)):
        is_valid, data, meta = generate_epsilon_summary(
            sample_incident, provider="anthropic", model="claude-sonnet-4-5", mock=False
        )
        assert is_valid is True
        assert data["problema"] == "Latencia crítica en cluster PostgreSQL afectando checkout."
        assert meta["mock"] is False
        assert meta["provider"] == "anthropic"


def test_generate_epsilon_summary_llm_validation_failure():
    sample_incident = {"codigo": "INC123"}
    # Problema con más de 40 palabras para forzar error 422
    invalid_llm_dict = {
        "problema": "palabra " * 45,
        "impacto": "Proceso afectado: Ventas. Sin workaround disponible.",
        "sistemas": "CRM",
        "solucion": "",
        "hitos": ["[30/10/2026 09:00]: Inicio"],
        "bloqueos": ["Ninguno"],
        "acciones_siguientes": "Revisión",
        "analisis_causa_raiz": "Desconocido"
    }

    with patch("converters.src.epsilon_service.call_anthropic", return_value=(invalid_llm_dict, 180, 0.35)):
        is_valid, data_or_errors, meta = generate_epsilon_summary(
            sample_incident, provider="anthropic", mock=False
        )
        assert is_valid is False
        assert "validation_errors" in data_or_errors
        assert any("40 palabras" in str(err) for err in data_or_errors["validation_errors"])


def test_find_incident_in_local_dumps(tmp_path):
    output_dir = tmp_path / "data" / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    massive_dump = output_dir / "2026-10-30-massive.json"
    massive_dump.write_text(json.dumps([
        {"ID de incidencia": "INC000004174655", "Descripción": "Incidencia B2B crítica", "Estatus": "Asignado"},
        {"ID de incidencia": "INC000004174656", "Descripción": "Incidencia menor", "Estatus": "Cerrado"}
    ]), encoding="utf-8")

    # Búsqueda exitosa
    result = find_incident_in_local_dumps("INC000004174655", project_root=tmp_path)
    assert result is not None
    inc_data, src_file, mtime = result
    assert inc_data["ID de incidencia"] == "INC000004174655"
    assert "2026-10-30-massive.json" in str(src_file)
    assert mtime > 0

    # Búsqueda no encontrada
    result_missing = find_incident_in_local_dumps("INC999999999999", project_root=tmp_path)
    assert result_missing is None


def test_count_words_and_timestamps():
    assert count_words("  Hola mundo  cruel   ") == 3
    assert count_words("") == 0
    assert count_words(None) == 0

    dt = parse_timestamp_dt("[30/10/2026 14:15]: Detección del incidente")
    assert dt is not None
    assert dt.day == 30
    assert dt.month == 10
    assert dt.year == 2026
    assert dt.hour == 14
    assert dt.minute == 15

    # Timestamp no fechado [S/F]
    assert parse_timestamp_dt("[S/F]: Incidencia histórica") is None
    # Timestamp inválido
    assert parse_timestamp_dt("invalid_string") is None
