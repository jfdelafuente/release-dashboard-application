#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
converters.cli.generate_release_report_html
-------------------------------------------
Generador del Informe Ejecutivo Global 360° en HTML para Releases mensuales IT:
  - Lee datos de catálogo de proyectos (data/config/projects_catalog.json o data/storage/projects/{release}.csv)
  - Lee telemetría de incidencias Remedy (data/output/{release}-postmortem.json)
  - Cruza diagnósticos de Epsilon Resumen IA (data/.epsilon_cache/ o .epsilon_cache/)
  - Cruza avance de pruebas PaP y bloqueos de Grafana Argos (data/storage/projects/{release}_grafana_pap.csv)
  - Genera informe corporativo estático y autocontenido con topbar en:
      dashboards/informes/comunicado-release-{release}/index.html
  - Enlazable directamente desde la consola Mesa de Release (/dashboards/release-desk/?release={release})

Uso CLI:
    python converters/cli/generate_release_report_html.py --release 2026R11
    python converters/cli/generate_release_report_html.py --release 2026R11 --force
"""

import argparse
import csv
import html
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Intento de reutilizar cargador de caché de Epsilon si está disponible
try:
    from converters.src.release_desk_overrides import load_cached_epsilon_summaries
except ImportError:
    load_cached_epsilon_summaries = None


def parse_releases_data_js(js_path: Path, target_release: str) -> Dict[str, Any]:
    """Extrae metadatos de la release desde dashboards/release-kpis/releases-data.js."""
    info = {
        "release": target_release,
        "year": None,
        "fecha_pap": "",
        "mes": "",
        "pap_entrada": 0,
        "pap_resueltas": 0,
        "post_entrada": 0,
        "post_resueltas": 0,
    }
    if not js_path.is_file():
        return info

    content = js_path.read_text(encoding="utf-8", errors="ignore")
    # Buscar línea con la release: ["2026R11", 2026, "22-nov.", "Noviembre", 0, 0, 0, 0]
    pattern = rf'\[\s*"{re.escape(target_release)}"\s*,\s*(\d{{4}})\s*,\s*"([^"]*)"\s*,\s*"([^"]*)"\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\]'
    match = re.search(pattern, content)
    if match:
        info["year"] = int(match.group(1))
        info["fecha_pap"] = match.group(2)
        info["mes"] = match.group(3)
        info["pap_entrada"] = int(match.group(4))
        info["pap_resueltas"] = int(match.group(5))
        info["post_entrada"] = int(match.group(6))
        info["post_resueltas"] = int(match.group(7))
    return info


def load_projects_catalog(catalog_path: Path, release: str) -> Dict[str, Dict[str, Any]]:
    """Carga catálogo de proyectos desde data/config/projects_catalog.json."""
    if not catalog_path.is_file():
        alt = PROJECT_ROOT / "data" / "projects_catalog.json"
        if alt.is_file():
            catalog_path = alt
        else:
            return {}

    try:
        data = json.loads(catalog_path.read_text(encoding="utf-8"))
        by_rel = data.get("by_release", {})
        if release in by_rel and isinstance(by_rel[release], dict):
            return by_rel[release]
        # Búsqueda fallback en general si no está agrupado por release
        return data.get("projects", {}) or {}
    except Exception as exc:
        print(f"[WARN] Error leyendo projects_catalog.json: {exc}", file=sys.stderr)
        return {}


def load_projects_csv(csv_path: Path) -> Dict[str, Dict[str, Any]]:
    """Carga y enriquece proyectos desde data/storage/projects/{release}.csv."""
    if not csv_path.is_file():
        return {}

    projects: Dict[str, Dict[str, Any]] = {}
    try:
        content = csv_path.read_text(encoding="utf-8-sig", errors="ignore")
        # Detectar delimitador (; o ,)
        delimiter = ";" if ";" in content.splitlines()[0] else ","
        reader = csv.DictReader(content.splitlines(), delimiter=delimiter)
        for row in reader:
            jira = (row.get("JIRA") or row.get("jira") or row.get("PRJ") or "").strip()
            if not jira:
                continue
            projects[jira] = {
                "jira": jira,
                "summary": (row.get("Summary") or row.get("summary") or "").strip(),
                "despliegue": (row.get("Despliegue") or row.get("despliegue") or "Completo").strip(),
                "descripcion": (row.get("Descripcion") or row.get("descripcion") or "").strip(),
                "pruebas": (row.get("Pruebas") or row.get("pruebas") or "Si").strip(),
                "responsable": (row.get("Responsable") or row.get("responsable") or "").strip(),
                "metodologia": (row.get("Metodologia") or row.get("metodologia") or "").strip(),
                "decision": (row.get("Decision") or row.get("decision") or "GO").strip(),
            }
    except Exception as exc:
        print(f"[WARN] Error leyendo CSV de proyectos {csv_path}: {exc}", file=sys.stderr)
    return projects


def load_grafana_pap_csv(csv_path: Path) -> Dict[str, Any]:
    """Carga y procesa resultados de pruebas PaP de Grafana Argos."""
    result = {
        "available": False,
        "total_tests": 0,
        "pass_count": 0,
        "pending_count": 0,
        "block_count": 0,
        "verify_count": 0,
        "executing_count": 0,
        "pass_rate": 0.0,
        "blocked_items": [],
        "by_project": {},
    }

    if not csv_path.is_file():
        return result

    try:
        content = csv_path.read_text(encoding="utf-8-sig", errors="ignore")
        delimiter = ";" if ";" in content.splitlines()[0] else ","
        reader = csv.DictReader(content.splitlines(), delimiter=delimiter)

        for row in reader:
            prj = (row.get("prj") or "").strip().upper()
            test_plan = (row.get("key_test_plan") or row.get("test_plan") or "").strip()
            resumen = (row.get("resumen_test_plan") or "").strip()
            sistema = (row.get("sistema_test") or "").strip().replace('{"', '').replace('"}', '').replace('""', '')
            prioridad = (row.get("prioridad_test_plan") or "").strip()
            blocking_comment = (row.get("blocking_comment") or "").strip()

            def _to_int(val):
                try:
                    return int(float(val or 0))
                except (ValueError, TypeError):
                    return 0

            num_test = _to_int(row.get("num_test"))
            pass_val = _to_int(row.get("pass"))
            pending_val = _to_int(row.get("pending"))
            block_val = _to_int(row.get("block"))
            verify_val = _to_int(row.get("verify"))
            executing_val = _to_int(row.get("executing"))

            result["total_tests"] += num_test
            result["pass_count"] += pass_val
            result["pending_count"] += pending_val
            result["block_count"] += block_val
            result["verify_count"] += verify_val
            result["executing_count"] += executing_val

            if block_val > 0 or blocking_comment:
                result["blocked_items"].append({
                    "prj": prj,
                    "test_plan": test_plan,
                    "resumen": resumen,
                    "sistema": sistema,
                    "prioridad": prioridad,
                    "block_count": block_val,
                    "comment": blocking_comment or "Bloqueado en ejecución",
                })

            if prj:
                if prj not in result["by_project"]:
                    result["by_project"][prj] = {
                        "total_tests": 0,
                        "pass_count": 0,
                        "pending_count": 0,
                        "block_count": 0,
                        "verify_count": 0,
                        "executing_count": 0,
                        "test_plans": [],
                    }
                p = result["by_project"][prj]
                p["total_tests"] += num_test
                p["pass_count"] += pass_val
                p["pending_count"] += pending_val
                p["block_count"] += block_val
                p["verify_count"] += verify_val
                p["executing_count"] += executing_val
                p["test_plans"].append({
                    "test_plan": test_plan,
                    "resumen": resumen,
                    "sistema": sistema,
                    "prioridad": prioridad,
                    "pass": pass_val,
                    "pending": pending_val,
                    "block": block_val,
                    "blocking_comment": blocking_comment,
                })

        result["available"] = result["total_tests"] > 0
        if result["total_tests"] > 0:
            result["pass_rate"] = round((result["pass_count"] / result["total_tests"]) * 100, 1)

    except Exception as exc:
        print(f"[WARN] Error leyendo Grafana PaP CSV {csv_path}: {exc}", file=sys.stderr)

    return result


def load_local_epsilon_cache(incident_ids: List[str]) -> Dict[str, Any]:
    """Carga resúmenes de IA desde data/.epsilon_cache/{id}.json o carpetas equivalentes."""
    summaries: Dict[str, Any] = {}
    candidate_dirs = [
        PROJECT_ROOT / "data" / ".epsilon_cache",
        PROJECT_ROOT / ".epsilon_cache",
        PROJECT_ROOT / "data" / "cache" / "epsilon",
    ]

    for inc_id in incident_ids:
        clean_id = inc_id.strip()
        if not clean_id:
            continue
        for cdir in candidate_dirs:
            candidate_file = cdir / f"{clean_id}.json"
            if candidate_file.is_file():
                try:
                    data = json.loads(candidate_file.read_text(encoding="utf-8"))
                    if isinstance(data, dict):
                        summaries[clean_id] = data
                        break
                except Exception:
                    pass
    return summaries


def extract_project_code(incident: Dict[str, Any]) -> str:
    """Extrae código PRJ-XXXXX del texto de la incidencia o proyecto asignado."""
    desc = incident.get("Descripción") or incident.get("descripcion") or ""
    proj = incident.get("PROYECTO") or incident.get("proyecto") or ""
    jira = incident.get("JIRA") or incident.get("jira") or ""

    for text in (proj, jira, desc):
        m = re.search(r'\b(PRJ-\d+|AB2CJ-\d+|OCA-\d+)\b', text, re.IGNORECASE)
        if m:
            return m.group(1).upper()
    return ""


def load_release_incidents(postmortem_path: Path) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Carga incidencias y metadatos del postmortem."""
    if not postmortem_path.is_file():
        return [], {}

    try:
        raw = json.loads(postmortem_path.read_text(encoding="utf-8"))
        data = raw.get("data", [])
        meta = raw.get("_metadata", {})
        return data, meta
    except Exception as exc:
        print(f"[ERROR] Error cargando postmortem JSON {postmortem_path}: {exc}", file=sys.stderr)
        return [], {}


