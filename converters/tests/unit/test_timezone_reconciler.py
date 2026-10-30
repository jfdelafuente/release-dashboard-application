import pytest
from datetime import datetime
from converters.src.csv_to_json.timezone_utils import (
    detect_site_timezone,
    parse_milestone_datetime,
    parse_remedy_datetime,
    reconcile_milestones,
    calculate_reconciled_reaction_lag
)


def test_detect_site_timezone_colombia():
    tz, label, alias = detect_site_timezone("Afecta 15 usuarios de Teleperformance Medellín (sede Andes)")
    assert tz == "America/Bogota"
    assert "Colombia" in label
    assert alias is not None

    tz_bogota, _, _ = detect_site_timezone("Servicio operado en sede Bogotá")
    assert tz_bogota == "America/Bogota"


def test_detect_site_timezone_international_sites():
    tz, label, _ = detect_site_timezone("Incidencia en centro de atención en Santiago de Chile")
    assert tz == "America/Santiago"

    tz_mex, _, _ = detect_site_timezone("Call center en CDMX con saturación")
    assert tz_mex == "America/Mexico_City"

    tz_morocco, _, _ = detect_site_timezone("Operadores en Casablanca")
    assert tz_morocco == "Africa/Casablanca"


def test_detect_site_timezone_spain_and_default():
    tz, label, alias = detect_site_timezone("Oficinas centrales en Pozuelo La Finca")
    assert tz == "Europe/Madrid"

    tz_def, label_def, alias_def = detect_site_timezone("Error general en el catálogo")
    assert tz_def == "Europe/Madrid"
    assert alias_def is None


def test_parse_milestone_datetime():
    dt = parse_milestone_datetime("30/10/2026: Detección incidencia 05:37 - No carga escaparate")
    assert dt is not None
    assert dt.year == 2026
    assert dt.month == 10
    assert dt.day == 30
    assert dt.hour == 5
    assert dt.minute == 37

    ref_date = datetime(2026, 10, 30, 0, 0)
    dt_time_only = parse_milestone_datetime("Escalado a las 06:15 por guardia", default_date=ref_date)
    assert dt_time_only is not None
    assert dt_time_only.hour == 6
    assert dt_time_only.minute == 15


def test_parse_remedy_datetime():
    # Spanish Remedy morning
    dt1 = parse_remedy_datetime("30/10/2026 11:52 a")
    assert dt1 is not None
    assert dt1.hour == 11
    assert dt1.minute == 52

    # Spanish Remedy afternoon
    dt2 = parse_remedy_datetime("30/10/2026 03:15 p")
    assert dt2 is not None
    assert dt2.hour == 15
    assert dt2.minute == 15

    # Standard 24h
    dt3 = parse_remedy_datetime("30/10/2026 18:45:00")
    assert dt3 is not None
    assert dt3.hour == 18
    assert dt3.minute == 45


def test_reconcile_milestones_medellin_inc000004171670():
    hitos = [
        "30/10/2026: Detección incidencia 05:37 - No carga escaparate completo dispositivos",
        "30/10/2026: Escalado a P2 SL2 por IM y +O",
        "30/10/2026: Identificado error clusterID=0 en GestorCatalogoDisponibleWS"
    ]
    context = "Afecta a Teleperformance Medellín (sede Andes)"
    reconciled = reconcile_milestones(hitos, context_text=context)

    assert len(reconciled) == 3
    # The first milestone has a time: 05:37 COT -> 11:37 CET
    assert reconciled[0]["has_remote_tz"] is True
    assert reconciled[0]["source_tz"] == "America/Bogota"
    assert reconciled[0]["source_str"] == "05:37"
    assert reconciled[0]["madrid_str"] == "11:37 CET"
    assert "11:37 CET" in reconciled[0]["reconciled"]
    assert "05:37" in reconciled[0]["reconciled"]


def test_calculate_reconciled_reaction_lag_inc000004171670():
    detection = "30/10/2026: Detección incidencia 05:37 - No carga escaparate completo dispositivos"
    remedy_open = "30/10/2026 11:52 a"
    context = "Afecta 15 usuarios de Teleperformance Medellín (sede Andes)"

    res = calculate_reconciled_reaction_lag(detection, remedy_open, context_text=context)

    assert res["is_reconciled"] is True
    assert res["lag_minutes"] == 15  # 11:37 CET vs 11:52 CET = 15 minutes!
    assert res["naive_lag_minutes"] == 375  # 6h 15m without timezone conversion
    assert res["correction_minutes"] == 360  # 6 hours = 360 mins correction
    assert "15 minutos" in res["summary"]
