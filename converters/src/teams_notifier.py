#!/usr/bin/env python3
"""Teams Notifier Module for Orange Tech Operations.

Handles:
- Configuration management for Microsoft Teams channels and action-based routing.
- Modern Adaptive Cards (v1.4) tailored for Power Automate Workflows.
- Legacy MessageCard fallbacks.
- Webhook dispatch with audit trail.
"""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import urllib.error
import urllib.request


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_FILE_PATH = PROJECT_ROOT / "data" / "teams_channels_config.json"
AUDIT_LOG_PATH = PROJECT_ROOT / "data" / "output" / "teams_delivery_audit.json"
DEFAULT_REMEDY_URL = (
    "https://epsilon-itsm.si.orange.es/arsys/forms/ars_front_f5.si.orange.es/"
    "SHR:LandingConsole/Default+Administrator+View/?cacheid=e870b03e"
)


def get_default_config() -> Dict[str, Any]:
    """Returns baseline Teams channels configuration."""
    return {
        "_version": "1.0",
        "descripcion": "Configuración de canales y enrutamiento de notificaciones operativas a Microsoft Teams (Orange Tech Operations)",
        "remedy_base_url": DEFAULT_REMEDY_URL,
        "canales": {
            "masivas_it": {
                "id": "masivas_it",
                "nombre": "Masivas IT",
                "descripcion": "Chat/Canal oficial de Masivas IT para seguimiento operativo y alertas",
                "tipo": "power_automate_workflow",
                "webhook_url": "https://defaultc10a36d829814b7b9b892ef5936549.3a.environment.api.powerplatform.com:443/powerautomate/automations/direct/cu/05/workflows/251b155948b445fb872eeb5ed34d1fa9/triggers/manual/paths/invoke?api-version=1&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=SsB01Uv2lgQf4-cucTfHGW_ciVlZD9f09M7VNM2_4gY",
                "activo": True,
                "creado_el": "2026-11-12T12:50:00Z",
                "actualizado_el": "2026-11-12T13:00:00Z"
            },
            "warroom_sl1": {
                "id": "warroom_sl1",
                "nombre": "War Room ITIL SL1/P1",
                "descripcion": "Canal de crisis y coordinación de emergencias de criticidad máxima (SL1)",
                "tipo": "power_automate_workflow",
                "webhook_url": "",
                "activo": False,
                "creado_el": "2026-11-12T13:00:00Z",
                "actualizado_el": "2026-11-12T13:00:00Z"
            },
            "notificaciones_direccion": {
                "id": "notificaciones_direccion",
                "nombre": "Notificaciones Dirección IT",
                "descripcion": "Canal de avisos ejecutivos a Dirección de Operaciones",
                "tipo": "power_automate_workflow",
                "webhook_url": "",
                "activo": False,
                "creado_el": "2026-11-12T13:00:00Z",
                "actualizado_el": "2026-11-12T13:00:00Z"
            }
        },
        "rutas_acciones": {
            "reclamacion_worklog": {
                "descripcion": "Reclamación formal de apunte técnico en Work Log de BMC Remedy",
                "canal_predeterminado": "masivas_it",
                "mapeo_por_grupo": {
                    "DES_DJINGO": "masivas_it",
                    "RED FIBRA": "masivas_it"
                }
            },
            "notificacion_direccion": {
                "descripcion": "Comunicaciones ejecutivas de incidentes para Dirección",
                "canal_predeterminado": "masivas_it",
                "mapeo_por_grupo": {}
            },
            "convocatoria_warroom": {
                "descripcion": "Apertura y convocatoria de War Room para incidencias SL1 / P1",
                "canal_predeterminado": "masivas_it",
                "mapeo_por_grupo": {}
            },
            "cierre_zombi": {
                "descripcion": "Solicitud formal de cierre administrativo para tickets zombi",
                "canal_predeterminado": "masivas_it",
                "mapeo_por_grupo": {}
            },
            "traspaso_guardia": {
                "descripcion": "Informe ejecutivo de relevo / traspaso de guardia ITIL",
                "canal_predeterminado": "masivas_it",
                "mapeo_por_grupo": {}
            }
        }
    }


