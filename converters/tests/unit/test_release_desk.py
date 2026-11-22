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


def _run_node_script(script: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["node", "-e", script],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )


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
        "btnViewTable",
        "btnViewByProject",
        "projectSummaryView",
        "filterSearch",
        "filterStatus",
        "filterGroup",
        "filterPriority",
        "filterProject",
        "incidentsTableBody",
    ):
        assert required_id in html, f"Falta {required_id} en release-desk/index.html"

    assert 'aria-label="Filtrar por sistema"' in html
    assert "Todos los sistemas" in html

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
    assert "Todos los sistemas" in js
    assert "high_priority_notifications.json" not in js
    assert "-massive.json" not in js


def test_projects_catalog_json_valid():
    catalog_path = PROJECT_ROOT / "data" / "config" / "projects_catalog.json"
    if not catalog_path.exists():
        catalog_path = PROJECT_ROOT / "data" / "projects_catalog.json"
    if not catalog_path.exists():
        pytest.skip("data/config/projects_catalog.json es un fichero local (gitignored)")
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
        proc = _run_node_script(script)
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
        proc = _run_node_script(script)
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
        proc = _run_node_script(script)
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
        proc = _run_node_script(script)
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
            "  },\n"
            "  {\n"
            "    'ID de incidencia': 'INC000002',\n"
            "    'Fecha de envío': '2026-11-11 10:00',\n"
            "    'Descripción': 'Otro problema',\n"
            "    'Prioridad': 'P3',\n"
            "    'Urgencia': 'Medio',\n"
            "    'Estatus': 'Asignado'\n"
            "  }\n"
            "];\n"
            "const iaCache = new Map([['INC000001', { problema: 'Resumen IA problema', siguienteAccion: 'Reiniciar servicio' }]]);\n"
            "const overrides = { 'INC000001': { fecha_prevista: '2026-11-25' } };\n"
            "const csv = rd.buildExportCsv(incidents, iaCache, {}, '2026R11', overrides);\n"
            "console.log(JSON.stringify({ hasBom: csv.startsWith('\\uFEFF'), lines: csv.slice(1).split('\\r\\n') }));\n"
        )
        proc = _run_node_script(script)
        out = json.loads(proc.stdout)
        assert out["hasBom"] is True
        assert len(out["lines"]) == 3
        assert out["lines"][0].startswith('"Código Incidencia";"Fecha Apertura";"Descripción problema"')
        assert '"INC000001";"2026-11-10 09:00";"[AURORA] Resumen IA problema";"Alta";"PORTAL";"JIRA-123";"-";"Reiniciar servicio";"En Curso";"2026-11-25";"-";"N1 Soporte"' == out["lines"][1]
        assert '"INC000002";"2026-11-11 10:00";"Otro problema";"P3 / Medio";"-";"";"-";"-";"Asignado";"";"-";"-"' == out["lines"][2]
    else:
        js = RELEASE_DESK_JS.read_text(encoding="utf-8")
        assert "buildExportCsv" in js


def test_release_desk_js_build_export_filename():
    if shutil.which("node") is not None:
        script = (
            f"const rd = require({json.dumps(str(RELEASE_DESK_JS))});\n"
            "const fixedDate = new Date(2026, 10, 22, 12, 47, 30);\n"
            "const fn1 = rd.buildExportFilename('2026R11', fixedDate);\n"
            "const fn2 = rd.buildExportFilename();\n"
            "console.log(JSON.stringify({ fn1, fn2 }));\n"
        )
        proc = _run_node_script(script)
        out = json.loads(proc.stdout)
        assert out["fn1"] == "mesa-release-2026R11_20261122_124730.csv"
        assert out["fn2"].startswith("mesa-release-release_")
        assert out["fn2"].endswith(".csv")
    else:
        js = RELEASE_DESK_JS.read_text(encoding="utf-8")
        assert "buildExportFilename" in js


