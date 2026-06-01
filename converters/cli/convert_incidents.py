#!/usr/bin/env python3
"""
Script de conversión CSV → JSON para Dashboard de Incidencias Masivas

Convierte archivos CSV de incidencias masivas al formato JSON compatible
con el Massive Incidents Dashboard con validación y normalización automática.

Uso:
    # Convertir archivo específico
    python convert_incidents.py data/input/datos.csv

    # Convertir y especificar salida
    python convert_incidents.py data/input/datos.csv -o data/output/incidents.json

    # Convertir con reporte de errores
    python convert_incidents.py data/input/datos.csv -e data/errors/errors.json

    # Convertir todos los CSV en un directorio
    python convert_incidents.py data/input/ -o data/output/

    # Ver help
    python convert_incidents.py --help
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime
import subprocess

# Add parent/src to path for csv_to_json module
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))
from csv_to_json import CsvToJsonConverter


# Configuración de rutas por defecto
DATA_ROOT = Path("data")
DEFAULT_OUTPUT_DIR = DATA_ROOT / "output"
DEFAULT_ERROR_DIR = DATA_ROOT / "errors"

# Backward compatibility fallback
if not DEFAULT_OUTPUT_DIR.exists():
    if Path("datos/json").exists():
        DEFAULT_OUTPUT_DIR = Path("datos/json")
        DEFAULT_ERROR_DIR = Path("datos/errors")


class Colors:
    """ANSI color codes para output en consola."""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_header(text):
    """Imprime un encabezado formateado."""
    print(f"\n{Colors.BOLD}{Colors.HEADER}{'='*70}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}{text:^70}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}{'='*70}{Colors.ENDC}\n")


def print_success(text):
    """Imprime mensaje de éxito."""
    print(f"{Colors.GREEN}[OK] {text}{Colors.ENDC}")


def print_error(text):
    """Imprime mensaje de error."""
    print(f"{Colors.RED}[ERROR] {text}{Colors.ENDC}")


def print_info(text):
    """Imprime mensaje informativo."""
    print(f"{Colors.CYAN}[INFO] {text}{Colors.ENDC}")


def print_warning(text):
    """Imprime mensaje de advertencia."""
    print(f"{Colors.YELLOW}[WARN] {text}{Colors.ENDC}")


def format_size(bytes):
    """Convierte bytes a formato legible."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes < 1024:
            return f"{bytes:.1f}{unit}"
        bytes /= 1024
    return f"{bytes:.1f}TB"


def get_csv_files(path):
    """Obtiene lista de archivos CSV del path (archivo o directorio)."""
    path = Path(path)

    if path.is_file():
        if path.suffix.lower() == '.csv':
            return [path]
        else:
            print_error(f"El archivo {path} no es un CSV")
            return []

    elif path.is_dir():
        csv_files = sorted(path.glob('*.csv'))
        if not csv_files:
            print_warning(f"No se encontraron archivos CSV en {path}")
        return csv_files

    else:
        print_error(f"Path no válido: {path}")
        return []


def convert_single_file(csv_file, output_path=None, error_path=None):
    """Convierte un archivo CSV individual."""
    print_info(f"Procesando: {csv_file.name}")
    print_info(f"Tamaño: {format_size(csv_file.stat().st_size)}")

    # Determinar rutas de salida
    if output_path is None:
        # Si no se especifica -o, usar data/output/ por defecto
        # Agregar sufijo -massive para identificar el tipo de datos
        output_filename = f"{csv_file.stem}-massive.json"
        if DEFAULT_OUTPUT_DIR.exists():
            output_path = DEFAULT_OUTPUT_DIR / output_filename
        else:
            output_path = csv_file.parent / output_filename
    else:
        output_path = Path(output_path)
        if output_path.is_dir():
            # Agregar sufijo -massive si se especifica solo directorio
            output_filename = f"{csv_file.stem}-massive.json"
            output_path = output_path / output_filename

    # Determinar ruta de errores
    if error_path is None:
        # Si no se especifica -e, usar DEFAULT_ERROR_DIR por defecto
        if DEFAULT_ERROR_DIR.exists():
            error_path = DEFAULT_ERROR_DIR / f"{csv_file.stem}_errors.json"
        else:
            error_path = output_path.parent / f"{output_path.stem}_errors.json"
    elif error_path and Path(error_path).is_dir():
        error_path = Path(error_path) / f"{csv_file.stem}_errors.json"

    # Crear directorios si es necesario
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if error_path:
        Path(error_path).parent.mkdir(parents=True, exist_ok=True)

    # Convertir
    try:
        converter = CsvToJsonConverter()
        success, report = converter.convert_file(
            str(csv_file),
            str(output_path),
            str(error_path) if error_path else None
        )

        # Mostrar resultados
        stats = report['stats']
        print(f"  {Colors.BLUE}Total registros:{Colors.ENDC} {stats['total_records']}")
        print(f"  {Colors.GREEN}Exitosos:{Colors.ENDC} {stats['successful']}")

        if stats['failed'] > 0:
            print(f"  {Colors.YELLOW}Fallidos:{Colors.ENDC} {stats['failed']}")

        print(f"  {Colors.CYAN}Tasa éxito:{Colors.ENDC} {stats['success_rate']:.1f}%")
        print(f"  {Colors.BLUE}Encoding:{Colors.ENDC} {report['encoding_detected']}")

        # Verificar archivos generados
        if output_path.exists():
            print_success(f"JSON guardado: {output_path}")
            print(f"           Tamaño: {format_size(output_path.stat().st_size)}")
        else:
            print_error(f"No se generó: {output_path}")

        if error_path and Path(error_path).exists():
            error_count = len(report['errors'])
            print_warning(f"Errores reportados: {error_path} ({error_count} registros)")

        return success

    except Exception as e:
        print_error(f"Error en conversión: {e}")
        return False


