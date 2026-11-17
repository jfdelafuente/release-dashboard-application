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
    compute_remedy_fingerprint,
    resolve_or_generate_epsilon_summary,
    pregenerate_epsilon_summaries,
    build_epsilon_system_prompt,
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


def test_generate_epsilon_summary_self_healing_retry():
    """Verifica que si el primer intento LLM incumple el contrato Pydantic, el reintento autocorrectivo lo subsana."""
    sample_incident = {"idRemedy": "INC000004199001", "resumen": "Error en autenticador"}
    invalid_first_attempt = {
        "success": True,
        "titulo": "Error en autenticador",
        "estadoActual": "Asignado",
        "problema": "Fallo en login.",
        "impacto": "Afecta a usuarios web.",  # Falta mención explícita de workaround/sin alternativa
        "sistemas": ["SSO"],
        "hitosTecnicos": ["[17/11/2026 10:00]: Alerta inicial"],
        "bloqueos": [],
    }
    valid_second_attempt = {
        "success": True,
        "titulo": "Error en autenticador",
        "estadoActual": "Asignado",
        "problema": "Fallo en servicio SSO al validar tokens OAuth2.",
        "impacto": "Afecta a usuarios del portal web. Sin método alternativo disponible.",
        "sistemas": ["SSO"],
        "hitosTecnicos": ["[17/11/2026 10:00]: Alerta inicial en pasarela OAuth2"],
        "bloqueos": [],
    }

    with patch(
        "converters.src.epsilon_service.call_anthropic",
        side_effect=[(invalid_first_attempt, 150, 0.3), (valid_second_attempt, 180, 0.4)],
    ) as mock_call:
        is_valid, data, meta = generate_epsilon_summary(
            sample_incident, provider="anthropic", mock=False, max_retries=1
        )
        assert is_valid is True
        assert mock_call.call_count == 2
        assert meta["retries"] == 1
        assert meta["tokens"] == 330
        assert "Sin método alternativo" in data["impacto"]


def test_resolve_or_generate_smart_fingerprint_and_invalidation(tmp_path, monkeypatch):
    """
    Verifica el ciclo completo del Smart Fingerprint Cache:
    1) Genera desde Remedy -> INTERNAL_LLM_GENERATED
    2) Sin cambios en Remedy -> FINGERPRINT_HIT (0 llamadas LLM)
    3) Nuevo worklog en Remedy -> invalida huella y regenera -> INTERNAL_LLM_GENERATED
    """
    monkeypatch.setenv("EPSILON_PROVIDER_MODE", "internal")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    remedy_state = {
        "codigoResp": 0,
        "remedy": {
            "idRemedy": "INC000004199002",
            "resumen": "Caída parcial TIBCO",
            "estadoDesc": "Asignado",
            "fechaUltimaModificacion": "2026-11-17T08:00:00.000+00:00",
            "worklog": [
                {"idWorklog": "1", "fecha": "2026-11-17T08:00:00.000+00:00", "detalle": "Detección inicial"}
            ],
        },
    }

    mock_montmc = MagicMock()
    mock_montmc.fetch_remedy_detail.side_effect = lambda code: json.loads(json.dumps(remedy_state))

    llm_output = {
        "success": True,
        "titulo": "Caída parcial TIBCO",
        "estadoActual": "Asignado",
        "problema": "Saturación de colas JMS en nodos TIBCO.",
        "impacto": "Retraso en provisión de pedidos. Sin alternativa disponible.",
        "sistemas": ["TIBCO"],
        "hitosTecnicos": ["[17/11/2026 09:00:00]: Detección inicial de encolamiento."],
        "bloqueos": [],
    }

    with patch("converters.src.epsilon_service.call_anthropic", return_value=(llm_output, 200, 0.5)) as mock_llm:
        # 1. Primera llamada: genera con LLM
        st1, d1, hdr1 = resolve_or_generate_epsilon_summary(
            "INC000004199002", project_root=tmp_path, montmc_client=mock_montmc
        )
        assert st1 == 200
        assert hdr1 == "INTERNAL_LLM_GENERATED"
        assert mock_llm.call_count == 1
        assert d1["meta"]["worklog_count"] == 1

        # 2. Segunda llamada sin cambios en Remedy: FINGERPRINT_HIT (0 llamadas extra al LLM)
        st2, d2, hdr2 = resolve_or_generate_epsilon_summary(
            "INC000004199002", project_root=tmp_path, montmc_client=mock_montmc
        )
        assert st2 == 200
        assert hdr2 == "FINGERPRINT_HIT"
        assert mock_llm.call_count == 1

        # 3. Entra nuevo worklog en Remedy: la huella cambia y regenera automáticamente
        remedy_state["remedy"]["worklog"].append(
            {"idWorklog": "2", "fecha": "2026-11-17T09:15:00.000+00:00", "detalle": "Reinicio de broker JMS"}
        )
        remedy_state["remedy"]["fechaUltimaModificacion"] = "2026-11-17T09:15:00.000+00:00"

        st3, d3, hdr3 = resolve_or_generate_epsilon_summary(
            "INC000004199002", project_root=tmp_path, montmc_client=mock_montmc
        )
        assert st3 == 200
        assert hdr3 == "INTERNAL_LLM_GENERATED"
        assert mock_llm.call_count == 2
        assert d3["meta"]["worklog_count"] == 2