def test_release_desk_js_sort_incidents():
    if shutil.which("node") is not None:
        script = (
            f"const rd = require({json.dumps(str(RELEASE_DESK_JS))});\n"
            "const a = { 'ID de incidencia': 'INC2', 'Prioridad': 'Media', 'Fecha de envío': '10/11/2026 09:00', 'Estatus': 'Asignado', 'Grupo asignado': 'SOP_TEIDE' };\n"
            "const b = { 'ID de incidencia': 'INC1', 'Prioridad': 'Crítica (P1)', 'Fecha de envío': '05/11/2026 08:00', 'Estatus': 'En Curso', 'Grupo asignado': 'CEP_CAU' };\n"
            "const c = { 'ID de incidencia': 'INC3', 'Prioridad': 'Alta', 'Fecha de envío': '12/11/2026 10:00', 'Estatus': 'Resuelto', 'Fecha de última resolución': '2026-11-15', 'Grupo asignado': 'DES_CRM' };\n"
            "const byPrioAsc = rd.sortIncidents([a, b, c], 'prioridad', 'asc', {}, '2026R11', {}).map(x => x['ID de incidencia']);\n"
            "const byDateDesc = rd.sortIncidents([a, b, c], 'fecha_apertura', 'desc', {}, '2026R11', {}).map(x => x['ID de incidencia']);\n"
            "const bySistemaAsc = rd.sortIncidents([a, b, c], 'sistema', 'asc', {}, '2026R11', {}).map(x => x['ID de incidencia']);\n"
            "const overrides = { 'INC2': { fecha_prevista: '2026-11-20' } };\n"
            "const byPrevAsc = rd.sortIncidents([a, b, c], 'fecha_prevista', 'asc', {}, '2026R11', overrides).map(x => x['ID de incidencia']);\n"
            "console.log(JSON.stringify({ byPrioAsc, byDateDesc, byPrevAsc, bySistemaAsc }));\n"
        )
        proc = _run_node_script(script)
        out = json.loads(proc.stdout)
        assert out["byPrioAsc"] == ["INC1", "INC3", "INC2"]
        assert out["byDateDesc"] == ["INC3", "INC2", "INC1"]
        assert out["byPrevAsc"] == ["INC3", "INC2", "INC1"]
        assert out["bySistemaAsc"] == ["INC1", "INC3", "INC2"]
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
            "const iaCache = new Map([['INC1', { problema: 'Fallo login PRO', impacto: 'Afectación login B2B', siguienteAccion: 'Reiniciar nodo' }]]);\n"
            "const catalog = { by_release: { '2026R11': { 'PRJ-101': { summary: 'Portal B2B', despliegue: 'Piloto' } } } };\n"
            "const overrides = { 'INC1': { fecha_prevista: '2026-11-10' } };\n"
            "const res = rd.buildMesaBriefing(incidents, iaCache, catalog, '2026R11', overrides, '2026-11-18T12:00:00Z');\n"
            "console.log(JSON.stringify(res));\n"
        )
        proc = _run_node_script(script)
        out = json.loads(proc.stdout)
        assert "Briefing Mesa de Release 2026R11 (2026-11-18)" in out["text"]
        assert "Total visibles: 2 | Resueltas: 1 | Compromisos vencidos: 1" in out["text"]
        assert "[Crítica (P1)] (1)" in out["text"]
        assert "⚠️ VENCIDA 2026-11-10" in out["text"]
        assert "[Piloto] PRJ-101 — Portal B2B" in out["text"]
        assert "Problema Detectado: [AURORA] Fallo login PRO" in out["text"]
        assert "IMPACTO: Afectación login B2B" in out["text"]
        assert "Acción: Reiniciar nodo" in out["text"]
        assert "[Media (P3)] (1)" in out["text"]
        assert "Problema Detectado: Consulta menor" in out["text"]
        assert "IMPACTO: Subsanado" in out["text"]
        assert "<ul><li><strong>INC1</strong>" in out["html"]
        assert "<strong>Problema Detectado:</strong> [AURORA] Fallo login PRO" in out["html"]
        assert "<strong>IMPACTO:</strong> Afectación login B2B" in out["html"]
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
        proc = _run_node_script(script)
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


