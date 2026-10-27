#!/usr/bin/env python3
"""
select_active_csvs.py
Selecciona de forma determinista y optimizada los archivos CSV activos más recientes
en un directorio de entrada para su procesamiento por generate-dashboards.sh.

Evita conversiones redundantes y bucles de archivado de ficheros históricos:
1. Para Incidencias Masivas: selecciona únicamente el CSV con la fecha más reciente.
2. Para Postmortems: agrupa por 'release' (p.ej. 2026R7, 2026R9) y selecciona el CSV
   con la fecha más reciente para cada release.

Uso:
    python select_active_csvs.py <input_dir>
Salida por stdout (líneas separadas por tabulación):
    <ruta_completa_csv>\t<massive|postmortem>\t<release_name>
"""

import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

MONTH_MAP = {
    'jan': 1, 'ene': 1, 'enero': 1, 'january': 1,
    'feb': 2, 'febrero': 2, 'february': 2,
    'mar': 3, 'marzo': 3, 'march': 3,
    'apr': 4, 'abr': 4, 'abril': 4, 'april': 4,
    'may': 5, 'mayo': 5,
    'jun': 6, 'junio': 6, 'june': 6,
    'jul': 7, 'julio': 7, 'july': 7,
    'aug': 8, 'ago': 8, 'agosto': 8, 'august': 8,
    'sep': 9, 'sept': 9, 'set': 9, 'septiembre': 9, 'september': 9,
    'oct': 10, 'octubre': 10, 'october': 10,
    'nov': 11, 'noviembre': 11, 'november': 11,
    'dec': 12, 'dic': 12, 'diciembre': 12, 'december': 12,
}


def parse_file_date_key(file_path: Path) -> Tuple[datetime, int, float]:
    """
    Extrae una clave de ordenación cronológica (fecha_parseada, secuencia, mtime)
    del nombre del archivo, con fallback al mtime del sistema de archivos.
    """
    filename = file_path.name
    mtime = file_path.stat().st_mtime if file_path.exists() else 0.0

    # Extraer número de secuencia p.ej. (1), (2)
    seq_match = re.search(r'\((\d+)\)', filename)
    seq = int(seq_match.group(1)) if seq_match else 0

    # Patrón 1: DD Mon YYYY (p.ej. 27 Oct 2026 o 04 Aug 2026)
    m1 = re.search(r'(\d{1,2})\s+([A-Za-z]{3,10})\s+(\d{4})', filename)
    if m1:
        day = int(m1.group(1))
        month_str = m1.group(2).lower()[:3]
        year = int(m1.group(3))
        month = MONTH_MAP.get(month_str, 1)
        try:
            return (datetime(year, month, day), seq, mtime)
        except ValueError:
            pass

    # Patrón 2: DD_MM_YYYY o DD-MM-YYYY (p.ej. 10_08_2026)
    m2 = re.search(r'(\d{2})[_-](\d{2})[_-](\d{4})', filename)
    if m2:
        day = int(m2.group(1))
        month = int(m2.group(2))
        year = int(m2.group(3))
        try:
            return (datetime(year, month, day), seq, mtime)
        except ValueError:
            pass

    # Patrón 3: YYYYMMDD
    m3 = re.search(r'(\d{4})(\d{2})(\d{2})', filename)
    if m3:
        year = int(m3.group(1))
        month = int(m3.group(2))
        day = int(m3.group(3))
        try:
            return (datetime(year, month, day), seq, mtime)
        except ValueError:
            pass

    # Fallback: fecha de modificación del fichero o 1970
    fallback_dt = datetime.fromtimestamp(mtime) if mtime > 0 else datetime(1970, 1, 1)
    return (fallback_dt, seq, mtime)


def detect_file_type_and_release(filename: str) -> Tuple[str, Optional[str]]:
    """
    Determina si un CSV es postmortem o masivo, y extrae release_name si existe.
    """
    fn_lower = filename.lower()
    is_postmortem = ('postmortem' in fn_lower) or ('mesa post' in fn_lower)

    # Extraer release (p.ej. 2026R7, 2026R9, R3)
    rel_match = re.search(r'([0-9]{4}R[0-9]+|R[0-9]+)', filename, re.IGNORECASE)
    release_name = rel_match.group(1).upper() if rel_match else None

    if is_postmortem:
        return ('postmortem', release_name)
    return ('massive', release_name)


def select_active_csv_files(input_dir: Path) -> List[Tuple[Path, str, Optional[str]]]:
    """
    Escanea input_dir y devuelve una lista ordenada de tuplas:
    (csv_path, file_type, release_name)
    con solo los archivos más recientes por categoría/release.
    """
    csv_files = [p for p in input_dir.glob('*.csv') if p.is_file()]
    if not csv_files:
        return []

    massive_files: List[Path] = []
    postmortem_by_release: Dict[str, List[Path]] = {}

    for p in csv_files:
        ftype, rel = detect_file_type_and_release(p.name)
        if ftype == 'massive':
            massive_files.append(p)
        else:
            group_key = rel if rel else p.stem
            postmortem_by_release.setdefault(group_key, []).append(p)

    selected: List[Tuple[Path, str, Optional[str]]] = []

    # 1. Postmortems: el más reciente por cada release encontrada
    for rel_key, files in sorted(postmortem_by_release.items()):
        best_pm = max(files, key=parse_file_date_key)
        _, rel_name = detect_file_type_and_release(best_pm.name)
        selected.append((best_pm, 'postmortem', rel_name))

    # 2. Incidencias masivas: únicamente el más reciente global
    if massive_files:
        best_massive = max(massive_files, key=parse_file_date_key)
        _, rel_name = detect_file_type_and_release(best_massive.name)
        selected.append((best_massive, 'massive', rel_name))

    return selected


def main():
    if len(sys.argv) < 2:
        print(f"Uso: {sys.argv[0]} <directorio_input>", file=sys.stderr)
        sys.exit(1)

    input_dir = Path(sys.argv[1])
    if not input_dir.exists() or not input_dir.is_dir():
        print(f"Error: Directorio no válido: {input_dir}", file=sys.stderr)
        sys.exit(1)

    selected = select_active_csv_files(input_dir)
    for p, ftype, rel_name in selected:
        rel_str = rel_name if rel_name else ""
        print(f"{p}\t{ftype}\t{rel_str}")


if __name__ == '__main__':
    main()

