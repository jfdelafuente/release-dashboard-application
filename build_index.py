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
    Build index.json listing all JSON files in output_dir.

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

    # Find all JSON files (excluding index.json itself)
    json_files = sorted(
        [p for p in output_path.glob('*.json') if p.name != 'index.json'],
        key=lambda p: p.stat().st_mtime,
        reverse=True  # Newest first
    )

    if not json_files:
        print(f"⚠️  Warning: No JSON files found in {output_dir}")
        # Still create empty index
        index = []
    else:
        print(f"✓ Found {len(json_files)} JSON file(s)")

    # Build index with file metadata
    index = []
    for file_path in json_files:
        stat = file_path.stat()
        file_info = {
            'name': file_path.name,
            'size': stat.st_size,
            'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
        }
        index.append(file_info)
        print(f"  • {file_path.name} ({stat.st_size:,} bytes, {file_info['modified']})")

    # Write index.json
    index_file = output_path / 'index.json'
    try:
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(index, f, indent=2, ensure_ascii=False)
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
