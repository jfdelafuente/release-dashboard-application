"""
Tests unitarios para la consola Mesa de Release (dashboards/release-desk/)
y su registro en dashboards/assets/topbar.js.
"""

import json
import re
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
        "btnCopyBriefing",
        "btnCopyBriefingSystem",
        "btnExportCsv",
        "filterSearch",
        "filterStatus",
        "filterGroup",
        "filterPriority",
        "filterProject",
        "incidentsTableBody",
    ):
        assert required_id in html, f"Falta {required_id} en release-desk/index.html"

    for col in (
        "Código Incidencia",
        "Fecha Apertura",
        "Descripción problema",
        "Prioridad / Urg.",
        "Sistema",
        "JIRA",
        "PROYECTO",
        "Acciones",
        "Status",
        "Fecha Prevista",
        "Motivo Estado Resuelto",
        "Grupo Peticionario",
    ):
        assert re.search(rf"<th\b[^>]*>{re.escape(col)}(?:<span[^>]*></span>)?</th>", html), (
            f"Falta columna {col} en release-desk/index.html"
        )


def test_release_desk_js_uses_postmortem_and_resumen_ia_only():
    js = RELEASE_DESK_JS.read_text(encoding="utf-8")
    assert "/data/output/index.json" in js
    assert "/data/projects_catalog.json" in js
    assert "/api/sync-postmortem" in js
    assert "/api/epsilon/resumenIA/" in js
    assert "Problema Detectado" in js
    assert "rd-detail-row" in js
    assert "btnCopyFollowup" in js
    assert "/api/release-desk/overrides" in js
    assert "high_priority_notifications.json" not in js
    assert "-massive.json" not in js


def test_projects_catalog_json_valid():
    catalog_path = PROJECT_ROOT / "data" / "projects_catalog.json"
    if not catalog_path.exists():
        pytest.skip("data/projects_catalog.json es un fichero local (gitignored)")
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    assert isinstance(catalog.get("by_release"), dict)
    assert isinstance(catalog.get("projects"), dict)
    assert len(catalog["by_release"]) >= 1
    assert len(catalog["projects"]) >= 1


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


def test_release_desk_overrides_persist_and_clear(tmp_path: Path):
    import sys
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    from converters.src.release_desk_overrides import (
        get_overrides_for_release,
        set_fecha_prevista_override,
    )

    res = set_fecha_prevista_override(tmp_path, "2026R9", "INC000004140329", "2026-11-22")
    assert res["success"] is True
    assert res["overrides"]["INC000004140329"]["fecha_prevista"] == "2026-11-22"

    set_fecha_prevista_override(tmp_path, "2026R11", "INC000004999999", "2026-12-01")
    assert get_overrides_for_release(tmp_path, "2026R9")["INC000004140329"]["fecha_prevista"] == "2026-11-22"
    assert get_overrides_for_release(tmp_path, "2026R11")["INC000004999999"]["fecha_prevista"] == "2026-12-01"

    cleared = set_fecha_prevista_override(tmp_path, "2026R9", "INC000004140329", "")
    assert "INC000004140329" not in cleared["overrides"]
    assert "INC000004999999" in get_overrides_for_release(tmp_path, "2026R11")


def test_release_desk_js_compute_open_age_days():
    if shutil.which("node") is not None:
        script = (
            f"const rd = require({json.dumps(str(RELEASE_DESK_JS))});\n"
            "const ref = new Date(2026, 10, 18, 12, 0, 0);\n"
            "console.log(JSON.stringify({\n"
            "  d10: rd.computeOpenAgeDays('08/11/2026 10:00', ref),\n"
            "  d4: rd.computeOpenAgeDays('14/11/2026 09:00', ref),\n"
            "  iso: rd.computeOpenAgeDays('2026-11-10T08:00:00Z', ref),\n"
            "  bad: rd.computeOpenAgeDays('-', ref)\n"
            "}));\n"
        )
        proc = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True)
        out = json.loads(proc.stdout)
        assert out["d10"] == 10
        assert out["d4"] == 4
        assert out["iso"] >= 7
        assert out["bad"] is None
    else:
        js = RELEASE_DESK_JS.read_text(encoding="utf-8")
        assert "computeOpenAgeDays" in js


