#!/usr/bin/env python3
"""
Utilidad para relanzar la obtención del Resumen IA de Epsilon para incidencias que dieron error o están incompletas.

Permite:
1. Relanzar automáticamente todas las incidencias con Resumen IA faltante según ingestion_audit_summary.json.
2. Relanzar incidencias específicas por código (ej. INC000004173662).
3. Forzar el refresco de todas las incidencias activas (--all / --force).
4. Guardar los resúmenes en data/.epsilon_cache/{id}.json y regenerar el catálogo y la auditoría.

Uso:
    python converters/cli/retry_epsilon_ia.py
    python converters/cli/retry_epsilon_ia.py INC000004173662 INC000004173771
    python converters/cli/retry_epsilon_ia.py --all --force
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import ssl
import subprocess
import sys
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional


CORPORATE_EPSILON_URL = "https://soptmc.si.orange.es/MonTMC/api/epsilon/resumenIA"
LOCAL_PROXY_URL = "http://127.0.0.1:8080/api/epsilon/resumenIA"


def get_project_root() -> Path:
    current = Path(__file__).resolve().parent
    for p in [current, current.parent, current.parent.parent]:
        if (p / "data").exists() and (p / "converters").exists():
            return p
    return Path.cwd()


def get_cache_dir(project_root: Path) -> Path:
    cache_dir = project_root / "data" / ".epsilon_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def find_missing_epsilon_incidents(project_root: Path) -> list[str]:
    """Identifica las incidencias activas que no tienen Resumen IA en el resumen de auditoría o en el catálogo."""
    missing: list[str] = []

    # 1. Intentar desde ingestion_audit_summary.json
    summary_path = project_root / "data" / "output" / "ingestion_audit_summary.json"
    if summary_path.exists():
        try:
            with open(summary_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for item in data.get("incidents", []):
                if item.get("is_terminal"):
                    continue
                resumen = item.get("resumen_ia", {})
                if not resumen.get("disponible"):
                    inc_id = item.get("id")
                    if inc_id and inc_id not in missing:
                        missing.append(inc_id)
            if missing:
                return missing
        except Exception as e:
            print(f"[WARN] Error leyendo {summary_path}: {e}")

    # 2. Fallback: desde high_priority_notifications.json
    catalog_path = project_root / "data" / "output" / "high_priority_notifications.json"
    if catalog_path.exists():
        try:
            with open(catalog_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for item in data.get("data", []):
                inc_id = item.get("id")
                resumen = item.get("resumen_ia")
                if not resumen or not (resumen.get("problema") or resumen.get("impacto")):
                    if inc_id and inc_id not in missing:
                        missing.append(inc_id)
        except Exception as e:
            print(f"[WARN] Error leyendo {catalog_path}: {e}")

    return missing


def find_all_active_incident_codes(project_root: Path) -> list[str]:
    """Obtiene todos los códigos de incidencias activas desde high_priority_notifications.json o ingestion_audit_summary.json."""
    codes: list[str] = []
    catalog_path = project_root / "data" / "output" / "high_priority_notifications.json"
    if catalog_path.exists():
        try:
            with open(catalog_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for item in data.get("data", []):
                inc_id = item.get("id")
                if inc_id and inc_id not in codes:
                    codes.append(inc_id)
            if codes:
                return codes
        except Exception as e:
            print(f"[WARN] Error leyendo {catalog_path}: {e}")

    summary_path = project_root / "data" / "output" / "ingestion_audit_summary.json"
    if summary_path.exists():
        try:
            with open(summary_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for item in data.get("incidents", []):
                if item.get("is_terminal"):
                    continue
                inc_id = item.get("id")
                if inc_id and inc_id not in codes:
                    codes.append(inc_id)
        except Exception as e:
            print(f"[WARN] Error leyendo {summary_path}: {e}")

    return codes


def fetch_epsilon_data(incident_code: str, base_urls: list[str], timeout: float = 8.0) -> tuple[Optional[dict[str, Any]], str]:
    """Intenta descargar el resumen IA consultando las URLs candidatas en orden."""
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE

    errors = []
    for base_url in base_urls:
        url = f"{base_url.rstrip('/')}/{incident_code}"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "ReleaseDashboard-RetryTool/1.0",
                "Accept": "application/json",
            }
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=ssl_ctx) as resp:
                if resp.status == 200:
                    payload = json.loads(resp.read().decode("utf-8"))
                    data = payload.get("data") if isinstance(payload, dict) and "data" in payload else payload
                    if data and isinstance(data, dict):
                        return data, f"200 OK desde {base_url}"
                    errors.append(f"{base_url}: 200 OK pero respuesta vacía")
                else:
                    errors.append(f"{base_url}: HTTP {resp.status}")
        except urllib.error.HTTPError as he:
            errors.append(f"{base_url}: HTTP {he.code} {he.reason}")
        except urllib.error.URLError as ue:
            errors.append(f"{base_url}: Error conexión ({ue.reason})")
        except Exception as ex:
            errors.append(f"{base_url}: {type(ex).__name__} ({ex})")

    return None, "; ".join(errors)


def retry_incidents(
    incident_codes: list[str],
    base_urls: Optional[list[str]] = None,
    force: bool = False,
    re_evaluate: bool = True,
    project_root: Optional[Path] = None,
) -> dict[str, Any]:
    root = project_root or get_project_root()
    cache_dir = get_cache_dir(root)

    if not base_urls:
        base_urls = [CORPORATE_EPSILON_URL, LOCAL_PROXY_URL]

    print("=" * 80)
    print(f"RELANZAMIENTO DE RESUMEN IA DE EPSILON ({len(incident_codes)} incidencias)")
    print(f"Endpoints candidatos: {', '.join(base_urls)}")
    print("=" * 80)

    results = {
        "success": [],
        "failed": [],
        "skipped_cached": [],
    }

    for idx, inc_id in enumerate(incident_codes, start=1):
        cache_file = cache_dir / f"{inc_id}.json"

        if not force and cache_file.exists():
            try:
                content = json.loads(cache_file.read_text(encoding="utf-8"))
                if content and isinstance(content, dict) and (content.get("problema") or content.get("impacto")):
                    print(f"[{idx}/{len(incident_codes)}] {inc_id}: OMITIDO (ya existe en caché local válida)")
                    results["skipped_cached"].append(inc_id)
                    continue
            except Exception:
                pass

        print(f"[{idx}/{len(incident_codes)}] {inc_id}: Consultando telemetría Epsilon...", end=" ", flush=True)
        data, reason = fetch_epsilon_data(inc_id, base_urls)

        if data:
            try:
                cache_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
                print(f"[OK] Guardado en caché ({reason})")
                results["success"].append({
                    "id": inc_id,
                    "titulo": data.get("titulo", ""),
                    "reason": reason,
                })
            except Exception as e:
                print(f"[ERROR al guardar caché: {e}]")
                results["failed"].append({"id": inc_id, "error": f"Error guardando caché: {e}"})
        else:
            print(f"[FALLO] {reason}")
            results["failed"].append({"id": inc_id, "error": reason})

    print("-" * 80)
    print(f"Balance de Relanzamiento: {len(results['success'])} recuperadas con éxito | {len(results['skipped_cached'])} ya cacheadas | {len(results['failed'])} fallidas.")
    print("-" * 80)

    # Si se recuperó al menos una o se forzó, relanzar evaluación para actualizar auditoría y notificaciones
    if re_evaluate and (results["success"] or force):
        print("\nRegenerando catálogo de notificaciones y actualizando auditoría...")
        eval_script = root / "converters" / "cli" / "evaluate_incident_notifications.py"
        if eval_script.exists():
            cmd = [sys.executable, str(eval_script)]
            res = subprocess.run(cmd, cwd=str(root), capture_output=True, text=True)
            if res.returncode == 0:
                print("[OK] Catálogo high_priority_notifications.json y auditoría ingestion_audit.log actualizados con éxito.")
            else:
                print(f"[WARN] La reevaluación finalizó con código {res.returncode}: {res.stderr[:200]}")
        else:
            print(f"[WARN] No se encontró el script de evaluación en {eval_script}")

    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Relanza la consulta de Resumen IA en Epsilon para incidencias con error o faltantes.")
    parser.add_argument("incidents", nargs="*", help="Códigos de incidencias a relanzar (ej. INC000004173662). Si se omite, se procesan las faltantes.")
    parser.add_argument("--all", action="store_true", help="Relanzar todas las incidencias activas detectadas.")
    parser.add_argument("--force", action="store_true", help="Ignorar caché previa y forzar nueva petición a la API.")
    parser.add_argument("--base-url", type=str, help="URL base específica de Epsilon")
    parser.add_argument("--no-eval", action="store_true", help="No relanzar evaluate_incident_notifications.py al terminar")

    args = parser.parse_args()
    project_root = get_project_root()

    candidate_urls = [args.base_url] if args.base_url else [CORPORATE_EPSILON_URL, LOCAL_PROXY_URL]

    incident_codes = list(args.incidents)
    if not incident_codes:
        if args.all:
            incident_codes = find_all_active_incident_codes(project_root)
        else:
            missing = find_missing_epsilon_incidents(project_root)
            if not missing:
                print("No se encontraron incidencias activas pendientes de Resumen IA en la auditoría actual.")
                print("Todas las incidencias activas ya cuentan con Resumen IA. Usa --all --force si deseas forzar un refresco general.")
                return 0
            incident_codes = missing

    results = retry_incidents(
        incident_codes=incident_codes,
        base_urls=candidate_urls,
        force=args.force,
        re_evaluate=not args.no_eval,
        project_root=project_root,
    )

    return 0 if not results["failed"] else 1


if __name__ == "__main__":
    sys.exit(main())

