#!/usr/bin/env python3
"""CLI de Prueba y Calibración del System Prompt de Epsilon Resumen IA.

Permite probar, calibrar y validar empíricamente las respuestas generadas
por LLMs para el volcado de incidencias Remedy siguiendo las directrices
definidas en data/resumen_incidencia_epsilon.md y la especificación specs/test-epsilon-prompt.md.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Tuple

# Asegurar importación de epsilon_service desde converters/src
CONVERTERS_SRC = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "converters", "src"))
if CONVERTERS_SRC not in sys.path:
    sys.path.insert(0, CONVERTERS_SRC)

from epsilon_service import (  # noqa: E402
    ALLOWED_BLOCK_PREFIXES,
    EPSILON_SYSTEM_PROMPT,
    TIMESTAMP_REGEX,
    USER_PROMPT_TEMPLATE,
    WORKAROUND_REGEX,
    EpsilonResumenModel,
    EpsilonResumenValidationCheck,
    build_epsilon_system_prompt,
    build_user_message,
    call_anthropic,
    call_gemini,
    call_mock,
    call_openai,
    count_words,
    evaluate_contract,
    extract_json_content,
    generate_epsilon_summary,
    load_project_env,
    normalize_anthropic_model_name,
    parse_timestamp_dt,
)

load_project_env()


def list_available_models() -> int:
    """Consulta el endpoint /v1/models del proveedor configurado y lista los modelos admitidos."""
    import ssl
    import urllib.error
    import urllib.request

    load_project_env()
    token = os.environ.get("ANTHROPIC_AUTH_TOKEN") or os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("OPENAI_API_KEY")
    base = os.environ.get("ANTHROPIC_BASE_URL") or os.environ.get("OPENAI_BASE_URL") or "https://api.anthropic.com"
    base = base.rstrip("/")
    if base.endswith("/v1"):
        endpoint = f"{base}/models"
    else:
        endpoint = f"{base}/v1/models"

    headers = {
        "x-api-key": token or "",
        "Authorization": f"Bearer {token or ''}",
        "anthropic-version": "2023-06-01",
    }
    req = urllib.request.Request(endpoint, headers=headers, method="GET")

    ssl_context = ssl.create_default_context()
    verify_ssl = os.environ.get("ANTHROPIC_VERIFY_SSL", "").lower() not in ("0", "false", "no")
    if not verify_ssl or os.environ.get("PYTHONHTTPSVERIFY") == "0":
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

    print(f"\nConsultando modelos disponibles en: {endpoint} ...")
    try:
        try:
            resp_cm = urllib.request.urlopen(req, timeout=15, context=ssl_context)
        except urllib.error.URLError as ssl_err:
            if "CERTIFICATE_VERIFY_FAILED" in str(ssl_err) or "certificate verify failed" in str(ssl_err):
                insecure_context = ssl._create_unverified_context()
                resp_cm = urllib.request.urlopen(req, timeout=15, context=insecure_context)
            else:
                raise ssl_err

        with resp_cm as resp:
            data = json.loads(resp.read().decode("utf-8"))
            models = []
            if isinstance(data, dict):
                if "data" in data and isinstance(data["data"], list):
                    models = [m.get("id") or m.get("name") for m in data["data"] if isinstance(m, dict)]
                elif "models" in data and isinstance(data["models"], list):
                    models = [m.get("name") or m.get("id") for m in data["models"] if isinstance(m, dict)]
            elif isinstance(data, list):
                models = [m.get("id") or str(m) for m in data]

            if models:
                print(f"\n[OK] Se han encontrado {len(models)} modelo(s) disponibles para tu clave:")
                for m in sorted(models):
                    marker = " -> [RECOMENDADO]" if "sonnet" in m.lower() else ""
                    print(f"  * {m}{marker}")
                print("\nPuedes invocar la CLI indicando cualquiera de ellos con:")
                print("  python scripts/test_epsilon_prompt.py --file <ruta.json> --model <nombre_modelo>\n")
            else:
                print(f"Respuesta del endpoint: {data}")
            return 0
    except Exception as e:
        sys.stderr.write(f"Error al consultar '{endpoint}': {e}\n")
        return 1


# =====================================================================
# RENDERIZADO VISUAL EN CONSOLA (TABLAS)
# =====================================================================
def print_report_table(
    checks: List[EpsilonResumenValidationCheck],
    all_passed: bool,
    elapsed: float,
    tokens: int,
    provider: str,
    model: str,
) -> None:
    """Imprime una tabla formateada en consola usando rich si está disponible o fallback ASCII."""
    try:
        from rich.console import Console
        from rich.panel import Panel
        from rich.table import Table

        console = Console()
        table = Table(
            title=f"Informe de Calibración Epsilon Resumen IA ({provider.upper()} - {model})",
            show_header=True,
            header_style="bold cyan",
        )
        table.add_column("Campo", style="bold", width=18)
        table.add_column("Criterio Evaluado", width=42)
        table.add_column("Métrica Real", width=36)
        table.add_column("Estado", justify="center", width=10)

        for c in checks:
            status_symbol = "[bold green]PASS[/bold green]" if c.cumple else "[bold red]FAIL[/bold red]"
            metrica_display = c.metrica
            if c.detalle:
                metrica_display += f" ([dim]{c.detalle}[/dim])"
            table.add_row(c.campo, c.criterio, metrica_display, status_symbol)

        console.print(table)
        color = "green" if all_passed else "red"
        status_text = (
            "TODAS LAS REGLAS CUMPLIDAS" if all_passed else "SE DETECTARON REGLAS INCUMPLIDAS"
        )
        summary = (
            f"[{color}]Resultado Final: {status_text}[/{color}]\n"
            f"Tiempo de respuesta: [bold]{elapsed:.2f}s[/bold] | "
            f"Tokens consumidos: [bold]{tokens}[/bold]"
        )
        console.print(Panel(summary, border_style=color, expand=False))
        return
    except ImportError:
        pass

    # Fallback ASCII robusto para cualquier terminal
    title = f"--- INFORME DE CALIBRACIÓN EPSILON RESUMEN IA ({provider.upper()} - {model}) ---"
    print("\n" + title)
    header_fmt = "{:<16} | {:<40} | {:<34} | {:<8}"
    row_sep = "-" * 105
    print(row_sep)
    print(header_fmt.format("Campo", "Criterio Evaluado", "Métrica Real", "Estado"))
    print(row_sep)

    for c in checks:
        status_symbol = "[OK]" if c.cumple else "[X]"
        metrica_display = c.metrica
        if c.detalle:
            metrica_display += f" ({c.detalle})"
        print(header_fmt.format(c.campo, c.criterio[:40], metrica_display[:34], status_symbol))

    print(row_sep)
    verdict = "TODAS LAS REGLAS CUMPLIDAS" if all_passed else "REGLAS INCUMPLIDAS DETECTADAS"
    print(f"Resultado Final: {verdict}")
    print(f"Tiempo: {elapsed:.2f}s | Tokens: {tokens}")
    print(row_sep + "\n")


# =====================================================================
# CLI PRINCIPAL
# =====================================================================
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Prueba, calibra y valida el System Prompt de Epsilon Resumen IA contra incidencias Remedy.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--file",
        "-f",
        dest="file_path",
        help="Ruta al archivo JSON con los datos en bruto de la incidencia Remedy.",
    )
    parser.add_argument(
        "--provider",
        "-p",
        choices=["openai", "gemini", "anthropic"],
        default=None,
        help="Proveedor LLM a invocar (default: autodetectado según API key en entorno, o 'openai').",
    )
    parser.add_argument(
        "--model",
        "-m",
        default="",
        help="Nombre específico del modelo (default según proveedor: gpt-4o, gemini-2.5-pro, anthropic/claude-sonnet-4-5 o claude-3-5-sonnet).",
    )
    parser.add_argument(
        "--mock",
        "--dry-run",
        action="store_true",
        dest="mock",
        help="Modo offline simulado sin llamadas a APIs externas.",
    )
    parser.add_argument(
        "--mock-response",
        dest="mock_response_path",
        help="Ruta a un JSON con respuesta simulada para pruebas de validación con errores.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        dest="strict",
        help="Salir con código de salida 1 si alguna regla del esquema resulta incumplida.",
    )
    parser.add_argument(
        "--json-only",
        action="store_true",
        dest="json_only",
        help="Imprimir únicamente el JSON devuelto sin la tabla de diagnóstico.",
    )
    parser.add_argument(
        "--list-models",
        action="store_true",
        dest="list_models",
        help="Consultar y mostrar los modelos disponibles en el endpoint o proxy (/v1/models).",
    )
    return parser


def main() -> int:
    load_project_env()
    parser = build_parser()
    args = parser.parse_args()

    if args.list_models:
        return list_available_models()

    # 1. Carga de datos de la incidencia
    remedy_raw_str: str = ""
    if args.file_path:
        if not os.path.isfile(args.file_path):
            sys.stderr.write(f"Error: El archivo de entrada '{args.file_path}' no existe.\n")
            return 1
        try:
            with open(args.file_path, "r", encoding="utf-8") as f:
                remedy_raw_str = f.read()
        except Exception as e:
            sys.stderr.write(f"Error al leer el archivo '{args.file_path}': {e}\n")
            return 1
    elif not sys.stdin.isatty():
        remedy_raw_str = sys.stdin.read()
    elif args.mock:
        default_sample = os.path.join(
            os.path.dirname(__file__), "..", "data", "samples", "remedy_incident_sample.json"
        )
        if os.path.isfile(default_sample):
            with open(default_sample, "r", encoding="utf-8") as f:
                remedy_raw_str = f.read()
        else:
            remedy_raw_str = json.dumps(
                {
                    "id": "INC000004122710",
                    "resumen": "Error en propagación de teléfono de contacto en recogidas de fijo",
                    "estado": "Pendiente",
                    "notas": "02/11/2026 09:15:00 - N1: Fallo detectado. 03/11/2026 14:00:00 - N2: Solución planificada.",
                }
            )
    else:
        sys.stderr.write(
            "Error: Debe proporcionar un archivo con '--file <ruta.json>', datos por stdin o activar '--mock'.\n"
        )
        return 1

    if not remedy_raw_str.strip():
        sys.stderr.write("Error: El volcado de entrada de la incidencia está vacío.\n")
        return 1

    try:
        incident_obj = json.loads(remedy_raw_str)
        remedy_formatted = json.dumps(incident_obj, ensure_ascii=False, indent=2)
    except json.JSONDecodeError as e:
        sys.stderr.write(f"Error: La entrada no es un JSON válido: {e}\n")
        return 1

    user_prompt = USER_PROMPT_TEMPLATE.format(remedy_json=remedy_formatted)

    # 2. Invocación al LLM o Mock
    try:
        selected_provider = args.provider
        if not selected_provider:
            has_anthropic_key = bool(os.environ.get("ANTHROPIC_AUTH_TOKEN") or os.environ.get("ANTHROPIC_API_KEY"))
            has_openai_key = bool(os.environ.get("OPENAI_API_KEY"))
            has_gemini_key = bool(os.environ.get("GEMINI_API_KEY"))

            if has_anthropic_key and not has_openai_key:
                selected_provider = "anthropic"
            elif has_gemini_key and not has_openai_key:
                selected_provider = "gemini"
            elif has_openai_key:
                selected_provider = "openai"
            elif has_anthropic_key:
                selected_provider = "anthropic"
            else:
                selected_provider = "openai"

        if args.mock:
            data, tokens, elapsed = call_mock(user_prompt, args.mock_response_path, incident_data=incident_obj)
            provider_label = "mock"
            model_label = "deterministic-fixture"
        elif selected_provider == "openai":
            provider_label = "openai"
            model_label = args.model or os.environ.get("OPENAI_MODEL") or "gpt-4o"
            data, tokens, elapsed = call_openai(user_prompt, model_label)
        elif selected_provider == "gemini":
            provider_label = "gemini"
            model_label = args.model or os.environ.get("GEMINI_MODEL") or "gemini-2.5-pro"
            data, tokens, elapsed = call_gemini(user_prompt, model_label)
        elif selected_provider == "anthropic":
            provider_label = "anthropic"
            model_label = normalize_anthropic_model_name(args.model)
            data, tokens, elapsed = call_anthropic(user_prompt, model_label)
        else:
            sys.stderr.write(f"Error: Proveedor desconocido '{selected_provider}'.\n")
            return 1
    except Exception as e:
        sys.stderr.write(f"Error durante la invocación del modelo: {e}\n")
        return 1

    # 3. Impresión del JSON devuelto
    if args.json_only:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print("\n=== RESPUESTA JSON DEVUELTA POR EL MODELO ===")
        print(json.dumps(data, ensure_ascii=False, indent=2))

    # 4. Evaluación de Contrato y Reglas Semánticas
    checks, all_passed = evaluate_contract(data)

    pydantic_error: Optional[str] = None
    try:
        EpsilonResumenModel(**data)
    except Exception as e:
        pydantic_error = str(e)
        all_passed = False

    if not args.json_only:
        print_report_table(
            checks=checks,
            all_passed=all_passed,
            elapsed=elapsed,
            tokens=tokens,
            provider=provider_label,
            model=model_label,
        )
        if pydantic_error:
            sys.stderr.write(f"\n[Aviso Pydantic]:\n{pydantic_error}\n")

    if args.strict and not all_passed:
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
