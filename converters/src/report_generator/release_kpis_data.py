"""Lectura de dashboards/release-kpis/releases-data.js desde Python.

RAW_RELEASES es un array de arrays de literales (strings y números), sin
ninguna expresión JS dinámica — su sintaxis es simultáneamente válida en
JS y en Python, así que basta con extraer el literal con una expresión
regular y evaluarlo con ast.literal_eval (ver research.md §4). No hace
falta un intérprete JS embebido.
"""
import ast
import re
from pathlib import Path

DEFAULT_RELEASES_DATA_PATH = Path("dashboards") / "release-kpis" / "releases-data.js"

_RAW_RELEASES_RE = re.compile(r"const\s+RAW_RELEASES\s*=\s*(\[.*?\]);", re.DOTALL)


def _format_date(fecha, month, year):
    """Réplica de formatDate(): usa la fecha si existe, si no cae al mes."""
    if not fecha:
        return f"{month} {year}"
    return re.sub(r"\.$", "", fecha).replace("-", " ") + f" {year}"


def parse_raw_releases(js_source):
    """Extrae y evalúa el literal RAW_RELEASES del contenido de releases-data.js."""
    match = _RAW_RELEASES_RE.search(js_source)
    if not match:
        raise ValueError("No se encontró RAW_RELEASES en el fichero de datos de release-kpis")
    return ast.literal_eval(match.group(1))


def build_releases(raw_releases):
    """Réplica de buildReleases(): añade totalEntrada/pctPaP/pctFirstWeek derivados."""
    releases = []
    for name, year, fecha, month, pap_entrada, pap_resueltas, post_entrada, post_resueltas in raw_releases:
        pct_pap = round(100 * pap_resueltas / pap_entrada) if pap_entrada else 0
        pct_first_week = round(100 * post_resueltas / post_entrada) if post_entrada else 0
        releases.append({
            "name": name,
            "year": year,
            "date": _format_date(fecha, month, year),
            "pap_entrada": pap_entrada,
            "pap_resueltas": pap_resueltas,
            "post_entrada": post_entrada,
            "post_resueltas": post_resueltas,
            "total_incidencias": pap_entrada + post_entrada,
            "pct_pap": pct_pap,
            "pct_first_week": pct_first_week,
        })
    return releases


def find_release(releases, release_name):
    """Busca una release por nombre exacto en la lista devuelta por build_releases(). None si no existe."""
    for release in releases:
        if release["name"] == release_name:
            return release
    return None


def load_release_kpis_context(path=None):
    """Lee releases-data.js y devuelve la lista de releases (orden cronológico ascendente).

    Mismo orden que usan las gráficas del dashboard (no el de la tabla,
    que se muestra invertido — ver renderTable() en app.js).
    """
    path = Path(path) if path else DEFAULT_RELEASES_DATA_PATH
    js_source = path.read_text(encoding="utf-8")
    return build_releases(parse_raw_releases(js_source))
