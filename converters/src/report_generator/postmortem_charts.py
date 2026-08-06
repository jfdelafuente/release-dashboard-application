"""Réplica de las 4 gráficas del dashboard de postmortem con Plotly (Python).

Cada función espejea, campo a campo y color a color, la función JS
equivalente en dashboards/postmortem/index.html (ver cabecera de cada
función para la referencia exacta). Mantener esa correspondencia 1:1 es lo
que permite que los tests de este módulo (con casos ya verificados
manualmente en JS) den garantías reales de paridad — ver research.md §2-3.
"""
from datetime import date, datetime, timedelta

import plotly.graph_objects as go

from report_generator.chart_utils import BASE_LAYOUT, STATUS_PALETTE, COLOR_INK

_MONTH_ABBR = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
_LEGACY_MONTHS = {name: idx for idx, name in enumerate(_MONTH_ABBR, start=1)}

_HOVER_LAYOUT_EXTRA = dict(hovermode="x unified", barmode="group")

_LEGEND = dict(
    orientation="h", x=0.5, xanchor="center", y=1.12, yanchor="bottom",
    bgcolor="rgba(255,255,255,0.9)", bordercolor="#E2DDD5", borderwidth=1, font=dict(size=11),
)


def _get(record, field):
    return record.get(field) or ""


def _is_closed_status(record):
    status = _get(record, "Estatus").lower()
    return "cerrado" in status or "resuelto" in status


def parse_date_only(date_str):
    """Réplica de parseDate(): soporta "DD/MM/YYYY[ HH:MM]" y el legacy "D-mmm"."""
    if not date_str:
        return None
    date_part = date_str.strip().split(" ")[0]

    if "/" in date_part:
        bits = date_part.split("/")
        if len(bits) >= 3:
            try:
                return date(int(bits[2]), int(bits[1]), int(bits[0]))
            except ValueError:
                return None
        return None

    bits = date_str.strip().lower().split("-")
    if len(bits) != 2:
        return None
    month = _LEGACY_MONTHS.get(bits[1].strip())
    if month is None:
        return None
    try:
        return date(2026, month, int(bits[0]))
    except ValueError:
        return None


def _to_date_key(d):
    return d.isoformat()


def _display_fallback(date_key):
    """Réplica del fallback de displayDate para días sin datos: "D-mmm"."""
    d = date.fromisoformat(date_key)
    return f"{d.day}-{_MONTH_ABBR[d.month - 1]}"


def build_evolution_chart(records):
    """Réplica de createEvolutionChart(). Devuelve (Figure, dates, backlog).

    `dates`/`backlog` se exponen para que build_open_incidents_chart() los
    reutilice, igual que el JS reutiliza `globalBacklogData`.
    """
    daily_data = {}
    date_map = {}

    for r in records:
        date_str = _get(r, "Fecha de envío")
        if not date_str:
            continue
        date_obj = parse_date_only(date_str)
        key = _to_date_key(date_obj) if date_obj else date_str
        if key not in daily_data:
            daily_data[key] = {"entries": 0, "resolutions": 0, "date_obj": date_obj}
            date_map[key] = date_str
        daily_data[key]["entries"] += 1

    for r in records:
        if not _is_closed_status(r):
            continue
        date_str = _get(r, "Fecha de última resolución")
        if not date_str:
            continue
        date_obj = parse_date_only(date_str)
        key = _to_date_key(date_obj) if date_obj else date_str
        if key not in daily_data:
            daily_data[key] = {"entries": 0, "resolutions": 0, "date_obj": date_obj}
            date_map[key] = date_str
        daily_data[key]["resolutions"] += 1

    # Rango de fechas a partir de AMBAS fechas (envío + resolución) — ver el
    # fix de 023-fix-evolution-chart-resolution-range: usar solo "Fecha de
    # envío" deja fuera resoluciones de meses posteriores.
    parsed_dates = [d["date_obj"] for d in daily_data.values() if d["date_obj"]]
    dates, entries, resolutions, backlog = [], [], [], []

    if parsed_dates:
        min_date, max_date = min(parsed_dates), max(parsed_dates)
        backlog_previous = 0
        current = min_date
        while current <= max_date:
            key = _to_date_key(current)
            day = daily_data.get(key)
            display_date = date_map[key] if day else _display_fallback(key)
            entradas = day["entries"] if day else 0
            solucionadas = day["resolutions"] if day else 0

            backlog_actual = backlog_previous + entradas - solucionadas
            backlog_previous = backlog_actual

            dates.append(display_date)
            entries.append(entradas)
            resolutions.append(solucionadas)
            backlog.append(max(0, backlog_actual))
            current += timedelta(days=1)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=dates, y=entries, name="Entradas Diarias", marker_color="#FFC08A", yaxis="y",
        text=[str(v) if v > 0 else "" for v in entries], textposition="outside",
        textfont=dict(size=10, color="#5C5852"),
    ))
    fig.add_trace(go.Bar(
        x=dates, y=resolutions, name="Resoluciones Diarias", marker_color="#FF7900", yaxis="y",
        text=[str(v) if v > 0 else "" for v in resolutions], textposition="outside",
        textfont=dict(size=10, color="#5C5852"),
    ))
    fig.add_trace(go.Scatter(
        x=dates, y=backlog, name="Backlog Acumulado", mode="lines+markers+text",
        line=dict(color=COLOR_INK, width=3), marker=dict(size=8, color=COLOR_INK),
        text=[str(v) for v in backlog], textposition="top center",
        textfont=dict(size=10, color=COLOR_INK), yaxis="y2",
    ))
    fig.update_layout(
        **BASE_LAYOUT, **_HOVER_LAYOUT_EXTRA, legend=_LEGEND, margin=dict(l=70, r=70, t=70, b=80),
        xaxis=dict(title="Fecha de Apertura", tickangle=-45, showgrid=True, gridcolor="#E2DDD5"),
        yaxis=dict(title="Entradas y Resoluciones (Volumen)", showgrid=True, gridcolor="#E2DDD5"),
        yaxis2=dict(title="Backlog Acumulado", overlaying="y", side="right", showgrid=False),
    )
    return fig, dates, backlog