def test_pregenerate_and_retry_cli_use_internal_engine(tmp_path, monkeypatch):
    """Verifica pregenerate_epsilon_summaries y retry_epsilon_ia en modo interno."""
    monkeypatch.setenv("EPSILON_MOCK", "1")
    monkeypatch.setenv("EPSILON_PROVIDER_MODE", "internal")

    mock_montmc = MagicMock()
    mock_montmc.fetch_remedy_detail.side_effect = lambda code: {
        "codigoResp": 0,
        "remedy": {
            "idRemedy": code,
            "resumen": f"Incidencia {code}",
            "estadoDesc": "En Curso",
            "fechaUltimaModificacion": "2026-11-17T10:00:00.000+00:00",
            "worklog": [{"idWorklog": "1", "fecha": "2026-11-17T10:00:00.000+00:00", "detalle": "Nota"}],
        },
    }

    batch_res = pregenerate_epsilon_summaries(
        ["INC000004100001", "INC000004100002"],
        project_root=tmp_path,
        montmc_client=mock_montmc,
    )
    assert batch_res["total"] == 2
    assert set(batch_res["generated"]) == {"INC000004100001", "INC000004100002"}

    # Segunda ejecución sin cambios -> fingerprint_hits
    batch_res_2 = pregenerate_epsilon_summaries(
        ["INC000004100001", "INC000004100002"],
        project_root=tmp_path,
        montmc_client=mock_montmc,
    )
    assert set(batch_res_2["fingerprint_hits"]) == {"INC000004100001", "INC000004100002"}
    assert batch_res_2["generated"] == []

    # Verificar CLI retry_incidents usando motor interno
    from converters.cli.retry_epsilon_ia import retry_incidents
    with patch("converters.src.montmc_client.MonTMCClient", return_value=mock_montmc):
        retry_res = retry_incidents(
            incident_codes=["INC000004100003"],
            force=True,
            re_evaluate=False,
            project_root=tmp_path,
        )
    assert len(retry_res["success"]) == 1
    assert "motor interno Epsilon" in retry_res["success"][0]["reason"]
    assert (tmp_path / "data" / ".epsilon_cache" / "INC000004100003.json").is_file()


def test_phase1_prompt_directives_present_in_system_prompt():
    """Verifica que el System Prompt cargado incluye todas las directivas de Fase 1."""
    prompt = build_epsilon_system_prompt()
    assert "Sin método alternativo disponible." in prompt
    assert "Workaround activo (pendiente de erradicación definitiva / visado CSO)." in prompt
    assert "Existe método alternativo operativo" in prompt
    assert "Deduplicación multisede (`OE-03`)" in prompt
    assert "Último hito sustantivo garantizado" in prompt
    assert "[Ventana Release]:" in prompt
    assert "[Validación Negocio]: Pendiente de confirmación por sede/peticionario" in prompt


