"""
Timezone Reconciler for International Sites and Operations.

Detects remote operational site timezones (e.g. Colombia, Chile, Mexico, Morocco)
from ticket descriptions or Epsilon IA telemetry and reconciles milestone timestamps
with Madrid Headquarters (Europe/Madrid - CET/CEST), preventing the "Timezone Blindness"
defect where remote detection times are mistakenly subtracted from Remedy Madrid timestamps.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Optional

try:
    from zoneinfo import ZoneInfo
except ImportError:
    # Fallback for Python < 3.9 if ever executed on legacy runtimes
    from backports.zoneinfo import ZoneInfo  # type: ignore

MADRID_TZ = ZoneInfo("Europe/Madrid")

# Canonical site mapping
KNOWN_SITE_TIMEZONES = [
    # Colombia (COT, UTC-5)
    (r"\b(medell[ií]n|bogot[aá]|colombia|teleperformance\s*medell[ií]n|sede\s*andes)\b", "America/Bogota", "Colombia (COT, UTC-5)"),
    # Chile (CLT/CLST)
    (r"\b(santiago(?:\s+de\s+chile)?|chile)\b", "America/Santiago", "Chile (CLT)"),
    # Mexico (CST)
    (r"\b(m[eé]xico|cdmx|guadalajara|monterrey)\b", "America/Mexico_City", "México (CST, UTC-6)"),
    # Argentina (ART, UTC-3)
    (r"\b(buenos\s*aires|argentina)\b", "America/Argentina/Buenos_Aires", "Argentina (ART, UTC-3)"),
    # Morocco (WET/WEST)
    (r"\b(casablanca|rabat|marruecos|morocco)\b", "Africa/Casablanca", "Marruecos (WET/WEST)"),
    # Spain / HQ (Europe/Madrid)
    (r"\b(madrid|pozuelo|la\s+finca|sevilla|barcelona|valencia|valladolid|españa|spain)\b", "Europe/Madrid", "España / HQ (CET/CEST)"),
]


def detect_site_timezone(text: str) -> tuple[str, Optional[str], Optional[str]]:
    """
    Detects if the incident context refers to an international operational site.

    Returns:
        tuple of (timezone_name, site_label, matched_alias)
        Defaults to ("Europe/Madrid", "España / HQ (CET/CEST)", None) if no remote site detected.
    """
    if not text:
        return "Europe/Madrid", "España / HQ (CET/CEST)", None

    for pattern, tz_name, label in KNOWN_SITE_TIMEZONES:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            # If match is Madrid/Spain, return it explicitly
            return tz_name, label, match.group(0)

    return "Europe/Madrid", "España / HQ (CET/CEST)", None


def parse_milestone_datetime(milestone_str: str, default_date: Optional[datetime] = None) -> Optional[datetime]:
    """
    Extracts date and time from a milestone text string, e.g.:
    - '30/10/2026: Detección incidencia 05:37'
    - '30/10/2026 05:37'
    - '05:37 - No carga escaparate'
    """
    if not milestone_str:
        return None

    # Try full date + time: DD/MM/YYYY ... HH:MM(:SS)
    full_pattern = re.search(r"(\d{1,2}/\d{1,2}/\d{4}).*?(\d{1,2}:\d{2}(?::\d{2})?)", milestone_str)
    if full_pattern:
        date_part = full_pattern.group(1)
        time_part = full_pattern.group(2)
        fmt = "%d/%m/%Y %H:%M:%S" if len(time_part.split(":")) == 3 else "%d/%m/%Y %H:%M"
        try:
            return datetime.strptime(f"{date_part} {time_part}", fmt)
        except ValueError:
            pass

    # Try time only: HH:MM with default date
    time_pattern = re.search(r"\b(\d{1,2}:\d{2}(?::\d{2})?)\b", milestone_str)
    if time_pattern and default_date:
        time_part = time_pattern.group(1)
        fmt = "%H:%M:%S" if len(time_part.split(":")) == 3 else "%H:%M"
        try:
            t = datetime.strptime(time_part, fmt).time()
            return datetime.combine(default_date.date(), t)
        except ValueError:
            pass

    return None


def parse_remedy_datetime(remedy_str: str) -> Optional[datetime]:
    """
    Parses Remedy CSV timestamp format, e.g.:
    '30/10/2026 11:52 a' or '30/10/2026 11:52:00' or '30/10/2026 11:52'
    """
    if not remedy_str:
        return None

    clean = remedy_str.strip()
    # Remedy Spanish format: '30/10/2026 11:52 a' or '30/10/2026 11:52 p'
    match_ampm = re.match(r"^(\d{1,2}/\d{1,2}/\d{4})\s+(\d{1,2}):(\d{2})(?::(\d{2}))?\s*([ap])$", clean, re.IGNORECASE)
    if match_ampm:
        date_p, h_p, m_p, s_p, ap = match_ampm.groups()
        hour = int(h_p)
        minute = int(m_p)
        sec = int(s_p) if s_p else 0
        ap_lower = ap.lower()
        if ap_lower == "p" and hour < 12:
            hour += 12
        elif ap_lower == "a" and hour == 12:
            hour = 0
        try:
            d = datetime.strptime(date_p, "%d/%m/%Y")
            return datetime(d.year, d.month, d.day, hour, minute, sec)
        except ValueError:
            pass

    # Standard formats
    for fmt in ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(clean, fmt)
        except ValueError:
            continue

    return None


def reconcile_milestones(
    hitos: list[str],
    context_text: str = "",
    reference_date: Optional[datetime] = None
) -> list[dict[str, Any]]:
    """
    Analyzes and reconciles technical milestones, converting remote site times to Madrid CET.
    """
    tz_name, tz_label, matched_site = detect_site_timezone(context_text)
    is_remote = tz_name != "Europe/Madrid"
    source_tz = ZoneInfo(tz_name)

    results = []
    for h in hitos:
        dt_naive = parse_milestone_datetime(h, default_date=reference_date)
        if not dt_naive:
            results.append({
                "original": h,
                "reconciled": h,
                "has_remote_tz": False,
                "dt_madrid": None
            })
            continue

        if is_remote:
            dt_source = dt_naive.replace(tzinfo=source_tz)
            dt_madrid = dt_source.astimezone(MADRID_TZ)
            madrid_str = dt_madrid.strftime("%H:%M CET")
            source_str = dt_source.strftime("%H:%M")

            # Annotate line with both times
            annotated = f"{h} [Reconciliado: {madrid_str} / {source_str} {tz_label}]"
            results.append({
                "original": h,
                "reconciled": annotated,
                "has_remote_tz": True,
                "source_tz": tz_name,
                "source_label": tz_label,
                "dt_madrid": dt_madrid,
                "madrid_str": madrid_str,
                "source_str": source_str
            })
        else:
            dt_madrid = dt_naive.replace(tzinfo=MADRID_TZ)
            results.append({
                "original": h,
                "reconciled": h,
                "has_remote_tz": False,
                "dt_madrid": dt_madrid
            })

    return results


def calculate_reconciled_reaction_lag(
    detection_str: str,
    ticket_open_str: str,
    context_text: str = ""
) -> dict[str, Any]:
    """
    Calculates true reaction lag between detection and Remedy ticket creation.
    Reconciles timezone differences when detection occurred at a remote site.

    Returns:
        dict with lag_minutes, is_reconciled, explanation
    """
    tz_name, tz_label, _ = detect_site_timezone(context_text)
    dt_remedy_naive = parse_remedy_datetime(ticket_open_str)
    if not dt_remedy_naive:
        return {"lag_minutes": None, "is_reconciled": False, "error": "Cannot parse Remedy ticket open time"}

    dt_remedy = dt_remedy_naive.replace(tzinfo=MADRID_TZ)

    dt_detection_naive = parse_milestone_datetime(detection_str, default_date=dt_remedy)
    if not dt_detection_naive:
        return {"lag_minutes": None, "is_reconciled": False, "error": "Cannot parse detection milestone time"}

    source_tz = ZoneInfo(tz_name)
    dt_detection = dt_detection_naive.replace(tzinfo=source_tz)
    dt_detection_madrid = dt_detection.astimezone(MADRID_TZ)

    delta = dt_remedy - dt_detection_madrid
    lag_minutes = int(delta.total_seconds() // 60)

    is_remote = tz_name != "Europe/Madrid"
    naive_delta = dt_remedy_naive - dt_detection_naive
    naive_lag_minutes = int(naive_delta.total_seconds() // 60)

    return {
        "lag_minutes": lag_minutes,
        "is_reconciled": is_remote,
        "source_tz": tz_name,
        "source_label": tz_label,
        "detection_madrid": dt_detection_madrid.strftime("%d/%m/%Y %H:%M CET"),
        "remedy_madrid": dt_remedy.strftime("%d/%m/%Y %H:%M CET"),
        "naive_lag_minutes": naive_lag_minutes,
        "correction_minutes": naive_lag_minutes - lag_minutes if is_remote else 0,
        "summary": (
            f"Detección en {tz_label} a las {dt_detection.strftime('%H:%M')} = {dt_detection_madrid.strftime('%H:%M CET')}. "
            f"Apertura en Remedy (Madrid) a las {dt_remedy.strftime('%H:%M CET')}. "
            f"Tiempo de reacción real: {lag_minutes} minutos (corrección de {naive_lag_minutes - lag_minutes} min aplicada por diferencia horaria)."
            if is_remote else
            f"Detección a las {dt_detection_madrid.strftime('%H:%M CET')}, apertura Remedy a las {dt_remedy.strftime('%H:%M CET')} ({lag_minutes} min)."
        )
    }
