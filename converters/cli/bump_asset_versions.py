#!/usr/bin/env python3
"""
Actualiza automáticamente el parámetro de cache-busting (?v=<version>) en los
enlaces locales (.css y .js) de los HTML de las consolas (Mesa de Release y
Consola de Triaje).

Uso:
    python converters/cli/bump_asset_versions.py [--version 20261119_0840]
"""

from __future__ import annotations

import argparse
import re
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

DEFAULT_HTML_TARGETS = [
    PROJECT_ROOT / "dashboards" / "release-desk" / "index.html",
    PROJECT_ROOT / "dashboards" / "emergency-triage-console" / "index.html",
]

_ASSET_ATTR_RE = re.compile(
    r"""(?P<prefix>(?:href|src)=["'])(?P<url>[^"']+?\.(?:css|js))(?:\?v=[^"']*)?(?P<suffix>["'])""",
    re.IGNORECASE,
)


def bump_html_content(html: str, version: str) -> str:
    """Reemplaza o añade ?v=<version> en todos los assets locales .css/.js."""

    def _replace(match: re.Match[str]) -> str:
        url = match.group("url")
        if url.startswith(("http://", "https://", "//", "data:")):
            return match.group(0)
        return f"{match.group('prefix')}{url}?v={version}{match.group('suffix')}"

    return _ASSET_ATTR_RE.sub(_replace, html)


def bump_html_asset_versions(
    html_paths: Optional[Iterable[Path | str]] = None,
    version: Optional[str] = None,
) -> List[Path]:
    """Actualiza ?v=<version> en los ficheros HTML indicados y devuelve los modificados."""
    ver = (version or datetime.now().strftime("%Y%m%d_%H%M")).strip()
    targets = [Path(p) for p in (html_paths if html_paths is not None else DEFAULT_HTML_TARGETS)]
    updated: List[Path] = []
    for path in targets:
        if not path.exists():
            continue
        original = path.read_text(encoding="utf-8")
        new_content = bump_html_content(original, ver)
        if new_content != original:
            path.write_text(new_content, encoding="utf-8")
            updated.append(path)
    return updated


def main() -> int:
    parser = argparse.ArgumentParser(description="Versiona assets CSS/JS locales en HTMLs del portal.")
    parser.add_argument("--version", help="Versión a aplicar (por defecto YYYYMMDD_HHMM)")
    args = parser.parse_args()
    updated = bump_html_asset_versions(version=args.version)
    print(f"Actualizados {len(updated)} fichero(s): {[str(p) for p in updated]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
