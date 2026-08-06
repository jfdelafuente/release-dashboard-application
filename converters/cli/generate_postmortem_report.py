#!/usr/bin/env python3
"""
Generador del informe PPT de Postmortem por Release.

Orquesta la carga de datos, el cálculo de KPIs, la construcción de las
gráficas y el ensamblado del .pptx — mismo patrón de "script fino +
librería reutilizable" que converters/cli/upload_csv.py.

Todos los KPIs y gráficas del informe se calculan a partir de
dashboards/release-kpis/releases-data.js (única fuente de datos); el JSON
de postmortem por release ya no se usa aquí.

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

from report_generator.release_kpis_data import (
    load_release_kpis_context,
    find_release,
    DEFAULT_RELEASES_DATA_PATH,
)
from report_generator.release_kpis_charts import (
    build_incidencias_por_release_chart,
    build_kpi_pap_chart,
    build_kpi_post_chart,
)
from report_generator.chart_utils import export_figure_to_png, KPI_TARGET_PCT
from report_generator.pptx_builder import new_presentation, add_kpi_and_chart_slide, add_dual_chart_slide
from report_generator.paths import report_output_path

# Nº de releases más recientes que muestran las gráficas del informe (eje X)
# — igual de criterio que el selector "Releases en gráficas" del dashboard de
# KPIs de Release, pero fijo a 9 en el informe PPT.
CHART_RELEASE_COUNT = 9


def _is_report_up_to_date(report_path, source_path):
    """True si `report_path` ya existe y es más reciente que releases-data.js
    — en ese caso no hace falta regenerar el informe, basta con servir el que
    ya hay (evita 30-60s de renderizado de gráficas en el caso común: nadie
    ha vuelto a subir datos desde la última descarga)."""
    if not report_path.exists():
        return False
    source_path = Path(source_path)
    if not source_path.exists():
        return False
    return source_path.stat().st_mtime <= report_path.stat().st_mtime


@contextlib.contextmanager
def _maybe_chdir(project_root):
    """Cambia el directorio de trabajo mientras dura el bloque, si se indica.

    Todas las rutas de report_generator (releases-data.js, data/reports/)
    son relativas al repo release-dashboard-application. Cuando este módulo
    se invoca desde el mismo proceso que ya vive en ese repo (CLI,
    serve_app.py, que hace chdir al arrancar), no hace falta nada. Pero
    invocado desde OTRO proceso con otro cwd — el backend del repo hermano —
    hay que apuntar temporalmente al repo correcto sin dejar el proceso
    entero con el cwd cambiado (podría romper otras rutas relativas de ese
    proceso, p. ej. su base de datos sqlite).
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

    Si ya existe un informe generado y es más reciente que releases-data.js
    (ver _is_report_up_to_date), se devuelve tal cual sin regenerarlo.

    Misma forma de resultado que converters/cli/upload_csv.py. `project_root`
    es opcional y solo hace falta cuando se invoca desde un proceso con un
    directorio de trabajo distinto al de este repo (ver _maybe_chdir).
    """
    with _maybe_chdir(project_root):
        final_path = Path(output_path) if output_path else report_output_path(release_name)
        if _is_report_up_to_date(final_path, DEFAULT_RELEASES_DATA_PATH):
            return {"success": True, "path": str(final_path.resolve())}

        try:
            releases = load_release_kpis_context()
        except (FileNotFoundError, ValueError) as e:
            return {"success": False, "error": f"No se pudieron cargar los datos de KPIs de Release: {e}"}

        release = find_release(releases, release_name)
        if release is None:
            return {"success": False, "error": f"No hay datos de KPIs de Release para la release '{release_name}'"}

        prs = new_presentation(release_name)
        # Ventana de las últimas CHART_RELEASE_COUNT releases terminando EN la
        # release solicitada (no en la última release existente) — el informe
        # de una release antigua no debe mostrar releases posteriores a ella.
        release_index = releases.index(release)
        window_start = max(0, release_index + 1 - CHART_RELEASE_COUNT)
        chart_releases = releases[window_start:release_index + 1]

        incidencias_chart = export_figure_to_png(build_incidencias_por_release_chart(chart_releases))
        add_kpi_and_chart_slide(prs, release, incidencias_chart, KPI_TARGET_PCT)

        # height=1000 (en vez del 650 por defecto): al ir cada gráfica a media
        # diapositiva, un aspect ratio más cuadrado aprovecha mejor el alto
        # disponible que el 1200x650 pensado para una gráfica a ancho completo.
        # legend_font_size=26: al mostrarse a media diapositiva (~5.97" de
        # ancho) en vez de ancho completo (~8.33"), el mismo tamaño de fuente
        # se ve más pequeño una vez insertada la imagen — se compensa
        # aumentándolo en la misma proporción (18 * 8.33/5.97 ≈ 25).
        pap_chart = export_figure_to_png(build_kpi_pap_chart(chart_releases, legend_font_size=26), height=1000)
        post_chart = export_figure_to_png(build_kpi_post_chart(chart_releases, legend_font_size=26), height=1000)
        add_dual_chart_slide(prs, "Comparativa de KPIs por Release", [
            ("KPI % PaP", pap_chart),
            ("KPI % 1ª semana", post_chart),
        ])

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
    """Genera el informe de todas las releases presentes en releases-data.js.

    No se detiene ante el fallo de una release (User Story 3). Devuelve
    {"generated": [...], "failed": [{"release_name": ..., "error": ...}]}.
    """
    with _maybe_chdir(project_root):
        try:
            releases = load_release_kpis_context()
        except (FileNotFoundError, ValueError):
            return {"generated": [], "failed": []}

        generated, failed = [], []
        for release in releases:
            release_name = release["name"]
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
