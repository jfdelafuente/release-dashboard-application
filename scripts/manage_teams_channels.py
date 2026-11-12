#!/usr/bin/env python3
"""CLI utility to manage Microsoft Teams channels and action routing for Orange Tech Operations.

Allows configuring channels, webhooks, action routings, and resolutor group overrides
both interactively and via scriptable CLI flags.

Usage examples:
    # 1. Listar canales y configuración actual:
    python scripts/manage_teams_channels.py --list

    # 2. Añadir o actualizar un canal:
    python scripts/manage_teams_channels.py --set-channel warroom_sl1 --name "War Room SL1" --url "https://..." --desc "Sala de crisis SL1"

    # 3. Enrutar una acción a un canal específico:
    python scripts/manage_teams_channels.py --route-action notificacion_direccion --channel notificaciones_direccion

    # 4. Enrutar un grupo resolutor específico (override):
    python scripts/manage_teams_channels.py --route-group "RED FIBRA" --channel fibra_ops --action reclamacion_worklog

    # 5. Probar conectividad con un canal o acción:
    python scripts/manage_teams_channels.py --test --action reclamacion_worklog
    python scripts/manage_teams_channels.py --test --channel masivas_it --incident-id INC000004100002
"""

import argparse
from datetime import datetime, timezone
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

# Asegurar import de converters/src/teams_notifier
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "converters" / "src"))

from teams_notifier import (  # noqa: E402
    load_teams_config,
    save_teams_config,
    resolve_channel,
    dispatch_teams_notification,
    DEFAULT_REMEDY_URL
)


def mask_url(url: str) -> str:
    """Masks webhook secret query parameters for terminal display."""
    if not url:
        return "(no configurada)"
    if "sig=" in url:
        base, _, query = url.partition("?")
        parts = query.split("&")
        masked_parts = []
        for p in parts:
            if p.startswith("sig="):
                masked_parts.append("sig=" + p[4:8] + "..." + p[-4:])
            else:
                masked_parts.append(p)
        return base + "?" + "&".join(masked_parts)
    if len(url) > 60:
        return url[:30] + "..." + url[-15:]
    return url


def cmd_list(config: Dict[str, Any]) -> None:
    """Prints current channels and action routings."""
    print("=" * 80)
    print(" CONFIGURACIÓN DE CANALES MICROSOFT TEAMS (ORANGE TECH OPERATIONS)")
    print("=" * 80)
    remedy_url = config.get("remedy_base_url", DEFAULT_REMEDY_URL)
    print(f"URL Portal BMC Remedy: {remedy_url}")
    print("-" * 80)

    channels = config.get("canales", {})
    print(f"\n📡 CANALES CONFIGURADOS ({len(channels)}):")
    for cid, cdata in channels.items():
        status_icon = "🟢 [ACTIVO]" if cdata.get("activo") and cdata.get("webhook_url") else "⚪ [INACTIVO/PENDIENTE]"
        print(f"  • [{cid}] {cdata.get('nombre', cid)}  {status_icon}")
        print(f"    - Descripción: {cdata.get('descripcion', '-')}")
        print(f"    - Tipo:        {cdata.get('tipo', 'power_automate_workflow')}")
        print(f"    - Webhook URL: {mask_url(cdata.get('webhook_url', ''))}")
        if cdata.get("actualizado_el"):
            print(f"    - Modificado:  {cdata.get('actualizado_el')}")
        print()

    routes = config.get("rutas_acciones", {})
    print(f"🔀 ENRUTAMIENTO DE ACCIONES OPERATIVAS:")
    for action, rdata in routes.items():
        def_channel = rdata.get("canal_predeterminado", "masivas_it")
        target_info = channels.get(def_channel, {})
        target_name = target_info.get("nombre", def_channel)
        print(f"  👉 Acción: {action.upper()}")
        print(f"     Descripción:          {rdata.get('descripcion', '-')}")
        print(f"     Canal Predeterminado: [{def_channel}] ({target_name})")
        group_map = rdata.get("mapeo_por_grupo", {})
        if group_map:
            print("     Mapeos por Grupo Resolutor:")
            for grp, mapped_cid in group_map.items():
                m_info = channels.get(mapped_cid, {})
                print(f"       * {grp:25} ➔ [{mapped_cid}] ({m_info.get('nombre', mapped_cid)})")
        else:
            print("     Mapeos por Grupo Resolutor: (ninguno)")
        print()
    print("=" * 80)


