# -*- coding: utf-8 -*-
"""
converters.src.desk_service
---------------------------
Capa de servicio unificada (Service Layer) para operaciones backend compartidas
entre serve_app.py (desarrollo local) y fastapi_remedy_router.py (producción ASGI/VPS):
  - Sincronización incremental de incidencias Remedy (sync-remedy)
  - Sincronización incremental de Postmortem / Mesa de Release (sync-postmortem)
  - Detalle profundo y worklogs de incidencias Remedy con doble caché (memoria y disco)
  - Gestión concurrente y atómica de Overrides de Mesa de Release (overrides)
  - Consulta en lote de resúmenes de IA en caché local (resumenIA/cached)
  - Diagnóstico de salud y observabilidad de Mesa de Release (health/release-desk)

Esta unificación garantiza paridad exacta en validación, manejo de errores y respuestas
entre ambos servidores, eliminando duplicidad de código (M21).
"""

import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from converters.src.montmc_client import MonTMCClient, MonTMCError, RemedyNotFoundError
from converters.src.release_desk_overrides import (
    get_overrides_for_release,
    load_cached_epsilon_summaries,
    set_fecha_prevista_override,
)
from converters.src.storage_utils import (
    atomic_write_json,
    build_release_desk_health,
    get_path_lock,
    resolve_cache_dir,
    resolve_high_priority_notifications_path,
    resolve_teams_audit_path,
    resolve_teams_channels_path,
)

try:
    from converters.src.teams_notifier import (
        dispatch_teams_notification,
        load_teams_config,
        save_teams_config,
    )
except ImportError:
    try:
        from teams_notifier import (
            dispatch_teams_notification,
            load_teams_config,
            save_teams_config,
        )
    except ImportError:
        dispatch_teams_notification = None
        load_teams_config = None
        save_teams_config = None

logger = logging.getLogger("release_dashboard.desk_service")

# =============================================================================
# Caché en memoria compartida para detalle de incidencias Remedy
# Formato: {id_remedy: (timestamp, payload_dict, status_code)}
# =============================================================================
GLOBAL_REMEDY_CACHE: Dict[str, Tuple[float, Dict[str, Any], int]] = {}
CACHE_TTL_SECONDS: int = 300


def clear_global_remedy_cache() -> None:
    """Limpia la caché en memoria compartida de Remedy."""
    GLOBAL_REMEDY_CACHE.clear()


def resolve_project_root(provided_root: Optional[Path] = None) -> Path:
    """Resuelve la raíz del repositorio de forma resiliente."""
    if provided_root and isinstance(provided_root, Path):
        return provided_root
    env_root = os.environ.get("RELEASE_DASHBOARD_ROOT", "").strip()
    if env_root:
        return Path(env_root).resolve()
    # converters/src/desk_service.py -> ../.. = project_root
    return Path(__file__).resolve().parent.parent.parent


def resolve_storage_dir(provided_storage_dir: Optional[Path] = None, project_root: Optional[Path] = None) -> Path:
    """Resuelve el directorio de datos persistentes (data/)."""
    if provided_storage_dir and isinstance(provided_storage_dir, Path):
        return provided_storage_dir
    env_storage = os.environ.get("RELEASE_DASHBOARD_STORAGE_DIR", "").strip()
    if env_storage:
        return Path(env_storage).resolve()
    root = resolve_project_root(project_root)
    return root / "data"


def resolve_remedy_cache_dir(project_root: Optional[Path] = None) -> Path:
    """Resuelve y crea el directorio de caché en disco para tickets Remedy (canónico: cache/remedy, fallback: .remedy_cache)."""
    storage = resolve_storage_dir(project_root=project_root)
    cache_dir = resolve_cache_dir(storage, "remedy")
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


# =============================================================================
# Servicio: Sync Remedy
# =============================================================================

def service_sync_remedy(
    payload: Optional[Dict[str, Any]] = None,
    dias: Optional[int] = None,
    usuario: Optional[str] = None,
    project_root: Optional[Path] = None,
    sync_fn: Any = None,
) -> Tuple[int, Dict[str, Any]]:
    """
    Ejecuta la sincronización incremental de Remedy.
    Devuelve (status_code, result_dict).
    """
    root = resolve_project_root(project_root)

    # Si no se inyecta la función de sync, intentar importarla
    if sync_fn is None:
        try:
            from converters.cli.sync_montmc_incidents import sync_remedy_incidents
            sync_fn = sync_remedy_incidents
        except ImportError:
            sync_fn = None

    if sync_fn is None:
        return 500, {"success": False, "error": "Módulo de sincronización MonTMC no disponible"}

    target_dias = dias if isinstance(dias, int) else 3
    target_user: Optional[str] = usuario.strip() if isinstance(usuario, str) and usuario.strip() else None

    if isinstance(payload, dict):
        if "dias" in payload:
            try:
                target_dias = int(payload["dias"])
            except (ValueError, TypeError):
                pass
        if "usuario" in payload and payload["usuario"]:
            target_user = str(payload["usuario"]).strip()

    try:
        result = sync_fn(
            dias=target_dias,
            usuario=target_user,
            project_root=root,
        )
        status_code = 200 if result.get("success") else 502
        return status_code, result
    except Exception as e:
        logger.exception("Error en sincronización Remedy: %s", e)
        return 502, {"success": False, "error": f"Fallo en sincronización Remedy: {e}"}