def format_badge_priority(prio: str) -> str:
    p = (prio or "").upper()
    if p in ("P1", "CRÍTICA", "CRITICA"):
        return '<span class="badge badge-p1" title="Prioridad P1 - Crítica">P1 Crítica</span>'
    elif p in ("P2", "ALTA"):
        return '<span class="badge badge-p2" title="Prioridad P2 - Alta">P2 Alta</span>'
    elif p in ("P3", "MEDIA", "MEDIO"):
        return '<span class="badge badge-p3" title="Prioridad P3 - Media">P3 Media</span>'
    else:
        return '<span class="badge badge-p4" title="Prioridad P4 - Baja">P4 Baja</span>'


def format_badge_status(status: str) -> str:
    s = (status or "").lower()
    if "cerrad" in s:
        return '<span class="badge badge-closed">Cerrado</span>'
    elif "resuelt" in s:
        return '<span class="badge badge-resolved">Resuelto</span>'
    elif "pendient" in s:
        return '<span class="badge badge-pending">Pendiente</span>'
    elif "en curso" in s or "asignad" in s:
        return '<span class="badge badge-inprogress">En Curso</span>'
    else:
        return f'<span class="badge badge-neutral">{html.escape(status)}</span>'


def format_badge_deployment(despliegue: str) -> str:
    d = (despliegue or "Completo").strip().lower()
    if "piloto" in d:
        return '<span class="badge badge-piloto">Piloto</span>'
    elif "pap" in d:
        return '<span class="badge badge-pap-tecnico">PAP Técnico</span>'
    elif "oculto" in d:
        return '<span class="badge badge-oculto">Modo Oculto</span>'
    else:
        return '<span class="badge badge-completo">Completo</span>'


