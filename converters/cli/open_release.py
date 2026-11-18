#!/usr/bin/env python3
"""
Automatiza la apertura de una nueva Release mensual (YYYYRMM, ej. 2026R12):
1. Registra la release en dashboards/release-kpis/releases-data.js (idempotente).
2. Opcionalmente importa el catálogo de proyectos CSV (--projects-csv) en data/projects_catalog.json.
3. Opcionalmente dispara la sincronización MonTMC (--sync-url http://localhost:8000).

Uso:
    python converters/cli/open_release.py 2026R12
    python converters/cli/open_release.py 2026R12 --fecha-pap "13-dic." --projects-csv proyecto_r12.csv
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from converters.cli.update_projects_catalog import update_projects_catalog  # noqa: E402

RELEASE_RE = re.compile(r"^(\d{4})R(\d{1,2})$", re.IGNORECASE)

MONTHS_ES = {
    1: "Enero",
    2: "Febrero",
    3: "Marzo",
    4: "Abril",
    5: "Mayo",
    6: "Junio",
    7: "Julio",
    8: "Agosto",
    9: "Septiembre",
    10: "Octubre",
    11: "Noviembre",
    12: "Diciembre",
}


def parse_release_code(release_name: str) -> Tuple[str, int, int, str]:
    """Valida el formato YYYYRMM (ej. 2026R12) y devuelve (codigo, año, num, mes_es)."""
    raw = (release_name or "").strip().upper()
    m = RELEASE_RE.match(raw)
    if not m:
        raise ValueError(f"Formato de release inválido '{release_name}'. Debe ser YYYYRMM (ej. 2026R12).")
    year = int(m.group(1))
    num = int(m.group(2))
    if not 1 <= num <= 12:
        raise ValueError(f"Número de release fuera de rango (1-12): {num}")
    return f"{year}R{num}", year, num, MONTHS_ES[num]


def register_release_in_js(
    release_name: str,
    fecha_pap: str = "",
    mes: Optional[str] = None,
    releases_js_path: Optional[Path | str] = None,
) -> Dict[str, Any]:
    """Inserta la release en RAW_RELEASES de releases-data.js si no existe todavía."""
    code, year, _, default_month = parse_release_code(release_name)
    month_name = (mes or default_month).strip()
    pap_date = (fecha_pap or "").strip()

    target = Path(releases_js_path) if releases_js_path else (PROJECT_ROOT / "dashboards" / "release-kpis" / "releases-data.js")
    if not target.exists():
        raise FileNotFoundError(f"No existe el fichero releases-data.js: {target}")

    content = target.read_text(encoding="utf-8")
    if re.search(rf'\["{re.escape(code)}"\s*,', content):
        return {"release_name": code, "added": False, "already_exists": True, "releases_js": str(target)}

    new_line = f'  ["{code}", {year}, {json.dumps(pap_date, ensure_ascii=False)}, {json.dumps(month_name, ensure_ascii=False)}, 0, 0, 0, 0],'
    idx = content.rfind("];")
    if idx == -1:
        raise ValueError(f"No se encontró el cierre '];' de RAW_RELEASES en {target}")

    before = content[:idx].rstrip()
    if before and not before.endswith(",") and not before.endswith("["):
        before += ","
    updated = f"{before}\n{new_line}\n{content[idx:]}"
    target.write_text(updated, encoding="utf-8")
    return {"release_name": code, "added": True, "already_exists": False, "releases_js": str(target)}


def trigger_sync_postmortem(release_name: str, sync_url: str) -> Dict[str, Any]:
    """Invoca POST /api/sync-postmortem sobre el servidor del dashboard."""
    base = sync_url.rstrip("/")
    url = f"{base}/api/sync-postmortem"
    payload = json.dumps({"release_name": release_name}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        return {"success": False, "skipped": True, "error": f"Servidor no accesible en {url}: {exc.reason}"}


def open_release(
    release_name: str,
    fecha_pap: str = "",
    mes: Optional[str] = None,
    projects_csv: Optional[Path | str] = None,
    catalog_path: Optional[Path | str] = None,
    releases_js_path: Optional[Path | str] = None,
    sync_url: Optional[str] = None,
) -> Dict[str, Any]:
    """Orquesta la apertura completa de una Release mensual."""
    code, _, _, _ = parse_release_code(release_name)
    result: Dict[str, Any] = {"success": True, "release_name": code}

    result["releases_data"] = register_release_in_js(
        code,
        fecha_pap=fecha_pap,
        mes=mes,
        releases_js_path=releases_js_path,
    )

    if projects_csv:
        result["projects_catalog"] = update_projects_catalog(
            projects_csv,
            code,
            catalog_path=catalog_path,
        )

    if sync_url:
        result["sync_postmortem"] = trigger_sync_postmortem(code, sync_url)

    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Abre una nueva Release mensual (YYYYRMM)")
    parser.add_argument("release", help="Código de la release (ej. 2026R12)")
    parser.add_argument("--fecha-pap", default="", help='Fecha PaP opcional (ej. "13-dic.")')
    parser.add_argument("--mes", default=None, help="Nombre del mes en español (opcional, se infiere de R1..R12)")
    parser.add_argument("--projects-csv", default=None, help="Ruta opcional al CSV de proyectos (;)")
    parser.add_argument("--catalog", default=None, help="Ruta opcional de projects_catalog.json")
    parser.add_argument("--releases-js", default=None, help="Ruta opcional de releases-data.js")
    parser.add_argument("--sync-url", default=None, help="URL base del servidor para POST /api/sync-postmortem")
    args = parser.parse_args()

    res = open_release(
        args.release,
        fecha_pap=args.fecha_pap,
        mes=args.mes,
        projects_csv=args.projects_csv,
        catalog_path=args.catalog,
        releases_js_path=args.releases_js,
        sync_url=args.sync_url,
    )
    print(json.dumps(res, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