# =============================================================================
# Servicio: Sync Postmortem / Mesa de Release
# =============================================================================

def service_sync_postmortem(
    payload: Optional[Dict[str, Any]] = None,
    release_name: Optional[str] = None,
    usuario: Optional[str] = None,
    project_root: Optional[Path] = None,
    sync_fn: Any = None,
) -> Tuple[int, Dict[str, Any]]:
    """
    Ejecuta la sincronización incremental de Postmortem / Mesa de Release.
    Devuelve (status_code, result_dict).
    """
    root = resolve_project_root(project_root)

    if sync_fn is None:
        try:
            from converters.cli.sync_montmc_postmortem import sync_postmortem_release
            sync_fn = sync_postmortem_release
        except ImportError:
            sync_fn = None

    if sync_fn is None:
        return 500, {"success": False, "error": "Módulo de sincronización Postmortem MonTMC no disponible"}

    target_release: Optional[str] = release_name.strip() if isinstance(release_name, str) and release_name.strip() else None
    target_user: Optional[str] = usuario.strip() if isinstance(usuario, str) and usuario.strip() else None

    if isinstance(payload, dict):
        if payload.get("release_name"):
            target_release = str(payload["release_name"]).strip()
        if payload.get("usuario"):
            target_user = str(payload["usuario"]).strip()

    try:
        result = sync_fn(
            release_name=target_release,
            usuario=target_user,
            project_root=root,
        )
        status_code = 200 if result.get("success") else 502
        return status_code, result
    except Exception as e:
        logger.exception("Error en sincronización Postmortem: %s", e)
        return 502, {"success": False, "error": f"Fallo en sincronización Postmortem: {e}"}


# =============================================================================
# Servicio: Detalle de Incidencia Remedy con Doble Caché
# =============================================================================

def service_get_remedy_detail(
    id_remedy: str,
    force: bool = False,
    cache_dir: Optional[Path] = None,
    memory_cache: Optional[Dict[str, Tuple[float, Dict[str, Any], int]]] = None,
    ttl_seconds: int = CACHE_TTL_SECONDS,
    client_cls: Any = None,
    project_root: Optional[Path] = None,
) -> Tuple[int, Dict[str, Any], Dict[str, str]]:
    """
    Obtiene el detalle, eventos y worklogs de una incidencia Remedy.
    Devuelve (status_code, payload, response_headers).
    """
    clean_id = (id_remedy or "").strip().upper()
    if not clean_id:
        return 400, {"success": False, "error": "Falta el identificador de incidencia (idRemedy)"}, {}

    effective_cache = GLOBAL_REMEDY_CACHE if memory_cache is None else memory_cache
    now = time.time()

    # 1. Caché en memoria
    if not force and clean_id in effective_cache:
        cached_time, cached_payload, cached_status = effective_cache[clean_id]
        if now - cached_time < ttl_seconds:
            resp_copy = dict(cached_payload)
            resp_copy["_cached"] = True
            return cached_status, resp_copy, {"X-Cache-Status": "MEMORY_HIT"}

    # 2. Consulta en vivo a la API MonTMC
    effective_client_cls = MonTMCClient if client_cls is None else client_cls
    effective_cache_dir = resolve_remedy_cache_dir(project_root) if cache_dir is None else cache_dir

    if effective_client_cls:
        try:
            client = effective_client_cls()
            data = client.fetch_remedy_detail(clean_id)
            remedy_node = data.get("remedy") or {}
            worklogs = remedy_node.get("worklog") or []

            payload = {
                "success": True,
                "idRemedy": clean_id,
                "remedy": remedy_node,
                "worklogs": worklogs,
                "detalle": remedy_node.get("detalle") or "",
                "solucion": remedy_node.get("detalleSolucion") or "",
                "estado": remedy_node.get("estadoDesc") or "",
                "paps": remedy_node.get("paps") or [],
                "_cached": False,
                "_source": "montmc_live",
            }

            effective_cache[clean_id] = (now, payload, 200)

            # Persistencia segura y atómica en disco
            try:
                disk_file = effective_cache_dir / f"{clean_id}.json"
                with get_path_lock(disk_file):
                    atomic_write_json(disk_file, payload, create_backup=False, indent=2)
            except Exception as disk_err:
                logger.debug("No se pudo escribir caché en disco para %s: %s", clean_id, disk_err)

            return 200, payload, {"X-Cache-Status": "LIVE_SOPTMC_HIT"}

        except RemedyNotFoundError as e:
            return 404, {"success": False, "error": str(e), "idRemedy": clean_id}, {}

        except Exception as e:
            logger.warning("Error consultando Remedy en MonTMC para %s: %s. Verificando caché en disco...", clean_id, e)

    # 3. Fallback a caché previa en disco
    disk_file = effective_cache_dir / f"{clean_id}.json"
    if not force and disk_file.exists():
        try:
            disk_payload = json.loads(disk_file.read_text(encoding="utf-8"))
            disk_payload["_cached"] = True
            disk_payload["_source"] = "disk_fallback"
            return 200, disk_payload, {"X-Cache-Status": "DISK_FALLBACK"}
        except Exception as read_err:
            logger.debug("Error leyendo caché en disco para %s: %s", clean_id, read_err)

    return 502, {
        "success": False,
        "error": f"No se pudo consultar el detalle de Remedy para {clean_id} ni se dispone de copia local",
        "idRemedy": clean_id,
    }, {}


