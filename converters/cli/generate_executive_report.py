"""
CLI para generar informes ejecutivos PowerPoint a partir de incidencias y postmortems.
Feature 010: 010-incident-executive-report

Uso:
    python converters/cli/generate_executive_report.py --ref 2606S77393 --title "Problema IVR"
    python converters/cli/generate_executive_report.py --ref 2606S77393 --file postmortem.html
    python converters/cli/generate_executive_report.py --ref 2606S77393 --url "https://confluence.si.orange.es/..."
"""

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from converters.src.report_generator.executive_models import (
    ExecutiveIncidentData,
    sanitize_incident_ref,
)
from converters.src.report_generator.executive_paths import (
    get_executive_report_path,
    get_executive_template_path,
)
from converters.src.report_generator.executive_report_builder import ExecutiveReportBuilder
from converters.src.report_generator.confluence_parser import ConfluenceParser


def main():
    parser = argparse.ArgumentParser(
        description="Generador de Informes Ejecutivos de Incidencias PowerPoint (Orange)."
    )
    parser.add_argument(
        "--ref",
        required=True,
        help="Código o identificador de la incidencia (ej: 2606S77393)",
    )
    parser.add_argument(
        "--title",
        default="",
        help="Título o resumen breve de la incidencia",
    )
    parser.add_argument(
        "--url",
        default="",
        help="URL de la página de Confluence del postmortem",
    )
    parser.add_argument(
        "--file",
        default="",
        help="Ruta a un archivo local HTML o de texto con el contenido del postmortem",
    )
    parser.add_argument(
        "--output",
        default="",
        help="Ruta de salida del archivo .pptx (por defecto: data/reports/executive/RESUMEN_EJECUTIVO_{ref}.pptx)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Sobrescribir el informe si ya existe",
    )

    args = parser.parse_args()

    clean_ref = sanitize_incident_ref(args.ref)
    out_path = Path(args.output) if args.output else get_executive_report_path(clean_ref)

    if out_path.exists() and not args.force:
        print(f"[INFO] El informe para {clean_ref} ya existe en: {out_path}")
        print("Use --force para regenerarlo.")
        sys.exit(0)

    # Cargar contenido si se provee archivo
    raw_content = ""
    if args.file:
        file_path = Path(args.file)
        if not file_path.is_file():
            print(f"[ERROR] Archivo no encontrado: {file_path}", file=sys.stderr)
            sys.exit(1)
        raw_content = file_path.read_text(encoding="utf-8", errors="ignore")

    # Parsear o construir datos
    if raw_content:
        c_parser = ConfluenceParser()
        incident_data = c_parser.parse(raw_content, fallback_ref=clean_ref, source_url=args.url)
        if args.title:
            incident_data.title = args.title
    else:
        incident_data = ExecutiveIncidentData(
            incident_ref=clean_ref,
            title=args.title or f"Incidencia {clean_ref}",
            source_url=args.url,
        )

    print(f"[PROCESANDO] Generando informe para {incident_data.incident_ref} - {incident_data.title}...")
    builder = ExecutiveReportBuilder()
    metadata = builder.generate(incident_data, out_path)

    print(f"[OK] Informe generado exitosamente:")
    print(f"  - Archivo: {metadata.file_path}")
    print(f"  - Tamaño: {metadata.size_bytes / 1024:.1f} KB")
    print(f"  - Diapositivas: {metadata.slide_count}")
    print(f"  - Fecha: {metadata.generated_at}")


if __name__ == "__main__":
    main()

