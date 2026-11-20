# -*- coding: utf-8 -*-
"""Tests unitarios M20: scripts de validación pre-despliegue y smoke test HTTP."""

import json
from pathlib import Path
import subprocess
import sys

from scripts.smoke_test_endpoints import ENDPOINTS, check_endpoint
from scripts.validate_pre_deploy import JS_TARGETS, PY_TARGETS, check_js_syntax, check_python_syntax


def test_js_targets_exist_and_pass_syntax():
    assert len(JS_TARGETS) >= 4
    for target in JS_TARGETS:
        assert target.exists(), f"Fichero JS faltante: {target}"
    assert check_js_syntax() is True


def test_python_targets_exist_and_compile():
    assert len(PY_TARGETS) >= 7
    for target in PY_TARGETS:
        assert target.exists(), f"Fichero Python faltante: {target}"
    assert check_python_syntax() is True


def test_endpoints_manifest_covers_both_consoles():
    names = [entry[0] for entry in ENDPOINTS]
    paths = [entry[1] for entry in ENDPOINTS]

    assert any("Release" in n for n in names)
    assert any("Triaje" in n for n in names)
    assert "/dashboards/release-desk/" in paths
    assert "/dashboards/emergency-triage-console/" in paths
    assert "/api/health/release-desk" in paths
    assert "/api/epsilon/resumenIA/cached" in paths


def test_smoke_check_endpoint_handles_http_errors():
    res = check_endpoint("http://127.0.0.1:99999", "Dummy", "/test", 200, timeout=0.2)
    assert res["ok"] is False
    assert res["status"] == 0
    assert res["error"] is not None