def load_teams_config(path: Optional[Path] = None) -> Dict[str, Any]:
    """Loads configuration from JSON file or returns baseline default."""
    target_path = path or CONFIG_FILE_PATH
    if target_path.is_file():
        try:
            with open(target_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict) and "canales" in data and "rutas_acciones" in data:
                    return data
        except Exception as err:
            print(f"[WARN] Error cargando {target_path}: {err}. Usando configuración por defecto.")
    return get_default_config()


def save_teams_config(config: Dict[str, Any], path: Optional[Path] = None) -> bool:
    """Saves configuration to JSON file."""
    target_path = path or CONFIG_FILE_PATH
    target_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    except Exception as err:
        print(f"[ERROR] No se pudo guardar configuración en {target_path}: {err}")
        return False


def resolve_channel(
    config: Dict[str, Any],
    action: Optional[str] = None,
    group: Optional[str] = None,
    channel_id: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Resolves target channel based on explicit ID or action + resolver group."""
    channels = config.get("canales", {})

    # 1. Si se especifica un canal directamente
    if channel_id:
        target = channels.get(channel_id)
        if not target or not target.get("activo", True):
            return None
        return target

    # 2. Si se especifica una acción
    if action:
        routes = config.get("rutas_acciones", {}).get(action, {})
        # Comprobar override específico por grupo resolutor
        if group:
            norm_group = group.strip()
            group_map = routes.get("mapeo_por_grupo", {})
            for g_key, c_id in group_map.items():
                if g_key.lower() == norm_group.lower() or g_key in norm_group:
                    target = channels.get(c_id)
                    if target and target.get("activo", True) and target.get("webhook_url"):
                        return target

        # Canal predeterminado para la acción
        def_channel_id = routes.get("canal_predeterminado")
        if def_channel_id and def_channel_id in channels:
            target = channels[def_channel_id]
            if target.get("activo", True):
                return target

    # 3. Fallback al primer canal activo con webhook configurado
    for ch in channels.values():
        if ch.get("activo") and ch.get("webhook_url"):
            return ch

    return None


def build_worklog_claim_card(incident: Dict[str, Any], remedy_url: Optional[str] = None) -> Dict[str, Any]:
    """Builds Adaptive Card v1.4 for Work Log claim notification."""
    inc_id = incident.get("id", "INC000000000000")
    prio = incident.get("prioridad_sugerida") or incident.get("prioridad_nominal") or "P2"
    wl_status = incident.get("worklog_status") or {}
    guia = incident.get("guia_operador") or {}
    horas_wl = wl_status.get("horas_sin_worklog", 0)
    nivel = wl_status.get("nivel_inactividad", "WL_ALERTA_6H")
    grupo = incident.get("grupo_asignado") or wl_status.get("ultimo_grupo") or "Grupo Resolutor"
    titulo = incident.get("titulo") or "Incidencia de Servicio"

    if nivel == "WL_BLOQUEO_24H":
        header_color = "Attention"
        container_style = "attention"
        badge_icon = "🚨"
        nivel_label = f"BLOQUEO CRÍTICO (>24h sin notas: {horas_wl}h)"
    elif nivel == "WL_ESTANCAMIENTO_12H":
        header_color = "Warning"
        container_style = "warning"
        badge_icon = "⏳"
        nivel_label = f"ESTANCAMIENTO (>12h sin notas: {horas_wl}h)"
    else:
        header_color = "Accent"
        container_style = "emphasis"
        badge_icon = "⚠️"
        nivel_label = f"ALERTA SEGUIMIENTO (>6h sin notas: {horas_wl}h)"

    claim_body = guia.get("plantilla_reclamacion_wl") or (
        f"Se constata que la incidencia {inc_id} asignada a {grupo} no registra notas técnicas "
        f"desde hace {horas_wl}h. Se requiere actualización inmediata en BMC Remedy."
    )

    url = remedy_url or DEFAULT_REMEDY_URL

    return {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "contentUrl": None,
                "content": {
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "type": "AdaptiveCard",
                    "version": "1.4",
                    "msteams": {"width": "Full"},
                    "body": [
                        {
                            "type": "Container",
                            "style": container_style,
                            "bleed": True,
                            "items": [
                                {
                                    "type": "TextBlock",
                                    "text": f"{badge_icon} RECLAMACIÓN DE WORK LOG · ORANGE TECH OPERATIONS",
                                    "weight": "Bolder",
                                    "size": "Medium",
                                    "color": header_color,
                                    "wrap": True
                                },
                                {
                                    "type": "TextBlock",
                                    "text": f"**{inc_id}** ({prio}) · {grupo}",
                                    "size": "Small",
                                    "isSubtle": True,
                                    "spacing": "None"
                                }
                            ]
                        },
                        {
                            "type": "TextBlock",
                            "text": f"**Título:** {titulo}",
                            "wrap": True,
                            "spacing": "Medium"
                        },
                        {
                            "type": "FactSet",
                            "spacing": "Medium",
                            "facts": [
                                {"title": "Incidencia:", "value": inc_id},
                                {"title": "Prioridad ITIL:", "value": prio},
                                {"title": "Grupo Asignado:", "value": grupo},
                                {"title": "Estado Work Log:", "value": nivel_label},
                                {"title": "Horas sin Notas:", "value": f"{horas_wl}h"}
                            ]
                        },
                        {
                            "type": "Container",
                            "style": "emphasis",
                            "items": [
                                {
                                    "type": "TextBlock",
                                    "text": "📝 **Requerimiento Operativo Formal:**",
                                    "weight": "Bolder",
                                    "size": "Small"
                                },
                                {
                                    "type": "TextBlock",
                                    "text": claim_body,
                                    "wrap": True,
                                    "size": "Small"
                                }
                            ]
                        }
                    ],
                    "actions": [
                        {
                            "type": "Action.OpenUrl",
                            "title": "🔗 Abrir Incidencia en BMC Remedy",
                            "url": url
                        }
                    ]
                }
            }
        ]
    }


def generate_default_warroom_url(inc_id: str) -> str:
    """Generates standard Microsoft Teams War Room meeting URL for the incident."""
    clean_id = "".join(c.lower() for c in str(inc_id) if c.isalnum())
    return (
        f"https://teams.microsoft.com/l/meetup-join/19%3ameeting_{clean_id}_orange_warroom%40thread.v2/0"
        f"?context=%7b%22Tid%22%3a%22orange-spain-tenant%22%2c%22Oid%22%3a%22im-cso-coordinator%22%7d"
    )


def build_executive_notification_card(
    incident: Dict[str, Any],
    remedy_url: Optional[str] = None,
    executive_text: Optional[str] = None
) -> Dict[str, Any]:
    """Builds Adaptive Card v1.4 for Executive Communications to Management (Dirección IT)."""
    inc_id = incident.get("id", "INC000000000000")
    prio_sug = incident.get("prioridad_sugerida") or "P2"
    prio_nom = incident.get("prioridad_original") or incident.get("prioridad_nominal") or prio_sug
    estatus = incident.get("estatus") or "En Gestión"
    grupo = incident.get("grupo_asignado") or "Grupo Resolutor"
    titulo = incident.get("titulo") or "Incidencia de Servicio"
    evaluacion = incident.get("evaluacion") or {}
    proceso = evaluacion.get("proceso_negocio") or evaluacion.get("proceso") or "Servicios IT Core"
    minutos = evaluacion.get("minutos_desde_apertura")
    horas_str = f"{round(minutos / 60, 1)}h" if minutos is not None else "En seguimiento"

    resumen_ia = incident.get("resumen_ia") or {}
    guia = incident.get("guia_operador") or {}

    mensajes_ej = incident.get("mensajes_ejecutivos") or {}
    oficial_txt = None
    for ph in ("apertura", "seguimiento", "cierre"):
        fase_obj = mensajes_ej.get(ph)
        if isinstance(fase_obj, dict) and fase_obj.get("completo"):
            oficial_txt = fase_obj.get("completo")
            break

    resumen_txt = (
        executive_text
        or oficial_txt
        or incident.get("mensaje_ejecutivo")
        or resumen_ia.get("problema")
        or guia.get("accion_recomendada")
        or titulo
    )

    impacto_txt = (
        resumen_ia.get("impacto")
        or evaluacion.get("impacto_justificacion")
        or "Impacto en evaluación técnica por parte del grupo especialista."
    )

    plan_txt = (
        guia.get("accion_recomendada")
        or resumen_ia.get("solucion_recomendada")
        or "Diagnóstico en curso con escalado al grupo resolutor designado."
    )

    prio_label = prio_sug if prio_sug == prio_nom else f"{prio_sug} (Nominal: {prio_nom})"
    url = remedy_url or DEFAULT_REMEDY_URL

    facts = [
        {"title": "Incidencia:", "value": inc_id},
        {"title": "Prioridad:", "value": prio_label},
        {"title": "Estado:", "value": estatus},
        {"title": "Proceso Crítico:", "value": proceso},
        {"title": "Grupo Asignado:", "value": grupo},
        {"title": "Tiempo Activo:", "value": horas_str}
    ]

    return {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "contentUrl": None,
                "content": {
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "type": "AdaptiveCard",
                    "version": "1.4",
                    "msteams": {"width": "Full"},
                    "body": [
                        {
                            "type": "Container",
                            "style": "emphasis",
                            "bleed": True,
                            "items": [
                                {
                                    "type": "TextBlock",
                                    "text": "📢 COMUNICACIÓN EJECUTIVA · DIRECCIÓN IT",
                                    "weight": "Bolder",
                                    "size": "Medium",
                                    "color": "Accent",
                                    "wrap": True
                                },
                                {
                                    "type": "TextBlock",
                                    "text": f"**{inc_id}** · Prioridad {prio_sug} · {proceso}",
                                    "size": "Small",
                                    "isSubtle": True,
                                    "spacing": "None"
                                }
                            ]
                        },
                        {
                            "type": "TextBlock",
                            "text": f"**Título:** {titulo}",
                            "wrap": True,
                            "spacing": "Medium"
                        },
                        {
                            "type": "FactSet",
                            "spacing": "Medium",
                            "facts": facts
                        },
                        {
                            "type": "Container",
                            "style": "default",
                            "items": [
                                {
                                    "type": "TextBlock",
                                    "text": "📢 **Comunicado Oficial Dirección IT (≤ 90 palabras):**",
                                    "weight": "Bolder",
                                    "size": "Small",
                                    "color": "Accent"
                                },
                                {
                                    "type": "TextBlock",
                                    "text": resumen_txt,
                                    "wrap": True,
                                    "size": "Small"
                                }
                            ]
                        },
                        {
                            "type": "Container",
                            "style": "emphasis",
                            "items": [
                                {
                                    "type": "TextBlock",
                                    "text": "🎯 **Afectación y Riesgo Operativo:**",
                                    "weight": "Bolder",
                                    "size": "Small"
                                },
                                {
                                    "type": "TextBlock",
                                    "text": impacto_txt,
                                    "wrap": True,
                                    "size": "Small"
                                }
                            ]
                        },
                        {
                            "type": "Container",
                            "style": "default",
                            "items": [
                                {
                                    "type": "TextBlock",
                                    "text": "⚡ **Plan de Acción Inmediato:**",
                                    "weight": "Bolder",
                                    "size": "Small"
                                },
                                {
                                    "type": "TextBlock",
                                    "text": plan_txt,
                                    "wrap": True,
                                    "size": "Small"
                                }
                            ]
                        }
                    ],
                    "actions": [
                        {
                            "type": "Action.OpenUrl",
                            "title": "🔗 Abrir Incidencia en BMC Remedy",
                            "url": url
                        }
                    ]
                }
            }
        ]
    }


def build_warroom_card(
    incident: Dict[str, Any],
    remedy_url: Optional[str] = None,
    teams_meeting_url: Optional[str] = None
) -> Dict[str, Any]:
    """Builds Adaptive Card v1.4 for Urgent War Room Session Call (SL1/P1 Emergencies)."""
    inc_id = incident.get("id", "INC000000000000")
    titulo = incident.get("titulo") or "Incidencia Crítica de Negocio"
    grupo = incident.get("grupo_asignado") or "Grupo Especialista"
    evaluacion = incident.get("evaluacion") or {}
    proceso = evaluacion.get("proceso_negocio") or evaluacion.get("proceso") or "Procesos Críticos de Negocio"
    sistemas = incident.get("sistemas")
    sistemas_str = ", ".join(sistemas) if isinstance(sistemas, list) else (str(sistemas) if sistemas else "Core IT")
    minutos = evaluacion.get("minutos_desde_apertura")
    horas_str = f"{round(minutos / 60, 1)}h ({minutos} min)" if minutos is not None else "En curso"

    resumen_ia = incident.get("resumen_ia") or {}
    sintoma = resumen_ia.get("problema") or evaluacion.get("urgencia_justificacion") or titulo

    remedy = remedy_url or DEFAULT_REMEDY_URL
    meet_url = teams_meeting_url or generate_default_warroom_url(inc_id)

    return {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "contentUrl": None,
                "content": {
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "type": "AdaptiveCard",
                    "version": "1.4",
                    "msteams": {"width": "Full"},
                    "body": [
                        {
                            "type": "Container",
                            "style": "attention",
                            "bleed": True,
                            "items": [
                                {
                                    "type": "TextBlock",
                                    "text": "🔥 CONVOCATORIA WAR ROOM ITIL · CRITICIDAD SL1 / P1",
                                    "weight": "Bolder",
                                    "size": "Medium",
                                    "color": "Attention",
                                    "wrap": True
                                },
                                {
                                    "type": "TextBlock",
                                    "text": f"**EMERGENCIA EN CURSO** · {inc_id} · {grupo}",
                                    "size": "Small",
                                    "isSubtle": True,
                                    "spacing": "None"
                                }
                            ]
                        },
                        {
                            "type": "TextBlock",
                            "text": f"**Título:** {titulo}",
                            "wrap": True,
                            "spacing": "Medium"
                        },
                        {
                            "type": "Container",
                            "style": "warning",
                            "items": [
                                {
                                    "type": "TextBlock",
                                    "text": "🚨 **CONVOCATORIA OBLIGATORIA:** Se requiere la incorporación inmediata a la sesión del grupo resolutor N2/N3, líder técnico y coordinador IM-CSO.",
                                    "wrap": True,
                                    "size": "Small"
                                }
                            ]
                        },
                        {
                            "type": "FactSet",
                            "spacing": "Medium",
                            "facts": [
                                {"title": "Incidencia:", "value": inc_id},
                                {"title": "Severidad ITIL:", "value": "SL1 / P1 (Máxima Criticidad)"},
                                {"title": "Proceso Afectado:", "value": proceso},
                                {"title": "Sistemas Impactados:", "value": sistemas_str},
                                {"title": "Grupo Asignado:", "value": grupo},
                                {"title": "Tiempo Activo:", "value": horas_str},
                                {"title": "Coordinación:", "value": "IM-CSO / Puente Operativo"}
                            ]
                        },
                        {
                            "type": "Container",
                            "style": "emphasis",
                            "items": [
                                {
                                    "type": "TextBlock",
                                    "text": "💥 **Afectación y Síntoma Crítico:**",
                                    "weight": "Bolder",
                                    "size": "Small"
                                },
                                {
                                    "type": "TextBlock",
                                    "text": sintoma,
                                    "wrap": True,
                                    "size": "Small"
                                }
                            ]
                        }
                    ],
                    "actions": [
                        {
                            "type": "Action.OpenUrl",
                            "title": "📞 Unirse a Sesión War Room (Teams)",
                            "url": meet_url
                        },
                        {
                            "type": "Action.OpenUrl",
                            "title": "🔗 Abrir Incidencia en BMC Remedy",
                            "url": remedy
                        }
                    ]
                }
            }
        ]
    }


def build_zombie_closure_card(
    incident: Dict[str, Any],
    remedy_url: Optional[str] = None
) -> Dict[str, Any]:
    """Builds Adaptive Card v1.4 for Zombie Ticket Administrative Closure Claim."""
    inc_id = incident.get("id", "INC000000000000")
    titulo = incident.get("titulo") or "Ticket Estancado sin Actividad"
    estatus = incident.get("estatus") or "Asignado"
    grupo = incident.get("grupo_asignado") or "Grupo Resolutor"
    detalle_zombi = incident.get("detalle_zombi") or (
        "El ticket no presenta impacto operativo activo o las actuaciones técnicas concluyeron "
        "sin que se formalizara el cambio de estado administrativo a 'Resuelto' en BMC Remedy."
    )
    guia = incident.get("guia_operador") or {}
    accion = guia.get("accion_recomendada") or (
        "Se solicita formalmente al grupo resolutor proceder con la resolución o cierre administrativo "
        "en BMC Remedy para regularizar el ciclo de vida del ticket."
    )

    url = remedy_url or DEFAULT_REMEDY_URL

    return {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "contentUrl": None,
                "content": {
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "type": "AdaptiveCard",
                    "version": "1.4",
                    "msteams": {"width": "Full"},
                    "body": [
                        {
                            "type": "Container",
                            "style": "warning",
                            "bleed": True,
                            "items": [
                                {
                                    "type": "TextBlock",
                                    "text": "🧟 SOLICITUD DE CIERRE ADMINISTRATIVO · TICKET ZOMBI",
                                    "weight": "Bolder",
                                    "size": "Medium",
                                    "color": "Warning",
                                    "wrap": True
                                },
                                {
                                    "type": "TextBlock",
                                    "text": f"**{inc_id}** · {grupo} · Auditoría de Ciclo de Vida ITIL",
                                    "size": "Small",
                                    "isSubtle": True,
                                    "spacing": "None"
                                }
                            ]
                        },
                        {
                            "type": "TextBlock",
                            "text": f"**Título:** {titulo}",
                            "wrap": True,
                            "spacing": "Medium"
                        },
                        {
                            "type": "FactSet",
                            "spacing": "Medium",
                            "facts": [
                                {"title": "Incidencia:", "value": inc_id},
                                {"title": "Estado Actual:", "value": estatus},
                                {"title": "Grupo Asignado:", "value": grupo},
                                {"title": "Diagnóstico:", "value": "Ticket sin impacto activo / Cierre pendiente"}
                            ]
                        },
                        {
                            "type": "Container",
                            "style": "emphasis",
                            "items": [
                                {
                                    "type": "TextBlock",
                                    "text": "📋 **Dictamen de Auditoría de Mesa:**",
                                    "weight": "Bolder",
                                    "size": "Small"
                                },
                                {
                                    "type": "TextBlock",
                                    "text": detalle_zombi,
                                    "wrap": True,
                                    "size": "Small"
                                }
                            ]
                        },
                        {
                            "type": "Container",
                            "style": "default",
                            "items": [
                                {
                                    "type": "TextBlock",
                                    "text": "📝 **Requerimiento Operativo Formal:**",
                                    "weight": "Bolder",
                                    "size": "Small"
                                },
                                {
                                    "type": "TextBlock",
                                    "text": accion,
                                    "wrap": True,
                                    "size": "Small"
                                }
                            ]
                        }
                    ],
                    "actions": [
                        {
                            "type": "Action.OpenUrl",
                            "title": "🔗 Regularizar en BMC Remedy",
                            "url": url
                        }
                    ]
                }
            }
        ]
    }


def build_shift_handover_card(
    report_text: str,
    meta_summary: Optional[str] = None,
    remedy_url: Optional[str] = None
) -> Dict[str, Any]:
    """Builds Adaptive Card v1.4 for Shift Handover (Relevo de Guardia) Report."""
    url = remedy_url or DEFAULT_REMEDY_URL
    summary = meta_summary or "Compilación de estado en tiempo real para relevo de turno"
    raw_text = (report_text or "").strip()
    # Microsoft Teams adaptive card text blocks have practical limits
    clean_text = raw_text[:3800] + "\n\n*(Informe truncado para Teams; consultar consola web para versión completa)*" if len(raw_text) > 3800 else raw_text

    return {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "contentUrl": None,
                "content": {
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "type": "AdaptiveCard",
                    "version": "1.4",
                    "msteams": {"width": "Full"},
                    "body": [
                        {
                            "type": "Container",
                            "style": "accent",
                            "bleed": True,
                            "items": [
                                {
                                    "type": "TextBlock",
                                    "text": "📋 RELEVO / TRASPASO DE GUARDIA ITIL",
                                    "weight": "Bolder",
                                    "size": "Medium",
                                    "color": "Accent",
                                    "wrap": True
                                },
                                {
                                    "type": "TextBlock",
                                    "text": f"Orange Tech Operations · {summary}",
                                    "size": "Small",
                                    "isSubtle": True,
                                    "spacing": "None"
                                }
                            ]
                        },
                        {
                            "type": "TextBlock",
                            "text": clean_text or "No se incluyeron notas adicionales en el informe de relevo.",
                            "wrap": True,
                            "spacing": "Medium"
                        }
                    ],
                    "actions": [
                        {
                            "type": "Action.OpenUrl",
                            "title": "🖥️ Abrir Consola de Triaje IT",
                            "url": url
                        }
                    ]
                }
            }
        ]
    }


def send_to_teams(webhook_url: str, payload: Dict[str, Any], timeout: int = 15) -> Tuple[bool, int, str]:
    """Posts payload to Microsoft Teams webhook."""
    if not webhook_url:
        return False, 0, "URL de Webhook vacía o no configurada"

    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        webhook_url,
        data=data,
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "Orange-IT-Triage-Console/2.0"
        },
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = resp.status
            body = resp.read().decode("utf-8", errors="replace")
            return (200 <= status < 300), status, body
    except urllib.error.HTTPError as http_err:
        body = http_err.read().decode("utf-8", errors="replace")
        return False, http_err.code, body
    except Exception as err:
        return False, 0, str(err)


def record_audit_entry(entry: Dict[str, Any]) -> None:
    """Appends delivery record to the audit log."""
    try:
        AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        items: List[Dict[str, Any]] = []
        if AUDIT_LOG_PATH.is_file():
            try:
                with open(AUDIT_LOG_PATH, "r", encoding="utf-8") as f:
                    items = json.load(f)
                    if not isinstance(items, list):
                        items = []
            except Exception:
                items = []

        items.append(entry)
        # Mantener últimos 500 envíos
        if len(items) > 500:
            items = items[-500:]

        with open(AUDIT_LOG_PATH, "w", encoding="utf-8") as f:
            json.dump(items, f, indent=2, ensure_ascii=False)
    except Exception as err:
        print(f"[WARN] No se pudo guardar entrada de auditoría Teams: {err}")


def dispatch_teams_notification(
    action: str,
    incident: Dict[str, Any],
    group: Optional[str] = None,
    channel_id: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None,
    teams_meeting_url: Optional[str] = None,
    executive_text: Optional[str] = None
) -> Dict[str, Any]:
    """Resolves channel, creates card payload, dispatches to Teams, and records audit."""
    cfg = config or load_teams_config()
    target_channel = resolve_channel(
        cfg,
        action=action,
        group=group or incident.get("grupo_asignado"),
        channel_id=channel_id
    )

    if not target_channel:
        return {
            "success": False,
            "status_code": 0,
            "error": f"No hay un canal configurado o activo para la acción '{action}'.",
            "channel": None
        }

    url = target_channel.get("webhook_url", "").strip()
    if not url:
        return {
            "success": False,
            "status_code": 0,
            "error": f"El canal '{target_channel.get('nombre')}' no tiene webhook URL configurada.",
            "channel": target_channel.get("nombre")
        }

    remedy_url = cfg.get("remedy_base_url") or DEFAULT_REMEDY_URL

    if action == "reclamacion_worklog":
        payload = build_worklog_claim_card(incident, remedy_url=remedy_url)
    elif action == "notificacion_direccion":
        payload = build_executive_notification_card(incident, remedy_url=remedy_url, executive_text=executive_text)
    elif action == "convocatoria_warroom":
        payload = build_warroom_card(incident, remedy_url=remedy_url, teams_meeting_url=teams_meeting_url)
    elif action == "cierre_zombi":
        payload = build_zombie_closure_card(incident, remedy_url=remedy_url)
    elif action == "traspaso_guardia":
        payload = build_shift_handover_card(
            report_text=incident.get("report_text") or executive_text or "",
            meta_summary=incident.get("meta_summary") or "",
            remedy_url=remedy_url
        )
    else:
        payload = build_worklog_claim_card(incident, remedy_url=remedy_url)

    success, code, body = send_to_teams(url, payload)

    audit_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "incident_id": incident.get("id") or incident.get("incident_id") or "",
        "channel_id": target_channel.get("id"),
        "channel_name": target_channel.get("nombre"),
        "success": success,
        "status_code": code,
        "response_excerpt": body[:200] if body else ""
    }
    record_audit_entry(audit_entry)

    return {
        "success": success,
        "status_code": code,
        "channel": target_channel,
        "channel_id": target_channel.get("id"),
        "channel_name": target_channel.get("nombre"),
        "response": body,
        "error": None if success else f"HTTP {code}: {body[:200]}"
    }