def test_release_desk_js_fecha_prevista_status():
    if shutil.which("node") is not None:
        script = (
            f"const rd = require({json.dumps(str(RELEASE_DESK_JS))});\n"
            "const inc1 = { 'ID de incidencia': 'INC1', 'Estatus': 'En Curso' };\n"
            "const inc2 = { 'ID de incidencia': 'INC2', 'Estatus': 'Asignado' };\n"
            "const inc3 = { 'ID de incidencia': 'INC3', 'Estatus': 'Asignado' };\n"
            "const inc4 = { 'ID de incidencia': 'INC4', 'Estatus': 'Asignado' };\n"
            "const inc5 = { 'ID de incidencia': 'INC5', 'Estatus': 'Resuelto' };\n"
            "const overrides = {\n"
            "  INC1: { fecha_prevista: '2026-11-10' },\n"
            "  INC2: { fecha_prevista: '2026-11-19' },\n"
            "  INC3: { fecha_prevista: '2026-11-25' }\n"
            "};\n"
            "const now = '2026-11-18T12:00:00Z';\n"
            "console.log(JSON.stringify({\n"
            "  s1: rd.getFechaPrevistaStatus(inc1, overrides, now),\n"
            "  s2: rd.getFechaPrevistaStatus(inc2, overrides, now),\n"
            "  s3: rd.getFechaPrevistaStatus(inc3, overrides, now),\n"
            "  s4: rd.getFechaPrevistaStatus(inc4, overrides, now),\n"
            "  s5: rd.getFechaPrevistaStatus(inc5, overrides, now),\n"
            "  f1: rd.matchesKpiFilter(inc1, 'overdue_or_missing', overrides, now),\n"
            "  f3: rd.matchesKpiFilter(inc3, 'overdue_or_missing', overrides, now),\n"
            "  f4: rd.matchesKpiFilter(inc4, 'overdue_or_missing', overrides, now)\n"
            "}));\n"
        )
        proc = _run_node_script(script)
        out = json.loads(proc.stdout)
        assert out == {
            "s1": "overdue",
            "s2": "due_soon",
            "s3": "ok",
            "s4": "missing",
            "s5": "resolved",
            "f1": True,
            "f3": False,
            "f4": True,
        }
    else:
        js = RELEASE_DESK_JS.read_text(encoding="utf-8")
        assert "getFechaPrevistaStatus" in js


def test_release_desk_js_group_incidents_by_project():
    if shutil.which("node") is not None:
        script = (
            f"const rd = require({json.dumps(str(RELEASE_DESK_JS))});\n"
            "const incidents = [\n"
            "  { 'ID de incidencia': 'INC1', 'Prioridad': 'Crítica (P1)', 'Descripción': 'PRJ-100 Fallo', 'Estatus': 'En Curso' },\n"
            "  { 'ID de incidencia': 'INC2', 'Prioridad': 'Media', 'Descripción': 'PRJ-200 Menor', 'Estatus': 'Resuelto' },\n"
            "  { 'ID de incidencia': 'INC3', 'Prioridad': 'Alta', 'Descripción': 'PRJ-300 Medio', 'Estatus': 'Asignado' },\n"
            "  { 'ID de incidencia': 'INC4', 'Prioridad': 'Media', 'Descripción': 'Sin tag proyecto', 'Estatus': 'Asignado' }\n"
            "];\n"
            "const catalog = { by_release: { '2026R11': {\n"
            "  'PRJ-100': { summary: 'Proyecto Critico', despliegue: 'Completo' },\n"
            "  'PRJ-200': { summary: 'Proyecto OK', despliegue: 'Piloto' },\n"
            "  'PRJ-300': { summary: 'Proyecto Warn', despliegue: 'Modo Oculto' }\n"
            "} } };\n"
            "const groups = rd.groupIncidentsByProject(incidents, catalog, '2026R11', {}, '2026-11-18T12:00:00Z');\n"
            "console.log(JSON.stringify(groups.map(g => ({ code: g.code, health: g.health, total: g.total, p1: g.p1, p2: g.p2 }))));\n"
        )
        proc = _run_node_script(script)
        out = json.loads(proc.stdout)
        assert out == [
            {"code": "PRJ-100", "health": "crit", "total": 1, "p1": 1, "p2": 0},
            {"code": "PRJ-300", "health": "warn", "total": 1, "p1": 0, "p2": 1},
            {"code": "PRJ-200", "health": "ok", "total": 1, "p1": 0, "p2": 0},
            {"code": "Sin proyecto", "health": "warn", "total": 1, "p1": 0, "p2": 0},
        ]
    else:
        js = RELEASE_DESK_JS.read_text(encoding="utf-8")
        assert "groupIncidentsByProject" in js


