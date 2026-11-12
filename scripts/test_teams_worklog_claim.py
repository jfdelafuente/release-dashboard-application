#!/usr/bin/env python3
"""Test utility for sending ITIL Work Log claim notifications to Microsoft Teams.

Supports both:
1. Power Automate Workflows (modern Adaptive Card v1.4, recommended by Microsoft).
2. Office 365 Incoming Webhooks (MessageCard fallback).
3. Automatic channel resolution via data/teams_channels_config.json.

Usage:
    # 1. Ver previsualización del payload (sin enviar nada a red):
    python scripts/test_teams_worklog_claim.py --dry-run

    # 2. Enviar prueba real usando el canal configurado en data/teams_channels_config.json:
    python scripts/test_teams_worklog_claim.py

    # 3. Enviar prueba para una incidencia concreta del catálogo:
    python scripts/test_teams_worklog_claim.py --incident-id INC000004100002

    # 4. Enviar a un canal específico (ej: masivas_it o warroom_sl1):
    python scripts/test_teams_worklog_claim.py --channel masivas_it

    # 5. Sobrescribir webhook URL manualmente:
    python scripts/test_teams_worklog_claim.py --webhook-url "https://prod-xx.westeurope.logic.azure.com/..."
"""

import argparse
from datetime import datetime, timezone
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
import urllib.error
import urllib.request

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "converters" / "src"))

from teams_notifier import (  # noqa: E402
    load_teams_config,
    resolve_channel,
    build_worklog_claim_card,
    send_to_teams,
    record_audit_entry,
    DEFAULT_REMEDY_URL
)

CATALOG_PATH = PROJECT_ROOT / "data" / "output" / "high_priority_notifications.json"


def load_incident_from_catalog(incident_id: Optional[str] = None) -> Dict[str, Any]:
    """Loads incident data from the generated notifications catalog."""
    if CATALOG_PATH.is_file():
        try:
            with open(CATALOG_PATH, "r", encoding="utf-8") as f:
                catalog = json.load(f)
            items = catalog.get("data", [])
            if incident_id:
                for it in items:
                    if it.get("id") == incident_id:
                        return it
            # Si no se indica o no se encuentra, buscar la primera con reclamación de Work Log
            for it in items:
                guia = it.get("guia_operador") or {}
                if guia.get("reclamar_worklog"):
                    return it
            if items:
                return items[0]
        except Exception as err:
            print(f"[WARN] No se pudo leer {CATALOG_PATH}: {err}")

    # Fallback sintético representativo de Orange Tech Operations
    return {
        "id": incident_id or "INC000004100002",
        "prioridad_sugerida": "P2",
        "titulo": "PROVISION FIBRA // CORTE GENERAL SEDE VALLADOLID",
        "estatus": "Asignado",
        "grupo_asignado": "RED FIBRA",
        "worklog_status": {
            "nivel_inactividad": "WL_BLOQUEO_24H",
            "horas_sin_worklog": 24.8,
            "minutos_sin_worklog": 1488,
            "ultimo_grupo": "RED FIBRA",
            "fecha_ultimo_worklog": "10/11/2026 12:00:00"
        },
        "guia_operador": {
            "alerta_worklog": "🚨 BLOQUEO CRÍTICO: Superadas 24h sin notas en Work Log (24.8h).",
            "plantilla_reclamacion_wl": (
                "[SEGUIMIENTO DE INCIDENCIA - RECLAMACIÓN DE WORK LOG]\n"
                "INCIDENCIA: INC000004100002\n"
                "GRUPO ASIGNADO: RED FIBRA\n\n"
                "Estimado equipo,\n"
                "Se constata que la incidencia no registra actualizaciones técnicas en el Work Log desde hace 24.8h. "
                "Conforme al protocolo de seguimiento operativo de Orange Tech Operations, se solicita incorporar de inmediato "
                "un apunte técnico con el estado actual del diagnóstico, avances y siguientes acciones planificadas.\n\n"
                "Gracias por su colaboración.\n"
                "Gestión Operativa de Incidencias IT"
            )
        }
    }


def build_message_card_payload(incident: Dict[str, Any], remedy_url: Optional[str] = None) -> Dict[str, Any]:
    """Builds a legacy Office 365 MessageCard payload (compatible with webhook.office.com)."""
    inc_id = incident.get("id", "INC000000000000")
    prio = incident.get("prioridad_sugerida", "P2")
    wl_status = incident.get("worklog_status") or {}
    guia = incident.get("guia_operador") or {}
    horas_wl = wl_status.get("horas_sin_worklog", 0)
    nivel = wl_status.get("nivel_inactividad", "WL_ALERTA_6H")
    grupo = incident.get("grupo_asignado") or wl_status.get("ultimo_grupo") or "Grupo Resolutor"
    titulo = incident.get("titulo") or "Incidencia de Servicio"

    theme_color = "D97706"  # Ámbar
    if nivel == "WL_BLOQUEO_24H":
        theme_color = "DC2626"  # Rojo
    elif nivel == "WL_ALERTA_6H":
        theme_color = "0284C7"  # Azul

    claim_body = guia.get("plantilla_reclamacion_wl") or (
        f"Se constata que la incidencia {inc_id} asignada a {grupo} no registra notas técnicas desde hace {horas_wl}h."
    )
    url = remedy_url or DEFAULT_REMEDY_URL

    return {
        "@type": "MessageCard",
        "@context": "http://schema.org/extensions",
        "themeColor": theme_color,
        "summary": f"Reclamación de Work Log para {inc_id}",
        "sections": [
            {
                "activityTitle": f"🚨 Reclamación de Work Log: {inc_id} ({prio})",
                "activitySubtitle": f"Grupo Resolutor: **{grupo}** | Tiempo sin notas: **{horas_wl}h**",
                "facts": [
                    {"name": "Incidencia:", "value": inc_id},
                    {"name": "Prioridad:", "value": prio},
                    {"name": "Título:", "value": titulo},
                    {"name": "Nivel de Alerta:", "value": nivel},
                    {"name": "Horas Inactivo:", "value": f"{horas_wl}h"}
                ],
                "text": f"**Requerimiento Operativo:**\n\n```\n{claim_body}\n```"
            }
        ],
        "potentialAction": [
            {
                "@type": "OpenUri",
                "name": "🔗 Abrir en BMC Remedy",
                "targets": [{"os": "default", "uri": url}]
            }
        ]
    }