def test_load_cached_epsilon_summaries_zero_cost(tmp_path: Path):
    import sys
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    from converters.src.release_desk_overrides import load_cached_epsilon_summaries

    cache_dir = tmp_path / ".epsilon_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    (cache_dir / "INC000004122361.json").write_text(
        json.dumps({"success": True, "problema": "Error test", "siguienteAccion": "Revisar logs"}),
        encoding="utf-8",
    )
    (cache_dir / "INC000004999999.json").write_text(
        json.dumps({"success": False, "error": "fallo"}),
        encoding="utf-8",
    )

    res = load_cached_epsilon_summaries(tmp_path, ["INC000004122361", "INC000004999999", "INC000000000000"])
    assert list(res.keys()) == ["INC000004122361"]
    assert res["INC000004122361"]["_from_disk_cache"] is True
    assert isinstance(res["INC000004122361"]["_cached_at_ms"], int)


def test_release_desk_js_is_ia_cache_stale():
    if shutil.which("node") is not None:
        script = (
            f"const rd = require({json.dumps(str(RELEASE_DESK_JS))});\n"
            "const cachedMs = Date.parse('2026-11-18T10:00:00Z');\n"
            "console.log(JSON.stringify({\n"
            "  newer: rd.isIaCacheStale({ _cached_at_ms: cachedMs }, { fechaUltimaModificacion: '2026-11-18T12:00:00Z' }),\n"
            "  older: rd.isIaCacheStale({ _cached_at_ms: cachedMs }, { fechaUltimaModificacion: '2026-11-18T09:00:00Z' }),\n"
            "  missing: rd.isIaCacheStale({ _cached_at_ms: cachedMs }, {})\n"
            "}));\n"
        )
        proc = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True)
        out = json.loads(proc.stdout)
        assert out == {"newer": True, "older": False, "missing": False}
    else:
        js = RELEASE_DESK_JS.read_text(encoding="utf-8")
        assert "isIaCacheStale" in js


def test_release_desk_js_matches_kpi_filter():
    if shutil.which("node") is not None:
        script = (
            f"const rd = require({json.dumps(str(RELEASE_DESK_JS))});\n"
            "const p1 = { 'Prioridad': 'Crítica (P1)', 'Estatus': 'En Curso' };\n"
            "const p3 = { 'Prioridad': 'Media', 'Estatus': 'Asignado' };\n"
            "const res = { 'Prioridad': 'Alta', 'Estatus': 'Resuelto' };\n"
            "console.log(JSON.stringify({\n"
            "  crit: [rd.matchesKpiFilter(p1, 'crit_high'), rd.matchesKpiFilter(p3, 'crit_high')],\n"
            "  prog: [rd.matchesKpiFilter(p1, 'in_progress'), rd.matchesKpiFilter(res, 'in_progress')],\n"
            "  res: [rd.matchesKpiFilter(p1, 'resolved'), rd.matchesKpiFilter(res, 'resolved')],\n"
            "  all: rd.matchesKpiFilter(p3, 'all')\n"
            "}));\n"
        )
        proc = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True)
        out = json.loads(proc.stdout)
        assert out == {"crit": [True, False], "prog": [True, False], "res": [False, True], "all": True}
    else:
        js = RELEASE_DESK_JS.read_text(encoding="utf-8")
        assert "matchesKpiFilter" in js


