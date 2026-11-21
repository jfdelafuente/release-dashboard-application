#!/usr/bin/env python3
"""
Build index.json for Dashboard Hub
Scans data/output/ directory and creates an index of all JSON files
sorted by modification time (newest first).

Usage:
    python build_index.py                    # Scan current data/output/
    python build_index.py <directory_path>   # Scan specific directory
"""

import json
import os
from pathlib import Path
from datetime import datetime
import sys

# Fix Unicode encoding for Windows when run directly
if __name__ == '__main__' and sys.platform == 'win32':
    import io
    if hasattr(sys.stdout, 'buffer'):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def build_index(output_dir='data/output'):
    """
    Actualiza solo la sección 'massive' en index.json para Dashboard Hub.

    Mantiene la sección 'postmortem' sin cambios si existe.
    Soporta la nueva estructura modular (data/storage/processed y data/storage/index.json)
    además del fallback compatible (data/output/index.json).

    Args:
        output_dir: Directory path to scan for JSON files

    Returns:
        bool: True if successful, False otherwise
    """
    output_path = Path(output_dir)

    # Si output_dir por defecto no tiene masivas pero data/storage/processed sí, o viceversa,
    # recopilamos masivas de output_path o de storage/processed si está disponible.
    if not output_path.exists():
        alt_path = Path('data/storage/processed')
        if alt_path.exists():
            output_path = alt_path

    # Verify directory exists
    if not output_path.exists():
        print(f"❌ Error: Directory does not exist: {output_dir}")
        return False

    if not output_path.is_dir():
        print(f"❌ Error: Path is not a directory: {output_dir}")
        return False

    # Leer index.json existente (si existe)
    index_file = output_path / 'index.json'
    existing_index = {}

    if index_file.exists():
        try:
            with open(index_file, 'r', encoding='utf-8') as f:
                existing_index = json.load(f)
        except Exception as e:
            print(f"⚠️  Warning: Could not read existing index.json: {e}")
            existing_index = {}
    elif Path('data/storage/index.json').exists():
        try:
            with open(Path('data/storage/index.json'), 'r', encoding='utf-8') as f:
                existing_index = json.load(f)
        except Exception:
            pass

    # Find all JSON files with -massive suffix (excluding index.json)
    massive_files = sorted(
        [p for p in output_path.glob('*-massive.json')],
        key=lambda p: p.stat().st_mtime,
        reverse=True  # Newest first
    )

    if not massive_files:
        print(f"⚠️  Warning: No massive JSON files found in {output_path}")
    else:
        print(f"✓ Found {len(massive_files)} massive file(s)")

    # Build massive index with file metadata
    massive_index = {
        'type': 'massive',
        'updated': datetime.now().isoformat() + 'Z',
        'count': len(massive_files),
        'files': []
    }

    for file_path in massive_files:
        stat = file_path.stat()
        posix_str = file_path.as_posix()
        data_marker = posix_str.find('data/')
        rel_web_path = posix_str[data_marker:] if data_marker != -1 else f"data/output/{file_path.name}"
        file_info = {
            'name': file_path.name,
            'size': stat.st_size,
            'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
            'path': rel_web_path
        }
        massive_index['files'].append(file_info)
        print(f"  • {file_path.name} ({stat.st_size:,} bytes, {file_info['modified']})")

    # Actualizar solo la sección massive, mantener postmortem intacta
    full_index = existing_index if isinstance(existing_index, dict) else {}
    full_index['massive'] = massive_index

    # Preservar sección postmortem si existe
    if 'postmortem' not in full_index and isinstance(existing_index, dict):
        full_index['postmortem'] = existing_index.get('postmortem', {
            'type': 'postmortem',
            'updated': None,
            'count': 0,
            'files': []
        })

    # Write index.json to scanned directory and mirror if canonical data/storage exists
    targets = [index_file]
    canonical_index = Path('data/storage/index.json')
    legacy_index = Path('data/output/index.json')
    if canonical_index.parent.exists() and canonical_index not in targets:
        targets.append(canonical_index)
    if legacy_index.parent.exists() and legacy_index not in targets:
        targets.append(legacy_index)

    success = True
    for target in targets:
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            with open(target, 'w', encoding='utf-8') as f:
                json.dump(full_index, f, indent=2, ensure_ascii=False)
            print(f"✅ Successfully written: {target}")
        except IOError as e:
            print(f"❌ Error writing {target}: {e}")
            success = False

    return success


if __name__ == '__main__':
    # Get directory from command line or use default
    if len(sys.argv) > 1:
        directory = sys.argv[1]
    else:
        directory = 'data/output'

    success = build_index(directory)
    sys.exit(0 if success else 1)
