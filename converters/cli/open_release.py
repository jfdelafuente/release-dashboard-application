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

MONTHS_ABBR_ES = {
    1: "ene",
    2: "feb",
    3: "mar",
    4: "abr",
    5: "may",
    6: "jun",
    7: "jul",
    8: "ago",
    9: "sep",
    10: "oct",
    11: "nov",
    12: "dic",
}

MONTH_NAME_TO_NUM = {
    "enero": 1, "ene": 1,
    "febrero": 2, "feb": 2,
    "marzo": 3, "mar": 3,
    "abril": 4, "abr": 4,
    "mayo": 5, "may": 5,
    "junio": 6, "jun": 6,
    "julio": 7, "jul": 7,
    "agosto": 8, "ago": 8,
    "septiembre": 9, "setiembre": 9, "sep": 9, "sept": 9,
    "octubre": 10, "oct": 10,
    "noviembre": 11, "nov": 11,
    "diciembre": 12, "dic": 12,
}


def normalize_fecha_pap(raw_date: Optional[str]) -> str:
    """Normaliza fechas en formatos libres (DD/MM/YYYY, YYYY-MM-DD, D-mes, etc.) al estándar 'D-mes.'."""
    if not raw_date:
        return ""
    val = str(raw_date).strip()
    if not val:
        return ""

    low = val.lower()

    # Caso 1: ya tiene formato "22-nov." o "22-nov" o "7-jun."
    m_abbr = re.match(r"^(\d{1,2})\s*-\s*([a-záéíóú]+)\.?$", low)
    if m_abbr:
        day = int(m_abbr.group(1))
        mon_str = m_abbr.group(2)
        mon_num = MONTH_NAME_TO_NUM.get(mon_str)
        if mon_num and 1 <= day <= 31:
            return f"{day}-{MONTHS_ABBR_ES[mon_num]}."
        return f"{day}-{mon_str}."

    # Caso 2: formato ISO YYYY-MM-DD o YYYY/MM/DD
    m_iso = re.match(r"^(\d{4})[/\-\.](\d{1,2})[/\-\.](\d{1,2})$", low)
    if m_iso:
        day = int(m_iso.group(3))
        month = int(m_iso.group(2))
        if 1 <= month <= 12 and 1 <= day <= 31:
            return f"{day}-{MONTHS_ABBR_ES[month]}."

    # Caso 3: formato DD/MM/YYYY o DD-MM-YYYY o DD.MM.YYYY o DD/MM
    m_dmy = re.match(r"^(\d{1,2})[/\-\.](\d{1,2})(?:[/\-\.]\d{2,4})?$", low)
    if m_dmy:
        day = int(m_dmy.group(1))
        month = int(m_dmy.group(2))
        if 1 <= month <= 12 and 1 <= day <= 31:
            return f"{day}-{MONTHS_ABBR_ES[month]}."

    # Caso 4: texto natural "22 de noviembre" o "22 noviembre 2026"
    m_text = re.match(r"^(\d{1,2})(?:\s+de)?\s+([a-záéíóú]+)(?:\s+(?:de\s+)?\d{2,4})?$", low)
    if m_text:
        day = int(m_text.group(1))
        mon_str = m_text.group(2)
        mon_num = MONTH_NAME_TO_NUM.get(mon_str)
        if mon_num and 1 <= day <= 31:
            return f"{day}-{MONTHS_ABBR_ES[mon_num]}."

    return val


def find_candidate_projects_csv(release_code: str, base_dir: Optional[Path | str] = None) -> Optional[Path]:
    """Busca automáticamente un fichero CSV de proyectos candidato en data/projects/ o raíz."""
    root = Path(base_dir) if base_dir else PROJECT_ROOT
    code_upper = release_code.upper()
    code_lower = release_code.lower()

    m = RELEASE_RE.match(code_upper)
    num = m.group(2) if m else ""

    candidates = [
        root / "data" / "projects" / f"{code_upper}.csv",
        root / "data" / "projects" / f"{code_lower}.csv",
        root / f"proyecto_{code_lower}.csv",
        root / f"proyectos_{code_lower}.csv",
    ]
    if num:
        candidates.extend([
            root / f"proyecto_r{num}.csv",
            root / f"proyectos_r{num}.csv",
            root / f"proyecto_R{num}.csv",
            root / f"proyectos_R{num}.csv",
            root / "data" / "projects" / f"R{num}.csv",
            root / "data" / "projects" / f"r{num}.csv",
        ])

    for c in candidates:
        if c.exists() and c.is_file() and c.stat().st_size > 0:
            return c
    return None


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
    pap_date = normalize_fecha_pap(fecha_pap)

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
    return {"release_name": code, "added": True, "already_exists": False, "releases_js": str(target), "fecha_pap": pap_date}


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
    auto_detect_projects: bool = True,
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

    csv_to_import: Optional[Path] = Path(projects_csv) if projects_csv else None
    auto_detected = False
    if not csv_to_import and auto_detect_projects:
        base_dir = Path(releases_js_path).resolve().parent.parent.parent if releases_js_path else PROJECT_ROOT
        detected = find_candidate_projects_csv(code, base_dir=base_dir)
        if detected:
            csv_to_import = detected
            auto_detected = True

    if csv_to_import:
        cat_res = update_projects_catalog(
            csv_to_import,
            code,
            catalog_path=catalog_path,
        )
        cat_res["source_csv"] = str(csv_to_import)
        cat_res["auto_detected"] = auto_detected
        result["projects_catalog"] = cat_res

    if sync_url:
        result["sync_postmortem"] = trigger_sync_postmortem(code, sync_url)

    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Abre una nueva Release mensual (YYYYRMM)")
    parser.add_argument("release", help="Código de la release (ej. 2026R12)")
    parser.add_argument("--fecha-pap", default="", help='Fecha PaP opcional (ej. "13-dic.", "22/11/2026", "2026-12-15")')
    parser.add_argument("--mes", default=None, help="Nombre del mes en español (opcional, se infiere de R1..R12)")
    parser.add_argument("--projects-csv", default=None, help="Ruta opcional al CSV de proyectos (;)")
    parser.add_argument("--catalog", default=None, help="Ruta opcional de projects_catalog.json")
    parser.add_argument("--releases-js", default=None, help="Ruta opcional de releases-data.js")
    parser.add_argument("--sync-url", default=None, help="URL base del servidor para POST /api/sync-postmortem")
    parser.add_argument("--no-auto-projects", action="store_true", help="Desactiva la búsqueda automática de CSV de proyectos si no se pasa --projects-csv")
    args = parser.parse_args()

    res = open_release(
        args.release,
        fecha_pap=args.fecha_pap,
        mes=args.mes,
        projects_csv=args.projects_csv,
        catalog_path=args.catalog,
        releases_js_path=args.releases_js,
        sync_url=args.sync_url,
        auto_detect_projects=not args.no_auto_projects,
    )
    print(json.dumps(res, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