def main():
    parser = argparse.ArgumentParser(description="Prueba de envío de reclamación de Work Log a Microsoft Teams.")
    parser.add_argument("--webhook-url", "-w", help="URL manual del Webhook / Power Automate (omite config).")
    parser.add_argument("--channel", "-c", help="ID del canal configurado en data/teams_channels_config.json (ej: masivas_it).")
    parser.add_argument("--action", default="reclamacion_worklog", help="Acción para resolución de canal (default: reclamacion_worklog).")
    parser.add_argument("--incident-id", "-i", help="ID de la incidencia a reclamar (ej. INC000004100002).")
    parser.add_argument("--format", choices=["adaptive", "messagecard", "auto"], default="auto", help="Formato de tarjeta (default: auto).")
    parser.add_argument("--dry-run", action="store_true", help="Solo muestra el payload JSON generado sin enviar a la red.")

    args = parser.parse_args()

    config = load_teams_config()
    incident = load_incident_from_catalog(args.incident_id)
    inc_id = incident.get("id")
    grupo = incident.get("grupo_asignado") or incident.get("worklog_status", {}).get("ultimo_grupo") or "Grupo Resolutor"
    remedy_url = config.get("remedy_base_url", DEFAULT_REMEDY_URL)

    # Resolución de canal y webhook URL
    target_channel = None
    if args.webhook_url:
        webhook_url = args.webhook_url
        channel_name = "Webhook Manual"
    else:
        target_channel = resolve_channel(
            config,
            action=args.action,
            group=grupo,
            channel_id=args.channel
        )
        if target_channel:
            webhook_url = target_channel.get("webhook_url", "")
            channel_name = f"[{target_channel.get('id')}] {target_channel.get('nombre')}"
        else:
            webhook_url = os.getenv("TEAMS_WEBHOOK_URL", "")
            channel_name = "Variable Entorno TEAMS_WEBHOOK_URL"

    print("=" * 65)
    print(" PRUEBA DE ENVÍO RECLAMACIÓN WORK LOG A MICROSOFT TEAMS")
    print("=" * 65)
    print(f"Incidencia:        {inc_id}")
    print(f"Grupo asignado:    {grupo}")
    print(f"Nivel inactividad: {incident.get('worklog_status', {}).get('nivel_inactividad')}")
    print(f"Horas sin notas:   {incident.get('worklog_status', {}).get('horas_sin_worklog')}h")
    print(f"Canal Teams:       {channel_name}")
    print(f"Remedy URL:        {remedy_url}")
    print("=" * 65)

    is_power_automate = bool(webhook_url and ("logic.azure.com" in webhook_url or "workflows" in webhook_url or "powerplatform.com" in webhook_url))
    use_adaptive = (args.format == "adaptive") or (args.format == "auto" and (is_power_automate or not webhook_url))

    if use_adaptive:
        payload = build_worklog_claim_card(incident, remedy_url=remedy_url)
        card_type = "Adaptive Card v1.4 (Power Automate Workflow)"
    else:
        payload = build_message_card_payload(incident, remedy_url=remedy_url)
        card_type = "Office 365 MessageCard (Legacy Incoming Webhook)"

    print(f"Formato seleccionado: {card_type}")

    if args.dry_run or not webhook_url:
        print("\n--- PAYLOAD JSON GENERADO (DRY RUN) ---")
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        if not webhook_url:
            print("\n[AVISO] No se ha configurado ninguna Webhook URL para este canal.")
            print("Configúrala con: python scripts/manage_teams_channels.py --set-channel <id> --url <url>")
        sys.exit(0)

    print(f"\nEnviando petición POST a Webhook de Teams ({channel_name})...")
    success, code, resp_body = send_to_teams(webhook_url, payload)

    # Registrar en auditoría
    if target_channel:
        record_audit_entry({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": args.action,
            "incident_id": inc_id,
            "channel_id": target_channel.get("id"),
            "channel_name": target_channel.get("nombre"),
            "success": success,
            "status_code": code,
            "response_excerpt": resp_body[:200] if resp_body else ""
        })

    if success:
        print(f"\n[OK] ¡Mensaje publicado con éxito en Teams! (HTTP {code})")
        if resp_body:
            print(f"Respuesta Teams: {resp_body[:200]}")
    else:
        print(f"\n[ERROR] Falló el envío a Teams (HTTP {code}):")
        print(f"Detalle: {resp_body}")
        if use_adaptive and code == 400:
            print("\n[SUGERENCIA] Prueba relanzar con: --format messagecard")
        sys.exit(1)


if __name__ == "__main__":
    main()
