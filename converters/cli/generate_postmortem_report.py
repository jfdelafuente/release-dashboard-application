#!/usr/bin/env python3
"""
Generador del informe PPT de Postmortem por Release.

Orquesta la carga de datos, el cálculo de KPIs, la construcción de las
gráficas y el ensamblado del .pptx — mismo patrón de "script fino +
librería reutilizable" que converters/cli/upload_csv.py.

Uso como CLI:
    python generate_postmortem_report.py <release_name> [-o OUTPUT_PATH]
    python generate_postmortem_report.py --all [--output-dir DIR]

Uso como librería:
    from converters.cli.generate_postmortem_report import generate_report
    result = generate_report("2026R7")
"""
import argparse
import contextlib
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from report_generator.data_loader import (
    load_postmortem_records,
    find_postmortem_file,
    list_available_release_names,
    ReleaseNotFoundError,
)
from report_generator.kpi_calculator import calculate_kpis
from report_generator.postmortem_charts import (
    build_evolution_chart,
    build_pap_evolution_chart,
    build_open_incidents_chart,
    build_system_chart,
)
from report_generator.release_kpis_data import load_release_kpis_context, DEFAULT_RELEASES_DATA_PATH
from report_generator.release_kpis_charts import (
    build_incidencias_por_release_chart,
    build_kpi_pap_chart,
    build_kpi_post_chart,
)
from report_generator.chart_utils import export_figure_to_png
from report_generator.pptx_builder import new_presentation, add_kpi_slide, add_chart_slides
from report_generator.paths import report_output_path


def _is_report_up_to_date(report_path, *source_paths):
    """True si `report_path` ya existe y es más reciente que todas sus
    fuentes (el JSON de postmortem de la release, releases-data.js) — en
    ese caso no hace falta regenerar el informe, basta con servir el que
    ya hay (evita 30-60s de renderizado de gráficas en el caso común: nadie
    ha vuelto a subir datos desde la última descarga)."""
    if not report_path.exists():
        return False
    report_mtime = report_path.stat().st_mtime
    for source_path in source_paths:
        if source_path and Path(source_path).exists() and Path(source_path).stat().st_mtime > report_mtime:
            return False
    return True


def _build_postmortem_chart_slides(records):
    """Construye las 4 gráficas propias del dashboard de postmortem como PNG.

    Devuelve una lista de (título, png_bytes) para pptx_builder.add_chart_slides.
    """
    evolution_fig, evolution_dates, evolution_backlog = build_evolution_chart(records)
    pap_fig = build_pap_evolution_chart(records)
    open_incidents_fig = build_open_incidents_chart(records, evolution_dates, evolution_backlog)
    system_fig = build_system_chart(records)

    return [
        ("Entradas, Resoluciones y Backlog", export_figure_to_png(evolution_fig)),
        ("Abiertas y Cerradas (solo PAP)", export_figure_to_png(pap_fig) if pap_fig else None),
        ("Incidencias No Cerradas y Backlog Acumulado", export_figure_to_png(open_incidents_fig)),
        ("Por Sistema", export_figure_to_png(system_fig)),
    ]


def _build_release_kpis_context_slides():
    """Construye las 3 gráficas generales de release-kpis (todas las releases).

    Devuelve [] si releases-data.js no está disponible o no tiene datos —
    el informe sigue generándose con la parte de postmortem (ver Edge Cases
    de spec.md: no fallar por completo si falta una sección).
    """
    try:
        releases = load_release_kpis_context()
    except (FileNotFoundError, ValueError):
        return []
    if not releases:
        return []

    return [
        ("Incidencias por Release (todas las releases)", export_figure_to_png(build_incidencias_por_release_chart(releases))),
        ("KPI % PaP (todas las releases)", export_figure_to_png(build_kpi_pap_chart(releases))),
        ("KPI % 1ª semana (todas las releases)", export_figure_to_png(build_kpi_post_chart(releases))),
    ]


@contextlib.contextmanager
def _maybe_chdir(project_root):
    """Cambia el directorio de trabajo mientras dura el bloque, si se indica.

    Todas las rutas de report_generator (data/output/, data/reports/,
    dashboards/release-kpis/) son relativas al repo release-dashboard-
    application. Cuando este módulo se invoca desde el mismo proceso que ya
    vive en ese repo (CLI, serve_app.py, que hace chdir al arrancar), no
    hace falta nada. Pero invocado desde OTRO proceso con otro cwd — el
    backend del repo hermano — hay que apuntar temporalmente al repo
    correcto sin dejar el proceso entero con el cwd cambiado (podría romper
    otras rutas relativas de ese proceso, p. ej. su base de datos sqlite).
    """
    if project_root is None:
        yield
        return
    previous_cwd = os.getcwd()
    os.chdir(project_root)
    try:
        yield
    finally:
        os.chdir(previous_cwd)


