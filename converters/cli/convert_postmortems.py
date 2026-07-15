#!/usr/bin/env python3
"""
Postmortem CSV to JSON Converter CLI.

Convierte archivos CSV de postmortem al formato JSON compatible con
Postmortem Dashboard y Dashboard Hub con validación y normalización automática.

Features:
- Detección automática de encoding y delimitador
- Normalización de nombres de campos y tipos de datos
- Cálculo de KPIs incluidos en metadatos
- Output con sufijo -postmortem para auto-descubrimiento en Dashboard Hub
- Generación de reportes de errores detallados
- Soporte para procesamiento batch de múltiples archivos
- Auto-actualización de index.json para Dashboard Hub

Uso:
    # Convertir archivo específico
    python convert_postmortems.py data/input/postmortem.csv

    # Convertir con output explícito
    python convert_postmortems.py data/input/postmortem.csv -o custom-output.json

    # Batch mode (procesa todos los CSV en directorio)
    python convert_postmortems.py data/input/ -b

    # Con reporte de errores
    python convert_postmortems.py data/input/postmortem.csv -e report.json

    # Ver help
    python convert_postmortems.py --help
"""

import argparse
import sys
import json
from pathlib import Path
from datetime import datetime
import subprocess

# Add parent/src to path for csv_to_json module
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))
from csv_to_json.postmortem_converter import PostmortemConverter


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
    """Códigos de color ANSI para output en consola."""
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


def get_output_path(input_path: Path, output_dir: Path = None) -> Path:
    """
    Genera ruta de output con sufijo -postmortem.

    Args:
        input_path: Ruta del archivo CSV de entrada
        output_dir: Directorio de salida (por defecto data/output/)

    Returns:
        Ruta del archivo JSON de salida con sufijo -postmortem
    """
    if output_dir is None:
        output_dir = DEFAULT_OUTPUT_DIR

    output_dir.mkdir(parents=True, exist_ok=True)

    # Extraer nombre base sin extensión
    base_name = input_path.stem

    # Agregar sufijo -postmortem
    output_filename = f"{base_name}-postmortem.json"
    return output_dir / output_filename


def get_error_report_path(output_path: Path, error_dir: Path = None) -> Path:
    """
    Genera ruta de reporte de errores basada en el nombre del output.

    Args:
        output_path: Ruta del archivo JSON de salida
        error_dir: Directorio de errores (por defecto data/errors/)

    Returns:
        Ruta del archivo de reporte de errores
    """
    if error_dir is None:
        error_dir = DEFAULT_ERROR_DIR

    error_dir.mkdir(parents=True, exist_ok=True)

    # Usar mismo nombre base que output con sufijo _errors
    error_filename = f"{output_path.stem}_errors.json"
    return error_dir / error_filename


def show_error_summary(error_path):
    """Muestra resumen de errores."""
    try:
        with open(error_path, 'r', encoding='utf-8') as f:
            report = json.load(f)

        summary = report.get('summary', {})
        if summary.get('failed', 0) == 0:
            print_success("No hay errores reportados")
            return

        print(f"\n{Colors.BOLD}Resumen de Errores:{Colors.ENDC}")
        print(f"  Total: {summary.get('total_records', 0)}")
        print(f"  Exitosos: {summary.get('successful', 0)}")
        print(f"  Fallidos: {summary.get('failed', 0)}")
        print(f"  Tasa: {summary.get('success_rate', 0):.1f}%")

        errors = report.get('errors', [])
        if errors and len(errors) <= 5:
            print(f"\n{Colors.BOLD}Errores encontrados:{Colors.ENDC}\n")
            for i, error in enumerate(errors, 1):
                row = error.get('row')
                record_id = error.get('record_id', 'N/A')
                issues = error.get('issues', [])
                print(f"{Colors.YELLOW}Error {i} (Fila {row}, ID: {record_id}):{Colors.ENDC}")
                for issue in issues:
                    print(f"  • {issue}")
                print()
        elif len(errors) > 5:
            print(f"\n{Colors.BOLD}Primeros 5 errores:{Colors.ENDC}\n")
            for i, error in enumerate(errors[:5], 1):
                row = error.get('row')
                record_id = error.get('record_id', 'N/A')
                print(f"{Colors.YELLOW}Error {i} (Fila {row}, ID: {record_id}){Colors.ENDC}")
            print(f"... y {len(errors) - 5} errores más")

    except Exception as e:
        print_warning(f"No se pudo leer reporte de errores: {e}")