@pytest.mark.parametrize(
    "workaround_formula",
    [
        "Afecta a 12 agentes en Konecta Madrid. Sin método alternativo disponible.",
        "Impacto en 25 operadores de Valencia. Workaround activo (pendiente de erradicación definitiva / visado CSO).",
        "Afecta a 8 agentes en Oviedo. Existe método alternativo operativo (registro manual en portal secundario).",
    ],
)
def test_normalized_workaround_formulas_pass_contract(workaround_formula):
    """Las tres fórmulas normalizadas de workaround de Fase 1 deben pasar WORKAROUND_REGEX y el contrato."""
    payload = {
        "success": True,
        "titulo": "Fallo funcional en aplicación CRM",
        "estadoActual": "ASIGNADO",
        "problema": "Error al tramitar altas de fibra en línea activa desde CRM.",
        "impacto": workaround_formula,
        "sistemas": ["CRM"],
        "hitosTecnicos": [
            "[17/11/2026 09:00]: Detección inicial del fallo en sede.",
            "[17/11/2026 10:15]: Diagnóstico técnico preliminar por N2.",
        ],
        "bloqueos": ["[Ventana Release]: Parche planificado en PaP nocturno del 18/11/2026."],
        "solucion": "Identificado defecto en validación de catálogo; parche comprometido para ventana del 18/11/2026.",
        "siguienteAccion": "Despliegue en ventana nocturna del 18/11/2026.",
    }
    model = EpsilonResumenModel(**payload)
    assert model.impacto == workaround_formula
    checks, all_passed = evaluate_contract(payload)
    assert all_passed is True
    assert all(c.cumple for c in checks)


def test_prompt_hash_change_invalidates_epsilon_cache(tmp_path, monkeypatch):
    """Modificar data/resumen_incidencia_epsilon.md cambia prompt_hash y regenera sin --force."""
    monkeypatch.setenv("EPSILON_PROVIDER_MODE", "internal")
    monkeypatch.setenv("EPSILON_MOCK", "0")
    monkeypatch.setattr("converters.src.epsilon_service.get_project_root", lambda: tmp_path)

    prompt_file = tmp_path / "data" / "resumen_incidencia_epsilon.md"
    prompt_file.parent.mkdir(parents=True, exist_ok=True)
    prompt_file.write_text(
        "# Prompt\n\n## 1. Instrucciones del Sistema (System Prompt)\nRegla A\n\n## 5. Implementación en Código\nIgnorar\n",
        encoding="utf-8",
    )

    mock_montmc = MagicMock()
    mock_montmc.fetch_remedy_detail.return_value = {
        "codigoResp": 0,
        "remedy": {
            "idRemedy": "INC000004199099",
            "resumen": "Fallo en CRM",
            "estadoDesc": "ASIGNADO",
            "fechaUltimaModificacion": "2026-11-17T09:00:00.000+00:00",
            "worklog": [{"idWorklog": "1", "fecha": "2026-11-17T09:00:00.000+00:00", "detalle": "Nota inicial"}],
        },
    }

    llm_output = {
        "success": True,
        "titulo": "Fallo en CRM",
        "estadoActual": "ASIGNADO",
        "problema": "Error funcional en CRM.",
        "impacto": "Afecta a 5 agentes. Sin método alternativo disponible.",
        "sistemas": ["CRM"],
        "hitosTecnicos": ["[17/11/2026 10:00:00]: Nota inicial."],
        "bloqueos": [],
    }

    with patch("converters.src.epsilon_service.call_anthropic", return_value=(llm_output, 200, 0.4)) as mock_llm:
        st1, d1, hdr1 = resolve_or_generate_epsilon_summary(
            "INC000004199099", project_root=tmp_path, montmc_client=mock_montmc
        )
        assert st1 == 200
        assert hdr1 == "INTERNAL_LLM_GENERATED"
        hash_v1 = d1["meta"]["prompt_hash"]

        # Sin cambios: hit de caché
        st2, d2, hdr2 = resolve_or_generate_epsilon_summary(
            "INC000004199099", project_root=tmp_path, montmc_client=mock_montmc
        )
        assert st2 == 200
        assert hdr2 == "FINGERPRINT_HIT"
        assert mock_llm.call_count == 1

        # Se edita el prompt (Sección 1): cambia prompt_hash y regenera automáticamente sin force=True
        prompt_file.write_text(
            "# Prompt\n\n## 1. Instrucciones del Sistema (System Prompt)\nRegla A + Regla B\n\n## 5. Implementación en Código\nIgnorar\n",
            encoding="utf-8",
        )
        st3, d3, hdr3 = resolve_or_generate_epsilon_summary(
            "INC000004199099", project_root=tmp_path, montmc_client=mock_montmc
        )
        assert st3 == 200
        assert hdr3 == "INTERNAL_LLM_GENERATED"
        assert mock_llm.call_count == 2
        assert d3["meta"]["prompt_hash"] != hash_v1