def generate_report(release_name, output_path=None, project_root=None):
    """Genera el informe .pptx de una release. Devuelve {"success": bool, ...}.

    Si ya existe un informe generado y es más reciente que sus fuentes de
    datos (ver _is_report_up_to_date), se devuelve tal cual sin
    regenerarlo — evita repetir el renderizado de las 7 gráficas cuando
    nadie ha vuelto a subir datos desde la última descarga.

    Misma forma de resultado que converters/cli/upload_csv.py. `project_root`
    es opcional y solo hace falta cuando se invoca desde un proceso con un
    directorio de trabajo distinto al de este repo (ver _maybe_chdir).
    """
    with _maybe_chdir(project_root):
        source_file = find_postmortem_file(release_name)
        if source_file is None:
            return {"success": False, "error": f"No hay datos de postmortem cargados para la release '{release_name}'"}

        final_path = Path(output_path) if output_path else report_output_path(release_name)
        if _is_report_up_to_date(final_path, source_file, DEFAULT_RELEASES_DATA_PATH):
            return {"success": True, "path": str(final_path.resolve())}

        try:
            records = load_postmortem_records(release_name)
        except ReleaseNotFoundError as e:
            return {"success": False, "error": str(e)}

        kpis = calculate_kpis(records)
        report_data = {**kpis, "release_name": release_name}

        prs = new_presentation(release_name)
        add_kpi_slide(prs, report_data)
        add_chart_slides(prs, _build_postmortem_chart_slides(records))
        add_chart_slides(prs, _build_release_kpis_context_slides())

        final_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            prs.save(str(final_path))
        except PermissionError:
            raise PermissionError(
                f"No se pudo guardar el informe de '{release_name}': el fichero anterior "
                f"({final_path.name}) está abierto en otro programa (p. ej. PowerPoint). "
                f"Cierra ese programa e inténtalo de nuevo."
            ) from None

        # Ruta absoluta: si se ha usado project_root, el chdir de _maybe_chdir
        # se revierte al salir de este bloque, y una ruta relativa dejaría de
        # ser válida para quien llamó desde fuera (ver el caso real: el
        # backend del repo hermano intentando leer el .pptx después).
        return {"success": True, "path": str(final_path.resolve())}


def generate_all_reports(output_dir=None, project_root=None):
    """Genera el informe de todas las releases con datos disponibles.

    No se detiene ante el fallo de una release (User Story 3). Devuelve
    {"generated": [...], "failed": [{"release_name": ..., "error": ...}]}.
    """
    with _maybe_chdir(project_root):
        generated, failed = [], []
        for release_name in list_available_release_names():
            output_path = report_output_path(release_name, output_dir) if output_dir else None
            try:
                result = generate_report(release_name, output_path)
            except Exception as e:  # una release con datos corruptos no debe abortar el lote
                failed.append({"release_name": release_name, "error": str(e)})
                continue

            if result["success"]:
                generated.append(release_name)
            else:
                failed.append({"release_name": release_name, "error": result["error"]})
        return {"generated": generated, "failed": failed}


def main():
    parser = argparse.ArgumentParser(
        description="Genera el informe .pptx de postmortem de una release",
    )
    parser.add_argument("release_name", nargs="?", help="Nombre de la release (omitir si se usa --all)")
    parser.add_argument("-o", "--output", default=None, help="Ruta de salida del .pptx")
    parser.add_argument("--all", action="store_true", help="Generar el informe de todas las releases disponibles")
    parser.add_argument("--output-dir", default=None, help="Directorio de salida en modo --all (default: data/reports/)")
    args = parser.parse_args()

    if args.all:
        result = generate_all_reports(args.output_dir)
        print(f"Generados: {len(result['generated'])} ({', '.join(result['generated']) or '-'})")
        if result["failed"]:
            print(f"Fallidos: {len(result['failed'])}")
            for failure in result["failed"]:
                print(f"  - {failure['release_name']}: {failure['error']}")
            return 1
        return 0

    if not args.release_name:
        parser.error("Falta release_name (o usa --all)")

    try:
        result = generate_report(args.release_name, args.output)
    except PermissionError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    if result["success"]:
        print(result["path"])
        return 0

    print(f"Error: {result['error']}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
