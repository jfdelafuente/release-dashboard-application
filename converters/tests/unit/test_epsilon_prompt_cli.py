"""Tests unitarios para el CLI de prueba y calibracion del prompt Epsilon (test_epsilon_prompt.py).

Cubre los validadores de esquema Pydantic, la evaluacion de directrices de negocio,
la extraccion de JSON envuelto en Markdown y la ejecucion CLI en modo mock y estricto.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from typing import Any, Dict

import pytest

# Asegurar importacion del script desde la carpeta scripts/
SCRIPTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "scripts"))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from test_epsilon_prompt import (
    EpsilonResumenModel,
    evaluate_contract,
    extract_json_content,
    count_words,
    parse_timestamp_dt,
)


@pytest.fixture
def valid_payload() -> Dict[str, Any]:
    return {
        "success": True,
        "titulo": "Ficha de Cliente - Error en sincronización de teléfono en recogidas de fijo",
        "estadoActual": "Pendiente",
        "problema": "El módulo de recogidas de equipamiento fijo no propaga el teléfono de contacto modificado hacia PS y Siebel 8 debido a un fallo en el microservicio MDG.",
        "impacto": "Medio. Afecta a la logística inversa de routers en bajas de fibra, con riesgo de envíos fallidos al transportista. Sin método alternativo disponible.",
        "solucion": "Bug identificado en microservicio de sincronización MDG. Parche de corrección por proveedor comprometido para despliegue en release del 12/11/2026.",
        "sistemas": ["Ficha de Cliente", "Siebel 8", "MDG", "PS"],
        "hitosTecnicos": [
            "[02/11/2026 09:15:00]: Detección de inconsistencia entre Ficha de Cliente y sistemas downstream.",
            "[03/11/2026 14:00:00]: N2 aísla el error en el microservicio MDG y traslada requerimiento a desarrollo.",
        ],
        "bloqueos": [
            "[Ventana Release]: Dependencia de entrega y despliegue de parche por proveedor para release del 12/11/2026."
        ],
        "siguienteAccion": "Despliegue y validación del parche en ventana del 12/11/2026.",
    }


def test_valid_payload_pydantic_passes(valid_payload):
    """Verifica que un payload conforme pasa la validacion de Pydantic."""
    model = EpsilonResumenModel(**valid_payload)
    assert model.success is True
    assert len(model.sistemas) == 4
    assert len(model.hitosTecnicos) == 2


def test_problema_exceeds_40_words_fails(valid_payload):
    """Verifica que un problema con mas de 40 palabras sea rechazado."""
    valid_payload["problema"] = " ".join(["palabra"] * 41)
    with pytest.raises(ValueError, match="40 palabras"):
        EpsilonResumenModel(**valid_payload)


def test_impacto_exceeds_30_words_fails(valid_payload):
    """Verifica que un impacto con mas de 30 palabras sea rechazado."""
    valid_payload["impacto"] = "Sin método alternativo disponible. " + " ".join(["palabra"] * 30)
    with pytest.raises(ValueError, match="30 palabras"):
        EpsilonResumenModel(**valid_payload)


def test_impacto_missing_workaround_fails(valid_payload):
    """Verifica que un impacto sin mencion a workaround o metodo alternativo sea rechazado."""
    valid_payload["impacto"] = "Afectación en clientes de fibra sin servicio."
    with pytest.raises(ValueError, match="método alternativo"):
        EpsilonResumenModel(**valid_payload)


def test_solucion_required_when_resolved(valid_payload):
    """Verifica que solucion no pueda ser omitida ni vacia si el estado es RESUELTO o CERRADO."""
    valid_payload["estadoActual"] = "Resuelto"
    valid_payload["solucion"] = None
    with pytest.raises(ValueError, match="es obligatoria cuando el estado es 'Resuelto'"):
        EpsilonResumenModel(**valid_payload)


def test_solucion_optional_when_in_progress(valid_payload):
    """Verifica que solucion pueda ser omitida si el estado es Pendiente o En Curso."""
    valid_payload["estadoActual"] = "En Curso"
    valid_payload["solucion"] = None
    model = EpsilonResumenModel(**valid_payload)
    assert model.solucion is None


def test_sistemas_cannot_be_empty(valid_payload):
    """Verifica que sistemas requiera al menos un elemento."""
    valid_payload["sistemas"] = []
    with pytest.raises(ValueError, match="al menos un sistema"):
        EpsilonResumenModel(**valid_payload)


def test_hitos_max_count_exceeded(valid_payload):
    """Verifica que no se permitan mas de 6 hitos tecnicos."""
    valid_payload["hitosTecnicos"] = [
        f"[01/11/2026 10:0{i}]: Hito de prueba {i}" for i in range(7)
    ]
    with pytest.raises(ValueError, match="máximo de 5-6 hitos"):
        EpsilonResumenModel(**valid_payload)


def test_hitos_invalid_timestamp_format(valid_payload):
    """Verifica que hitos sin marca temporal adaptativa estandar sean rechazados."""
    valid_payload["hitosTecnicos"] = ["Ayer por la tarde: Se reinició el microservicio."]
    with pytest.raises(ValueError, match="formato adaptativo"):
        EpsilonResumenModel(**valid_payload)


def test_hitos_chronological_order_violation(valid_payload):
    """Verifica que hitos desordenados cronologicamente sean detectados como error."""
    valid_payload["hitosTecnicos"] = [
        "[05/11/2026 10:00]: Hito reciente.",
        "[02/11/2026 09:00]: Hito antiguo posterior.",
    ]
    with pytest.raises(ValueError, match="orden cronológico"):
        EpsilonResumenModel(**valid_payload)


def test_bloqueos_invalid_prefix(valid_payload):
    """Verifica que bloqueos sin prefijo estandarizado sean rechazados."""
    valid_payload["bloqueos"] = ["Esperando parche del proveedor sin prefijo."]
    with pytest.raises(ValueError, match="prefijo válido"):
        EpsilonResumenModel(**valid_payload)


def test_evaluate_contract_pass_and_fail(valid_payload):
    """Verifica que evaluate_contract clasifique correctamente las reglas cumplidas e incumplidas."""
    checks, all_passed = evaluate_contract(valid_payload)
    assert all_passed is True
    assert len(checks) == 10

    # Forzar violacion en impacto (sin ninguna palabra clave de contingencia)
    valid_payload["impacto"] = "Afectación general grave en todas las sedes."
    checks, all_passed = evaluate_contract(valid_payload)
    assert all_passed is False
    impacto_check = next(c for c in checks if c.campo == "impacto")
    assert impacto_check.cumple is False


def test_extract_json_content():
    """Verifica que extract_json_content limpie delimitadores Markdown y texto circundante."""
    # Caso 1: JSON puro
    assert extract_json_content('{"a": 1}') == '{"a": 1}'

    # Caso 2: Markdown ```json ... ```
    md_json = "```json\n{\n  \"status\": \"ok\"\n}\n```"
    assert json.loads(extract_json_content(md_json)) == {"status": "ok"}

    # Caso 3: Texto previo y posterior
    wrapped = "Aquí está el resultado:\n{\n  \"code\": 200\n}\nEspero te sirva."
    assert json.loads(extract_json_content(wrapped)) == {"code": 200}


def test_cli_execution_mock_mode():
    """Ejecuta el script CLI en modo mock y verifica codigo de salida 0."""
    script_path = os.path.join(SCRIPTS_DIR, "test_epsilon_prompt.py")
    res = subprocess.run(
        [sys.executable, script_path, "--mock"],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0
    assert "RESPUESTA JSON DEVUELTA POR EL MODELO" in res.stdout
    assert "TODAS LAS REGLAS CUMPLIDAS" in res.stdout


def test_cli_execution_mock_strict_mode():
    """Ejecuta el script CLI en modo mock con --strict y verifica codigo 0."""
    script_path = os.path.join(SCRIPTS_DIR, "test_epsilon_prompt.py")
    res = subprocess.run(
        [sys.executable, script_path, "--mock", "--strict"],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0


def test_cli_execution_mock_strict_with_invalid_response_fails(valid_payload):
    """Verifica que el modo --strict falle con codigo 1 si la respuesta mock incumple reglas."""
    script_path = os.path.join(SCRIPTS_DIR, "test_epsilon_prompt.py")

    # Modificar payload para incumplir
    invalid_data = dict(valid_payload)
    invalid_data["problema"] = " ".join(["palabra"] * 50)  # Excede 40 palabras

    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".json", encoding="utf-8") as f:
        json.dump(invalid_data, f)
        temp_name = f.name

    try:
        # En modo strict debe salir con 1
        res = subprocess.run(
            [sys.executable, script_path, "--mock", "--mock-response", temp_name, "--strict"],
            capture_output=True,
            text=True,
        )
        assert res.returncode == 1

        # En modo normal (sin strict) debe salir con 0 pero reportar FAIL
        res_normal = subprocess.run(
            [sys.executable, script_path, "--mock", "--mock-response", temp_name],
            capture_output=True,
            text=True,
        )
        assert res_normal.returncode == 0
        assert "REGLAS INCUMPLIDAS DETECTADAS" in res_normal.stdout
    finally:
        if os.path.exists(temp_name):
            os.remove(temp_name)


def test_anthropic_proxy_env_variables_resolution(monkeypatch):
    """Verifica que las variables de proxy corporativo MasOrange se resuelvan correctamente."""
    from test_epsilon_prompt import call_anthropic

    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "sk-token-masorange")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://llm.tools.cloud.masorange.es")
    monkeypatch.setenv("ANTHROPIC_MODEL", "anthropic/claude-sonnet-4-5")

    # Mock urllib.request.urlopen para capturar el Request
    import urllib.request
    captured_request = {}

    class DummyResponse:
        def read(self):
            return json.dumps({
                "content": [{"type": "text", "text": '{"success": true}'}],
                "usage": {"input_tokens": 10, "output_tokens": 20}
            }).encode("utf-8")

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

    def mock_urlopen(req, *args, **kwargs):
        captured_request["url"] = req.full_url
        captured_request["headers"] = dict(req.headers)
        return DummyResponse()

    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)

    data, tokens, elapsed = call_anthropic(
        user_prompt="test prompt",
        model_name="",
    )

    assert captured_request["url"] == "https://llm.tools.cloud.masorange.es/v1/messages"
    assert captured_request["headers"]["X-api-key"] == "sk-token-masorange"
    assert captured_request["headers"]["Authorization"] == "Bearer sk-token-masorange"
    assert data == {"success": True}
    assert tokens == 30
