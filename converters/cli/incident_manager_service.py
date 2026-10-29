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


def parse_remedy_datetime_to_epoch_ms(date_str: Optional[str]) -> Optional[int]:
    """Parsea una cadena de fecha Remedy (DD/MM/YYYY HH:mm o ISO) a timestamp epoch ms UTC."""
    if not date_str or not isinstance(date_str, str):
        return None
    s = date_str.strip()
    if not s:
        return None
    try:
        from datetime import datetime, timezone
        if "T" in s or (len(s) >= 10 and s[4] == "-" and s[7] == "-"):
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
            return int(dt.timestamp() * 1000)
    except Exception:
        pass

    m = re.match(
        r"^(\d{1,2})/(\d{1,2})/(\d{4})\s+(\d{1,2}):(\d{2})(?::(\d{2}))?(?:\s*([ap])\.?m?\.?)?$",
        s,
        re.IGNORECASE,
    )
    if m:
        try:
            day = int(m.group(1))
            month = int(m.group(2))
            year = int(m.group(3))
            hours = int(m.group(4))
            minutes = int(m.group(5))
            seconds = int(m.group(6)) if m.group(6) else 0
            meridiem = m.group(7).lower() if m.group(7) else None

            if meridiem:
                if meridiem == "p" and hours < 12:
                    hours += 12
                elif meridiem == "a" and hours == 12:
                    hours = 0

            from datetime import datetime, timezone
            dt = datetime(year, month, day, hours, minutes, seconds, tzinfo=timezone.utc)
            return int(dt.timestamp() * 1000)
        except Exception:
            pass
    return None


