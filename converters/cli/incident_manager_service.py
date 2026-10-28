#!/usr/bin/env python3
"""
Incident Manager Service (013-incident-manager-monitor)

Provee funciones de negocio para el Frontal de Monitorización del Incident Manager:
- Cálculo de KPIs y discriminación de incidencias pendientes de redacción de agente.
- Validación reactiva de límites de palabras (completo <= 90 monopárrafo, breve <= 30).
- Persistencia en data/agent_executive_messages.json y reevaluación del catálogo.
"""

import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from update_agent_message import (
        parse_agent_raw_output,
        resolve_default_paths,
        run_re_evaluation,
        update_agent_store,
    )
except ImportError:
    from converters.cli.update_agent_message import (
        parse_agent_raw_output,
        resolve_default_paths,
        run_re_evaluation,
        update_agent_store,
    )

logger = logging.getLogger("incident_manager_service")


def get_default_catalog_path() -> Path:
    """Obtiene la ruta a data/output/high_priority_notifications.json."""
    env_dir = os.environ.get("RELEASE_DASHBOARD_STORAGE_DIR", "").strip()
    if env_dir:
        storage = Path(env_dir)
    elif os.name != "nt" and Path("/infocodes/var/storage/release-dashboard").is_dir():
        storage = Path("/infocodes/var/storage/release-dashboard")
    else:
        storage = Path(__file__).resolve().parent.parent.parent / "data"

    return storage / "output" / "high_priority_notifications.json"


def get_default_store_path() -> Path:
    """Obtiene la ruta a data/agent_executive_messages.json."""
    store_path, _ = resolve_default_paths()
    return store_path


def get_pending_incidents_payload(
    catalog_path: Optional[Path] = None,
    store_path: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Carga el catálogo de alta prioridad y el almacén oficial para calcular
    KPIs y separar incidencias pendientes vs completadas.
    """
    if catalog_path is None:
        catalog_path = get_default_catalog_path()
    if store_path is None:
        store_path = get_default_store_path()

    catalog_data: Dict[str, Any] = {"incidents": [], "_metadata": {}}
    if catalog_path.exists():
        try:
            with open(catalog_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict):
                    catalog_data = loaded
        except Exception as e:
            logger.warning("Error leyendo catálogo %s: %e", catalog_path, e)

    store_data: Dict[str, Any] = {"incidents": {}, "_metadata": {}}
    if store_path.exists():
        try:
            with open(store_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict):
                    store_data = loaded
        except Exception as e:
            logger.warning("Error leyendo almacén %s: %e", store_path, e)

    # El catálogo oficial de notificaciones guarda la lista en 'data' (o fallback 'incidents')
    incidents = catalog_data.get("data") if "data" in catalog_data else catalog_data.get("incidents", [])
    if not isinstance(incidents, list):
        incidents = []
    store_incidents = store_data.get("incidents", {})

    pending_list: List[Dict[str, Any]] = []
    completed_list: List[Dict[str, Any]] = []
    all_active_list: List[Dict[str, Any]] = []

    p1_count = 0
    p2_count = 0
    discrepancies_count = 0

    for raw_inc in incidents:
        inc = dict(raw_inc)
        inc_id = inc.get("id", "")
        prio_sug = inc.get("prioridad_sugerida", "P2")

        if prio_sug == "P1":
            p1_count += 1
        elif prio_sug == "P2":
            p2_count += 1

        if inc.get("es_discrepancia"):
            discrepancies_count += 1

        # Comprobar si está pendiente de redacción de agente (alineado con scan_pending_incidents.py)
        mensajes = inc.get("mensajes_ejecutivos", {})
        apertura = mensajes.get("apertura", {}) if isinstance(mensajes, dict) else {}
        store_entry = store_incidents.get(inc_id, {}).get("apertura", {})
        in_store = inc_id in store_incidents and bool(store_entry.get("completo")) and store_entry.get("generado_por_agente") is not False

        is_pending = (
            apertura.get("estado") == "pendiente"
            or not bool(apertura.get("completo"))
            or not in_store
        )

        inc["is_pending"] = is_pending
        all_active_list.append(inc)

        if is_pending:
            pending_list.append(inc)
        else:
            completed_list.append(inc)

    metadata = catalog_data.get("_metadata", {})
    kpis = {
        "total_active": len(incidents),
        "completed_count": len(completed_list),
        "pending_count": len(pending_list),
        "p1_count": p1_count,
        "p2_count": p2_count,
        "discrepancies_count": discrepancies_count,
        "generated_at": metadata.get("generated_at", ""),
        "source_file": metadata.get("source_file", "")
    }

    return {
        "kpis": kpis,
        "pending_incidents": pending_list,
        "completed_incidents": completed_list,
        "all_active_incidents": all_active_list
    }


def validate_and_save_agent_message(
    incident_id: str,
    phase: str,
    completo: str,
    breve: str,
    origen: str = "incident-reporter",
    store_path: Optional[Path] = None,
    eval_script: Optional[Path] = None
) -> Tuple[int, Dict[str, Any]]:
    """
    Valida las restricciones de longitud y formato monopárrafo, persiste en
    el almacén oficial y reevalúa el catálogo.
    Devuelve (status_code, payload_dict).
    """
    incident_id = (incident_id or "").strip().upper()
    phase = (phase or "").strip().lower()

    if not incident_id:
        return 400, {"success": False, "error": "El campo 'incident_id' es requerido."}

    if phase not in ("apertura", "seguimiento", "cierre"):
        return 400, {
            "success": False,
            "error": f"Fase '{phase}' no válida. Debe ser 'apertura', 'seguimiento' o 'cierre'."
        }

    clean_comp = (completo or "").strip()
    clean_brev = (breve or "").strip()

    if not clean_comp:
        return 400, {"success": False, "error": "La 'versión completa' es requerida."}
    if not clean_brev:
        return 400, {"success": False, "error": "La 'versión breve' es requerida."}

    # Normalización monopárrafo estricta (sin saltos de línea internos)
    norm_comp = " ".join(clean_comp.split())
    norm_brev = " ".join(clean_brev.split())

    words_comp = len(norm_comp.split())
    words_brev = len(norm_brev.split())

    if words_comp > 90:
        return 400, {
            "success": False,
            "error": f"Límite de palabras excedido: versión completa tiene {words_comp} palabras (máximo 90 permitido)."
        }

    if words_brev > 30:
        return 400, {
            "success": False,
            "error": f"Límite de palabras excedido: versión breve tiene {words_brev} palabras (máximo 30 permitido)."
        }

    # Persistencia en almacén
    if store_path is None or eval_script is None:
        def_store, def_eval = resolve_default_paths()
        if store_path is None:
            store_path = def_store
        if eval_script is None:
            eval_script = def_eval

    try:
        entry = update_agent_store(
            store_path=store_path,
            incident_id=incident_id,
            phase=phase,
            completo=norm_comp,
            breve=norm_brev,
            origen=origen
        )
    except Exception as e:
        logger.error("Error al persistir en almacén oficial: %s", e)
        return 500, {
            "success": False,
            "error": f"Error al persistir en {store_path.name}: {e}"
        }

    # Reevaluación del catálogo
    reevaluated = False
    try:
        reevaluated = run_re_evaluation(eval_script)
    except Exception as e:
        logger.warning("Fallo al ejecutar reevaluación automática: %s", e)

    return 200, {
        "success": True,
        "incident_id": incident_id,
        "phase": phase,
        "entry": entry,
        "reevaluated": reevaluated,
        "message": "Mensaje oficial guardado y notificaciones actualizadas con éxito."
    }

