#!/usr/bin/env python3
"""
Limpieza puntual de data/output/: para cada release de postmortem con más
de un fichero -postmortem.json acumulado (por subidas repetidas del CSV
antes de que convert_postmortems.py archivara automáticamente la versión
anterior), conserva solo el más reciente y mueve el resto a data/archive/.

No borra nada: es un mover, no un delete. Los ficheros sin release_name
(generados antes de specs/007-per-release-dashboards) se dejan intactos,
al no poder saber con certeza si pertenecen a la misma release.

Uso (desde la raíz del repo):
    python converters/cli/cleanup_release_output.py --dry-run   # solo muestra qué haría
    python converters/cli/cleanup_release_output.py             # aplica los cambios
"""
import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from convert_postmortems import DEFAULT_OUTPUT_DIR, DEFAULT_ARCHIVE_DIR, build_index_for_hub


def find_release_groups(output_dir):
    """Agrupa los -postmortem.json de output_dir por _metadata.release_name.

    Devuelve {release_name: [Path, ...]} solo para release_name no vacíos;
    los ficheros sin release_name quedan fuera (no se tocan).
    """
    groups = defaultdict(list)
    for file_path in Path(output_dir).glob('*-postmortem.json'):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = json.load(f)
        except (json.JSONDecodeError, IOError, OSError) as e:
            print(f"[WARN] No se pudo leer {file_path.name}: {e}")
            continue
        release_name = content.get('_metadata', {}).get('release_name')
        if release_name:
            groups[release_name.strip()].append(file_path)
    return groups


def cleanup(output_dir=None, archive_dir=None, dry_run=False):
    output_dir = Path(output_dir or DEFAULT_OUTPUT_DIR)
    archive_dir = Path(archive_dir or DEFAULT_ARCHIVE_DIR)

    groups = find_release_groups(output_dir)
    archived_count = 0

    for release_name, files in sorted(groups.items()):
        if len(files) <= 1:
            continue

        # Más reciente primero: ese es el que se conserva.
        files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        keeper, stale = files[0], files[1:]

        print(f"\nRelease '{release_name}': {len(files)} ficheros, conservando '{keeper.name}'")
        for file_path in stale:
            if dry_run:
                print(f"  [DRY-RUN] archivaría: {file_path.name}")
            else:
                archive_dir.mkdir(parents=True, exist_ok=True)
                timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                archived_path = archive_dir / f"{file_path.stem}_{timestamp}{file_path.suffix}"
                file_path.rename(archived_path)
                print(f"  archivado: {file_path.name} -> data/archive/{archived_path.name}")
            archived_count += 1

    if archived_count == 0:
        print("Nada que archivar: cada release ya tiene como máximo un fichero en data/output/.")
    elif dry_run:
        print(f"\n[DRY-RUN] Se archivarían {archived_count} fichero(s). Ejecuta sin --dry-run para aplicar.")
    else:
        print(f"\n{archived_count} fichero(s) archivado(s). Regenerando index.json...")
        build_index_for_hub(str(output_dir))

    return archived_count


def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('--dry-run', action='store_true', help='Solo muestra qué se archivaría, sin mover nada')
    parser.add_argument('--output-dir', default=None, help='Directorio a limpiar (default: data/output/)')
    parser.add_argument('--archive-dir', default=None, help='Directorio de archivo (default: data/archive/)')
    args = parser.parse_args()

    cleanup(args.output_dir, args.archive_dir, args.dry_run)


if __name__ == '__main__':
    main()
