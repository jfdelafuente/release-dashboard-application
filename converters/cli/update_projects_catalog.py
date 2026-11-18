#!/usr/bin/env python3
"""
Actualiza de forma incremental y no destructiva el catálogo de proyectos
por release mensual en data/projects_catalog.json a partir de un CSV
con columnas: JIRA;Summary;Despliegue;Descripcion.

Uso:
    python update_projects_catalog.py data/projects/2026R11.csv --release 2026R11
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime
import json
from pathlib import Path
import sys
from typing import Any, Dict, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def update_projects_catalog(
    csv_path: Path | str,
    release_name: str,
    catalog_path: Optional[Path | str] = None,
) -> Dict[str, Any]:
    """Importa un CSV de proyectos para `release_name` preservando releases previas."""
    src = Path(csv_path)
    if not src.exists():
        raise FileNotFoundError(f"No existe el fichero CSV: {src}")

    rel = (release_name or "").strip()
    if not rel:
        raise ValueError("release_name es obligatorio")

    dest = Path(catalog_path) if catalog_path else (PROJECT_ROOT / "data" / "projects_catalog.json")
    catalog: Dict[str, Any] = {"by_release": {}, "projects": {}}

    if dest.exists():
        try:
            loaded = json.loads(dest.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                if "by_release" in loaded and "projects" in loaded:
                    catalog = loaded
                else:
                    # Migrar formato plano previo si existiera
                    catalog["projects"] = {k: v for k, v in loaded.items() if isinstance(v, dict)}
        except Exception:
            pass

    by_release: Dict[str, Dict[str, Any]] = catalog.setdefault("by_release", {})
    projects: Dict[str, Dict[str, Any]] = catalog.setdefault("projects", {})
    release_bucket: Dict[str, Any] = {}

    with open(src, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            code = (row.get("JIRA") or "").strip().upper()
            if not code:
                continue
            entry = {
                "jira": code,
                "summary": (row.get("Summary") or "").strip(),
                "despliegue": (row.get("Despliegue") or "").strip(),
                "descripcion": (row.get("Descripcion") or "").strip(),
            }
            release_bucket[code] = entry

            existing = projects.get(code, {})
            releases_list = list(existing.get("releases") or [])
            if rel not in releases_list:
                releases_list.append(rel)
            projects[code] = {
                **entry,
                "releases": releases_list,
            }

    by_release[rel] = release_bucket
    catalog["updated"] = datetime.now().isoformat()

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "success": True,
        "release_name": rel,
        "imported_count": len(release_bucket),
        "total_releases": len(by_release),
        "total_projects": len(projects),
        "catalog_path": str(dest),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Actualiza data/projects_catalog.json por release mensual")
    parser.add_argument("csv_path", help="Ruta al CSV de proyectos (separador ';')")
    parser.add_argument("--release", required=True, help="Nombre de la release mensual (ej. 2026R11)")
    parser.add_argument("--catalog", default=None, help="Ruta opcional del catálogo JSON destino")
    args = parser.parse_args()

    res = update_projects_catalog(args.csv_path, args.release, args.catalog)
    print(json.dumps(res, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