def enrich_emergency_incident(
    raw_inc: Dict[str, Any],
    now_ms: Optional[int] = None,
    is_pending: Optional[bool] = None,
    is_redaction_pending: Optional[bool] = None,
) -> Dict[str, Any]:
    """Enriquece una incidencia con los objetos requeridos por la Consola de Emergencias Orange."""
    import time

    if now_ms is None:
        now_ms = int(time.time() * 1000)

    inc = dict(raw_inc)
    inc_id = inc.get("id", "")
    prio_sug = inc.get("prioridad_sugerida", "P2")
    severidad_calc = "SL1" if prio_sug == "P1" else "SL2"
    inc["severidad_calculada"] = severidad_calc

    evaluacion = inc.get("evaluacion", {}) if isinstance(inc.get("evaluacion"), dict) else {}
    fecha_apertura = inc.get("fecha_apertura") or evaluacion.get("fecha_apertura") or inc.get("fecha_envio") or ""
    inc["fecha_apertura"] = fecha_apertura

    epoch_ms = parse_remedy_datetime_to_epoch_ms(fecha_apertura)
    inc["apertura_epoch_ms"] = epoch_ms

    if epoch_ms is not None:
        mins_elapsed = max(0, int((now_ms - epoch_ms) / 60000))
    else:
        mins_elapsed = int(evaluacion.get("minutos_desde_apertura", 0))
    inc["minutos_desde_apertura"] = mins_elapsed

    # 1. Discrepancia
    es_disc = bool(inc.get("es_discrepancia"))
    prio_orig = inc.get("prioridad_original", "Media")
    proceso = evaluacion.get("proceso", "Sistemas Core")
    criterio = evaluacion.get("criterio", "Regla de Oro N1")
    justificacion = evaluacion.get("impacto_justificacion", "Afectación en proceso de negocio.")

    severidad_itil = "SL1 / P1 - Emergencia Crítica" if prio_sug == "P1" else "SL2 / P2 - Mayor"
    discrepancia_obj = {
        "es_discrepancia": es_disc,
        "prioridad_remedy": prio_orig,
        "severidad_itil": severidad_itil,
        "proceso_critico": proceso,
        "criterio_umbral": criterio,
        "justificacion": justificacion,
    }
    inc["discrepancia"] = discrepancia_obj
    inc["discrepancia_proceso"] = proceso
    inc["discrepancia_criterio"] = criterio

    # 2. Timeline
    sla_1a_vencido = mins_elapsed >= 20
    if mins_elapsed < 45:
        fase_esc = "NORMAL"
        estamento = "N1 / Guardias"
    elif mins_elapsed < 105:
        fase_esc = "ESCALADO_45M_REQUERIDO"
        estamento = "Resolutores N2/N3"
    else:
        fase_esc = "ESCALADO_SUPERIOR_REQUERIDO"
        estamento = "Estamentos Superiores vía IM-CSO"

    req_tel = prio_sug == "P1" or evaluacion.get("requiere_escalado_telefonico", False)
    esc_sup = fase_esc == "ESCALADO_SUPERIOR_REQUERIDO" or evaluacion.get("escalado_estamentos_superiores", False)

    timeline_obj = {
        "minutos_transcurridos": mins_elapsed,
        "sla_1a_notif_vencido": sla_1a_vencido,
        "fase_escalado": fase_esc,
        "requiere_canal_telefonico": req_tel,
        "estamento_convocado": estamento,
        "frecuencia_updates_min": 30 if prio_sug == "P1" else 60,
    }
    inc["timeline"] = timeline_obj
    inc["requiere_escalado_telefonico"] = req_tel
    inc["escalado_estamentos_superiores"] = esc_sup

    # 3. Workaround Governance
    raw_wa = str(evaluacion.get("workaround", "") or "").strip()
    wa_gob = str(evaluacion.get("workaround_gobernanza", "") or "").strip()

    wa_detected = False
    if raw_wa and raw_wa.lower() not in ("desconocido", "no", "no identificado", "ninguno", "false", "", "none"):
        wa_detected = True
    elif "workaround" in wa_gob.lower() and "sin" not in wa_gob.lower() and "no" not in wa_gob.lower():
        wa_detected = True

    cso_auth = False
    if "autorizado" in wa_gob.lower() and "pendiente" not in wa_gob.lower():
        cso_auth = True

    estatus = str(inc.get("estatus", "") or "").strip().lower()
    impacto_erradicado = estatus in ("cerrado", "resuelta", "resuelto")

    # Invariant: workaround_detectado && !impacto_erradicado => desescalada_bloqueada
    if wa_detected and not impacto_erradicado:
        desescalada_bloqueada = True
        motivo_bloqueo = "Workaround activo sin erradicación de impacto total (Regla de Oro CSO)"
    else:
        desescalada_bloqueada = False
        motivo_bloqueo = None

    if not wa_detected:
        estado_gob = "SIN_WORKAROUND"
    elif not cso_auth:
        estado_gob = "PENDIENTE_AUTORIZACION_CSO"
    elif not impacto_erradicado:
        estado_gob = "AUTORIZADO_CSO_IMPACTO_ACTIVO"
    else:
        estado_gob = "ERRADICADO_CIERRE_PERMITIDO"

    workaround_obj = {
        "workaround_detectado": wa_detected,
        "estado_gobernanza": estado_gob,
        "autorizado_cso": cso_auth,
        "impacto_erradicado": impacto_erradicado,
        "desescalada_bloqueada": desescalada_bloqueada,
        "motivo_bloqueo": motivo_bloqueo,
    }
    inc["workaround"] = workaround_obj

    # 4. Reporte de Emergencia
    if not inc.get("reporte_emergencia"):
        sistemas_str = ", ".join(inc.get("sistemas", [])) if isinstance(inc.get("sistemas"), list) else str(inc.get("sistemas", "Servicios Core"))
        reporte_lines = [
            "🚨 REPORTE DE EMERGENCIA IT - ORANGE TECH OPERATIONS",
            "────────────────────────────────────────────────────────────",
            "[1] CLASIFICACIÓN DEL TICKET",
            f"• Incidencia: {inc_id} ({severidad_itil})",
            f"• Proceso Crítico: {proceso}",
            f"• Umbral de Emergencia: {criterio}",
            f"• Alcance y Sistemas: {sistemas_str}",
            f"• Impacto: {evaluacion.get('impacto', 'Alto')} ({justificacion})",
            f"• Urgencia: {evaluacion.get('urgencia', 'Media')}",
            "",
            "[2] ESTADO DE COMUNICACIONES Y SLAS",
            f"• Tiempo desde Apertura: {mins_elapsed} min",
            f"• 1ª Notificación a Dirección: {'⚠️ SLA Vencido' if sla_1a_vencido else '✅ En SLA'}",
            f"• Frecuencia de Actualizaciones: Cada {timeline_obj['frecuencia_updates_min']} min",
            "• War Room / Teams: Liderado por Incident Manager (IM)",
            "",
            "[3] PLAN DE ACCIÓN Y GOBERNANZA DE WORKAROUNDS",
            f"• Diagnóstico Técnico: {inc.get('titulo', 'En curso')}",
            f"• Workaround: {raw_wa or 'No'} | Gobernanza: {estado_gob}",
            "• Regla de Oro: Prohibida la desescalada automática sin erradicación total del impacto",
            "",
            "[4] ESTADO DE ESCALADO TELEFÓNICO",
            f"• Protocolo de Tiempos: {fase_esc} ({mins_elapsed} min)",
            f"• Canal de Escalado: {'Vía Telefónica obligatoria (Regla de Oro)' if req_tel else 'Canal estándar'}",
            "• Gobernanza RACI: Incident Manager (R) / Customer & Service Ops IM-CSO (A)",
            "────────────────────────────────────────────────────────────",
        ]
        inc["reporte_emergencia"] = "\n".join(reporte_lines)

    if is_pending is not None:
        inc["is_pending"] = is_pending
    if is_redaction_pending is not None:
        inc["is_redaction_pending"] = is_redaction_pending

    return inc


