"""Tests de report_generator.postmortem_charts.

Casos centrados en la forma de los datos (nº de trazas, nº de puntos,
valores agregados), no en el aspecto visual — eso ya lo verifica
export_figure_to_png() al no lanzar excepción (probado en el test de
integración end-to-end).
"""
from report_generator.postmortem_charts import (
    build_evolution_chart,
    build_pap_evolution_chart,
    build_open_incidents_chart,
    build_system_chart,
    parse_date_only,
)


def _incident(estatus, envio, resolucion="", despliegue="MESA", grupo="SOP_A"):
    return {
        "Estatus": estatus,
        "Fecha de envío": envio,
        "Fecha de última resolución": resolucion,
        "Despliegue": despliegue,
        "Grupo asignado": grupo,
    }


class TestParseDateOnly:
    def test_strips_time_component(self):
        assert parse_date_only("26/04/2026 08:40").isoformat() == "2026-04-26"

    def test_legacy_dd_mmm_format(self):
        assert parse_date_only("26-abr").isoformat() == "2026-04-26"

    def test_invalid_returns_none(self):
        assert parse_date_only("no-es-fecha") is None
        assert parse_date_only("") is None


class TestBuildEvolutionChart:
    def test_three_traces_entries_resolutions_backlog(self):
        records = [_incident("Cerrado", "10/06/2026 08:00", "10/06/2026 10:00")]
        fig, dates, backlog = build_evolution_chart(records)
        assert len(fig.data) == 3
        assert fig.data[0].name == "Entradas Diarias"
        assert fig.data[1].name == "Resoluciones Diarias"
        assert fig.data[2].name == "Backlog Acumulado"

    def test_date_range_includes_resolutions_after_last_envio(self):
        """Regresión del bug corregido en 023-fix-evolution-chart-resolution-range:
        una incidencia abierta en julio y resuelta en agosto debe seguir
        apareciendo en el rango de fechas del eje X."""
        records = [_incident("Cerrado", "31/07/2026 08:00", "05/08/2026 10:00")]
        fig, dates, backlog = build_evolution_chart(records)
        assert dates[0] == "31/07/2026 08:00"
        assert dates[-1] == "05/08/2026 10:00"
        assert sum(fig.data[1].y) == 1  # la resolución de agosto sí se cuenta

    def test_empty_records_produce_empty_chart(self):
        fig, dates, backlog = build_evolution_chart([])
        assert dates == []
        assert len(fig.data) == 3

    def test_backlog_never_negative(self):
        records = [_incident("Cerrado", "10/06/2026 08:00", "10/06/2026 09:00")]
        _, _, backlog = build_evolution_chart(records)
        assert all(v >= 0 for v in backlog)


class TestBuildPapEvolutionChart:
    def test_none_when_no_pap_incidents(self):
        records = [_incident("Cerrado", "10/06/2026 08:00", despliegue="MESA")]
        assert build_pap_evolution_chart(records) is None

    def test_thirty_two_slots_from_08_to_2330(self):
        records = [_incident("Cerrado", "10/06/2026 09:00", "10/06/2026 10:00", despliegue="PAP")]
        fig = build_pap_evolution_chart(records)
        assert len(fig.data[0].x) == 32  # 08:00..23:30 en pasos de 30 min
        assert fig.data[0].x[0] == "10/06 08:00"
        assert fig.data[0].x[-1] == "10/06 23:30"

    def test_resolution_next_day_not_counted_but_stays_in_backlog(self):
        records = [_incident("Cerrado", "10/06/2026 09:00", "11/06/2026 10:00", despliegue="PAP")]
        fig = build_pap_evolution_chart(records)
        assert sum(fig.data[1].y) == 0  # ninguna resolución se cuenta ese día
        assert fig.data[2].y[-1] == 1  # pero sigue en el backlog hasta el final del día


class TestBuildOpenIncidentsChart:
    def test_excludes_closed_incidents_from_status_traces(self):
        records = [
            _incident("Cerrado", "10/06/2026 08:00", "10/06/2026 09:00"),
            _incident("Asignado", "10/06/2026 08:00"),
        ]
        _, dates, backlog = build_evolution_chart(records)
        fig = build_open_incidents_chart(records, dates, backlog)
        status_names = [trace.name for trace in fig.data]
        assert "Asignado" in status_names
        assert "Cerrado" not in status_names

    def test_reuses_evolution_chart_dates_and_backlog(self):
        records = [_incident("Asignado", "10/06/2026 08:00")]
        _, dates, backlog = build_evolution_chart(records)
        fig = build_open_incidents_chart(records, dates, backlog)
        assert list(fig.data[-1].x) == dates
        assert list(fig.data[-1].y) == backlog


class TestBuildSystemChart:
    def test_excludes_closed_and_resolved_by_default(self):
        records = [
            _incident("Cerrado", "10/06/2026 08:00", grupo="SOP_A"),
            _incident("Resuelto", "10/06/2026 08:00", grupo="SOP_A"),
            _incident("Asignado", "10/06/2026 08:00", grupo="SOP_B"),
        ]
        fig = build_system_chart(records)
        assert list(fig.data[0].y) == ["SOP_B"]

    def test_orders_systems_by_volume_descending(self):
        records = (
            [_incident("Asignado", "10/06/2026 08:00", grupo="SOP_A")] * 3
            + [_incident("Pendiente", "10/06/2026 08:00", grupo="SOP_B")]
        )
        fig = build_system_chart(records)
        assert list(fig.data[0].y) == ["SOP_A", "SOP_B"]

    def test_no_open_incidents_produces_no_traces(self):
        records = [_incident("Cerrado", "10/06/2026 08:00")]
        fig = build_system_chart(records)
        assert len(fig.data) == 0