def build_pap_evolution_chart(records):
    """Réplica de createPapEvolutionChart(). Devuelve None si no hay incidencias PaP."""
    pap_incidents = [r for r in records if _get(r, "Despliegue") == "PAP"]
    if not pap_incidents:
        return None

    def parse_datetime(date_str):
        if not date_str:
            return None
        parts = date_str.strip().split(" ")
        date_part = parts[0]
        time_part = parts[1] if len(parts) > 1 else "00:00"
        if "/" not in date_part:
            return None
        bits = date_part.split("/")
        if len(bits) < 3:
            return None
        try:
            day, month, year = int(bits[0]), int(bits[1]), int(bits[2])
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

    def floor_to_half_hour(dt):
        return dt.replace(minute=0 if dt.minute < 30 else 30, second=0, microsecond=0)

    def format_slot(dt):
        return f"{dt.day:02d}/{dt.month:02d} {dt.hour:02d}:{dt.minute:02d}"

    pap_day = None
    for incident in pap_incidents:
        dt = parse_datetime(_get(incident, "Fecha de envío"))
        if dt:
            pap_day = dt.date()
            break

    slot_data = {}
    for incident in pap_incidents:
        dt = parse_datetime(_get(incident, "Fecha de envío"))
        if not dt:
            continue
        slot = floor_to_half_hour(dt)
        slot_data.setdefault(slot, {"entries": 0, "resolutions": 0})["entries"] += 1

    for incident in pap_incidents:
        if not _is_closed_status(incident):
            continue
        dt = parse_datetime(_get(incident, "Fecha de última resolución"))
        if not dt or not pap_day or dt.date() != pap_day:
            continue
        slot = floor_to_half_hour(dt)
        slot_data.setdefault(slot, {"entries": 0, "resolutions": 0})["resolutions"] += 1

    dates, entries, resolutions, backlog = [], [], [], []
    if pap_day:
        pap_day_start = datetime(pap_day.year, pap_day.month, pap_day.day, 8, 0)  # PAP_DAY_START_HOUR = 8
        thirty_min = timedelta(minutes=30)
        max_slot = pap_day_start.replace(hour=0, minute=0) + 47 * thirty_min

        backlog_previous = 0
        slot = pap_day_start
        while slot <= max_slot:
            bucket = slot_data.get(slot, {"entries": 0, "resolutions": 0})
            backlog_actual = backlog_previous + bucket["entries"] - bucket["resolutions"]
            backlog_previous = backlog_actual

            dates.append(format_slot(slot))
            entries.append(bucket["entries"])
            resolutions.append(bucket["resolutions"])
            backlog.append(max(0, backlog_actual))
            slot += thirty_min

    fig = go.Figure()
    fig.add_trace(go.Bar(x=dates, y=entries, name="Abiertas (PAP)", marker_color="#FFC08A", yaxis="y"))
    fig.add_trace(go.Bar(x=dates, y=resolutions, name="Cerradas (PAP)", marker_color="#FF7900", yaxis="y"))
    fig.add_trace(go.Scatter(
        x=dates, y=backlog, name="Backlog PAP", mode="lines+markers",
        line=dict(color=COLOR_INK, width=3), marker=dict(size=8, color=COLOR_INK), yaxis="y2",
    ))
    fig.update_layout(
        **BASE_LAYOUT, **_HOVER_LAYOUT_EXTRA, legend=_LEGEND, margin=dict(l=70, r=70, t=70, b=80),
        xaxis=dict(title="Hora (intervalos de 30 min)", tickangle=-45, showgrid=True, gridcolor="#E2DDD5"),
        yaxis=dict(title="Abiertas y Cerradas (Volumen)", showgrid=True, gridcolor="#E2DDD5"),
        yaxis2=dict(title="Backlog PAP", overlaying="y", side="right", showgrid=False),
    )
    return fig


