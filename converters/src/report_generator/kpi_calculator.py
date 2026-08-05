"""Cálculo de los 8 KPIs globales del informe.

Réplica exacta de analyzeData() en dashboards/postmortem/index.html (FR-004):
el informe nunca debe mostrar una cifra distinta a la que vería el usuario en
el dashboard para los mismos datos.
"""
from datetime import datetime


def _get(record, field):
    return record.get(field) or ""


def _is_closed_status(record):
    status = _get(record, "Estatus").lower()
    return "cerrado" in status or "resuelto" in status


def parse_datetime(date_str):
    """Parsea "DD/MM/YYYY HH:MM" (formato de parsePostmortemDateTime()).

    Réplica de parseDateTime() en analyzeData() — mismo comportamiento ante
    entradas vacías o mal formadas (devuelve None).
    """
    if not date_str:
        return None
    parts = date_str.strip().split(" ")
    date_part = parts[0]
    time_part = parts[1] if len(parts) > 1 else "00:00"
    if "/" not in date_part:
        return None

    date_bits = date_part.split("/")
    if len(date_bits) < 3:
        return None

    try:
        day, month, year = (int(x) for x in date_bits[:3])
    except ValueError:
        return None

    time_bits = time_part.split(":")
    try:
        hour = int(time_bits[0])
    except (ValueError, IndexError):
        hour = 0
    try:
        minute = int(time_bits[1])
    except (ValueError, IndexError):
        minute = 0

    try:
        return datetime(year, month, day, hour, minute)
    except ValueError:
        return None


def _format_duration(total_seconds):
    """Réplica de formatDuration(): "Xd Yh" / "Xh Ym" / "Xm"."""
    total_minutes = round(total_seconds / 60)
    days, rem = divmod(total_minutes, 60 * 24)
    hours, minutes = divmod(rem, 60)
    if days > 0:
        return f"{days}d {hours}h"
    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def _pap_day(pap_incidents):
    """Día (sin hora) de la "Fecha de envío" más antigua entre las PAP.

    Réplica del bucle de papDay en analyzeData(): se queda con la primera
    incidencia PAP (en el orden en que aparece en los datos) que tenga una
    "Fecha de envío" parseable, igual que el JS.
    """
    for incident in pap_incidents:
        dt = parse_datetime(_get(incident, "Fecha de envío"))
        if dt:
            return dt.date()
    return None


def calculate_kpis(records):
    """Calcula los 8 KPIs globales para la lista de registros de una release.

    Devuelve un dict con las mismas claves que consume pptx_builder.add_kpi_slide.
    """
    total = len(records)
    closed = sum(1 for r in records if _is_closed_status(r))
    closed_percent = round((closed / total) * 100) if total > 0 else 0
    pending_total = total - closed

    pap_incidents = [r for r in records if _get(r, "Despliegue") == "PAP"]
    pap_day = _pap_day(pap_incidents)

    def resolved_same_pap_day(incident):
        if not _is_closed_status(incident):
            return False
        if pap_day is None:
            return True
        resolved_at = parse_datetime(_get(incident, "Fecha de última resolución"))
        return resolved_at is not None and resolved_at.date() == pap_day

    pap_resolved = sum(1 for r in pap_incidents if resolved_same_pap_day(r))
    pap_percent = round((pap_resolved / len(pap_incidents)) * 100) if pap_incidents else 0

    pap_closed_anytime = sum(1 for r in pap_incidents if _is_closed_status(r))
    pap_pending = len(pap_incidents) - pap_closed_anytime

    mesa_incidents = [r for r in records if _get(r, "Despliegue") == "MESA"]
    mesa_resolved = sum(1 for r in mesa_incidents if _is_closed_status(r))
    mesa_percent = round((mesa_resolved / len(mesa_incidents)) * 100) if mesa_incidents else 0
    mesa_pending = len(mesa_incidents) - mesa_resolved

    resolution_durations = []
    for r in records:
        if not _is_closed_status(r):
            continue
        sent_at = parse_datetime(_get(r, "Fecha de envío"))
        resolved_at = parse_datetime(_get(r, "Fecha de última resolución"))
        if sent_at and resolved_at and resolved_at >= sent_at:
            resolution_durations.append((resolved_at - sent_at).total_seconds())

    avg_resolution_seconds = (
        sum(resolution_durations) / len(resolution_durations) if resolution_durations else None
    )

    return {
        "total_incidencias": total,
        "total_pendientes": pending_total,
        "pct_cerradas": closed_percent,
        "cerradas_detalle": f"{closed} de {total} incidencias",
        "tiempo_medio_resolucion": (
            _format_duration(avg_resolution_seconds) if avg_resolution_seconds is not None else None
        ),
        "tiempo_medio_detalle": f"{len(resolution_durations)} de {closed} incidencias cerradas con fechas válidas",
        "pct_resueltas_pap": pap_percent,
        "pap_detalle": f"{pap_resolved} de {len(pap_incidents)} incidencias PaP resueltas el día del PaP",
        "pap_pendientes": pap_pending,
        "pct_resueltas_mesa": mesa_percent,
        "mesa_detalle": f"{mesa_resolved} de {len(mesa_incidents)} incidencias Mesa",
        "mesa_pendientes": mesa_pending,
    }
