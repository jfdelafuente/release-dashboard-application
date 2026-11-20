"""Tests unitarios para converters/cli/open_release.py."""

import json
import sys
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from converters.cli.open_release import (
    find_candidate_projects_csv,
    normalize_fecha_pap,
    open_release,
    parse_release_code,
    register_release_in_js,
)


def test_parse_release_code_valid_and_invalid():
    assert parse_release_code("2026R12") == ("2026R12", 2026, 12, "Diciembre")
    assert parse_release_code("2026r9") == ("2026R9", 2026, 9, "Septiembre")

    with pytest.raises(ValueError):
        parse_release_code("R12")
    with pytest.raises(ValueError):
        parse_release_code("2026R13")


def test_normalize_fecha_pap():
    assert normalize_fecha_pap("22/11/2026") == "22-nov."
    assert normalize_fecha_pap("22-11-2026") == "22-nov."
    assert normalize_fecha_pap("2026-11-22") == "22-nov."
    assert normalize_fecha_pap("2026/12/15") == "15-dic."
    assert normalize_fecha_pap("7/6/2026") == "7-jun."
    assert normalize_fecha_pap("07/06/2026") == "7-jun."
    assert normalize_fecha_pap("22 de noviembre") == "22-nov."
    assert normalize_fecha_pap("13-dic.") == "13-dic."
    assert normalize_fecha_pap("13-dic") == "13-dic."
    assert normalize_fecha_pap("") == ""
    assert normalize_fecha_pap(None) == ""


def test_register_release_in_js_normalizes_freeform_date(tmp_path: Path):
    js_file = tmp_path / "releases-data.js"
    js_file.write_text(
        '"use strict";\nconst RAW_RELEASES = [\n  ["2026R10", 2026, "", "Octubre", 0, 0, 0, 0],\n];\n',
        encoding="utf-8",
    )
    res = register_release_in_js("2026R11", fecha_pap="22/11/2026", releases_js_path=js_file)
    assert res["added"] is True
    assert res["fecha_pap"] == "22-nov."
    content = js_file.read_text(encoding="utf-8")
    assert '["2026R11", 2026, "22-nov.", "Noviembre", 0, 0, 0, 0],' in content


def test_find_candidate_projects_csv_and_auto_import(tmp_path: Path):
    proj_dir = tmp_path / "data" / "projects"
    proj_dir.mkdir(parents=True)
    csv_file = proj_dir / "2026R12.csv"
    csv_file.write_text("JIRA;Summary;Despliegue;Descripcion\nPRJ-100;Test Candidate;Completo;AutoDesc\n", encoding="utf-8")

    candidate = find_candidate_projects_csv("2026R12", base_dir=tmp_path)
    assert candidate is not None
    assert candidate.resolve() == csv_file.resolve()

    js_file = tmp_path / "dashboards" / "release-kpis" / "releases-data.js"
    js_file.parent.mkdir(parents=True)
    js_file.write_text('"use strict";\nconst RAW_RELEASES = [\n];\n', encoding="utf-8")
    catalog_file = tmp_path / "data" / "projects_catalog.json"

    res = open_release(
        "2026R12",
        fecha_pap="15/12/2026",
        catalog_path=catalog_file,
        releases_js_path=js_file,
        auto_detect_projects=True,
    )
    assert res["success"] is True
    assert res["projects_catalog"]["imported_count"] == 1
    assert res["projects_catalog"]["auto_detected"] is True


def test_register_release_in_js_idempotent(tmp_path: Path):
    js_file = tmp_path / "releases-data.js"
    js_file.write_text(
        '"use strict";\nconst RAW_RELEASES = [\n  ["2026R11", 2026, "", "Noviembre", 0, 0, 0, 0],\n];\n',
        encoding="utf-8",
    )

    first = register_release_in_js("2026R12", fecha_pap="13-dic.", releases_js_path=js_file)
    assert first["added"] is True
    assert first["already_exists"] is False
    content = js_file.read_text(encoding="utf-8")
    assert '["2026R12", 2026, "13-dic.", "Diciembre", 0, 0, 0, 0],' in content

    second = register_release_in_js("2026R12", releases_js_path=js_file)
    assert second["added"] is False
    assert second["already_exists"] is True


def test_open_release_with_projects_csv(tmp_path: Path):
    js_file = tmp_path / "releases-data.js"
    js_file.write_text(
        '"use strict";\nconst RAW_RELEASES = [\n  ["2026R11", 2026, "", "Noviembre", 0, 0, 0, 0],\n];\n',
        encoding="utf-8",
    )
    csv_file = tmp_path / "proyectos_r12.csv"
    csv_file.write_text("JIRA;Summary;Despliegue;Descripcion\nPRJ-99999;Proyecto Test R12;Completo;Desc\n", encoding="utf-8")
    catalog_file = tmp_path / "projects_catalog.json"

    res = open_release(
        "2026R12",
        projects_csv=csv_file,
        catalog_path=catalog_file,
        releases_js_path=js_file,
    )
    assert res["success"] is True
    assert res["releases_data"]["added"] is True
    assert res["projects_catalog"]["imported_count"] == 1

    catalog = json.loads(catalog_file.read_text(encoding="utf-8"))
    assert "PRJ-99999" in catalog["by_release"]["2026R12"]
