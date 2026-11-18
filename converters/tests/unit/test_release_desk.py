"""
Tests unitarios para la consola Mesa de Release (dashboards/release-desk/)
y su registro en dashboards/assets/topbar.js.
"""

import json
import shutil
import subprocess
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
TOPBAR_JS = PROJECT_ROOT / "dashboards" / "assets" / "topbar.js"
RELEASE_DESK_HTML = PROJECT_ROOT / "dashboards" / "release-desk" / "index.html"
RELEASE_DESK_JS = PROJECT_ROOT / "dashboards" / "release-desk" / "release-desk.js"


def test_topbar_includes_release_desk_link():
    content = TOPBAR_JS.read_text(encoding="utf-8")
    assert "id: 'release-desk'" in content
    assert "label: 'Mesa de Release'" in content
    assert "href: '/dashboards/release-desk/'" in content


def test_release_desk_html_has_required_controls():
    html = RELEASE_DESK_HTML.read_text(encoding="utf-8")
    for required_id in (
        "mo-topbar-root",
        'data-active="release-desk"',
        "releaseSelect",
        "btnSyncPostmortem",
        "btnEmptySync",
        "filterSearch",
        "filterStatus",
        "filterGroup",
        "filterPriority",
        "filterProject",
        "btnCopyFollowup",
        "incidentsTableBody",
        "detailBody",
    ):
        assert required_id in html, f"Falta {required_id} en release-desk/index.html"

    for col in (
        "Código Incidencia",
        "Fecha Apertura",
        "Descripción problema",
        "Impacto Remedy",
        "Sistema",
        "JIRA",
        "PROYECTO",
        "Acciones",
        "Status",
        "Fecha Prevista",
        "Motivo Estado Resuelto",
        "Peticionario",
    ):
        assert f"<th>{col}</th>" in html, f"Falta columna {col} en release-desk/index.html"


def test_release_desk_js_uses_postmortem_and_resumen_ia_only():
    js = RELEASE_DESK_JS.read_text(encoding="utf-8")
    assert "/data/output/index.json" in js
    assert "/data/projects_catalog.json" in js
    assert "/api/sync-postmortem" in js
    assert "/api/epsilon/resumenIA/" in js
    assert "Problema Detectado" in js
    assert "high_priority_notifications.json" not in js
    assert "-massive.json" not in js


def test_projects_catalog_json_valid():
    catalog_path = PROJECT_ROOT / "data" / "projects_catalog.json"
    if not catalog_path.exists():
        pytest.skip("data/projects_catalog.json es un fichero local (gitignored)")
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    assert "2026R11" in catalog.get("by_release", {})
    assert "PRJ-12305" in catalog["by_release"]["2026R11"]
    assert catalog["by_release"]["2026R11"]["PRJ-12305"]["despliegue"] == "Completo"
    assert "PRJ-11894" in catalog.get("projects", {})
    assert catalog["projects"]["PRJ-11894"]["despliegue"] == "Piloto"


def test_update_projects_catalog_preserves_older_releases(tmp_path: Path):
    import sys
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    from converters.cli.update_projects_catalog import update_projects_catalog

    csv_r11 = tmp_path / "2026R11.csv"
    csv_r11.write_text("JIRA;Summary;Despliegue;Descripcion\nPRJ-100;Proyecto R11;Completo;Desc R11\n", encoding="utf-8")
    csv_r12 = tmp_path / "2026R12.csv"
    csv_r12.write_text("JIRA;Summary;Despliegue;Descripcion\nPRJ-200;Proyecto R12;Piloto;Desc R12\n", encoding="utf-8")
    catalog_file = tmp_path / "projects_catalog.json"

    update_projects_catalog(csv_r11, "2026R11", catalog_file)
    update_projects_catalog(csv_r12, "2026R12", catalog_file)

    data = json.loads(catalog_file.read_text(encoding="utf-8"))
    assert "2026R11" in data["by_release"]
    assert "2026R12" in data["by_release"]
    assert "PRJ-100" in data["by_release"]["2026R11"]
    assert "PRJ-200" in data["by_release"]["2026R12"]
    assert "PRJ-100" in data["projects"]
    assert "PRJ-200" in data["projects"]


def test_release_desk_js_excludes_only_closed_status():
    if shutil.which("node") is not None:
        script = (
            f"const rd = require({json.dumps(str(RELEASE_DESK_JS))});\n"
            "const records = [\n"
            "  { 'ID de incidencia': 'INC1', 'Estatus': 'Cerrado' },\n"
            "  { 'ID de incidencia': 'INC2', 'Estatus': ' cerrado ' },\n"
            "  { 'ID de incidencia': 'INC3', 'Estatus': 'Asignado' },\n"
            "  { 'ID de incidencia': 'INC4', 'Estatus': 'En Curso' },\n"
            "  { 'ID de incidencia': 'INC5', 'Estatus': 'Pendiente' },\n"
            "  { 'ID de incidencia': 'INC6', 'Estatus': 'Resuelto' }\n"
            "];\n"
            "const active = rd.filterNonClosedIncidents(records);\n"
            "const txt = rd.buildFollowupText(active[0], { resumenEjecutivo: 'Test IA' }, '2026R9');\n"
            "console.log(JSON.stringify({ ids: active.map(r => r['ID de incidencia']), txt }));\n"
        )
        proc = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True)
        out = json.loads(proc.stdout)
        assert out["ids"] == ["INC3", "INC4", "INC5", "INC6"]
        assert "[2026R9] INC3" in out["txt"]
        assert "Resumen IA: Test IA" in out["txt"]
    else:
        js = RELEASE_DESK_JS.read_text(encoding="utf-8")
        assert "String(status).trim().toLowerCase() === 'cerrado'" in js
        assert "!isClosedStatus(rec['Estatus'])" in js
        assert "buildFollowupText" in js
