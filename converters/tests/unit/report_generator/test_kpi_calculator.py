"""Tests de report_generator.kpi_calculator.

Los casos replican exactamente los que se verificaron manualmente en
JavaScript (analyzeData()) durante el desarrollo del dashboard de
postmortem, para dar la mayor garantía posible de paridad JS↔Python
(ver research.md §2-3: riesgo de duplicación de lógica).
"""
from report_generator.kpi_calculator import calculate_kpis, parse_datetime, _pap_day


class TestParseDatetime:
    def test_parses_full_datetime(self):
        dt = parse_datetime("26/04/2026 08:49")
        assert (dt.year, dt.month, dt.day, dt.hour, dt.minute) == (2026, 4, 26, 8, 49)

    def test_date_only_defaults_to_midnight(self):
        dt = parse_datetime("26/04/2026")
        assert (dt.hour, dt.minute) == (0, 0)

    def test_empty_returns_none(self):
        assert parse_datetime("") is None
        assert parse_datetime(None) is None

    def test_malformed_returns_none(self):
        assert parse_datetime("no-es-una-fecha") is None


class TestCalculateKpis:
    def _incidents(self):
        # Mismo dataset usado para verificar manualmente el JS en la sesión
        # de desarrollo (ver verify_new_kpis.js): PAP resuelta al día
        # siguiente del despliegue (no cuenta para % pero sí para pendientes),
        # Mesa con una pendiente.
        return [
            {"Estatus": "Cerrado", "Despliegue": "PAP", "Fecha de envío": "10/06/2026 08:00", "Fecha de última resolución": "10/06/2026 10:00"},
            {"Estatus": "Asignado", "Despliegue": "PAP", "Fecha de envío": "10/06/2026 09:00", "Fecha de última resolución": ""},
            {"Estatus": "Resuelto", "Despliegue": "PAP", "Fecha de envío": "10/06/2026 10:00", "Fecha de última resolución": "11/06/2026 10:00"},
            {"Estatus": "Cerrado", "Despliegue": "MESA", "Fecha de envío": "12/06/2026 08:00", "Fecha de última resolución": "12/06/2026 09:30"},
            {"Estatus": "Pendiente", "Despliegue": "MESA", "Fecha de envío": "12/06/2026 09:00", "Fecha de última resolución": ""},
        ]

    def test_totals_and_pending(self):
        kpis = calculate_kpis(self._incidents())
        assert kpis["total_incidencias"] == 5
        assert kpis["total_pendientes"] == 2  # Asignado (PAP) + Pendiente (MESA)

    def test_pap_pending_counts_any_time_not_resolved(self):
        kpis = calculate_kpis(self._incidents())
        # 3 incidencias PAP, 2 cerradas/resueltas en cualquier momento -> 1 pendiente
        assert kpis["pap_pendientes"] == 1

    def test_pap_percent_only_counts_same_day_resolutions(self):
        kpis = calculate_kpis(self._incidents())
        # Solo la primera (resuelta el mismo día 10/06) cuenta; la tercera se
        # resuelve el 11/06, un día después del despliegue -> no cuenta.
        assert kpis["pct_resueltas_pap"] == 33  # round(1/3 * 100)

    def test_mesa_pending(self):
        kpis = calculate_kpis(self._incidents())
        assert kpis["mesa_pendientes"] == 1

    def test_closed_percent_includes_cerrado_and_resuelto(self):
        kpis = calculate_kpis(self._incidents())
        assert kpis["pct_cerradas"] == 60  # 3 de 5

    def test_average_resolution_time_uses_valid_durations_only(self):
        kpis = calculate_kpis(self._incidents())
        # (2h + 24h + 1.5h) / 3 = 9.1666h -> 9h 10m
        assert kpis["tiempo_medio_resolucion"] == "9h 10m"
        assert kpis["tiempo_medio_detalle"] == "3 de 3 incidencias cerradas con fechas válidas"

    def test_no_pap_incidents_gives_zero_percent_and_pending(self):
        kpis = calculate_kpis([{"Estatus": "Pendiente", "Despliegue": "MESA", "Fecha de envío": "01/01/2026 00:00"}])
        assert kpis["pct_resueltas_pap"] == 0
        assert kpis["pap_pendientes"] == 0

    def test_no_closed_incidents_gives_none_average_resolution_time(self):
        kpis = calculate_kpis([{"Estatus": "Pendiente", "Despliegue": "MESA", "Fecha de envío": "01/01/2026 00:00"}])
        assert kpis["tiempo_medio_resolucion"] is None

    def test_empty_dataset(self):
        kpis = calculate_kpis([])
        assert kpis["total_incidencias"] == 0
        assert kpis["pct_cerradas"] == 0
        assert kpis["tiempo_medio_resolucion"] is None


class TestPapDay:
    def test_uses_earliest_sendable_date_among_pap(self):
        pap_incidents = [
            {"Fecha de envío": "10/06/2026 09:00"},
            {"Fecha de envío": "10/06/2026 08:00"},
        ]
        # Réplica del JS: usa la PRIMERA incidencia con fecha parseable en el
        # orden de los datos, no necesariamente la cronológicamente menor.
        assert _pap_day(pap_incidents).isoformat() == "2026-06-10"

    def test_none_when_no_parseable_dates(self):
        assert _pap_day([{"Fecha de envío": ""}]) is None
