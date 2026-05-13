#!/usr/bin/env python3
"""
Convierte archivos CSV a JSON.
"""

import csv
import json
import sys
import argparse
from pathlib import Path


def detect_delimiter(csv_file, encoding='utf-8'):
    """
    Detecta automáticamente el delimitador del CSV.
    """
    with open(csv_file, 'r', encoding=encoding) as f:
        first_line = f.readline()

    if ';' in first_line:
        return ';'
    elif '\t' in first_line:
        return '\t'
    else:
        return ','


def csv_to_json(csv_file, json_file=None, encoding='utf-8', delimiter=None):
    """
    Convierte un archivo CSV a JSON.

    Args:
        csv_file: Ruta del archivo CSV
        json_file: Ruta del archivo JSON de salida (opcional)
        encoding: Codificación del archivo CSV
        delimiter: Delimitador del CSV (auto-detectado si no se especifica)

    Returns:
        Lista de diccionarios con los datos del CSV
    """
    data = []

    try:
        if not delimiter:
            delimiter = detect_delimiter(csv_file, encoding)

        with open(csv_file, 'r', encoding=encoding) as f:
            csv_reader = csv.DictReader(f, delimiter=delimiter)
            for row in csv_reader:
                data.append(row)

        if json_file:
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"[OK] Convertido: {csv_file} -> {json_file}")
        else:
            print(json.dumps(data, ensure_ascii=False, indent=2))

        return data

    except FileNotFoundError:
        print(f"Error: No se encontró el archivo {csv_file}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error al procesar {csv_file}: {e}", file=sys.stderr)
        sys.exit(1)


def convert_directory(directory, output_dir=None, encoding='utf-8', delimiter=None):
    """
    Convierte todos los archivos CSV en un directorio a JSON.

    Args:
        directory: Directorio con archivos CSV
        output_dir: Directorio de salida (por defecto, el mismo directorio)
        encoding: Codificación de los archivos CSV
        delimiter: Delimitador del CSV (auto-detectado si no se especifica)
    """
    csv_files = Path(directory).glob('*.csv')
    count = 0

    for csv_file in csv_files:
        output_dir_path = Path(output_dir) if output_dir else csv_file.parent
        json_file = output_dir_path / (csv_file.stem + '.json')
        csv_to_json(str(csv_file), str(json_file), encoding, delimiter)
        count += 1

    if count == 0:
        print(f"No se encontraron archivos CSV en {directory}")
    else:
        print(f"\n[OK] Se convirtieron {count} archivos")


def main():
    parser = argparse.ArgumentParser(
        description='Convierte archivos CSV a JSON'
    )
    parser.add_argument(
        'input',
        help='Archivo CSV o directorio con archivos CSV'
    )
    parser.add_argument(
        '-o', '--output',
        help='Archivo o directorio de salida JSON'
    )
    parser.add_argument(
        '-e', '--encoding',
        default='utf-8',
        help='Codificación del archivo CSV (por defecto: utf-8)'
    )
    parser.add_argument(
        '-d', '--delimiter',
        default=None,
        help='Delimitador del CSV (por defecto: auto-detectado)'
    )

    args = parser.parse_args()
    input_path = Path(args.input)

    if input_path.is_file():
        # Convertir un archivo CSV
        output_file = args.output or input_path.stem + '.json'
        csv_to_json(str(input_path), output_file, args.encoding, args.delimiter)

    elif input_path.is_dir():
        # Convertir todos los CSV en un directorio
        convert_directory(str(input_path), args.output, args.encoding, args.delimiter)

    else:
        print(f"Error: {args.input} no existe", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