def show_error_summary(error_path):
    """Muestra resumen de errores."""
    try:
        with open(error_path, 'r', encoding='utf-8') as f:
            report = json.load(f)

        errors = report.get('errors', [])
        if not errors:
            print_success("No hay errores reportados")
            return

        print(f"\n{Colors.BOLD}Primeros 5 errores encontrados:{Colors.ENDC}\n")

        for i, error in enumerate(errors[:5], 1):
            row = error.get('row')
            fields = error.get('fields', {})

            print(f"{Colors.YELLOW}Error {i} (Fila {row}):{Colors.ENDC}")
            for field_name, field_info in fields.items():
                original = field_info.get('original', '')
                error_msg = field_info.get('error', '')
                print(f"  • {field_name}:")
                print(f"    Valor: {original}")
                print(f"    Razón: {error_msg}\n")

        if len(errors) > 5:
            print(f"... y {len(errors) - 5} errores más en {error_path}")

    except Exception as e:
        print_error(f"No se pudo leer reporte de errores: {e}")


def main():
    """Función principal."""
    parser = argparse.ArgumentParser(
        description='Convierte CSV de incidencias masivas a JSON para Dashboard',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  # Convertir archivo específico
  python convert_incidents.py data/input/datos.csv

  # Convertir y especificar directorio de salida
  python convert_incidents.py data/input/datos.csv -o data/output/

  # Convertir todos los CSV en un directorio
  python convert_incidents.py data/input/

  # Ver resumen de errores
  python convert_incidents.py data/input/datos.csv --show-errors
        """
    )

    parser.add_argument(
        'input',
        help='Archivo CSV o directorio con archivos CSV'
    )

    parser.add_argument(
        '-o', '--output',
        help='Archivo o directorio de salida JSON (default: data/output/)',
        default=None
    )

    parser.add_argument(
        '-e', '--errors',
        help='Archivo o directorio para reporte de errores (default: data/errors/)',
        default=None
    )

    parser.add_argument(
        '--show-errors',
        action='store_true',
        help='Mostrar resumen de errores después de la conversión'
    )

    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Output más detallado'
    )

    args = parser.parse_args()

    # Banner
    print_header("Dashboard Incidents CSV to JSON Converter")

    # Validar input
    input_path = Path(args.input)
    if not input_path.exists():
        print_error(f"Path no encontrado: {args.input}")
        return 1

    # Obtener archivos CSV
    csv_files = get_csv_files(input_path)
    if not csv_files:
        return 1

    print_info(f"Encontrados {len(csv_files)} archivo(s) CSV para procesar\n")

    # Procesar cada archivo
    total_success = True
    error_paths = []

    for i, csv_file in enumerate(csv_files, 1):
        print(f"{Colors.BOLD}[{i}/{len(csv_files)}]{Colors.ENDC}")

        success = convert_single_file(
            csv_file,
            args.output,
            args.errors
        )

        if not success:
            total_success = False

        # Guardar ruta de errores para mostrar después
        if args.errors:
            error_path = Path(args.errors)
            if error_path.is_dir():
                error_paths.append(error_path / f"{csv_file.stem}_errors.json")
            else:
                error_paths.append(error_path)
        else:
            if args.output and Path(args.output).is_dir():
                error_paths.append(Path(args.output) / f"{csv_file.stem}_errors.json")
            else:
                error_paths.append(csv_file.with_name(f"{csv_file.stem}_errors.json"))

        if i < len(csv_files):
            print()

    # Mostrar resumen final
    print_header("Resumen de Conversión")

    if total_success:
        print_success(f"Conversión completada sin errores fatales")
    else:
        print_warning(f"Conversión completada con algunos registros inválidos")

    # Mostrar errores si está solicitado
    if args.show_errors:
        for error_path in error_paths:
            if Path(error_path).exists():
                print(f"\n{Colors.BOLD}Archivo: {error_path.name}{Colors.ENDC}")
                show_error_summary(error_path)

    # Build index.json for Dashboard Hub
    print()
    print_info("Generando index.json para Dashboard Hub...")
    try:
        # Call build_index as subprocess
        cli_path = Path(__file__).parent / 'build_index.py'
        result = subprocess.run(
            [sys.executable, str(cli_path), str(DEFAULT_OUTPUT_DIR)],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print_success(f"Index actualizado: {DEFAULT_OUTPUT_DIR / 'index.json'}")
            if result.stdout:
                for line in result.stdout.strip().split('\n'):
                    print(f"  {line}")
        else:
            print_warning("No se pudo generar index.json")
            if result.stderr:
                print_warning(f"Error: {result.stderr}")
    except Exception as e:
        print_warning(f"Error al generar index.json: {e}")

    print()
    print_info("Para más información, consulta: specs/001-csv-to-json-workflow/quickstart.md")
    print()

    return 0 if total_success else 1


if __name__ == '__main__':
    sys.exit(main())