def has_official_phase_message(
    inc: Dict[str, Any],
    phase: str,
    store_incidents: Optional[Dict[str, Any]] = None
) -> bool:
    """Comprueba si una incidencia tiene mensaje oficial válido para una fase dada."""
    inc_id = inc.get("id", "")
    mensajes = inc.get("mensajes_ejecutivos", {}) or {}
    msg_obj = mensajes.get(phase, {}) if isinstance(mensajes, dict) else {}

    if store_incidents and inc_id in store_incidents:
        st_phase = store_incidents.get(inc_id, {}).get(phase, {})
        if st_phase and isinstance(st_phase, dict) and st_phase.get("completo"):
            msg_obj = st_phase

    if phase == "apertura" and inc.get("is_redaction_pending"):
        return False

    if not isinstance(msg_obj, dict):
        return False

    completo = (msg_obj.get("completo") or "").strip()
    if not completo:
        return False
    if msg_obj.get("estado") == "pendiente":
        return False
    if msg_obj.get("generado_por_agente") is False:
        return False
    return True


def get_pending_incidents_payload(
    catalog_path: Optional[Path] = None,
    store_path: Optional[Path] = None,
    now_ms: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Carga el catálogo de alta prioridad y el almacén oficial para calcular
    KPIs y separar incidencias pendientes vs completadas, enriqueciendo cada
    registro con los metadatos de emergencia y cronometraje.
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
        inc_id = raw_inc.get("id", "")
        prio_sug = raw_inc.get("prioridad_sugerida", "P2")

        if prio_sug == "P1":
            p1_count += 1
        elif prio_sug == "P2":
            p2_count += 1

        if raw_inc.get("es_discrepancia"):
            discrepancies_count += 1

        # Comprobar si está pendiente de redacción de agente según catálogo y almacén
        catalog_mensajes = raw_inc.get("mensajes_ejecutivos", {}) or {}
        catalog_apertura = catalog_mensajes.get("apertura", {}) if isinstance(catalog_mensajes, dict) else {}
        store_entry = store_incidents.get(inc_id, {}).get("apertura", {})
        in_store = inc_id in store_incidents and bool(store_entry.get("completo")) and store_entry.get("generado_por_agente") is not False

        is_redaction_pending = (
            catalog_apertura.get("estado") == "pendiente"
            or not bool(catalog_apertura.get("completo"))
            or not in_store
        )

        # Enriquecer mensajes ejecutivos con los persistidos en el almacén oficial
        mensajes = dict(catalog_mensajes)
        store_inc = store_incidents.get(inc_id, {})
        for ph in ("apertura", "seguimiento", "cierre"):
            ph_store = store_inc.get(ph)
            if ph_store and isinstance(ph_store, dict) and ph_store.get("completo"):
                if ph == "apertura" and is_redaction_pending:
                    continue
                mensajes[ph] = ph_store
        raw_inc["mensajes_ejecutivos"] = mensajes

        # Enriquecer con objetos de consola de emergencias
        inc = enrich_emergency_incident(raw_inc, now_ms=now_ms)
        mins_elapsed = inc.get("minutos_desde_apertura", 0)
        es_disc = bool(inc.get("es_discrepancia") or inc.get("discrepancia", {}).get("es_discrepancia"))

        # Nueva visión de Pendientes:
        # Requiere redacción oficial inmediata (SL1/P2), escalado telefónico (>45 min) o revisión de discrepancias
        is_pending = bool(
            is_redaction_pending
            or mins_elapsed >= 45
            or es_disc
        )

        inc["is_redaction_pending"] = is_redaction_pending
        inc["is_pending"] = is_pending
        all_active_list.append(inc)

        if is_pending:
            pending_list.append(inc)
        else:
            completed_list.append(inc)

    metadata = catalog_data.get("_metadata", {})
    disc_sl1 = sum(1 for i in all_active_list if i.get("es_discrepancia") and i.get("severidad_calculada") == "SL1")
    disc_sl2 = sum(1 for i in all_active_list if i.get("es_discrepancia") and i.get("severidad_calculada") == "SL2")
    esc_alerts = sum(1 for i in all_active_list if i.get("minutos_desde_apertura", 0) >= 45)
    wa_pending_cso = sum(
        1 for i in all_active_list
        if i.get("workaround", {}).get("workaround_detectado") and not i.get("workaround", {}).get("autorizado_cso")
    )

    kpis = {
        "total_active": len(incidents),
        "completed_count": len(completed_list),
        "pending_count": len(pending_list),
        "redactions_pending_count": sum(1 for i in all_active_list if i.get("is_redaction_pending")),
        "p1_count": p1_count,
        "p2_count": p2_count,
        "discrepancies_count": discrepancies_count,
        "discrepancies_sl1": disc_sl1,
        "discrepancies_sl2": disc_sl2,
        "escalation_alerts_count": esc_alerts,
        "workarounds_pending_cso_count": wa_pending_cso,
        "generated_at": metadata.get("generated_at", ""),
        "source_file": metadata.get("source_file", ""),
    }

    return {
        "kpis": kpis,
        "pending_incidents": pending_list,
        "completed_incidents": completed_list,
        "all_active_incidents": all_active_list,
    }


def get_emergency_cockpit_payload(
    catalog_path: Optional[Path] = None,
    store_path: Optional[Path] = None,
    only_pending: bool = False,
    severity: str = "all",
    comm_phase: str = "all",
    now_ms: Optional[int] = None,
) -> Dict[str, Any]:
    """Genera la telemetría consolidada para GET /api/incident-manager/emergency-cockpit."""
    from datetime import datetime, timezone
    import time

    if catalog_path is None:
        catalog_path = get_default_catalog_path()
    if store_path is None:
        store_path = get_default_store_path()
    if now_ms is None:
        now_ms = int(time.time() * 1000)

    base_payload = get_pending_incidents_payload(
        catalog_path=catalog_path, store_path=store_path, now_ms=now_ms
    )
    all_active = base_payload.get("all_active_incidents", [])

    filtered_incidents = []
    sl1_count = 0
    sl2_count = 0
    disc_count = 0
    esc_45m_count = 0
    esc_sup_count = 0
    wa_pending_cso_count = 0
    redac_pending_count = 0

    for inc in all_active:
        sev = inc.get("severidad_calculada", "SL2")
        mins = inc.get("minutos_desde_apertura", 0)
        wa = inc.get("workaround", {})
        is_pend = inc.get("is_pending", False)

        if sev == "SL1":
            sl1_count += 1
        elif sev == "SL2":
            sl2_count += 1

        if inc.get("es_discrepancia"):
            disc_count += 1

        if mins >= 45:
            esc_45m_count += 1
        if mins >= 105:
            esc_sup_count += 1

        if wa.get("workaround_detectado") and not wa.get("autorizado_cso"):
            wa_pending_cso_count += 1

        is_redac_pend = inc.get("is_redaction_pending", False)

        if is_redac_pend:
            redac_pending_count += 1

        # Filtros de query
        if only_pending and not is_pend:
            continue
        if severity.upper() in ("SL1", "P1") and sev != "SL1":
            continue
        if severity.upper() in ("SL2", "P2") and sev != "SL2":
            continue

        # Filtro por Comunicación Oficial (Apertura / Seguimiento / Cierre)
        if comm_phase and comm_phase != "all":
            has_ap = has_official_phase_message(inc, "apertura")
            has_seg = has_official_phase_message(inc, "seguimiento")
            has_cie = has_official_phase_message(inc, "cierre")

            if comm_phase == "missing_any" and (has_ap and has_seg and has_cie):
                continue
            if comm_phase == "missing_apertura" and has_ap:
                continue
            if comm_phase == "missing_seguimiento" and has_seg:
                continue
            if comm_phase == "missing_cierre" and has_cie:
                continue
            if comm_phase == "missing_all" and (has_ap or has_seg or has_cie):
                continue
            if comm_phase == "has_apertura" and not has_ap:
                continue
            if comm_phase == "has_seguimiento" and not has_seg:
                continue
            if comm_phase == "has_cierre" and not has_cie:
                continue
            if comm_phase == "all_completed" and (not has_ap or not has_seg or not has_cie):
                continue

        filtered_incidents.append(inc)

    metadata = base_payload.get("kpis", {})
    return {
        "_metadata": {
            "version": "1.0.0",
            "generated_at": metadata.get("generated_at", ""),
            "server_time": datetime.now(timezone.utc).isoformat(),
            "source_file": metadata.get("source_file", ""),
        },
        "kpis": {
            "total_activas": len(all_active),
            "sl1_criticas": sl1_count,
            "sl2_altas": sl2_count,
            "discrepancias_subescalacion": disc_count,
            "alertas_escalado_45m": esc_45m_count,
            "alertas_escalado_superior": esc_sup_count,
            "workarounds_pendientes_cso": wa_pending_cso_count,
            "redacciones_pendientes": redac_pending_count,
            "pendientes_por_tratar": sum(1 for i in all_active if i.get("is_pending")),
        },
        "incidents": filtered_incidents,
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