def test_release_desk_js_build_export_csv():
    if shutil.which("node") is not None:
        script = (
            f"const rd = require({json.dumps(str(RELEASE_DESK_JS))});\n"
            "const incidents = [\n"
            "  {\n"
            "    'ID de incidencia': 'INC000001',\n"
            "    'Fecha de envío': '2026-11-10 09:00',\n"
            "    'Descripción': 'Error \"crítico\" en\\nlínea',\n"
            "    'Prioridad': 'Alta',\n"
            "    'producto': 'AURORA',\n"
            "    'Grupo asignado': 'PORTAL',\n"
            "    'JIRA': 'JIRA-123',\n"
            "    'Estatus': 'En Curso',\n"
            "    'Grupo Remitente': 'N1 Soporte',\n"
            "    'Motivo de estado': ''\n"
            "  }\n"
            "];\n"
            "const iaCache = new Map([['INC000001', { problema: 'Resumen IA problema', siguienteAccion: 'Reiniciar servicio' }]]);\n"
            "const overrides = { 'INC000001': { fecha_prevista: '2026-11-25' } };\n"
            "const csv = rd.buildExportCsv(incidents, iaCache, {}, '2026R11', overrides);\n"
            "console.log(JSON.stringify({ hasBom: csv.startsWith('\\uFEFF'), lines: csv.slice(1).split('\\r\\n') }));\n"
        )
        proc = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True)
        out = json.loads(proc.stdout)
        assert out["hasBom"] is True
        assert len(out["lines"]) == 2
        assert out["lines"][0].startswith('"Código Incidencia";"Fecha Apertura";"Descripción problema"')
        assert '"INC000001";"2026-11-10 09:00";"[AURORA] Resumen IA problema";"Alta";"PORTAL";"JIRA-123";"-";"Reiniciar servicio";"En Curso";"2026-11-25";"-";"N1 Soporte"' == out["lines"][1]
    else:
        js = RELEASE_DESK_JS.read_text(encoding="utf-8")
        assert "buildExportCsv" in js


def test_release_desk_js_sort_incidents():
    if shutil.which("node") is not None:
        script = (
            f"const rd = require({json.dumps(str(RELEASE_DESK_JS))});\n"
            "const a = { 'ID de incidencia': 'INC2', 'Prioridad': 'Media', 'Fecha de envío': '10/11/2026 09:00', 'Estatus': 'Asignado' };\n"
            "const b = { 'ID de incidencia': 'INC1', 'Prioridad': 'Crítica (P1)', 'Fecha de envío': '05/11/2026 08:00', 'Estatus': 'En Curso' };\n"
            "const c = { 'ID de incidencia': 'INC3', 'Prioridad': 'Alta', 'Fecha de envío': '12/11/2026 10:00', 'Estatus': 'Resuelto', 'Fecha de última resolución': '2026-11-15' };\n"
            "const byPrioAsc = rd.sortIncidents([a, b, c], 'prioridad', 'asc', {}, '2026R11', {}).map(x => x['ID de incidencia']);\n"
            "const byDateDesc = rd.sortIncidents([a, b, c], 'fecha_apertura', 'desc', {}, '2026R11', {}).map(x => x['ID de incidencia']);\n"
            "const overrides = { 'INC2': { fecha_prevista: '2026-11-20' } };\n"
            "const byPrevAsc = rd.sortIncidents([a, b, c], 'fecha_prevista', 'asc', {}, '2026R11', overrides).map(x => x['ID de incidencia']);\n"
            "console.log(JSON.stringify({ byPrioAsc, byDateDesc, byPrevAsc }));\n"
        )
        proc = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True)
        out = json.loads(proc.stdout)
        assert out["byPrioAsc"] == ["INC1", "INC3", "INC2"]
        assert out["byDateDesc"] == ["INC3", "INC2", "INC1"]
        assert out["byPrevAsc"] == ["INC3", "INC2", "INC1"]
    else:
        js = RELEASE_DESK_JS.read_text(encoding="utf-8")
        assert "sortIncidents" in js