def build_release_report_html(
    release: str,
    output_path: Path,
    grafana_csv: Optional[Path] = None,
    projects_csv: Optional[Path] = None,
    postmortem_json: Optional[Path] = None,
    catalog_json: Optional[Path] = None,
    releases_data_js: Optional[Path] = None,
) -> Path:
    """Genera el archivo HTML autocontenido del informe de release."""
    rel = release.strip()
    storage_dir = PROJECT_ROOT / "data"

    # 1. Rutas por defecto si no se especifican
    if not releases_data_js:
        releases_data_js = PROJECT_ROOT / "dashboards" / "release-kpis" / "releases-data.js"
    if not postmortem_json:
        postmortem_json = storage_dir / "output" / f"{rel}-postmortem.json"
    if not catalog_json:
        catalog_json = storage_dir / "config" / "projects_catalog.json"
    if not projects_csv:
        projects_csv = storage_dir / "storage" / "projects" / f"{rel}.csv"
    if not grafana_csv:
        grafana_csv = storage_dir / "storage" / "projects" / f"{rel}_grafana_pap.csv"

    # 2. Cargar fuentes de datos
    rel_info = parse_releases_data_js(releases_data_js, rel)
    catalog = load_projects_catalog(catalog_json, rel)
    csv_projects = load_projects_csv(projects_csv)
    grafana_data = load_grafana_pap_csv(grafana_csv)
    incidents, meta = load_release_incidents(postmortem_json)

    # Combinar proyectos de catálogo y CSV
    all_projects: Dict[str, Dict[str, Any]] = {}
    for code, pdata in catalog.items():
        all_projects[code] = {
            "jira": code,
            "summary": pdata.get("summary") or pdata.get("name") or "",
            "despliegue": pdata.get("despliegue") or "Completo",
            "descripcion": pdata.get("descripcion") or "",
            "responsable": pdata.get("responsable") or "",
            "metodologia": pdata.get("metodologia") or "",
            "decision": pdata.get("decision") or "GO",
            "pruebas": "Si",
        }
    for code, pdata in csv_projects.items():
        if code not in all_projects:
            all_projects[code] = pdata
        else:
            for k, v in pdata.items():
                if v and not all_projects[code].get(k):
                    all_projects[code][k] = v

    # Cargar Epsilon IA para todas las incidencias
    inc_ids = [inc.get("ID de incidencia") for inc in incidents if inc.get("ID de incidencia")]
    ia_summaries = load_local_epsilon_cache(inc_ids)

    # 3. Categorizar incidencias y cruzarlas con proyectos
    incidents_by_project: Dict[str, List[Dict[str, Any]]] = {}
    incidents_without_project: List[Dict[str, Any]] = []

    total_incidents = len(incidents)
    active_incidents = 0
    resolved_closed_incidents = 0
    active_p1_p2 = 0
    active_p3 = 0
    active_p4 = 0

    for inc in incidents:
        st = (inc.get("Estatus") or "").strip().lower()
        prio = (inc.get("Prioridad") or inc.get("Urgencia") or "").strip().upper()
        is_closed = "cerrad" in st or "resuelt" in st

        if is_closed:
            resolved_closed_incidents += 1
        else:
            active_incidents += 1
            if prio in ("P1", "CRÍTICA", "CRITICA"):
                active_p1_p2 += 1
            elif prio in ("P2", "ALTA"):
                active_p1_p2 += 1
            elif prio in ("P3", "MEDIA", "MEDIO"):
                active_p3 += 1
            else:
                active_p4 += 1

        prj_code = extract_project_code(inc)
        if prj_code:
            if prj_code not in incidents_by_project:
                incidents_by_project[prj_code] = []
            incidents_by_project[prj_code].append(inc)
            if prj_code not in all_projects:
                all_projects[prj_code] = {
                    "jira": prj_code,
                    "summary": f"Iniciativa {prj_code}",
                    "despliegue": "Completo",
                    "descripcion": "",
                    "responsable": "",
                    "metodologia": "",
                    "decision": "GO",
                    "pruebas": "Si",
                }
        else:
            incidents_without_project.append(inc)

    # Asegurar que proyectos de Grafana estén en all_projects
    for prj_code in grafana_data.get("by_project", {}).keys():
        if prj_code and prj_code not in all_projects:
            all_projects[prj_code] = {
                "jira": prj_code,
                "summary": f"Proyecto {prj_code}",
                "despliegue": "Completo",
                "descripcion": "",
                "responsable": "",
                "metodologia": "",
                "decision": "GO",
                "pruebas": "Si",
            }

    # Balance de GO / NoGO de proyectos
    total_projects = len(all_projects)
    go_projects = sum(1 for p in all_projects.values() if (p.get("decision") or "").upper() == "GO")
    pap_tec_projects = sum(1 for p in all_projects.values() if "PAP" in (p.get("decision") or "").upper() or "PAP" in (p.get("despliegue") or "").upper())
    nogo_projects = sum(1 for p in all_projects.values() if "NOGO" in (p.get("decision") or "").upper())

    # Ordenar proyectos:
    # 1. Proyectos con incidencias P1/P2 activas o bloqueos de pruebas
    # 2. Proyectos con incidencias activas
    # 3. Proyectos con pruebas PaP
    # 4. Resto alfabéticamente
    def project_sort_key(prj_code: str) -> Tuple[int, int, str]:
        p_incidents = incidents_by_project.get(prj_code, [])
        has_crit = any(
            (i.get("Prioridad") or "").upper() in ("P1", "P2", "CRÍTICA", "ALTA")
            and "cerrad" not in (i.get("Estatus") or "").lower()
            and "resuelt" not in (i.get("Estatus") or "").lower()
            for i in p_incidents
        )
        p_grafana = grafana_data.get("by_project", {}).get(prj_code, {})
        has_block = p_grafana.get("block_count", 0) > 0
        has_active = any(
            "cerrad" not in (i.get("Estatus") or "").lower() and "resuelt" not in (i.get("Estatus") or "").lower()
            for i in p_incidents
        )

        tier = 3
        if has_crit or has_block:
            tier = 0
        elif has_active:
            tier = 1
        elif p_incidents or p_grafana:
            tier = 2
        return (tier, -len(p_incidents), prj_code)

    sorted_project_codes = sorted(all_projects.keys(), key=project_sort_key)

    # 4. Renderizado HTML
    now_str = datetime.now().strftime("%d/%m/%Y %H:%M")
    fecha_pap_display = rel_info.get("fecha_pap") or rel_info.get("mes") or "En curso"

    html_lines = []
    html_lines.append("<!DOCTYPE html>")
    html_lines.append('<html lang="es">')
    html_lines.append("<head>")
    html_lines.append('    <meta charset="UTF-8">')
    html_lines.append('    <meta name="viewport" content="width=device-width, initial-scale=1.0">')
    html_lines.append(f'    <title>Informe Ejecutivo Release {html.escape(rel)} · Customer & Service Operations</title>')
    html_lines.append('    <link rel="stylesheet" href="/dashboards/assets/topbar.css?v=20261122_1530">')
    html_lines.append('    <link rel="stylesheet" href="/dashboards/assets/shared.css?v=20261122_1530">')
    html_lines.append('    <style>')
    html_lines.append('        :root {')
    html_lines.append('            --mo-orange: #FF7900;')
    html_lines.append('            --mo-black: #000000;')
    html_lines.append('            --mo-white: #FFFFFF;')
    html_lines.append('            --mo-bg: #F8F9FA;')
    html_lines.append('            --mo-card-bg: #FFFFFF;')
    html_lines.append('            --mo-border: #E5E7EB;')
    html_lines.append('            --mo-text-main: #1F2937;')
    html_lines.append('            --mo-text-muted: #6B7280;')
    html_lines.append('            --color-p1: #DC2626;')
    html_lines.append('            --color-p2: #EA580C;')
    html_lines.append('            --color-p3: #D97706;')
    html_lines.append('            --color-p4: #2563EB;')
    html_lines.append('            --color-success: #16A34A;')
    html_lines.append('        }')
    html_lines.append('        body {')
    html_lines.append('            background: var(--mo-bg);')
    html_lines.append('            color: var(--mo-text-main);')
    html_lines.append('            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;')
    html_lines.append('            margin: 0;')
    html_lines.append('            padding: 0;')
    html_lines.append('            -webkit-font-smoothing: antialiased;')
    html_lines.append('        }')
    html_lines.append('        .report-wrapper {')
    html_lines.append('            max-width: 1360px;')
    html_lines.append('            margin: 0 auto;')
    html_lines.append('            padding: 24px 20px 60px;')
    html_lines.append('        }')
    html_lines.append('        .report-header {')
    html_lines.append('            display: flex;')
    html_lines.append('            flex-wrap: wrap;')
    html_lines.append('            align-items: flex-start;')
    html_lines.append('            justify-content: space-between;')
    html_lines.append('            gap: 16px;')
    html_lines.append('            margin-bottom: 24px;')
    html_lines.append('            background: #FFFFFF;')
    html_lines.append('            border: 1px solid var(--mo-border);')
    html_lines.append('            border-radius: 12px;')
    html_lines.append('            padding: 24px 28px;')
    html_lines.append('            box-shadow: 0 1px 3px rgba(0,0,0,0.04);')
    html_lines.append('        }')
    html_lines.append('        .eyebrow {')
    html_lines.append('            font-size: 11px;')
    html_lines.append('            font-weight: 800;')
    html_lines.append('            text-transform: uppercase;')
    html_lines.append('            letter-spacing: 0.8px;')
    html_lines.append('            color: var(--mo-orange);')
    html_lines.append('            margin-bottom: 4px;')
    html_lines.append('        }')
    html_lines.append('        .report-title {')
    html_lines.append('            font-size: 26px;')
    html_lines.append('            font-weight: 800;')
    html_lines.append('            margin: 0 0 8px;')
    html_lines.append('            color: var(--mo-black);')
    html_lines.append('            letter-spacing: -0.5px;')
    html_lines.append('        }')
    html_lines.append('        .report-meta {')
    html_lines.append('            font-size: 13px;')
    html_lines.append('            color: var(--mo-text-muted);')
    html_lines.append('            display: flex;')
    html_lines.append('            gap: 16px;')
    html_lines.append('            align-items: center;')
    html_lines.append('            flex-wrap: wrap;')
    html_lines.append('        }')
    html_lines.append('        .btn-cta {')
    html_lines.append('            display: inline-flex;')
    html_lines.append('            align-items: center;')
    html_lines.append('            gap: 8px;')
    html_lines.append('            background: var(--mo-orange);')
    html_lines.append('            color: #FFFFFF;')
    html_lines.append('            font-weight: 700;')
    html_lines.append('            font-size: 14px;')
    html_lines.append('            padding: 10px 18px;')
    html_lines.append('            border-radius: 8px;')
    html_lines.append('            text-decoration: none;')
    html_lines.append('            transition: background 0.15s ease;')
    html_lines.append('        }')
    html_lines.append('        .btn-cta:hover {')
    html_lines.append('            background: #E66D00;')
    html_lines.append('        }')
    html_lines.append('        /* KPI Grid */')
    html_lines.append('        .kpi-grid {')
    html_lines.append('            display: grid;')
    html_lines.append('            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));')
    html_lines.append('            gap: 16px;')
    html_lines.append('            margin-bottom: 28px;')
    html_lines.append('        }')
    html_lines.append('        .kpi-card {')
    html_lines.append('            background: #FFFFFF;')
    html_lines.append('            border: 1px solid var(--mo-border);')
    html_lines.append('            border-radius: 10px;')
    html_lines.append('            padding: 18px 20px;')
    html_lines.append('            box-shadow: 0 1px 3px rgba(0,0,0,0.03);')
    html_lines.append('            border-top: 4px solid var(--mo-orange);')
    html_lines.append('        }')
    html_lines.append('        .kpi-card.kpi-warn { border-top-color: var(--color-p2); }')
    html_lines.append('        .kpi-card.kpi-crit { border-top-color: var(--color-p1); }')
    html_lines.append('        .kpi-card.kpi-success { border-top-color: var(--color-success); }')
    html_lines.append('        .kpi-value {')
    html_lines.append('            font-size: 30px;')
    html_lines.append('            font-weight: 800;')
    html_lines.append('            line-height: 1.1;')
    html_lines.append('            margin-bottom: 4px;')
    html_lines.append('            color: var(--mo-black);')
    html_lines.append('        }')
    html_lines.append('        .kpi-label {')
    html_lines.append('            font-size: 12px;')
    html_lines.append('            font-weight: 700;')
    html_lines.append('            text-transform: uppercase;')
    html_lines.append('            letter-spacing: 0.5px;')
    html_lines.append('            color: var(--mo-text-muted);')
    html_lines.append('        }')
    html_lines.append('        .kpi-subtext {')
    html_lines.append('            font-size: 11.5px;')
    html_lines.append('            color: #6B7280;')
    html_lines.append('            margin-top: 6px;')
    html_lines.append('        }')
    html_lines.append('        /* Section Headers */')
    html_lines.append('        .section-heading {')
    html_lines.append('            display: flex;')
    html_lines.append('            align-items: center;')
    html_lines.append('            justify-content: space-between;')
    html_lines.append('            margin: 32px 0 16px;')
    html_lines.append('            padding-bottom: 8px;')
    html_lines.append('            border-bottom: 2px solid #E5E7EB;')
    html_lines.append('        }')
    html_lines.append('        .section-heading h2 {')
    html_lines.append('            font-size: 18px;')
    html_lines.append('            font-weight: 800;')
    html_lines.append('            margin: 0;')
    html_lines.append('            color: var(--mo-black);')
    html_lines.append('            letter-spacing: -0.3px;')
    html_lines.append('        }')
    html_lines.append('        .section-heading .badge-count {')
    html_lines.append('            background: #E5E7EB;')
    html_lines.append('            color: #374151;')
    html_lines.append('            font-size: 11px;')
    html_lines.append('            font-weight: 700;')
    html_lines.append('            padding: 2px 8px;')
    html_lines.append('            border-radius: 999px;')
    html_lines.append('        }')
    html_lines.append('        /* Tables */')
    html_lines.append('        .data-table-wrap {')
    html_lines.append('            background: #FFFFFF;')
    html_lines.append('            border: 1px solid var(--mo-border);')
    html_lines.append('            border-radius: 10px;')
    html_lines.append('            overflow-x: auto;')
    html_lines.append('            margin-bottom: 28px;')
    html_lines.append('            box-shadow: 0 1px 3px rgba(0,0,0,0.03);')
    html_lines.append('        }')
    html_lines.append('        table.data-table {')
    html_lines.append('            width: 100%;')
    html_lines.append('            border-collapse: collapse;')
    html_lines.append('            font-size: 13px;')
    html_lines.append('            text-align: left;')
    html_lines.append('        }')
    html_lines.append('        table.data-table th {')
    html_lines.append('            background: #F9FAFB;')
    html_lines.append('            color: #4B5563;')
    html_lines.append('            font-weight: 700;')
    html_lines.append('            font-size: 11.5px;')
    html_lines.append('            text-transform: uppercase;')
    html_lines.append('            letter-spacing: 0.5px;')
    html_lines.append('            padding: 12px 14px;')
    html_lines.append('            border-bottom: 1px solid var(--mo-border);')
    html_lines.append('        }')
    html_lines.append('        table.data-table td {')
    html_lines.append('            padding: 12px 14px;')
    html_lines.append('            border-bottom: 1px solid #F3F4F6;')
    html_lines.append('            vertical-align: top;')
    html_lines.append('        }')
    html_lines.append('        table.data-table tr:last-child td {')
    html_lines.append('            border-bottom: none;')
    html_lines.append('        }')
    html_lines.append('        table.data-table tr:hover td {')
    html_lines.append('            background: #F9FAFB;')
    html_lines.append('        }')
    html_lines.append('        /* Badges */')
    html_lines.append('        .badge {')
    html_lines.append('            display: inline-block;')
    html_lines.append('            font-size: 11px;')
    html_lines.append('            font-weight: 700;')
    html_lines.append('            padding: 2px 8px;')
    html_lines.append('            border-radius: 999px;')
    html_lines.append('            white-space: nowrap;')
    html_lines.append('        }')
    html_lines.append('        .badge-p1 { background: #FEE2E2; color: #991B1B; border: 1px solid #FCA5A5; }')
    html_lines.append('        .badge-p2 { background: #FFEDD5; color: #9A3412; border: 1px solid #FDBA74; }')
    html_lines.append('        .badge-p3 { background: #FEF3C7; color: #92400E; border: 1px solid #FCD34D; }')
    html_lines.append('        .badge-p4 { background: #EFF6FF; color: #1E40AF; border: 1px solid #BFDBFE; }')
    html_lines.append('        .badge-closed { background: #F3F4F6; color: #4B5563; }')
    html_lines.append('        .badge-resolved { background: #DCFCE7; color: #166534; }')
    html_lines.append('        .badge-pending { background: #FFEDD5; color: #9A3412; }')
    html_lines.append('        .badge-inprogress { background: #DBEAFE; color: #1E40AF; }')
    html_lines.append('        .badge-neutral { background: #F3F4F6; color: #374151; }')
    html_lines.append('        .badge-completo { background: #E0E7FF; color: #3730A3; }')
    html_lines.append('        .badge-piloto { background: #FEF3C7; color: #92400E; }')
    html_lines.append('        .badge-pap-tecnico { background: #F3E8FF; color: #6B21A8; }')
    html_lines.append('        .badge-oculto { background: #F3F4F6; color: #4B5563; }')
    html_lines.append('        /* Project Cards */')
    html_lines.append('        .project-card {')
    html_lines.append('            background: #FFFFFF;')
    html_lines.append('            border: 1px solid var(--mo-border);')
    html_lines.append('            border-radius: 12px;')
    html_lines.append('            margin-bottom: 24px;')
    html_lines.append('            padding: 22px 24px;')
    html_lines.append('            box-shadow: 0 1px 4px rgba(0,0,0,0.03);')
    html_lines.append('        }')
    html_lines.append('        .project-card.has-crit {')
    html_lines.append('            border-left: 5px solid var(--color-p1);')
    html_lines.append('        }')
    html_lines.append('        .project-card.has-warn {')
    html_lines.append('            border-left: 5px solid var(--color-p2);')
    html_lines.append('        }')
    html_lines.append('        .project-header-top {')
    html_lines.append('            display: flex;')
    html_lines.append('            flex-wrap: wrap;')
    html_lines.append('            align-items: center;')
    html_lines.append('            justify-content: space-between;')
    html_lines.append('            gap: 12px;')
    html_lines.append('            margin-bottom: 8px;')
    html_lines.append('        }')
    html_lines.append('        .project-code-title {')
    html_lines.append('            display: flex;')
    html_lines.append('            align-items: center;')
    html_lines.append('            gap: 10px;')
    html_lines.append('        }')
    html_lines.append('        .project-code {')
    html_lines.append('            background: #111827;')
    html_lines.append('            color: #FFFFFF;')
    html_lines.append('            font-size: 12px;')
    html_lines.append('            font-weight: 800;')
    html_lines.append('            padding: 3px 10px;')
    html_lines.append('            border-radius: 6px;')
    html_lines.append('            letter-spacing: 0.5px;')
    html_lines.append('        }')
    html_lines.append('        .project-title {')
    html_lines.append('            font-size: 16px;')
    html_lines.append('            font-weight: 800;')
    html_lines.append('            color: var(--mo-black);')
    html_lines.append('            margin: 0;')
    html_lines.append('        }')
    html_lines.append('        .project-desc {')
    html_lines.append('            font-size: 13px;')
    html_lines.append('            color: #4B5563;')
    html_lines.append('            font-style: italic;')
    html_lines.append('            margin: 6px 0 14px;')
    html_lines.append('            line-height: 1.5;')
    html_lines.append('        }')
    html_lines.append('        /* PaP Testing mini banner inside project */')
    html_lines.append('        .project-pap-banner {')
    html_lines.append('            display: flex;')
    html_lines.append('            align-items: center;')
    html_lines.append('            gap: 16px;')
    html_lines.append('            background: #F9FAFB;')
    html_lines.append('            border: 1px solid #E5E7EB;')
    html_lines.append('            border-radius: 8px;')
    html_lines.append('            padding: 10px 14px;')
    html_lines.append('            font-size: 12px;')
    html_lines.append('            margin-bottom: 16px;')
    html_lines.append('        }')
    html_lines.append('        /* Incident Row & Resumen IA Box */')
    html_lines.append('        .incident-item {')
    html_lines.append('            border: 1px solid #E5E7EB;')
    html_lines.append('            border-radius: 8px;')
    html_lines.append('            padding: 14px 16px;')
    html_lines.append('            margin-bottom: 12px;')
    html_lines.append('            background: #FFFFFF;')
    html_lines.append('        }')
    html_lines.append('        .incident-head {')
    html_lines.append('            display: flex;')
    html_lines.append('            flex-wrap: wrap;')
    html_lines.append('            align-items: center;')
    html_lines.append('            justify-content: space-between;')
    html_lines.append('            gap: 10px;')
    html_lines.append('            margin-bottom: 8px;')
    html_lines.append('        }')
    html_lines.append('        .incident-id {')
    html_lines.append('            font-family: monospace;')
    html_lines.append('            font-weight: 700;')
    html_lines.append('            font-size: 13px;')
    html_lines.append('            color: #111827;')
    html_lines.append('        }')
    html_lines.append('        .incident-desc-raw {')
    html_lines.append('            font-size: 13px;')
    html_lines.append('            font-weight: 600;')
    html_lines.append('            color: #1F2937;')
    html_lines.append('            margin-bottom: 10px;')
    html_lines.append('        }')
    html_lines.append('        .ia-box {')
    html_lines.append('            background: #FFFBF5;')
    html_lines.append('            border: 1px solid #FED7AA;')
    html_lines.append('            border-left: 4px solid var(--mo-orange);')
    html_lines.append('            border-radius: 6px;')
    html_lines.append('            padding: 12px 14px;')
    html_lines.append('            font-size: 12.5px;')
    html_lines.append('            line-height: 1.5;')
    html_lines.append('            margin-top: 8px;')
    html_lines.append('        }')
    html_lines.append('        .ia-box-header {')
    html_lines.append('            font-size: 10.5px;')
    html_lines.append('            font-weight: 800;')
    html_lines.append('            text-transform: uppercase;')
    html_lines.append('            letter-spacing: 0.8px;')
    html_lines.append('            color: #C2410C;')
    html_lines.append('            margin-bottom: 6px;')
    html_lines.append('            display: flex;')
    html_lines.append('            align-items: center;')
    html_lines.append('            gap: 6px;')
    html_lines.append('        }')
    html_lines.append('        .ia-impact-highlight {')
    html_lines.append('            background: #FEF2F2;')
    html_lines.append('            border: 1px solid #FECACA;')
    html_lines.append('            border-left: 3px solid #DC2626;')
    html_lines.append('            border-radius: 4px;')
    html_lines.append('            padding: 6px 10px;')
    html_lines.append('            margin-bottom: 8px;')
    html_lines.append('            color: #991B1B;')
    html_lines.append('            font-size: 12px;')
    html_lines.append('        }')
    html_lines.append('        .ia-field {')
    html_lines.append('            margin-bottom: 4px;')
    html_lines.append('            color: #374151;')
    html_lines.append('        }')
    html_lines.append('        .ia-field strong {')
    html_lines.append('            color: #111827;')
    html_lines.append('        }')
    html_lines.append('        .footer-banner {')
    html_lines.append('            margin-top: 40px;')
    html_lines.append('            padding: 24px;')
    html_lines.append('            background: #FFFFFF;')
    html_lines.append('            border: 1px solid var(--mo-border);')
    html_lines.append('            border-radius: 12px;')
    html_lines.append('            text-align: center;')
    html_lines.append('            font-size: 13px;')
    html_lines.append('            color: var(--mo-text-muted);')
    html_lines.append('        }')
    html_lines.append('    </style>')
    html_lines.append("</head>")
    html_lines.append("<body>")
    html_lines.append('    <div id="mo-topbar-root" data-active="informes"></div>')
    html_lines.append('    <main class="report-wrapper">')

    # Header Card
    html_lines.append('        <header class="report-header">')
    html_lines.append('            <div>')
    html_lines.append('                <div class="eyebrow">Customer &amp; Service Operations · Tech Operations</div>')
    html_lines.append(f'                <h1 class="report-title">Informe Ejecutivo Global de Release · {html.escape(rel)}</h1>')
    html_lines.append('                <div class="report-meta">')
    html_lines.append(f'                    <span>📅 <strong>Fecha PaP:</strong> {html.escape(fecha_pap_display)}</span>')
    html_lines.append(f'                    <span>🕒 <strong>Generado:</strong> {now_str}</span>')
    html_lines.append(f'                    <span>📦 <strong>Total Proyectos:</strong> {total_projects}</span>')
    html_lines.append('                </div>')
    html_lines.append('            </div>')
    html_lines.append('            <div>')
    html_lines.append(f'                <a href="/dashboards/release-desk/?release={html.escape(rel)}" class="btn-cta" title="Ir a la consola interactiva Mesa de Release">📊 Abrir en Mesa de Release ↗</a>')
    html_lines.append('            </div>')
    html_lines.append('        </header>')

    # KPI Banner (5 Cards)
    html_lines.append('        <section class="kpi-grid">')
    # Card 1: Total Proyectos
    html_lines.append('            <div class="kpi-card">')
    html_lines.append(f'                <div class="kpi-value">{total_projects}</div>')
    html_lines.append('                <div class="kpi-label">Proyectos en Release</div>')
    html_lines.append(f'                <div class="kpi-subtext">🟢 {go_projects} GO | 🔧 {pap_tec_projects} PaP Técnico</div>')
    html_lines.append('            </div>')

    # Card 2: Avance Pruebas PaP
    card2_class = "kpi-card kpi-success" if grafana_data.get("pass_rate", 0) >= 80 else "kpi-card"
    html_lines.append(f'            <div class="{card2_class}">')
    if grafana_data.get("available"):
        html_lines.append(f'                <div class="kpi-value">{grafana_data["pass_rate"]}%</div>')
        html_lines.append('                <div class="kpi-label">Avance Pruebas PaP</div>')
        html_lines.append(f'                <div class="kpi-subtext">✅ {grafana_data["pass_count"]} OK de {grafana_data["total_tests"]} pruebas</div>')
    else:
        html_lines.append('                <div class="kpi-value">N/D</div>')
        html_lines.append('                <div class="kpi-label">Avance Pruebas PaP</div>')
        html_lines.append('                <div class="kpi-subtext">Sin CSV de Argos cargado</div>')
    html_lines.append('            </div>')

    # Card 3: Pruebas Bloqueadas
    card3_class = "kpi-card kpi-crit" if grafana_data.get("block_count", 0) > 0 else "kpi-card kpi-success"
    html_lines.append(f'            <div class="{card3_class}">')
    html_lines.append(f'                <div class="kpi-value">{grafana_data.get("block_count", 0)}</div>')
    html_lines.append('                <div class="kpi-label">Pruebas Bloqueadas</div>')
    html_lines.append(f'                <div class="kpi-subtext">⏳ {grafana_data.get("pending_count", 0)} pendientes de ejecución</div>')
    html_lines.append('            </div>')

    # Card 4: Incidencias Activas
    card4_class = "kpi-card kpi-crit" if active_p1_p2 > 0 else "kpi-card"
    html_lines.append(f'            <div class="{card4_class}">')
    html_lines.append(f'                <div class="kpi-value">{active_incidents}</div>')
    html_lines.append('                <div class="kpi-label">Incidencias Activas</div>')
    html_lines.append(f'                <div class="kpi-subtext">🔥 {active_p1_p2} P1/P2 | 🟡 {active_p3} P3 | 🔵 {active_p4} P4</div>')
    html_lines.append('            </div>')

    # Card 5: Resueltas / Cerradas
    res_pct = round((resolved_closed_incidents / total_incidents * 100), 1) if total_incidents > 0 else 0.0
    html_lines.append('            <div class="kpi-card kpi-success">')
    html_lines.append(f'                <div class="kpi-value">{resolved_closed_incidents}</div>')
    html_lines.append('                <div class="kpi-label">Resueltas / Cerradas</div>')
    html_lines.append(f'                <div class="kpi-subtext">✨ {res_pct}% del total de tickets Remedy</div>')
    html_lines.append('            </div>')
    html_lines.append('        </section>')

    # SECCIÓN 1: Bloqueos de Pruebas PaP (Grafana Argos)
    if grafana_data.get("available") and grafana_data.get("blocked_items"):
        html_lines.append('        <section>')
        html_lines.append('            <div class="section-heading">')
        html_lines.append(f'                <h2>⚠️ Pruebas Bloqueadas en PaP (Grafana Argos) <span class="badge-count">{len(grafana_data["blocked_items"])}</span></h2>')
        html_lines.append('            </div>')
        html_lines.append('            <div class="data-table-wrap">')
        html_lines.append('                <table class="data-table">')
        html_lines.append('                    <thead>')
        html_lines.append('                        <tr>')
        html_lines.append('                            <th>Proyecto</th>')
        html_lines.append('                            <th>Test Plan</th>')
        html_lines.append('                            <th>Resumen Test Plan</th>')
        html_lines.append('                            <th>Sistema</th>')
        html_lines.append('                            <th>Prioridad</th>')
        html_lines.append('                            <th>Bloqueadas</th>')
        html_lines.append('                            <th>Comentario / Causa Bloqueo</th>')
        html_lines.append('                        </tr>')
        html_lines.append('                    </thead>')
        html_lines.append('                    <tbody>')
        for b_item in grafana_data["blocked_items"]:
            html_lines.append('                        <tr>')
            html_lines.append(f'                            <td><strong>{html.escape(b_item["prj"])}</strong></td>')
            html_lines.append(f'                            <td><code>{html.escape(b_item["test_plan"])}</code></td>')
            html_lines.append(f'                            <td>{html.escape(b_item["resumen"])}</td>')
            html_lines.append(f'                            <td>{html.escape(b_item["sistema"])}</td>')
            html_lines.append(f'                            <td>{html.escape(b_item["prioridad"])}</td>')
            html_lines.append(f'                            <td><span class="badge badge-p1">{b_item["block_count"]}</span></td>')
            html_lines.append(f'                            <td><span class="badge badge-p2">{html.escape(b_item["comment"])}</span></td>')
            html_lines.append('                        </tr>')
        html_lines.append('                    </tbody>')
        html_lines.append('                </table>')
        html_lines.append('            </div>')
        html_lines.append('        </section>')

    # SECCIÓN 2: Detalle de Proyectos e Incidencias con Diagnóstico IA
    html_lines.append('        <section>')
    html_lines.append('            <div class="section-heading">')
    html_lines.append(f'                <h2>Seguimiento de Proyectos e Incidencias Remedy <span class="badge-count">{total_projects} proyectos</span></h2>')
    html_lines.append('            </div>')

    for prj_code in sorted_project_codes:
        p_info = all_projects.get(prj_code, {})
        p_incidents = incidents_by_project.get(prj_code, [])
        p_grafana = grafana_data.get("by_project", {}).get(prj_code, {})

        has_crit = any(
            (i.get("Prioridad") or "").upper() in ("P1", "P2", "CRÍTICA", "ALTA")
            and "cerrad" not in (i.get("Estatus") or "").lower()
            and "resuelt" not in (i.get("Estatus") or "").lower()
            for i in p_incidents
        ) or p_grafana.get("block_count", 0) > 0

        card_class = "project-card has-crit" if has_crit else "project-card"
        html_lines.append(f'            <article class="{card_class}" id="card-{html.escape(prj_code)}">')

        # Project Header
        html_lines.append('                <div class="project-header-top">')
        html_lines.append('                    <div class="project-code-title">')
        html_lines.append(f'                        <span class="project-code">{html.escape(prj_code)}</span>')
        html_lines.append(f'                        <h3 class="project-title">{html.escape(p_info.get("summary") or prj_code)}</h3>')
        html_lines.append('                    </div>')
        html_lines.append('                    <div style="display:flex; gap:8px; align-items:center;">')
        html_lines.append(f'                        {format_badge_deployment(p_info.get("despliegue", "Completo"))}')
        dec = (p_info.get("decision") or "GO").upper()
        if "GO" in dec:
            html_lines.append('                        <span class="badge" style="background:#DCFCE7; color:#166534;">GO</span>')
        else:
            html_lines.append(f'                        <span class="badge badge-neutral">{html.escape(dec)}</span>')
        if p_info.get("metodologia"):
            html_lines.append(f'                        <span class="badge badge-neutral">{html.escape(p_info["metodologia"])}</span>')
        html_lines.append('                    </div>')
        html_lines.append('                </div>')

        # Project Description
        if p_info.get("descripcion"):
            html_lines.append(f'                <div class="project-desc">"{html.escape(p_info["descripcion"])}"</div>')

        # Grafana PaP mini banner
        if p_grafana and p_grafana.get("total_tests", 0) > 0:
            p_pass = p_grafana.get("pass_count", 0)
            p_tot = p_grafana.get("total_tests", 0)
            p_blk = p_grafana.get("block_count", 0)
            p_pend = p_grafana.get("pending_count", 0)
            p_rate = round((p_pass / p_tot) * 100, 1) if p_tot > 0 else 0.0

            html_lines.append('                <div class="project-pap-banner">')
            html_lines.append(f'                    <span>🧪 <strong>Pruebas PaP:</strong> {p_pass}/{p_tot} Pasadas ({p_rate}%)</span>')
            if p_blk > 0:
                html_lines.append(f'                    <span style="color:#DC2626; font-weight:700;">⚠️ {p_blk} Bloqueadas</span>')
            if p_pend > 0:
                html_lines.append(f'                    <span style="color:#6B7280;">⏳ {p_pend} Pendientes</span>')
            html_lines.append('                </div>')

        # Incidents List for this project
        if p_incidents:
            html_lines.append(f'                <div style="margin-top:14px;">')
            html_lines.append(f'                    <div style="font-size:12px; font-weight:700; text-transform:uppercase; color:#6B7280; margin-bottom:8px;">Incidencias Remedy ({len(p_incidents)}):</div>')
            for inc in p_incidents:
                inc_id = inc.get("ID de incidencia") or "INC"
                prio = inc.get("Prioridad") or inc.get("Urgencia") or "P3"
                status = inc.get("Estatus") or "Asignado"
                desc = inc.get("Descripción") or inc.get("descripcion") or ""
                sistema = inc.get("Impacto") or inc.get("producto") or inc.get("Grupo asignado") or "Tecnología"
                fecha_prev = inc.get("Fecha Prevista") or inc.get("fecha_prevista") or "Pendiente de acordar"

                ia_data = ia_summaries.get(inc_id, {})

                html_lines.append('                    <div class="incident-item">')
                html_lines.append('                        <div class="incident-head">')
                html_lines.append('                            <div style="display:flex; align-items:center; gap:8px;">')
                html_lines.append(f'                                <span class="incident-id">{html.escape(inc_id)}</span>')
                html_lines.append(f'                                {format_badge_priority(prio)}')
                html_lines.append(f'                                {format_badge_status(status)}')
                html_lines.append(f'                                <span class="badge badge-neutral">{html.escape(sistema)}</span>')
                html_lines.append('                            </div>')
                html_lines.append(f'                            <div style="font-size:12px; color:#6B7280;">📅 Prevista: <strong>{html.escape(fecha_prev)}</strong></div>')
                html_lines.append('                        </div>')
                html_lines.append(f'                        <div class="incident-desc-raw">{html.escape(desc)}</div>')

                # Resumen IA
                if ia_data and (ia_data.get("problema") or ia_data.get("impacto") or ia_data.get("solucion")):
                    html_lines.append('                        <div class="ia-box">')
                    html_lines.append('                            <div class="ia-box-header">🤖 Diagnóstico Epsilon Resumen IA</div>')
                    if ia_data.get("impacto"):
                        html_lines.append(f'                            <div class="ia-impact-highlight"><strong>💥 Impacto en Servicio y Negocio:</strong> {html.escape(ia_data["impacto"])}</div>')
                    if ia_data.get("problema"):
                        html_lines.append(f'                            <div class="ia-field"><strong>🔍 Problema detectado:</strong> {html.escape(ia_data["problema"])}</div>')
                    if ia_data.get("solucion"):
                        html_lines.append(f'                            <div class="ia-field"><strong>🛠️ Solución / Causa raíz:</strong> {html.escape(ia_data["solucion"])}</div>')
                    sig = ia_data.get("siguienteAccion") or ia_data.get("siguiente_accion")
                    if sig:
                        html_lines.append(f'                            <div class="ia-field"><strong>➡️ Próxima acción:</strong> {html.escape(sig)}</div>')
                    bloqueos = ia_data.get("bloqueos")
                    if bloqueos and isinstance(bloqueos, list) and len(bloqueos) > 0:
                        html_lines.append(f'                            <div class="ia-field" style="color:#DC2626;"><strong>⛔ Bloqueos:</strong> {html.escape(", ".join(str(b) for b in bloqueos))}</div>')
                    html_lines.append('                        </div>')

                html_lines.append('                    </div>')
            html_lines.append('                </div>')
        else:
            html_lines.append('                <div style="font-size:12px; color:#16A34A; margin-top:8px;">✅ Sin incidencias Remedy abiertas para este proyecto.</div>')

        html_lines.append('            </article>')

    # Incidencias sin proyecto asignado (transversales)
    if incidents_without_project:
        html_lines.append('            <article class="project-card" id="card-transversales">')
        html_lines.append('                <div class="project-header-top">')
        html_lines.append('                    <div class="project-code-title">')
        html_lines.append('                        <span class="project-code" style="background:#4B5563;">TRANSVERSAL</span>')
        html_lines.append('                        <h3 class="project-title">Incidencias Transversales / Sin Proyecto Asignado</h3>')
        html_lines.append('                    </div>')
        html_lines.append(f'                    <span class="badge badge-neutral">{len(incidents_without_project)} incidencias</span>')
        html_lines.append('                </div>')
        html_lines.append('                <div style="margin-top:14px;">')
        for inc in incidents_without_project:
            inc_id = inc.get("ID de incidencia") or "INC"
            prio = inc.get("Prioridad") or inc.get("Urgencia") or "P3"
            status = inc.get("Estatus") or "Asignado"
            desc = inc.get("Descripción") or inc.get("descripcion") or ""
            sistema = inc.get("Impacto") or inc.get("producto") or inc.get("Grupo asignado") or "Tecnología"
            fecha_prev = inc.get("Fecha Prevista") or inc.get("fecha_prevista") or "Pendiente de acordar"
            ia_data = ia_summaries.get(inc_id, {})

            html_lines.append('                    <div class="incident-item">')
            html_lines.append('                        <div class="incident-head">')
            html_lines.append('                            <div style="display:flex; align-items:center; gap:8px;">')
            html_lines.append(f'                                <span class="incident-id">{html.escape(inc_id)}</span>')
            html_lines.append(f'                                {format_badge_priority(prio)}')
            html_lines.append(f'                                {format_badge_status(status)}')
            html_lines.append(f'                                <span class="badge badge-neutral">{html.escape(sistema)}</span>')
            html_lines.append('                            </div>')
            html_lines.append(f'                            <div style="font-size:12px; color:#6B7280;">📅 Prevista: <strong>{html.escape(fecha_prev)}</strong></div>')
            html_lines.append('                        </div>')
            html_lines.append(f'                        <div class="incident-desc-raw">{html.escape(desc)}</div>')
            if ia_data and (ia_data.get("problema") or ia_data.get("impacto") or ia_data.get("solucion")):
                html_lines.append('                        <div class="ia-box">')
                html_lines.append('                            <div class="ia-box-header">🤖 Diagnóstico Epsilon Resumen IA</div>')
                if ia_data.get("impacto"):
                    html_lines.append(f'                            <div class="ia-impact-highlight"><strong>💥 Impacto en Servicio y Negocio:</strong> {html.escape(ia_data["impacto"])}</div>')
                if ia_data.get("problema"):
                    html_lines.append(f'                            <div class="ia-field"><strong>🔍 Problema detectado:</strong> {html.escape(ia_data["problema"])}</div>')
                if ia_data.get("solucion"):
                    html_lines.append(f'                            <div class="ia-field"><strong>🛠️ Solución / Causa raíz:</strong> {html.escape(ia_data["solucion"])}</div>')
                sig = ia_data.get("siguienteAccion") or ia_data.get("siguiente_accion")
                if sig:
                    html_lines.append(f'                            <div class="ia-field"><strong>➡️ Próxima acción:</strong> {html.escape(sig)}</div>')
                html_lines.append('                        </div>')
            html_lines.append('                    </div>')
        html_lines.append('                </div>')
        html_lines.append('            </article>')

    html_lines.append('        </section>')

    # Footer Banner
    html_lines.append('        <footer class="footer-banner">')
    html_lines.append(f'            <p><strong>Mesa de Seguimiento de Incidencias IT · Release {html.escape(rel)}</strong></p>')
    html_lines.append(f'            <p>Reporte oficial generado por <code>@release-communicator</code> · Customer &amp; Service Operations (IM-CSO).</p>')
    html_lines.append(f'            <p><a href="/dashboards/release-desk/?release={html.escape(rel)}" class="btn-cta" style="margin-top:10px;">Ir a la Mesa de Release</a></p>')
    html_lines.append('        </footer>')

    html_lines.append('    </main>')
    html_lines.append('    <script src="/dashboards/assets/topbar.js?v=20261122_1530" defer></script>')
    html_lines.append('</body>')
    html_lines.append('</html>')

    # Guardar archivo
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(html_lines), encoding="utf-8")
    print(f"[OK] Informe generado con éxito en: {output_path}")
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Generador del Informe Ejecutivo HTML de Release 360°.")
    parser.add_argument("--release", required=True, help="Código de la release (ej: 2026R11)")
    parser.add_argument("--output", default="", help="Ruta de destino del HTML (por defecto: dashboards/informes/comunicado-release-{release}/index.html)")
    parser.add_argument("--grafana-csv", default="", help="Ruta al CSV exportado de Grafana PaP")
    parser.add_argument("--projects-csv", default="", help="Ruta al CSV de proyectos de la release")
    parser.add_argument("--postmortem-json", default="", help="Ruta al JSON de postmortem")
    parser.add_argument("--catalog-json", default="", help="Ruta al catálogo projects_catalog.json")
    parser.add_argument("--releases-data", default="", help="Ruta a releases-data.js")
    parser.add_argument("--force", action="store_true", help="Sobrescribir si ya existe")

    args = parser.parse_args()
    rel = args.release.strip()

    if args.output:
        out_path = Path(args.output)
    else:
        out_path = PROJECT_ROOT / "dashboards" / "informes" / f"comunicado-release-{rel}" / "index.html"

    if out_path.exists() and not args.force:
        print(f"[INFO] El informe para {rel} ya existe en: {out_path}")
        print("Use --force para regenerarlo.")
        sys.exit(0)

    grafana_p = Path(args.grafana_csv) if args.grafana_csv else None
    projects_p = Path(args.projects_csv) if args.projects_csv else None
    postmortem_p = Path(args.postmortem_json) if args.postmortem_json else None
    catalog_p = Path(args.catalog_json) if args.catalog_json else None
    releases_data_p = Path(args.releases_data) if args.releases_data else None

    build_release_report_html(
        release=rel,
        output_path=out_path,
        grafana_csv=grafana_p,
        projects_csv=projects_p,
        postmortem_json=postmortem_p,
        catalog_json=catalog_p,
        releases_data_js=releases_data_p,
    )


if __name__ == "__main__":
    main()
