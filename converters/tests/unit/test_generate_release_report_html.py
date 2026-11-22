# -*- coding: utf-8 -*-
"""
Tests unitarios para el generador del Informe Ejecutivo HTML de Release
(converters/cli/generate_release_report_html.py).
"""

import json
from pathlib import Path
import pytest

from converters.cli.generate_release_report_html import (
    parse_releases_data_js,
    load_grafana_pap_csv,
    load_projects_catalog,
    load_projects_csv,
    extract_project_code,
    normalize_system_name,
    system_matches,
    build_release_report_html,
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def test_parse_releases_data_js():
    js_path = PROJECT_ROOT / "dashboards" / "release-kpis" / "releases-data.js"
    info = parse_releases_data_js(js_path, "2026R11")
    assert info["release"] == "2026R11"
    assert info["year"] == 2026
    assert info["fecha_pap"] == "22-nov."


def test_load_grafana_pap_csv(tmp_path):
    csv_file = tmp_path / "sample_grafana.csv"
    csv_file.write_text(
        '"mv_id","prj","key_test_plan","proyecto_test","test_plan","tribu_id","resumen_test_plan","sistema_test","release_planificada_test_plan","test_environment_test_plan","test_layer_test_plan","fix_versions_test_plan","prioridad_test_plan","tipologia_prueba","agrupacion_funcional","blocking_comment","num_test","pass","pending","block","verify","executing"\n'
        '27,PRJ-10699,TMMC-7988,TMMC,688638,,PRJ-10699 RESPONSABILIDADES,"{""CRM B2B OSP""}",R2026-11,{PRODUCCION},E2E,{R2026-11},High,PROGRESION,ALTA POSPAGO,,10,8,1,1,0,0\n'
        '36,PRJ-10987,TMMC-7872,TMMC,684096,,PRJ-10987 DESARROLLO FEMTOCELDAS,"{""CRM B2B OSP""}",R2026-11,{PRODUCCION},E2E,{R2026-11},High,PROGRESION,POSTVENTA,Error de config,5,3,0,2,0,0\n',
        encoding="utf-8",
    )
    res = load_grafana_pap_csv(csv_file)
    assert res["available"] is True
    assert res["total_tests"] == 15
    assert res["pass_count"] == 11
    assert res["block_count"] == 3
    assert res["pending_count"] == 1
    assert len(res["blocked_items"]) == 2
    assert "PRJ-10699" in res["by_project"]
    assert "PRJ-10987" in res["by_project"]
    assert len(res["blocked_projects"]) == 2
    # Ordenado por bloqueos descendente: PRJ-10987 (2 bloq) va antes de PRJ-10699 (1 bloq)
    assert res["blocked_projects"][0]["prj"] == "PRJ-10987"
    assert res["blocked_projects"][0]["block_count"] == 2
    assert res["blocked_projects"][1]["prj"] == "PRJ-10699"
    assert res["blocked_projects"][1]["block_count"] == 1


def test_extract_project_code():
    assert extract_project_code({"Descripción": "[2026R11] - PRJ-11894 - SIRES error"}) == "PRJ-11894"
    assert extract_project_code({"PROYECTO": "PRJ-10699"}) == "PRJ-10699"
    assert extract_project_code({"JIRA": "AB2CJ-501"}) == "AB2CJ-501"
    assert extract_project_code({"Descripción": "Error general sin código"}) == ""


def test_system_matches():
    initiative_systems = ["CRM B2B OSP", "ESHOP FRONTEND OSP", "TEIDE OSP"]
    assert system_matches("CRM B2B", initiative_systems) is True
    assert system_matches("TEIDE", initiative_systems) is True
    assert system_matches("FICHA DE CLIENTE", initiative_systems) is False
    assert system_matches("", initiative_systems) is False
    assert system_matches("CRM B2B", []) is False
    assert system_matches("XNET", initiative_systems) is False


def test_build_release_report_html_generates_valid_file(tmp_path):
    output_html = tmp_path / "comunicado-release-2026R11" / "index.html"
    res_path = build_release_report_html(
        release="2026R11",
        output_path=output_html,
    )
    assert res_path.is_file()
    content = res_path.read_text(encoding="utf-8")

    # Verifica estructura y tokens obligatorios
    assert '<div id="mo-topbar-root" data-active="informes"></div>' in content
    assert "Informe Ejecutivo Global de Release · 2026R11" in content
    assert "/dashboards/release-desk/?release=2026R11" in content
    assert "Proyectos en Release" in content
    assert "Avance Pruebas PaP" in content
    assert "Pruebas Bloqueadas" in content
    assert "Resumen Agregado por Proyecto" in content
    assert "Progresión por Proyectos" in content
    assert "Regresión Transversal E2E" in content
    assert "Incidencias Activas" in content
    assert "Diagnóstico Epsilon Resumen IA" in content
    assert "Impacto en Servicio y Negocio" in content

    # Verifica que no aparezcan incidencias en estado 'Cerrado' en todo el informe
    # (ni en la tabla de Resumen Agregado ni en las fichas de proyectos/transversales)
    # Tickets cerrados en 2026R11: INC000004192171, INC000004191881, INC000004192065, etc.
    assert "INC000004192171" not in content
    assert "INC000004191881" not in content
    assert "INC000004192065" not in content
    assert "INC000004192066" not in content
    assert "INC000004192168" not in content
    assert "badge-status-cerrado" not in content

    # Verifica coherencia 1:1 en PRJ-8058 (3 incidencias directas) y TRANSVERSAL (sin proyecto)
    table_match = content[content.find("Resumen Agregado por Proyecto"):content.find("Seguimiento de Proyectos")]
    assert 'href="#card-PRJ-8058"' in table_match
    assert 'href="#card-transversales"' in table_match
    assert "INC000004192176" in table_match
    assert "INC000004192073" in table_match
    assert "INC000004192062" in table_match


def test_build_release_report_html_applies_mesa_overrides(tmp_path, monkeypatch):
    import converters.cli.generate_release_report_html as rep_module

    # Simulamos que en Mesa de Release se acordó una fecha prevista para INC000004192176
    mock_overrides = {
        "INC000004192176": {
            "fecha_prevista": "2026-11-30",
            "updated_at": "2026-11-22T17:00:00"
        }
    }
    monkeypatch.setattr(rep_module, "get_overrides_for_release", lambda storage_dir, rel: mock_overrides)

    output_html = tmp_path / "comunicado-release-2026R11-overrides" / "index.html"
    res_path = rep_module.build_release_report_html(
        release="2026R11",
        output_path=output_html,
    )
    assert res_path.is_file()
    content = res_path.read_text(encoding="utf-8")

    # Verifica que la fecha acordada en Mesa de Release se refleje con su distintivo
    assert "2026-11-30" in content
    assert "Acordada Mesa" in content