def cmd_set_channel(
    config: Dict[str, Any],
    channel_id: str,
    name: Optional[str] = None,
    url: Optional[str] = None,
    desc: Optional[str] = None,
    ctype: Optional[str] = None,
    active: Optional[bool] = None
) -> bool:
    channels = config.setdefault("canales", {})
    now = datetime.now(timezone.utc).isoformat()
    if channel_id not in channels:
        channels[channel_id] = {
            "id": channel_id,
            "nombre": name or channel_id,
            "descripcion": desc or "",
            "tipo": ctype or "power_automate_workflow",
            "webhook_url": url or "",
            "activo": True if active is None else active,
            "creado_el": now,
            "actualizado_el": now
        }
        print(f"[OK] Canal '{channel_id}' creado.")
    else:
        c = channels[channel_id]
        if name is not None:
            c["nombre"] = name
        if desc is not None:
            c["descripcion"] = desc
        if url is not None:
            c["webhook_url"] = url
        if ctype is not None:
            c["tipo"] = ctype
        if active is not None:
            c["activo"] = active
        c["actualizado_el"] = now
        print(f"[OK] Canal '{channel_id}' actualizado.")

    return save_teams_config(config)


def cmd_delete_channel(config: Dict[str, Any], channel_id: str) -> bool:
    channels = config.get("canales", {})
    if channel_id not in channels:
        print(f"[WARN] El canal '{channel_id}' no existe.")
        return False

    del channels[channel_id]
    # Limpiar referencias
    routes = config.get("rutas_acciones", {})
    for action, rdata in routes.items():
        if rdata.get("canal_predeterminado") == channel_id:
            rdata["canal_predeterminado"] = "masivas_it"
        group_map = rdata.get("mapeo_por_grupo", {})
        keys_to_del = [g for g, cid in group_map.items() if cid == channel_id]
        for k in keys_to_del:
            del group_map[k]

    print(f"[OK] Canal '{channel_id}' eliminado y rutas limpiadas.")
    return save_teams_config(config)


def cmd_route_action(config: Dict[str, Any], action: str, channel_id: str) -> bool:
    channels = config.get("canales", {})
    if channel_id not in channels:
        print(f"[WARN] El canal '{channel_id}' no existe en la lista de canales.")
        print(f"Canales disponibles: {', '.join(channels.keys())}")
        return False

    routes = config.setdefault("rutas_acciones", {})
    if action not in routes:
        routes[action] = {
            "descripcion": f"Acción {action}",
            "canal_predeterminado": channel_id,
            "mapeo_por_grupo": {}
        }
    else:
        routes[action]["canal_predeterminado"] = channel_id

    print(f"[OK] Acción '{action}' enrutada por defecto al canal '[{channel_id}]'.")
    return save_teams_config(config)


def cmd_route_group(config: Dict[str, Any], group: str, channel_id: str, action: str = "reclamacion_worklog") -> bool:
    channels = config.get("canales", {})
    if channel_id not in channels:
        print(f"[WARN] El canal '{channel_id}' no existe en la lista de canales.")
        print(f"Canales disponibles: {', '.join(channels.keys())}")
        return False

    routes = config.setdefault("rutas_acciones", {})
    if action not in routes:
        routes[action] = {
            "descripcion": f"Acción {action}",
            "canal_predeterminado": "masivas_it",
            "mapeo_por_grupo": {}
        }
    group_map = routes[action].setdefault("mapeo_por_grupo", {})
    group_map[group] = channel_id
    print(f"[OK] Grupo '{group}' enrutado al canal '[{channel_id}]' para la acción '{action}'.")
    return save_teams_config(config)


def cmd_unroute_group(config: Dict[str, Any], group: str, action: str = "reclamacion_worklog") -> bool:
    routes = config.get("rutas_acciones", {})
    if action in routes and group in routes[action].get("mapeo_por_grupo", {}):
        del routes[action]["mapeo_por_grupo"][group]
        print(f"[OK] Mapeo del grupo '{group}' eliminado de la acción '{action}'.")
        return save_teams_config(config)
    print(f"[WARN] No había mapeo específico para el grupo '{group}' en la acción '{action}'.")
    return False


def load_sample_incident(incident_id: Optional[str] = None) -> Dict[str, Any]:
    """Loads incident from notifications catalog or builds synthetic sample."""
    catalog_path = PROJECT_ROOT / "data" / "output" / "high_priority_notifications.json"
    if catalog_path.is_file():
        try:
            with open(catalog_path, "r", encoding="utf-8") as f:
                cat = json.load(f)
            items = cat.get("data", [])
            if incident_id:
                for it in items:
                    if it.get("id") == incident_id:
                        return it
            for it in items:
                if it.get("guia_operador", {}).get("reclamar_worklog"):
                    return it
            if items:
                return items[0]
        except Exception:
            pass

    return {
        "id": incident_id or "INC000004100002",
        "prioridad_sugerida": "P2",
        "titulo": "CORTE DE FIBRA ACCESO CLIENTES SEDE VALLADOLID",
        "estatus": "Asignado",
        "grupo_asignado": "RED FIBRA",
        "worklog_status": {
            "nivel_inactividad": "WL_BLOQUEO_24H",
            "horas_sin_worklog": 24.8,
            "minutos_sin_worklog": 1488,
            "ultimo_grupo": "RED FIBRA"
        },
        "guia_operador": {
            "plantilla_reclamacion_wl": (
                "[SEGUIMIENTO DE INCIDENCIA - RECLAMACIÓN DE WORK LOG]\n"
                "INCIDENCIA: INC000004100002\n"
                "GRUPO ASIGNADO: RED FIBRA\n\n"
                "Estimado equipo,\n"
                "Se constata que la incidencia no registra actualizaciones técnicas en el Work Log desde hace 24.8h.\n"
                "Conforme al protocolo de seguimiento operativo de Orange Tech Operations, se solicita incorporar de inmediato "
                "un apunte técnico con el estado actual del diagnóstico y siguientes acciones.\n\n"
                "Gracias por su colaboración.\n"
                "Gestión Operativa de Incidencias IT"
            )
        }
    }


