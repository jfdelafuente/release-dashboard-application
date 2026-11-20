#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Smoke Test HTTP post-despliegue y validación de endpoints para:
- Mesa de Release (/dashboards/release-desk/)
- Consola de Triaje (/dashboards/emergency-triage-console/)
- Endpoints compartidos (/api/health/release-desk, /api/epsilon/resumenIA/cached, etc.)

Uso:
    python scripts/smoke_test_endpoints.py [--base-url http://localhost:8080] [--timeout 5]
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from typing import Any, Dict, List, Tuple


ENDPOINTS: List[Tuple[str, str, int, str]] = [
    ("Portal", "/dashboards/portal/", 200, "text/html"),
    ("Mesa de Release UI", "/dashboards/release-desk/", 200, "text/html"),
    ("Mesa de Release CSS", "/dashboards/release-desk/release-desk.css", 200, "text/css"),
    ("Mesa de Release Domain JS", "/dashboards/release-desk/release-desk-domain.js", 200, "application/javascript"),
    ("Mesa de Release UI JS", "/dashboards/release-desk/release-desk.js", 200, "application/javascript"),
    ("Consola Triaje UI", "/dashboards/emergency-triage-console/", 200, "text/html"),
    ("Consola Triaje JS", "/dashboards/emergency-triage-console/triage.js", 200, "application/javascript"),
    ("Health General", "/api/health", 200, "application/json"),
    ("Health Release Desk (M19)", "/api/health/release-desk", 200, "application/json"),
    ("Epsilon Resumen IA Cached", "/api/epsilon/resumenIA/cached", 200, "application/json"),
    ("Overrides Release Desk", "/api/release-desk/overrides?release=2026R11", 200, "application/json"),
]


def check_endpoint(base_url: str, name: str, path: str, expected_status: int, timeout: float = 5.0) -> Dict[str, Any]:
    url = f"{base_url.rstrip('/')}{path}"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "ReleaseDashboardSmokeTest/1.0", "Accept": "*/*"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = resp.status
            body = resp.read()
            is_json = "application/json" in (resp.headers.get("Content-Type") or "").lower()
            parsed_json = None
            if is_json:
                try:
                    parsed_json = json.loads(body.decode("utf-8"))
                except Exception:
                    pass
            ok = (status == expected_status)
            return {
                "name": name,
                "path": path,
                "url": url,
                "status": status,
                "expected_status": expected_status,
                "ok": ok,
                "size_bytes": len(body),
                "is_json": is_json,
                "json_valid": parsed_json is not None if is_json else True,
                "error": None,
            }
    except urllib.error.HTTPError as exc:
        return {
            "name": name,
            "path": path,
            "url": url,
            "status": exc.code,
            "expected_status": expected_status,
            "ok": exc.code == expected_status,
            "size_bytes": 0,
            "is_json": False,
            "json_valid": False,
            "error": str(exc),
        }
    except Exception as exc:
        return {
            "name": name,
            "path": path,
            "url": url,
            "status": 0,
            "expected_status": expected_status,
            "ok": False,
            "size_bytes": 0,
            "is_json": False,
            "json_valid": False,
            "error": str(exc),
        }


def run_smoke_tests(base_url: str, timeout: float = 5.0) -> Tuple[bool, List[Dict[str, Any]]]:
    results = []
    all_ok = True
    for name, path, expected_status, _ in ENDPOINTS:
        res = check_endpoint(base_url, name, path, expected_status, timeout=timeout)
        results.append(res)
        if not res["ok"] or (res["is_json"] and not res["json_valid"]):
            all_ok = False
    return all_ok, results


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke test HTTP para Release Dashboard y consolas")
    parser.add_argument("--base-url", default="http://127.0.0.1:8080", help="URL base del servidor (default: http://127.0.0.1:8080)")
    parser.add_argument("--timeout", type=float, default=5.0, help="Timeout en segundos por petición")
    args = parser.parse_args()

    print(f"Iniciando Smoke Test contra {args.base_url} ...\n")
    all_ok, results = run_smoke_tests(args.base_url, timeout=args.timeout)

    for r in results:
        status_str = f"HTTP {r['status']}" if r['status'] > 0 else "CONEXIÓN FALLIDA"
        icon = "✓" if r["ok"] and (not r["is_json"] or r["json_valid"]) else "✗"
        print(f"  [{icon}] {r['name']:<28} {r['path']:<45} -> {status_str} (esperado {r['expected_status']})")
        if r["error"]:
            print(f"      Error: {r['error']}")

    print("\n" + ("=" * 60))
    if all_ok:
        print("RESULTADO: TODOS LOS ENDPOINTS HAN RESPONDIDO CORRECTAMENTE (OK)")
        print("=" * 60)
        return 0
    else:
        print("RESULTADO: AL MENOS UN ENDPOINT HA FALLADO")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