def build_open_incidents_chart(records, evolution_dates, evolution_backlog):
    """Réplica de createOpenIncidentsChart() (ruta con globalBacklogData ya disponible)."""
    daily_open = {}
    status_list = []

    for r in records:
        status = _get(r, "Estatus") or "Unknown"
        if _is_closed_status(r):
            continue
        date_str = _get(r, "Fecha de envío")
        if not date_str:
            continue
        date_obj = parse_date_only(date_str)
        key = _to_date_key(date_obj) if date_obj else date_str
        bucket = daily_open.setdefault(key, {"by_status": {}})
        bucket["by_status"][status] = bucket["by_status"].get(status, 0) + 1
        if status not in status_list:
            status_list.append(status)

    status_data = {status: [] for status in status_list}
    for display_date in evolution_dates:
        parsed = parse_date_only(display_date)
        key = _to_date_key(parsed) if parsed else None
        bucket = daily_open.get(key, {}) if key else {}
        by_status = bucket.get("by_status", {})
        for status in status_list:
            status_data[status].append(by_status.get(status, 0))

    fig = go.Figure()
    for idx, status in enumerate(status_list):
        fig.add_trace(go.Bar(
            x=evolution_dates, y=status_data[status], name=status,
            marker_color=STATUS_PALETTE[idx % len(STATUS_PALETTE)], yaxis="y",
        ))
    fig.add_trace(go.Scatter(
        x=evolution_dates, y=evolution_backlog, name="Backlog Acumulado", mode="lines+markers",
        line=dict(color=COLOR_INK, width=3), marker=dict(size=8, color=COLOR_INK), yaxis="y2",
    ))
    fig.update_layout(
        **BASE_LAYOUT, legend=_LEGEND, hovermode="x unified", barmode="stack", margin=dict(l=70, r=70, t=70, b=80),
        xaxis=dict(title="Fecha de Apertura", tickangle=-45, showgrid=True, gridcolor="#E2DDD5"),
        yaxis=dict(title="Incidencias No Cerradas", showgrid=True, gridcolor="#E2DDD5"),
        yaxis2=dict(title="Backlog Acumulado", overlaying="y", side="right", showgrid=False),
    )
    return fig


def build_system_chart(records):
    """Réplica de createSystemChart() (comportamiento por defecto: excluye Cerrado/Resuelto).

    El informe no tiene un filtro interactivo de Estado como el dashboard,
    así que siempre usa el criterio por defecto (FR-006/007: mismo estilo,
    no una réplica interactiva).
    """
    open_incidents = [r for r in records if not _is_closed_status(r)]

    totals_by_system = {}
    counts_by_system_status = {}
    status_list = []

    for r in open_incidents:
        system = _get(r, "Grupo asignado") or "Unknown"
        status = _get(r, "Estatus") or "Sin estado"
        totals_by_system[system] = totals_by_system.get(system, 0) + 1
        counts_by_system_status.setdefault(system, {})[status] = (
            counts_by_system_status.setdefault(system, {}).get(status, 0) + 1
        )
        if status not in status_list:
            status_list.append(status)

    systems = [system for system, _ in sorted(totals_by_system.items(), key=lambda kv: kv[1], reverse=True)]

    fig = go.Figure()
    for idx, status in enumerate(status_list):
        fig.add_trace(go.Bar(
            y=systems,
            x=[counts_by_system_status.get(system, {}).get(status, 0) for system in systems],
            name=status, orientation="h",
            marker_color=STATUS_PALETTE[idx % len(STATUS_PALETTE)],
        ))
    fig.update_layout(
        **BASE_LAYOUT, legend=_LEGEND, hovermode="x unified", barmode="stack",
        margin=dict(l=180, r=70, t=70, b=40),
        xaxis=dict(showgrid=True, gridcolor="#E2DDD5"),
        yaxis=dict(showgrid=False),
    )
    return fig