def main():
    parser = argparse.ArgumentParser(
        description="Gestor de Canales y Enrutamiento de Notificaciones a Microsoft Teams."
    )
    parser.add_argument("--list", "-l", action="store_true", help="Listar configuración actual de canales y rutas.")
    parser.add_argument("--set-channel", help="ID del canal a crear o actualizar (ej: warroom_sl1).")
    parser.add_argument("--name", help="Nombre descriptivo del canal.")
    parser.add_argument("--url", help="URL del Webhook de Teams / Power Automate.")
    parser.add_argument("--desc", help="Descripción del propósito del canal.")
    parser.add_argument("--type", choices=["power_automate_workflow", "incoming_webhook"], default="power_automate_workflow")
    parser.add_argument("--active", type=lambda v: v.lower() in ("true", "1", "yes", "si"), help="Activar o desactivar canal (true/false).")
    parser.add_argument("--delete-channel", help="Eliminar un canal por su ID.")
    parser.add_argument("--route-action", help="Acción a enrutar (ej: reclamacion_worklog, notificacion_direccion).")
    parser.add_argument("--channel", help="ID del canal destino para enrutamiento o prueba.")
    parser.add_argument("--route-group", help="Nombre del grupo resolutor para override (ej: 'RED FIBRA').")
    parser.add_argument("--unroute-group", help="Eliminar override de grupo resolutor.")
    parser.add_argument("--action", default="reclamacion_worklog", help="Acción asociada al grupo o prueba (default: reclamacion_worklog).")
    parser.add_argument("--test", action="store_true", help="Ejecutar prueba de envío real al canal/acción.")
    parser.add_argument("--incident-id", "-i", help="ID de la incidencia para la prueba (ej: INC000004100002).")
    parser.add_argument("--set-remedy-url", help="Actualizar la URL base oficial de BMC Remedy.")

    args = parser.parse_args()
    config = load_teams_config()

    if args.set_remedy_url:
        config["remedy_base_url"] = args.set_remedy_url
        save_teams_config(config)
        print(f"[OK] URL de BMC Remedy actualizada: {args.set_remedy_url}")
        return

    if args.set_channel:
        cmd_set_channel(
            config,
            channel_id=args.set_channel,
            name=args.name,
            url=args.url,
            desc=args.desc,
            ctype=args.type,
            active=args.active
        )
        return

    if args.delete_channel:
        cmd_delete_channel(config, args.delete_channel)
        return

    if args.route_action and args.channel:
        cmd_route_action(config, args.route_action, args.channel)
        return

    if args.route_group and args.channel:
        cmd_route_group(config, args.route_group, args.channel, action=args.action)
        return

    if args.unroute_group:
        cmd_unroute_group(config, args.unroute_group, action=args.action)
        return

    if args.test:
        incident = load_sample_incident(args.incident_id)
        inc_id = incident.get("id")
        action = args.action
        channel_id = args.channel
        group = incident.get("grupo_asignado")

        target = resolve_channel(config, action=action, group=group, channel_id=channel_id)
        if not target:
            print(f"[ERROR] No se pudo resolver ningún canal para acción='{action}', channel='{channel_id}'.")
            sys.exit(1)

        print(f"Iniciando prueba de envío:")
        print(f"  • Incidencia:  {inc_id}")
        print(f"  • Acción:      {action}")
        print(f"  • Canal:       [{target.get('id')}] {target.get('nombre')}")
        print(f"  • Webhook:     {mask_url(target.get('webhook_url', ''))}")
        print("-" * 60)

        result = dispatch_teams_notification(
            action=action,
            incident=incident,
            group=group,
            channel_id=channel_id,
            config=config
        )

        if result.get("success"):
            print(f"[OK] ¡Mensaje enviado con éxito a Microsoft Teams! (HTTP {result.get('status_code')})")
            if result.get("response"):
                print(f"Respuesta Teams: {result.get('response')[:200]}")
        else:
            print(f"[ERROR] Falló el envío a Teams (HTTP {result.get('status_code')}):")
            print(f"Detalle: {result.get('error')}")
            sys.exit(1)
        return

    # Si no se pasó otra opción, o si se pasó --list, mostrar configuración
    cmd_list(config)


if __name__ == "__main__":
    main()