# =============================================================================
# Servicio: Overrides de Mesa de Release
# =============================================================================

def service_get_overrides(
    storage_dir: Optional[Path] = None,
    release_name: str = "",
    project_root: Optional[Path] = None,
) -> Dict[str, Any]:
    """Obtiene el mapa de overrides de una release."""
    target_storage = resolve_storage_dir(storage_dir, project_root)
    clean_release = (release_name or "").strip()
    overrides = get_overrides_for_release(target_storage, clean_release)
    return {"success": True, "release_name": clean_release, "overrides": overrides}


def service_set_override(
    payload: Dict[str, Any],
    storage_dir: Optional[Path] = None,
    project_root: Optional[Path] = None,
) -> Tuple[int, Dict[str, Any]]:
    """Guarda un override de fecha prevista de forma atómica y concurrente."""
    target_storage = resolve_storage_dir(storage_dir, project_root)
    try:
        result = set_fecha_prevista_override(
            storage_dir=target_storage,
            release_name=str(payload.get("release_name") or ""),
            incident_id=str(payload.get("incident_id") or ""),
            fecha_prevista=str(payload.get("fecha_prevista") or ""),
        )
        return 200, result
    except ValueError as exc:
        return 400, {"success": False, "error": str(exc)}
    except Exception as exc:
        logger.exception("Error guardando override: %s", exc)
        return 500, {"success": False, "error": f"Error guardando override: {exc}"}


# =============================================================================
# Servicio: Caché Resumen IA Epsilon
# =============================================================================

def service_get_cached_epsilon(
    ids: Union[str, List[str]],
    storage_dir: Optional[Path] = None,
    project_root: Optional[Path] = None,
) -> Dict[str, Any]:
    """Carga los resúmenes de IA almacenados en disco para los IDs solicitados."""
    target_storage = resolve_storage_dir(storage_dir, project_root)
    if isinstance(ids, str):
        id_list = [part.strip() for part in ids.split(",") if part.strip()]
    elif isinstance(ids, (list, tuple)):
        id_list = [str(x).strip() for x in ids if str(x).strip()]
    else:
        id_list = []

    summaries = load_cached_epsilon_summaries(target_storage, id_list)
    return {"success": True, "count": len(summaries), "summaries": summaries}


# =============================================================================
# Servicio: Health de Mesa de Release
# =============================================================================

def service_get_health(
    storage_dir: Optional[Path] = None,
    project_root: Optional[Path] = None,
) -> Tuple[int, Dict[str, Any]]:
    """Genera el diagnóstico integral de salud de Mesa de Release."""
    root = resolve_project_root(project_root)
    target_storage = resolve_storage_dir(storage_dir, root)
    payload = build_release_desk_health(target_storage, root)
    status_code = 200 if payload.get("status") == "ok" else 503
    return status_code, payload


# =============================================================================
# Servicios: Microsoft Teams (Canales, Auditoría y Notificaciones)
# =============================================================================

def service_get_teams_channels(
    storage_dir: Optional[Path] = None,
    project_root: Optional[Path] = None,
) -> Tuple[int, Dict[str, Any]]:
    """Retorna la configuración actual de canales de Microsoft Teams."""
    if not load_teams_config:
        return 500, {"success": False, "error": "Módulo teams_notifier no disponible"}
    root = resolve_project_root(project_root)
    storage = resolve_storage_dir(storage_dir, root)
    cfg_path = resolve_teams_channels_path(storage_dir=storage, project_root=root)
    try:
        cfg = load_teams_config(cfg_path)
        return 200, {"success": True, "config": cfg}
    except Exception as exc:
        logger.exception("Error al cargar configuración de canales Teams: %s", exc)
        return 500, {"success": False, "error": f"Error al cargar configuración: {exc}"}


