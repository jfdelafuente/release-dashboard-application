# -*- coding: utf-8 -*-
"""
fastapi_remedy_router.py
------------------------
Router oficial de FastAPI para los endpoints de integración con MonTMC Remedy en Producción.

Rutas expuestas:
  - POST /api/sync-remedy (y alias POST /sync-remedy): sincronización incremental de incidencias
  - POST /api/sync-postmortem (y alias POST /sync-postmortem): sincronización incremental postmortem
  - GET  /api/remedy/detail/{id_remedy} (y alias GET /detail/{id_remedy}): detalle y notas de Remedy
  - GET / POST /api/release-desk/overrides: reclasificaciones y fechas previstas de Mesa de Release
  - GET / POST /api/epsilon/resumenIA/cached: resúmenes de IA en caché local
  - GET /api/health/release-desk: diagnóstico de salud integral
  - GET / POST /api/teams/channels: configuración de canales Microsoft Teams
  - GET /api/teams/audit: historial de auditoría de notificaciones Teams
  - POST /api/teams/send: despacho de tarjetas adaptativas a Teams

Todas las operaciones de negocio delegan en la capa unificada de servicio desk_service.py (M21),
garantizando paridad absoluta con serve_app.py.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
import sys
from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, HTTPException, Query
from fastapi.responses import JSONResponse

# Asegurar importación de módulos hermanos
try:
    from converters.src.montmc_client import MonTMCClient, MonTMCError, RemedyNotFoundError
except ImportError:
    try:
        from montmc_client import MonTMCClient, MonTMCError, RemedyNotFoundError
    except ImportError:
        _curr = Path(__file__).resolve()
        for parent in (_curr.parent, _curr.parent.parent, _curr.parent.parent.parent):
            if str(parent) not in sys.path:
                sys.path.insert(0, str(parent))
        from converters.src.montmc_client import MonTMCClient, MonTMCError, RemedyNotFoundError

try:
    from converters.cli.sync_montmc_incidents import sync_remedy_incidents
except ImportError:
    try:
        from sync_montmc_incidents import sync_remedy_incidents
    except ImportError:
        sync_remedy_incidents = None

try:
    from converters.cli.sync_montmc_postmortem import sync_postmortem_release
except ImportError:
    try:
        from sync_montmc_postmortem import sync_postmortem_release
    except ImportError:
        sync_postmortem_release = None

try:
    from converters.src.desk_service import (
        GLOBAL_REMEDY_CACHE,
        clear_global_remedy_cache,
        resolve_project_root,
        resolve_storage_dir,
        resolve_remedy_cache_dir,
        service_generate_release_report,
        service_get_cached_epsilon,
        service_get_health,
        service_get_overrides,
        service_get_remedy_detail,
        service_get_teams_audit,
        service_get_teams_channels,
        service_send_teams,
        service_set_override,
        service_set_teams_channels,
        service_sync_postmortem,
        service_sync_remedy,
        service_upload_argos_csv,
    )
except ImportError:
    from desk_service import (
        GLOBAL_REMEDY_CACHE,
        clear_global_remedy_cache,
        resolve_project_root,
        resolve_storage_dir,
        resolve_remedy_cache_dir,
        service_generate_release_report,
        service_get_cached_epsilon,
        service_get_health,
        service_get_overrides,
        service_get_remedy_detail,
        service_get_teams_audit,
        service_get_teams_channels,
        service_send_teams,
        service_set_override,
        service_set_teams_channels,
        service_sync_postmortem,
        service_sync_remedy,
        service_upload_argos_csv,
    )

try:
    from converters.src.release_desk_overrides import (
        get_overrides_for_release,
        load_cached_epsilon_summaries,
        set_fecha_prevista_override,
    )
except ImportError:
    from release_desk_overrides import (
        get_overrides_for_release,
        load_cached_epsilon_summaries,
        set_fecha_prevista_override,
    )

logger = logging.getLogger("fastapi_remedy_router")

router = APIRouter(tags=["Remedy MonTMC Integration"])

# Caché en memoria para detalle técnico de Remedy compartida con desk_service
FASTAPI_REMEDY_CACHE = GLOBAL_REMEDY_CACHE
CACHE_TTL_SECONDS = 300


def _get_project_root() -> Path:
    """Resuelve la raíz del proyecto para localizar ficheros de datos y scripts."""
    env_root = os.environ.get("RELEASE_DASHBOARD_ROOT", "").strip()
    if env_root and Path(env_root).is_dir():
        return Path(env_root)

    # Entorno estándar de producción en VPS
    vps_current = Path("/infocodes/project/release-dashboard-application/current")
    if vps_current.is_dir():
        return vps_current

    return resolve_project_root()


def _get_cache_dir() -> Path:
    """Obtiene o crea el directorio de caché persistente en disco para ficheros Remedy."""
    vps_storage = Path("/infocodes/var/storage/release-dashboard")
    if vps_storage.is_dir():
        target = vps_storage / ".remedy_cache"
        try:
            target.mkdir(parents=True, exist_ok=True)
            return target
        except Exception:
            pass

    return resolve_remedy_cache_dir(_get_project_root())


def clear_fastapi_remedy_cache() -> None:
    """Limpia la caché en memoria (útil tras sincronizaciones o en pruebas unitarias)."""
    clear_global_remedy_cache()


# =============================================================================
# POST /api/sync-remedy
# =============================================================================

@router.post("/api/sync-remedy")
@router.post("/sync-remedy")
def sync_remedy(
    payload: Optional[Dict[str, Any]] = Body(default=None),
    dias: Optional[int] = Query(default=None, description="Número de días hacia atrás a consultar"),
    usuario: Optional[str] = Query(default=None, description="Usuario de consulta MonTMC"),
):
    """
    Dispara la sincronización incremental de incidencias masivas recientes desde MonTMC Remedy.
    Realiza un upsert seguro sin destruir registros históricos fuera de la ventana consultada.
    """
    status_code, result = service_sync_remedy(
        payload=payload,
        dias=dias,
        usuario=usuario,
        project_root=_get_project_root(),
        sync_fn=sync_remedy_incidents,
    )
    return JSONResponse(status_code=status_code, content=result)


# =============================================================================
# POST /api/sync-postmortem
# =============================================================================

@router.post("/api/sync-postmortem")
@router.post("/sync-postmortem")
def sync_postmortem(
    payload: Optional[Dict[str, Any]] = Body(default=None),
    release_name: Optional[str] = Query(default=None, description="Nombre de la release de postmortem"),
    usuario: Optional[str] = Query(default=None, description="Usuario de consulta MonTMC"),
):
    """
    Dispara la sincronización incremental del dashboard Postmortem desde MonTMC /api/epsilon/release.
    Realiza un upsert seguro sin destruir registros históricos ni mezclar massive/notificaciones.
    """
    status_code, result = service_sync_postmortem(
        payload=payload,
        release_name=release_name,
        usuario=usuario,
        project_root=_get_project_root(),
        sync_fn=sync_postmortem_release,
    )
    return JSONResponse(status_code=status_code, content=result)


# =============================================================================
# GET /api/remedy/detail/{id_remedy}
# =============================================================================

@router.get("/api/remedy/detail/{id_remedy}")
@router.get("/remedy/detail/{id_remedy}")
@router.get("/detail/{id_remedy}")
def get_remedy_detail(
    id_remedy: str,
    force: bool = Query(False, description="Forzar consulta en vivo ignorando caché"),
    refresh: bool = Query(False, description="Alias de force"),
):
    """
    Obtiene el detalle profundo, eventos y notas técnicas (worklogs) de una incidencia Remedy.
    Implementa caché en memoria (TTL 300s) y fallback resiliente en disco.
    """
    clean_id = (id_remedy or "").strip().upper()
    if not clean_id:
        raise HTTPException(
            status_code=400,
            detail={"success": False, "error": "Falta el identificador de incidencia (idRemedy)"},
        )

    force_val = force if isinstance(force, bool) else False
    refresh_val = refresh if isinstance(refresh, bool) else False
    force_refresh = bool(force_val or refresh_val)

    status_code, payload, headers = service_get_remedy_detail(
        id_remedy=clean_id,
        force=force_refresh,
        cache_dir=_get_cache_dir(),
        memory_cache=FASTAPI_REMEDY_CACHE,
        ttl_seconds=CACHE_TTL_SECONDS,
        client_cls=MonTMCClient,
        project_root=_get_project_root(),
    )

    return JSONResponse(status_code=status_code, content=payload, headers=headers)


# =============================================================================
# GET / POST /api/release-desk/overrides
# =============================================================================

@router.get("/api/release-desk/overrides")
@router.get("/release-desk/overrides")
def api_get_release_desk_overrides(
    release: str = Query(default="", description="Código de release (ej. 2026R9)"),
):
    root = _get_project_root()
    storage_dir = Path(os.environ.get("RELEASE_DASHBOARD_STORAGE_DIR", "").strip() or (root / "data"))
    return service_get_overrides(storage_dir=storage_dir, release_name=release, project_root=root)


@router.post("/api/release-desk/overrides")
@router.post("/release-desk/overrides")
def api_set_release_desk_override(payload: Dict[str, Any] = Body(...)):
    root = _get_project_root()
    storage_dir = Path(os.environ.get("RELEASE_DASHBOARD_STORAGE_DIR", "").strip() or (root / "data"))
    code, result = service_set_override(payload=payload, storage_dir=storage_dir, project_root=root)
    return JSONResponse(status_code=code, content=result)


# =============================================================================
# GET / POST /api/epsilon/resumenIA/cached
# =============================================================================

@router.get("/api/epsilon/resumenIA/cached")
@router.get("/epsilon/resumenIA/cached")
def api_get_cached_epsilon_summaries(ids: str = Query(default="")):
    root = _get_project_root()
    storage_dir = Path(os.environ.get("RELEASE_DASHBOARD_STORAGE_DIR", "").strip() or (root / "data"))
    return service_get_cached_epsilon(ids=ids, storage_dir=storage_dir, project_root=root)


@router.post("/api/epsilon/resumenIA/cached")
@router.post("/epsilon/resumenIA/cached")
def api_post_cached_epsilon_summaries(payload: Dict[str, Any] = Body(...)):
    root = _get_project_root()
    storage_dir = Path(os.environ.get("RELEASE_DASHBOARD_STORAGE_DIR", "").strip() or (root / "data"))
    raw_ids = payload.get("ids") if isinstance(payload, dict) and isinstance(payload.get("ids"), list) else []
    return service_get_cached_epsilon(ids=raw_ids, storage_dir=storage_dir, project_root=root)


# =============================================================================
# GET /api/health/release-desk
# =============================================================================

@router.get("/api/health/release-desk")
@router.get("/health/release-desk")
def api_health_release_desk():
    root = _get_project_root()
    storage_dir = Path(os.environ.get("RELEASE_DASHBOARD_STORAGE_DIR", "").strip() or (root / "data"))
    code, payload = service_get_health(storage_dir=storage_dir, project_root=root)
    return JSONResponse(status_code=code, content=payload)


# =============================================================================
# GET / POST /api/teams/channels
# =============================================================================

@router.get("/api/teams/channels")
@router.get("/teams/channels")
def api_get_teams_channels():
    root = _get_project_root()
    storage_dir = Path(os.environ.get("RELEASE_DASHBOARD_STORAGE_DIR", "").strip() or (root / "data"))
    code, result = service_get_teams_channels(storage_dir=storage_dir, project_root=root)
    return JSONResponse(status_code=code, content=result)


@router.post("/api/teams/channels")
@router.post("/teams/channels")
def api_post_teams_channels(payload: Dict[str, Any] = Body(...)):
    root = _get_project_root()
    storage_dir = Path(os.environ.get("RELEASE_DASHBOARD_STORAGE_DIR", "").strip() or (root / "data"))
    code, result = service_set_teams_channels(payload=payload, storage_dir=storage_dir, project_root=root)
    return JSONResponse(status_code=code, content=result)


# =============================================================================
# GET /api/teams/audit
# =============================================================================

@router.get("/api/teams/audit")
@router.get("/teams/audit")
def api_get_teams_audit():
    root = _get_project_root()
    storage_dir = Path(os.environ.get("RELEASE_DASHBOARD_STORAGE_DIR", "").strip() or (root / "data"))
    code, result = service_get_teams_audit(storage_dir=storage_dir, project_root=root)
    return JSONResponse(status_code=code, content=result)


# =============================================================================
# POST /api/teams/send
# =============================================================================

@router.post("/api/teams/send")
@router.post("/teams/send")
def api_post_teams_send(payload: Dict[str, Any] = Body(...)):
    root = _get_project_root()
    storage_dir = Path(os.environ.get("RELEASE_DASHBOARD_STORAGE_DIR", "").strip() or (root / "data"))
    code, result = service_send_teams(payload=payload, storage_dir=storage_dir, project_root=root)
    return JSONResponse(status_code=code, content=result)


# =============================================================================
# POST /api/release-desk/upload-argos
# =============================================================================

@router.post("/api/release-desk/upload-argos")
@router.post("/release-desk/upload-argos")
def api_post_release_desk_upload_argos(payload: Dict[str, Any] = Body(...)):
    root = _get_project_root()
    storage_dir = Path(os.environ.get("RELEASE_DASHBOARD_STORAGE_DIR", "").strip() or (root / "data"))
    code, result = service_upload_argos_csv(payload=payload, storage_dir=storage_dir, project_root=root)
    return JSONResponse(status_code=code, content=result)


# =============================================================================
# POST /api/release-desk/generate-report
# =============================================================================

@router.post("/api/release-desk/generate-report")
@router.post("/release-desk/generate-report")
def api_post_release_desk_generate_report(payload: Dict[str, Any] = Body(...)):
    root = _get_project_root()
    storage_dir = Path(os.environ.get("RELEASE_DASHBOARD_STORAGE_DIR", "").strip() or (root / "data"))
    code, result = service_generate_release_report(payload=payload, storage_dir=storage_dir, project_root=root)
    return JSONResponse(status_code=code, content=result)
