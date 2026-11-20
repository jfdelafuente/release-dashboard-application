#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Validador pre-despliegue local y CI para Release Dashboard:
1. Verificación de sintaxis de todos los ficheros JS clave (`node --check`).
2. Compilación de ficheros Python clave (`py_compile`).
3. Ejecución de la suite completa de tests (`pytest`).

Uso:
    python scripts/validate_pre_deploy.py [--skip-pytest]
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import py_compile
import subprocess
import sys

if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent

JS_TARGETS = [
    PROJECT_ROOT / "dashboards" / "release-desk" / "release-desk-domain.js",
    PROJECT_ROOT / "dashboards" / "release-desk" / "release-desk.js",
    PROJECT_ROOT / "dashboards" / "emergency-triage-console" / "triage.js",
    PROJECT_ROOT / "dashboards" / "assets" / "topbar.js",
]

PY_TARGETS = [
    PROJECT_ROOT / "serve_app.py",
    PROJECT_ROOT / "converters" / "src" / "storage_utils.py",
    PROJECT_ROOT / "converters" / "src" / "release_desk_overrides.py",
    PROJECT_ROOT / "converters" / "src" / "desk_service.py",
    PROJECT_ROOT / "converters" / "cli" / "sync_montmc_postmortem.py",
    PROJECT_ROOT / "converters" / "cli" / "update_agent_message.py",
    PROJECT_ROOT / "converters" / "cli" / "incident_manager_service.py",
    PROJECT_ROOT / "converters" / "src" / "fastapi_remedy_router.py",
]


def check_js_syntax() -> bool:
    print("[1/3] Verificando sintaxis JavaScript con node --check...")
    all_ok = True
    for js_file in JS_TARGETS:
        if not js_file.exists():
            print(f"  [!] Fichero no encontrado: {js_file}")
            all_ok = False
            continue
        res = subprocess.run(["node", "--check", str(js_file)], capture_output=True, text=True)
        if res.returncode == 0:
            print(f"  [✓] {js_file.relative_to(PROJECT_ROOT)}")
        else:
            print(f"  [✗] Error de sintaxis en {js_file.relative_to(PROJECT_ROOT)}:\n{res.stderr}")
            all_ok = False
    return all_ok


def check_python_syntax() -> bool:
    print("\n[2/3] Verificando compilación Python (py_compile)...")
    all_ok = True
    for py_file in PY_TARGETS:
        if not py_file.exists():
            print(f"  [!] Fichero no encontrado: {py_file}")
            all_ok = False
            continue
        try:
            py_compile.compile(str(py_file), doraise=True)
            print(f"  [✓] {py_file.relative_to(PROJECT_ROOT)}")
        except Exception as exc:
            print(f"  [✗] Error de sintaxis en {py_file.relative_to(PROJECT_ROOT)}: {exc}")
            all_ok = False
    return all_ok


def run_pytest_suite() -> bool:
    print("\n[3/3] Ejecutando suite de tests pytest...")
    test_files = [
        "converters/tests/unit/test_release_desk.py",
        "converters/tests/unit/test_sync_montmc_postmortem.py",
        "converters/tests/unit/test_m18_storage_concurrency.py",
        "converters/tests/unit/test_m19_health_and_parallel_sync.py",
        "converters/tests/unit/test_m20_ci_and_smoke_tests.py",
        "converters/tests/unit/test_m21_desk_service.py",
        "converters/tests/unit/test_fastapi_remedy_router.py",
        "converters/tests/unit/test_serve_app_remedy.py",
    ]
    cmd = [sys.executable, "-m", "pytest"] + test_files + ["-v"]
    env = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}
    res = subprocess.run(cmd, cwd=str(PROJECT_ROOT), env=env)
    return res.returncode == 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Validación pre-despliegue Release Dashboard")
    parser.add_argument("--skip-pytest", action="store_true", help="Omite la ejecución de pytest")
    args = parser.parse_args()

    js_ok = check_js_syntax()
    py_ok = check_python_syntax()
    tests_ok = True if args.skip_pytest else run_pytest_suite()

    print("\n" + ("=" * 60))
    if js_ok and py_ok and tests_ok:
        print("VALIDACIÓN PRE-DESPLIEGUE EXITOSA: TODO CORRECTO")
        print("=" * 60)
        return 0
    else:
        print("VALIDACIÓN PRE-DESPLIEGUE FALLIDA")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