def service_set_teams_channels(
    payload: Any,
    storage_dir: Optional[Path] = None,
    project_root: Optional[Path] = None,
) -> Tuple[int, Dict[str, Any]]:
    """Valida y guarda la configuración de canales de Microsoft Teams."""
    if not save_teams_config:
        return 500, {"success": False, "error": "Módulo teams_notifier no disponible"}
    root = resolve_project_root(project_root)
    storage = resolve_storage_dir(storage_dir, root)
    cfg_path = resolve_teams_channels_path(storage_dir=storage, project_root=root)

    if not isinstance(payload, dict):
        return 400, {"success": False, "error": "Formato de configuración inválido"}

    cfg = payload.get("config", payload)
    if not isinstance(cfg, dict) or "canales" not in cfg:
        return 400, {"success": False, "error": "Formato de configuración inválido: falta 'canales'"}

    try:
        saved = save_teams_config(cfg, cfg_path)
        if saved:
            return 200, {
                "success": True,
                "message": "Configuración de canales guardada con éxito",
                "config": cfg,
            }
        return 500, {"success": False, "error": "Error al persistir configuración"}
    except Exception as exc:
        logger.exception("Error guardando configuración de Teams: %s", exc)
        return 400, {"success": False, "error": f"Error procesando petición: {exc}"}


def service_get_teams_audit(
    storage_dir: Optional[Path] = None,
    project_root: Optional[Path] = None,
) -> Tuple[int, Dict[str, Any]]:
    """Retorna el historial de despachos a Teams."""
    root = resolve_project_root(project_root)
    storage = resolve_storage_dir(storage_dir, root)
    audit_file = resolve_teams_audit_path(storage_dir=storage, project_root=root)

    if audit_file.is_file():
        try:
            with open(audit_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return 200, {"success": True, "audit": data if isinstance(data, list) else []}
        except Exception as exc:
            logger.exception("Error leyendo log de auditoría Teams: %s", exc)
            return 500, {"success": False, "error": str(exc)}
    return 200, {"success": True, "audit": []}


def service_send_teams(
    payload: Any,
    storage_dir: Optional[Path] = None,
    project_root: Optional[Path] = None,
) -> Tuple[int, Dict[str, Any]]:
    """Despacha una notificación adaptativa a Microsoft Teams."""
    if not dispatch_teams_notification:
        return 500, {"success": False, "error": "Módulo teams_notifier no disponible"}
    root = resolve_project_root(project_root)
    storage = resolve_storage_dir(storage_dir, root)

    if not isinstance(payload, dict):
        return 400, {"success": False, "error": "Cuerpo de solicitud inválido"}

    action = payload.get("action", "reclamacion_worklog")
    incident = payload.get("incident")
    incident_id = payload.get("incident_id")
    channel_id = payload.get("channel_id")
    group = payload.get("group")
    teams_meeting_url = payload.get("teams_meeting_url")
    executive_text = payload.get("executive_text")

    if not incident and incident_id:
        cat_path = resolve_high_priority_notifications_path(storage_dir=storage, project_root=root)
        if cat_path.is_file():
            try:
                with open(cat_path, "r", encoding="utf-8") as f:
                    cat = json.load(f)
                for item in cat.get("data", []):
                    if isinstance(item, dict) and item.get("id") == incident_id:
                        incident = item
                        break
            except Exception as exc:
                logger.warning("No se pudo leer catálogo de alta prioridad: %s", exc)

    if not incident:
        if action == "traspaso_guardia":
            incident = {
                "id": "RELEVO-GUARDIA",
                "report_text": payload.get("report_text") or executive_text or "",
                "meta_summary": payload.get("meta_summary", ""),
            }
        else:
            return 400, {"success": False, "error": "Se requiere objeto 'incident' o 'incident_id' válido"}

    cfg_path = resolve_teams_channels_path(storage_dir=storage, project_root=root)
    cfg = load_teams_config(cfg_path) if load_teams_config else None
    audit_path = resolve_teams_audit_path(storage_dir=storage, project_root=root)

    try:
        result = dispatch_teams_notification(
            action=action,
            incident=incident,
            group=group,
            channel_id=channel_id,
            config=cfg,
            teams_meeting_url=teams_meeting_url,
            executive_text=executive_text,
            audit_path=audit_path,
        )
        status_http = 200 if result.get("success") else 502
        return status_http, result
    except Exception as exc:
        logger.exception("Fallo al despachar a Teams: %s", exc)
        return 500, {"success": False, "error": f"Fallo al despachar a Teams: {exc}"}
