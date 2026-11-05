"""
Interfaz de línea de comandos (CLI) para el Generador de Informes Ejecutivos de Incidencias.
"""

import argparse
import os
import sys
import warnings

try:
    from requests.exceptions import RequestsDependencyWarning
    warnings.filterwarnings("ignore", category=RequestsDependencyWarning)
except ImportError:
    pass

from incident_report.config import _load_env_files, resolve_template_path
from incident_report.domain.validators import apply_pending_placeholders
from incident_report.services.pipeline import ReportPipeline

_load_env_files()

DEFAULT_TEMPLATE = resolve_template_path()
DEFAULT_PPTX_OUTPUT = os.path.join("reports", "informe_ejecutivo.pptx")
DEFAULT_MD_OUTPUT = os.path.join("reports", "informe_incidencia.md")


def parse_args(args=None):
    parser = argparse.ArgumentParser(
        description="Generador de Informes Ejecutivos de Incidencias (Markdown Etapa 1 y PowerPoint Etapa 2)."
    )

    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        "--url",
        type=str,
        help="URL de Confluence del postmortem de la incidencia.",
    )
    input_group.add_argument(
        "--file",
        type=str,
        help="Ruta a un archivo local (HTML o texto exportado) del postmortem.",
    )
    input_group.add_argument(
        "--from-md",
        type=str,
        dest="from_md",
        help="Generar el PowerPoint directamente a partir de un archivo Markdown previamente validado.",
    )

    parser.add_argument(
        "--output",
        type=str,
        default=DEFAULT_PPTX_OUTPUT,
        help=f"Ruta de salida del archivo PowerPoint (.pptx). Por defecto: '{DEFAULT_PPTX_OUTPUT}'.",
    )
    parser.add_argument(
        "--md-output",
        type=str,
        dest="md_output",
        default=None,
        help="Ruta de salida del archivo Markdown intermedio. Por defecto: en 'reports/' derivado del ID.",
    )
    parser.add_argument(
        "--only-md",
        action="store_true",
        dest="only_md",
        help="Detenerse tras generar el archivo Markdown estructurado para revisión y edición manual.",
    )
    parser.add_argument(
        "--use-llm",
        action="store_true",
        dest="use_llm",
        help="Activar opcionalmente asistencia de modelo de lenguaje (LLM) para extracción desestructurada.",
    )
    parser.add_argument(
        "--no-verify-ssl",
        "--insecure",
        action="store_true",
        dest="no_verify_ssl",
        help="Desactivar la verificación de certificados SSL (útil en redes corporativas con inspección SSL/proxy).",
    )
    parser.add_argument(
        "--template",
        type=str,
        default=DEFAULT_TEMPLATE,
        help="Ruta o alias de la plantilla PowerPoint (ej. 'default' o ruta a .pptx).",
    )

    return parser.parse_args(args)


def main(argv=None):
    args = parse_args(argv)
    pipeline = ReportPipeline(
        use_llm=args.use_llm,
        verify_ssl=False if args.no_verify_ssl else None,
        template_path=args.template,
    )

    # Modo 1: Generar directamente desde Markdown revisado (Etapa 2)
    if args.from_md:
        if not os.path.exists(args.from_md):
            sys.stderr.write(f"Error: El archivo Markdown especificado no existe: {args.from_md}\n")
            sys.exit(1)

        try:
            report = pipeline.load_from_markdown(args.from_md)
        except Exception as e:
            sys.stderr.write(f"Error al leer el archivo Markdown ({args.from_md}): {e}\n")
            sys.exit(1)

        errors = report.validate()
        if errors:
            sys.stderr.write(
                f"Error de validación en Markdown: Faltan campos obligatorios: {', '.join(errors)}\n"
            )
            sys.exit(1)

        try:
            pipeline.render_pptx(report, args.output)
            print(f"Informe ejecutivo en PowerPoint generado con éxito desde Markdown: {args.output}")
            sys.exit(0)
        except Exception as e:
            sys.stderr.write(f"Error al generar la presentación PowerPoint: {e}\n")
            sys.exit(1)

    # Modo 2: Ingesta desde URL o archivo local (Etapa 1 -> Etapa 2)
    html_content = ""
    if args.url:
        try:
            print(f"Obteniendo postmortem desde Confluence: {args.url} ...")
            html_content = pipeline.fetch_html_from_url(args.url)
        except Exception as e:
            sys.stderr.write(f"Error: {e}\n")
            sys.exit(1)
    elif args.file:
        if not os.path.exists(args.file):
            sys.stderr.write(f"Error: El archivo local no existe: {args.file}\n")
            sys.exit(1)
        try:
            html_content = pipeline.read_local_file(args.file)
        except Exception as e:
            sys.stderr.write(f"Error al leer el archivo local ({args.file}): {e}\n")
            sys.exit(1)

    print("Extrayendo información estructurada del postmortem...")
    report = pipeline.extract_report(html_content)

    errors = report.validate()
    if errors:
        if args.only_md:
            print(
                f"[Aviso] La fuente de datos no contiene algunos campos obligatorios: {', '.join(errors)}"
            )
            print(
                "[Aviso] Se generará el borrador Markdown con marcadores para que pueda completarlos manualmente."
            )
            apply_pending_placeholders(report)
        else:
            sys.stderr.write(
                f"Error: La fuente de datos no contiene los campos obligatorios requeridos: {', '.join(errors)}\n"
            )
            sys.exit(1)

    if args.md_output:
        md_path = args.md_output
    elif report.incident_id:
        clean_id = "".join(c for c in report.incident_id if c.isalnum() or c in "-_")
        md_path = os.path.join("reports", f"informe_{clean_id}.md")
    else:
        md_path = DEFAULT_MD_OUTPUT

    try:
        pipeline.save_markdown(report, md_path)
        print(f"[Etapa 1/2] Archivo Markdown estructurado generado: {md_path}")
    except Exception as e:
        sys.stderr.write(f"Error al guardar el archivo Markdown ({md_path}): {e}\n")
        sys.exit(1)

    if args.only_md:
        print("\nEjecución detenida (--only-md activado).")
        print(f"Puede revisar y ajustar el contenido en: {md_path}")
        print("Para generar la presentación final tras su revisión, ejecute:")
        print(f"  python generate_report.py --from-md {md_path} --output {args.output}")
        sys.exit(0)

    try:
        pipeline.render_pptx(report, args.output)
        print(f"[Etapa 2/2] Informe ejecutivo en PowerPoint generado con éxito: {args.output}")
    except Exception as e:
        sys.stderr.write(f"Error al generar la presentación PowerPoint: {e}\n")
        sys.exit(1)

