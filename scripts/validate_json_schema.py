#!/usr/bin/env python3
"""
Validador de esquema JSON para index.json
Verifica que el archivo index.json tiene la estructura esperada para el Dashboard Hub
"""

import json
import sys
from pathlib import Path


def validate_index_json(filepath):
    """
    Valida la estructura del archivo index.json

    Estructura esperada:
    {
        "postmortem": {
            "type": "postmortem",
            "updated": "ISO timestamp",
            "count": number,
            "files": [
                {
                    "name": "string",
                    "size": number,
                    "modified": "ISO timestamp",
                    "path": "string"
                }
            ]
        },
        "massive": {
            "type": "massive",
            "updated": "ISO timestamp",
            "count": number,
            "files": [
                {
                    "name": "string",
                    "size": number,
                    "modified": "ISO timestamp",
                    "path": "string"
                }
            ]
        }
    }
    """

    filepath = Path(filepath)

    # Verificar que el archivo existe
    if not filepath.exists():
        print(f"❌ ERROR: Archivo no encontrado: {filepath}")
        return False

    # Cargar JSON
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ ERROR: JSON inválido: {e}")
        return False
    except Exception as e:
        print(f"❌ ERROR: No se pudo leer el archivo: {e}")
        return False

    # Validar estructura
    errors = []

    # Validar que los tipos principales existen
    for dataset_type in ['massive', 'postmortem']:
        if dataset_type not in data:
            errors.append(f"Falta sección '{dataset_type}'")
            continue

        dataset = data[dataset_type]

        # Validar estructura del dataset
        required_fields = ['type', 'updated', 'count', 'files']
        for field in required_fields:
            if field not in dataset:
                errors.append(f"{dataset_type}.{field} está faltando")

        # Validar tipo
        if dataset.get('type') != dataset_type:
            errors.append(f"{dataset_type}.type debe ser '{dataset_type}'")

        # Validar que count coincide con length de files
        files = dataset.get('files', [])
        count = dataset.get('count', 0)
        if len(files) != count:
            errors.append(f"{dataset_type}: count ({count}) no coincide con files ({len(files)})")

        # Validar estructura de cada archivo
        for idx, file_obj in enumerate(files):
            file_required = ['name', 'size', 'modified', 'path']
            for field in file_required:
                if field not in file_obj:
                    errors.append(f"{dataset_type}.files[{idx}].{field} está faltando")

    # Reportar resultados
    if errors:
        print(f"❌ Validación FALLIDA - {len(errors)} error(es) encontrado(s):")
        for error in errors:
            print(f"   - {error}")
        return False
    else:
        # Contar archivos
        massive_count = len(data.get('massive', {}).get('files', []))
        postmortem_count = len(data.get('postmortem', {}).get('files', []))

        print(f"✅ Validación EXITOSA")
        print(f"   - Archivos 'massive': {massive_count}")
        print(f"   - Archivos 'postmortem': {postmortem_count}")
        return True


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Uso: validate_json_schema.py <path_to_index.json>")
        print()
        print("Valida que index.json tiene la estructura correcta para Dashboard Hub")
        sys.exit(1)

    filepath = sys.argv[1]
    success = validate_index_json(filepath)
    sys.exit(0 if success else 1)
