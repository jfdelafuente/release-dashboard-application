"""Cálculo de tendencia de una release frente a la media móvil de las
releases anteriores, a partir de la misma fuente que el resto del informe
(dashboards/release-kpis/releases-data.js vía release_kpis_data).

No depende del JSON de postmortem — mismo criterio que el resto de
report_generator tras el rediseño de la feature 008.
"""
from report_generator.release_kpis_data import find_release

DEFAULT_TREND_WINDOW = 4

_METRICS = ("pct_pap", "pct_first_week", "total_incidencias")


def _mean(values):
    return sum(values) / len(values)


def compute_release_trend(releases, release_name, window=DEFAULT_TREND_WINDOW):
    """Compara `release_name` contra la media móvil de las `window` releases
    cronológicamente anteriores en `releases` (orden ascendente, igual que
    build_releases()/load_release_kpis_context()).

    Si no hay ninguna release anterior en el histórico (p. ej. es la release
    más antigua registrada), `has_baseline` es False y todos los campos de
    baseline/delta quedan en None — nunca se calcula una media con cero
    muestras.
    """
    release = find_release(releases, release_name)
    if release is None:
        raise ValueError(f"No hay datos de KPIs de Release para la release '{release_name}'")

    release_index = releases.index(release)
    window_start = max(0, release_index - window)
    window_releases = releases[window_start:release_index]

    result = {
        "release": release,
        "window_releases": window_releases,
        "has_baseline": bool(window_releases),
    }

    for metric in _METRICS:
        baseline_key = f"baseline_{metric}"
        delta_key = f"delta_{metric}"
        if window_releases:
            baseline = round(_mean([r[metric] for r in window_releases]), 1)
            result[baseline_key] = baseline
            result[delta_key] = round(release[metric] - baseline, 1)
        else:
            result[baseline_key] = None
            result[delta_key] = None

    return result


def build_trend_narrative(trend):
    """Genera el texto narrativo de 2-3 frases para la diapositiva de
    tendencia ejecutiva. Plantilla determinista (sin LLM): este código corre
    dentro del pipeline de generación de PPT, no en una skill de agente."""
    release = trend["release"]
    name = release["name"]

    if not trend["has_baseline"]:
        return (
            f"{name} es la primera release registrada en el histórico; "
            "no hay media móvil de comparación disponible."
        )

    n = len(trend["window_releases"])
    return (
        f"{name} resuelve el {release['pct_pap']}% de PaP "
        f"({trend['delta_pct_pap']:+.1f} pp vs. media de las {n} releases anteriores) "
        f"y el {release['pct_first_week']}% en primera semana "
        f"({trend['delta_pct_first_week']:+.1f} pp). "
        f"Total de incidencias: {release['total_incidencias']} "
        f"({trend['delta_total_incidencias']:+.1f} vs. media)."
    )