def test_release_desk_js_get_sync_change_badge():
    if shutil.which("node") is not None:
        script = (
            f"const rd = require({json.dumps(str(RELEASE_DESK_JS))});\n"
            "const changes = { new_ids: ['INC1'], status_changed_ids: ['INC2'], updated_ids: ['INC2', 'INC3'] };\n"
            "console.log(JSON.stringify({\n"
            "  a: rd.getSyncChangeBadge('INC1', changes),\n"
            "  b: rd.getSyncChangeBadge('INC2', changes),\n"
            "  c: rd.getSyncChangeBadge('INC3', changes),\n"
            "  d: rd.getSyncChangeBadge('INC4', changes)\n"
            "}));\n"
        )
        proc = _run_node_script(script)
        out = json.loads(proc.stdout)
        assert out == {"a": "new", "b": "status", "c": "updated", "d": None}
    else:
        js = RELEASE_DESK_JS.read_text(encoding="utf-8")
        assert "getSyncChangeBadge" in js


def test_release_desk_massive_incident_badge():
    if shutil.which("node") is not None:
        script = (
            f"const rd = require({json.dumps(str(RELEASE_DESK_JS))});\n"
            "console.log(JSON.stringify({\n"
            "  p1_normal: rd.getPriorityBadgeClass('P1', 'Crítica', false),\n"
            "  p1_masiva: rd.getPriorityBadgeClass('P1', 'Crítica', true),\n"
            "  p2_normal: rd.getPriorityBadgeClass('P2', 'Alta', false),\n"
            "  p2_masiva: rd.getPriorityBadgeClass('P2', 'Alta', true),\n"
            "  p3_normal: rd.getPriorityBadgeClass('P3', 'Medio', false),\n"
            "  p3_masiva: rd.getPriorityBadgeClass('P3', 'Medio', true)\n"
            "}));\n"
        )
        proc = _run_node_script(script)
        out = json.loads(proc.stdout)
        assert out == {
            "p1_normal": "rd-badge-critica",
            "p1_masiva": "rd-badge-critica rd-badge-masiva",
            "p2_normal": "rd-badge-alta",
            "p2_masiva": "rd-badge-alta rd-badge-masiva",
            "p3_normal": "rd-badge-media",
            "p3_masiva": "rd-badge-masiva",
        }
    else:
        js = RELEASE_DESK_JS.read_text(encoding="utf-8")
        assert "rd-badge-masiva" in js


def test_release_desk_is_massive_incident():
    if shutil.which("node") is not None:
        script = (
            f"const rd = require({json.dumps(str(RELEASE_DESK_JS))});\n"
            "const inc1 = { 'ID de incidencia': 'INC1', masiva: true };\n"
            "const inc2 = { 'ID de incidencia': 'INC2', 'Impacto': 'Masiva' };\n"
            "const inc3 = { 'ID de incidencia': 'INC3', 'Prioridad': 'P3' };\n"
            "const massiveIds = new Set(['INC3']);\n"
            "const inc4 = { 'ID de incidencia': 'INC4', 'Prioridad': 'P3' };\n"
            "console.log(JSON.stringify({\n"
            "  m1: rd.isMassiveIncident(inc1),\n"
            "  m2: rd.isMassiveIncident(inc2),\n"
            "  m3: rd.isMassiveIncident(inc3, massiveIds),\n"
            "  m4: rd.isMassiveIncident(inc4, massiveIds)\n"
            "}));\n"
        )
        proc = _run_node_script(script)
        out = json.loads(proc.stdout)
        assert out == {
            "m1": True,
            "m2": True,
            "m3": True,
            "m4": False,
        }
    else:
        js = RELEASE_DESK_JS.read_text(encoding="utf-8")
        assert "isMassiveIncident" in js


def test_bump_asset_versions_updates_both_consoles(tmp_path):
    from converters.cli.bump_asset_versions import bump_html_content

    sample = (
        '<link rel="stylesheet" href="/dashboards/assets/topbar.css">\n'
        '<link rel="stylesheet" href="./triage.css?v=old">\n'
        '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter">\n'
        '<script src="/dashboards/release-desk/release-desk.js"></script>\n'
    )
    out = bump_html_content(sample, "20261119_0838")
    assert 'href="/dashboards/assets/topbar.css?v=20261119_0838"' in out
    assert 'href="./triage.css?v=20261119_0838"' in out
    assert 'href="https://fonts.googleapis.com/css2?family=Inter"' in out
    assert 'src="/dashboards/release-desk/release-desk.js?v=20261119_0838"' in out

    for html_path in (
        RELEASE_DESK_HTML,
        PROJECT_ROOT / "dashboards" / "emergency-triage-console" / "index.html",
    ):
        text = html_path.read_text(encoding="utf-8")
        assert "?v=" in text
