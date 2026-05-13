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

# Fix Unicode encoding for Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def build_index(output_dir='data/output'):
    """
    Actualiza solo la sección 'massive' en index.json para Dashboard Hub.

    Mantiene la sección 'postmortem' sin cambios si existe.

    Args:
        output_dir: Directory path to scan for JSON files

    Returns:
        bool: True if successful, False otherwise
    """
    output_path = Path(output_dir)

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

    # Find all JSON files with -massive suffix (excluding index.json)
    massive_files = sorted(
        [p for p in output_path.glob('*-massive.json')],
        key=lambda p: p.stat().st_mtime,
        reverse=True  # Newest first
    )

    if not massive_files:
        print(f"⚠️  Warning: No massive JSON files found in {output_dir}")
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
        file_info = {
            'name': file_path.name,
            'size': stat.st_size,
            'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
            'path': f"data/output/{file_path.name}"
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

    # Write index.json
    try:
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(full_index, f, indent=2, ensure_ascii=False)
        print(f"\n✅ Successfully created: {index_file}")
        return True

    except IOError as e:
        print(f"❌ Error writing index.json: {e}")
        return False


if __name__ == '__main__':
    # Get directory from command line or use default
    if len(sys.argv) > 1:
        directory = sys.argv[1]
    else:
        directory = 'data/output'

    success = build_index(directory)
    sys.exit(0 if success else 1)