def convert_single_file(csv_file, output_path=None, error_path=None, release_name=None):
    """Convierte un archivo CSV individual."""
    print_info(f"Procesando: {csv_file.name}")
    print_info(f"Tamaño: {format_size(csv_file.stat().st_size)}")

    # Determinar rutas de salida
    if output_path is None:
        # Si no se especifica -o, usar DEFAULT_OUTPUT_DIR por defecto
        output_filename = f"{csv_file.stem}-postmortem.json"
        output_path = DEFAULT_OUTPUT_DIR / output_filename
    else:
        output_path = Path(output_path)
        if output_path.is_dir():
            # Agregar sufijo -postmortem si se especifica solo directorio
            output_filename = f"{csv_file.stem}-postmortem.json"
            output_path = output_path / output_filename

    # Determinar ruta de errores
    if error_path is None:
        # Si no se especifica -e, usar DEFAULT_ERROR_DIR por defecto
        error_path = DEFAULT_ERROR_DIR / f"{csv_file.stem}-postmortem_errors.json"
    elif error_path and Path(error_path).is_dir():
        error_path = Path(error_path) / f"{csv_file.stem}-postmortem_errors.json"

    # Crear directorios si es necesario
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if error_path:
        Path(error_path).parent.mkdir(parents=True, exist_ok=True)

    # Convertir
    try:
        converter = PostmortemConverter()
        success, report = converter.convert_file(
            str(csv_file),
            str(output_path),
            str(error_path) if error_path else None,
            release_name=release_name
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
            print(f"         Tamaño: {format_size(output_path.stat().st_size)}")
        else:
            print_error(f"No se generó: {output_path}")
            return False

        if error_path and Path(error_path).exists():
            error_count = stats['failed']
            print_warning(f"Errores reportados: {error_path} ({error_count} registros)")

        return success

    except Exception as e:
        print_error(f"Error en conversión: {e}")
        return False


def build_index_for_hub(output_dir=None):
    """
    Actualiza solo la sección 'postmortem' en index.json para Dashboard Hub.

    Mantiene la sección 'massive' sin cambios si existe.

    Args:
        output_dir: Directorio a indexar (por defecto data/output/)

    Returns:
        bool: True si éxito, False si fallo
    """
    if output_dir is None:
        output_dir = DEFAULT_OUTPUT_DIR

    output_path = Path(output_dir)

    # Verificar directorio
    if not output_path.exists():
        print_warning(f"Directorio no existe: {output_dir}")
        return False

    if not output_path.is_dir():
        print_warning(f"Path no es un directorio: {output_dir}")
        return False

    # Leer index.json existente (si existe)
    index_file = output_path / 'index.json'
    existing_index = {}

    if index_file.exists():
        try:
            with open(index_file, 'r', encoding='utf-8') as f:
                existing_index = json.load(f)
        except Exception as e:
            print_warning(f"No se pudo leer index.json existente: {e}")
            existing_index = {}

    # Buscar todos los JSONs con sufijo -postmortem
    postmortem_files = sorted(
        [p for p in output_path.glob('*-postmortem.json')],
        key=lambda p: p.stat().st_mtime,
        reverse=True  # Más recientes primero
    )

    if postmortem_files:
        print_info(f"Encontrados {len(postmortem_files)} archivo(s) postmortem")
    else:
        print_warning(f"No se encontraron archivos postmortem en {output_dir}")

    # Construir índice postmortem
    postmortem_index = {
        'type': 'postmortem',
        'updated': datetime.now().isoformat() + 'Z',
        'count': len(postmortem_files),
        'files': []
    }

    for file_path in postmortem_files:
        stat = file_path.stat()

        # Leer release_name de _metadata (ausente/None para archivos generados
        # antes de esta feature — ver specs/007-per-release-dashboards)
        release_name = None
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                file_content = json.load(f)
            release_name = file_content.get('_metadata', {}).get('release_name')
        except (json.JSONDecodeError, IOError, OSError):
            pass

        file_info = {
            'name': file_path.name,
            'size': stat.st_size,
            'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
            'path': f"data/output/{file_path.name}",
            'release_name': release_name
        }
        postmortem_index['files'].append(file_info)
        print(f"  • {file_path.name} ({format_size(stat.st_size)})")

    # Actualizar solo la sección postmortem, mantener massive intacta
    full_index = existing_index if isinstance(existing_index, dict) else {}
    full_index['postmortem'] = postmortem_index

    # Preservar sección massive si existe
    if 'massive' not in full_index and isinstance(existing_index, dict):
        full_index['massive'] = existing_index.get('massive', {
            'type': 'massive',
            'updated': None,
            'count': 0,
            'files': []
        })

    # Escribir index.json actualizado
    try:
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(full_index, f, indent=2, ensure_ascii=False)
        print_success(f"Index actualizado: {index_file}")
        return True

    except IOError as e:
        print_error(f"Error escribiendo index.json: {e}")
        return False


def main():
    """Función principal."""
    parser = argparse.ArgumentParser(
        description='Convierte CSV de postmortem a JSON para Dashboard Postmortem',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  # Convertir archivo específico
  python convert_postmortems.py data/input/postmortem.csv

  # Batch mode (convierte todos los CSV en directorio)
  python convert_postmortems.py data/input/ -b

  # Convertir con directorio de salida personalizado
  python convert_postmortems.py data/input/postmortem.csv -o data/output/

  # Batch con directorios personalizados
  python convert_postmortems.py data/input/ -b -o data/output/ -e data/errors/

  # Ver resumen de errores
  python convert_postmortems.py data/input/postmortem.csv --show-errors
        """
    )

    parser.add_argument(
        'input',
        help='Archivo CSV o directorio con archivos CSV'
    )

    parser.add_argument(
        '-b', '--batch',
        action='store_true',
        help='Batch mode: procesa todos los CSV en directorio de entrada'
    )

    parser.add_argument(
        '-o', '--output',
        help='Directorio o archivo de salida JSON (default: data/output/)',
        default=None
    )

    parser.add_argument(
        '-e', '--errors',
        help='Directorio o archivo para reporte de errores (default: data/errors/)',
        default=None
    )

    parser.add_argument(
        '--show-errors',
        action='store_true',
        help='Mostrar resumen de errores después de la conversión'
    )

    parser.add_argument(
        '--release-name',
        help='Nombre de la release a asociar a los datos convertidos (se guarda en _metadata.release_name)',
        default=None
    )

    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Output más detallado'
    )

    args = parser.parse_args()

    # Banner
    print_header("Postmortem Converter - CSV to JSON")

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

        # Determinar rutas de salida y error
        if args.batch or len(csv_files) > 1:
            output_dir = Path(args.output) if args.output else DEFAULT_OUTPUT_DIR
            error_dir = Path(args.errors) if args.errors else DEFAULT_ERROR_DIR
            output_path = get_output_path(csv_file, output_dir)
            error_path = get_error_report_path(output_path, error_dir)
        else:
            output_path = Path(args.output) if args.output else None
            error_path = Path(args.errors) if args.errors else None

        success = convert_single_file(csv_file, output_path, error_path, release_name=args.release_name)

        if not success:
            total_success = False

        # Guardar ruta de errores para mostrar después
        if error_path:
            error_paths.append(error_path)

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
        if build_index_for_hub(str(DEFAULT_OUTPUT_DIR)):
            print_success(f"Index actualizado para Dashboard Hub")
        else:
            print_warning("No se pudo generar index.json")
    except Exception as e:
        print_warning(f"Error al generar index.json: {e}")

    print()
    print_info("Para más información, consulta: POSTMORTEM_CONVERTER.md")
    print()

    return 0 if total_success else 1


if __name__ == "__main__":
    main()