def test_release_desk_js_build_mesa_briefing():
    if shutil.which("node") is not None:
        script = (
            f"const rd = require({json.dumps(str(RELEASE_DESK_JS))});\n"
            "const incidents = [\n"
            "  { 'ID de incidencia': 'INC1', 'Prioridad': 'Crítica (P1)', 'producto': 'AURORA', 'Descripción': '[2026R11] PRJ-101 Fallo login', 'Estatus': 'En Curso', 'Grupo asignado': 'SOP_A' },\n"
            "  { 'ID de incidencia': 'INC2', 'Prioridad': 'Media', 'Descripción': 'Consulta menor', 'Estatus': 'Resuelto', 'Fecha de última resolución': '17/11/2026' }\n"
            "];\n"
            "const iaCache = new Map([['INC1', { problema: 'Fallo login PRO', siguienteAccion: 'Reiniciar nodo' }]]);\n"
            "const catalog = { by_release: { '2026R11': { 'PRJ-101': { summary: 'Portal B2B', despliegue: 'Piloto' } } } };\n"
            "const overrides = { 'INC1': { fecha_prevista: '2026-11-10' } };\n"
            "const res = rd.buildMesaBriefing(incidents, iaCache, catalog, '2026R11', overrides, '2026-11-18T12:00:00Z');\n"
            "console.log(JSON.stringify(res));\n"
        )
        proc = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True)
        out = json.loads(proc.stdout)
        assert "Briefing Mesa de Release 2026R11 (2026-11-18)" in out["text"]
        assert "Total visibles: 2 | Resueltas: 1 | Compromisos vencidos: 1" in out["text"]
        assert "[Crítica (P1)] (1)" in out["text"]
        assert "⚠️ VENCIDA 2026-11-10" in out["text"]
        assert "[Piloto] PRJ-101 — Portal B2B" in out["text"]
        assert "Acción: Reiniciar nodo" in out["text"]
        assert "[Media (P3)] (1)" in out["text"]
        assert "<ul><li><strong>INC1</strong>" in out["html"]
        assert "<em>Acción:</em> Reiniciar nodo" in out["html"]
    else:
        js = RELEASE_DESK_JS.read_text(encoding="utf-8")
        assert "buildMesaBriefing" in js


def test_release_desk_js_build_mesa_briefing_by_system():
    if shutil.which("node") is not None:
        script = (
            f"const rd = require({json.dumps(str(RELEASE_DESK_JS))});\n"
            "const incidents = [\n"
            "  { 'ID de incidencia': 'INC1', 'Prioridad': 'Media', 'Descripción': 'Error A', 'Estatus': 'Asignado', 'Grupo asignado': 'SOP_SMC_GIROS' },\n"
            "  { 'ID de incidencia': 'INC2', 'Prioridad': 'Crítica (P1)', 'Descripción': 'Error B', 'Estatus': 'En Curso', 'Grupo asignado': 'DES_CRM4T' },\n"
            "  { 'ID de incidencia': 'INC3', 'Prioridad': 'Alta', 'Descripción': 'Error C', 'Estatus': 'Asignado', 'Grupo asignado': 'SOP_SMC_GIROS' }\n"
            "];\n"
            "const res = rd.buildMesaBriefingBySystem(incidents, null, {}, '2026R11', {}, '2026-11-18T12:00:00Z');\n"
            "console.log(JSON.stringify(res));\n"
        )
        proc = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True)
        out = json.loads(proc.stdout)
        assert "Briefing Mesa de Release por Sistema 2026R11 (2026-11-18)" in out["text"]
        assert "[DES_CRM4T] (1)" in out["text"]
        assert "[SOP_SMC_GIROS] (2)" in out["text"]
        assert out["text"].index("INC3") < out["text"].index("INC1")
        assert "<strong>SOP_SMC_GIROS (2)</strong>" in out["html"]
        assert "<li><strong>INC3</strong>" in out["html"]
    else:
        js = RELEASE_DESK_JS.read_text(encoding="utf-8")
        assert "buildMesaBriefingBySystem" in js
