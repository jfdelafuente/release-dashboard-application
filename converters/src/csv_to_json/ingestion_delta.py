"""Ingestion Delta Analyzer.

Compares newly ingested massive incident batches against previous/archived batches to detect:
1. Tickets nuevos: Newly registered incidents.
2. Tickets resueltos: Incidents transitioning to terminal status (Resuelto, Cerrado, Cancelado).
3. Tickets reabiertos: Incidents transitioning from terminal to active status (Asignado, En Curso, Pendiente).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
import re
from typing import Any, Optional, Sequence, Set

logger = logging.getLogger("ingestion_delta")

TERMINAL_STATUS_PREFIXES = ("resuel", "cerrad", "cancel", "clos", "resolv")


def is_status_terminal(status: Optional[str]) -> bool:
    """Returns True if status string represents a closed, resolved, or cancelled ticket."""
    if not status:
        return False
    s = str(status).strip().lower()
    return any(s.startswith(prefix) for prefix in TERMINAL_STATUS_PREFIXES)


def find_latest_archived_massive_file(
    archive_dir: Path,
    exclude_file: Optional[Path] = None
) -> Optional[Path]:
    """Finds the most recent archived massive JSON file, optionally excluding a file."""
    if not archive_dir.exists() or not archive_dir.is_dir():
        return None

    exclude_res = exclude_file.resolve() if exclude_file and exclude_file.exists() else None
    candidates: list[Path] = []

    for f in archive_dir.glob("*massive*.json"):
        if not f.is_file():
            continue
        if exclude_res and f.resolve() == exclude_res:
            continue
        candidates.append(f)

    if not candidates:
        return None

    def sort_key(p: Path) -> tuple[float, str]:
        # Extract timestamp digits if present (e.g. 20261104134631)
        m = re.search(r"(\d{14})", p.name)
        ts_str = m.group(1) if m else ""
        return (p.stat().st_mtime, ts_str, p.name)

    candidates.sort(key=sort_key, reverse=True)
    return candidates[0]


def extract_incident_id(ticket: dict[str, Any]) -> str:
    """Extracts incident identifier from Remedy or normalized dictionary."""
    return str(ticket.get("ID de incidencia") or ticket.get("id") or ticket.get("codigo") or "").strip()


def extract_incident_status(ticket: dict[str, Any]) -> str:
    """Extracts incident status string."""
    return str(
        ticket.get("Estatus") or ticket.get("estatus")
        or ticket.get("Estado") or ticket.get("estado")
        or ticket.get("Status") or ticket.get("status") or ""
    ).strip()


def compute_ingestion_delta(
    current_tickets: Sequence[dict[str, Any]],
    previous_tickets: Sequence[dict[str, Any]],
    previous_file_name: str = ""
) -> dict[str, Any]:
    """Calculates delta between two incident batches."""
    prev_map: dict[str, dict[str, Any]] = {}
    for t in previous_tickets:
        inc_id = extract_incident_id(t)
        if inc_id:
            prev_map[inc_id] = t

    cur_map: dict[str, dict[str, Any]] = {}
    for t in current_tickets:
        inc_id = extract_incident_id(t)
        if inc_id:
            cur_map[inc_id] = t

    tickets_nuevos: list[str] = []
    tickets_resueltos: list[str] = []
    tickets_reabiertos: list[str] = []

    for inc_id, cur_t in cur_map.items():
        cur_status = extract_incident_status(cur_t)
        is_cur_term = is_status_terminal(cur_status)

        if inc_id not in prev_map:
            tickets_nuevos.append(inc_id)
            continue

        prev_t = prev_map[inc_id]
        prev_status = extract_incident_status(prev_t)
        is_prev_term = is_status_terminal(prev_status)

        # Transición: Terminal -> Activo = Reapertura
        if is_prev_term and not is_cur_term:
            tickets_reabiertos.append(inc_id)
        # Transición: Activo -> Terminal = Resuelto en este lote
        elif not is_prev_term and is_cur_term:
            tickets_resueltos.append(inc_id)

    return {
        "fichero_anterior": previous_file_name,
        "total_actual": len(current_tickets),
        "total_anterior": len(previous_tickets),
        "conteo_nuevos": len(tickets_nuevos),
        "conteo_resueltos": len(tickets_resueltos),
        "conteo_reabiertos": len(tickets_reabiertos),
        "tickets_nuevos": tickets_nuevos,
        "tickets_resueltos": tickets_resueltos,
        "tickets_reabiertos": tickets_reabiertos,
    }


def mark_reopened_tickets(
    tickets: list[dict[str, Any]],
    reabiertos_ids: Optional[Set[str]] = None
) -> int:
    """Marks tickets in-place with 'es_reapertura': True.
    
    Detection triggers:
    1. ID is present in reabiertos_ids (from batch delta).
    2. Active ticket possesses an explicit 'Fecha de última resolución' or similar resolution timestamp.
    
    Returns count of reopened tickets detected.
    """
    reab_set = set(reabiertos_ids) if reabiertos_ids else set()
    count = 0

    for t in tickets:
        inc_id = extract_incident_id(t)
        status = extract_incident_status(t)
        is_terminal = is_status_terminal(status)

        is_reopen = False
        if inc_id and inc_id in reab_set:
            is_reopen = True
        elif not is_terminal:
            # Intrinsic detection: active ticket with previous resolution date
            res_date = (
                t.get("Fecha de última resolución")
                or t.get("fecha_ultima_resolucion")
                or t.get("fecha_resolucion")
                or t.get("Fecha de ultima resolucion")
            )
            if res_date and str(res_date).strip():
                is_reopen = True

        if is_reopen:
            t["es_reapertura"] = True
            count += 1

    return count