def test_epsilon_triaje_model_valid_invalid_and_optional():
    """Valida EpsilonTriajeModel (Fase 2) como bloque opcional compatible hacia atrás."""
    from pydantic import ValidationError

    base_payload = {
        "success": True,
        "titulo": "Degradación parcial multisede en CRM",
        "estadoActual": "ASIGNADO",
        "problema": "Fallo intermitente en alta de pedidos desde CRM.",
        "impacto": "Afecta a 2 sedes. Workaround activo (pendiente de erradicación definitiva / visado CSO).",
        "sistemas": ["CRM"],
        "hitosTecnicos": ["[17/11/2026 09:00]: Detección inicial del fallo en sede."],
        "bloqueos": [],
    }

    # Sin triaje: compatible hacia atrás
    model_without = EpsilonResumenModel(**base_payload)
    assert model_without.triaje is None
    checks_without, ok_without = evaluate_contract(base_payload)
    assert ok_without is True
    assert any(c.campo == "triaje" and c.cumple for c in checks_without)

    # Con triaje válido
    with_triaje = {
        **base_payload,
        "triaje": {
            "escenario": "RESOLUCION_PARCIAL",
            "workaround": True,
            "multisede": True,
            "alertaInfratriaje": False,
            "desgloseSedes": [
                {"sede": "Bosch-Vigo", "estado": "OK_CONFIRMADO"},
                {"sede": "Madison-Valladolid", "estado": "FALLO_ACTIVO"},
            ],
        },
    }
    model_with = EpsilonResumenModel(**with_triaje)
    assert model_with.triaje is not None
    assert model_with.triaje.escenario == "RESOLUCION_PARCIAL"
    assert len(model_with.triaje.desgloseSedes) == 2
    checks_with, ok_with = evaluate_contract(with_triaje)
    assert ok_with is True
    triaje_check = next(c for c in checks_with if c.campo == "triaje")
    assert "RESOLUCION_PARCIAL" in triaje_check.metrica

    # Con escenario inválido: falla Pydantic y evaluate_contract
    bad_triaje = {
        **base_payload,
        "triaje": {
            "escenario": "NO_EXISTE",
            "workaround": False,
            "multisede": False,
            "alertaInfratriaje": False,
            "desgloseSedes": [],
        },
    }
    with pytest.raises(ValidationError):
        EpsilonResumenModel(**bad_triaje)
    _, ok_bad = evaluate_contract(bad_triaje)
    assert ok_bad is False


def test_severity_evaluator_prioritizes_phase2_triaje_and_exposes_desglose_sedes():
    """SeverityEvaluator prioriza epsilon_data['triaje'] sobre regex y expone desglose_sedes."""
    from converters.cli.evaluate_incident_notifications import SeverityEvaluator

    ev = SeverityEvaluator()
    ticket = {
        "id": "INC000004199888",
        "Descripción": "CRM | Error funcional | Sede A",
        "Prioridad": "Media",
        "Estatus": "En Curso",
        "Fecha": "2026-11-17 09:00:00",
    }
    epsilon_data = {
        "titulo": "CRM - Error funcional multisede",
        "estadoActual": "EN CURSO",
        "problema": "Fallo en portal de contratación.",
        "impacto": "Afecta a 2 sedes. Sin método alternativo disponible.",  # Texto dice sin alternativa, pero triaje.workaround=True manda
        "solucion": "Mitigación aplicada.",
        "bloqueos": [],
        "hitosTecnicos": ["[17/11/2026 10:00]: Mitigación aplicada."],
        "triaje": {
            "escenario": "REAPERTURA",
            "workaround": True,
            "multisede": True,
            "alertaInfratriaje": True,
            "desgloseSedes": [
                {"sede": "Bosch-Vigo", "estado": "OK_CONFIRMADO"},
                {"sede": "Madison-Valladolid", "estado": "FALLO_ACTIVO"},
            ],
        },
    }

    res = ev.evaluate(ticket, epsilon_data=epsilon_data)
    assert res["es_reapertura"] is True
    assert res["evaluacion"]["workaround"] == "Sí"
    assert len(res["desglose_sedes"]) == 2
    assert res["evaluacion"]["desglose_sedes"][1]["estado"] == "FALLO_ACTIVO"
    assert res["evaluacion"]["metricas_cuantitativas"]["sedes"] == 2
