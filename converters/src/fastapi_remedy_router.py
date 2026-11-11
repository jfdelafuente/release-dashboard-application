# -*- coding: utf-8 -*-
"""
fastapi_remedy_router.py
------------------------
Router oficial de FastAPI para los endpoints de integración con MonTMC Remedy en Producción.

Rutas expuestas:
  - POST /api/sync-remedy (y alias POST /sync-remedy): sincronización incremental de incidencias
  - GET  /api/remedy/detail/{id_remedy} (y alias GET /detail/{id_remedy}): detalle y notas de Remedy

Puede montarse directamente en la aplicación FastAPI corporativa (cso-incident-masivas-report
o cualquier microservicio FastAPI) mediante:
    from converters.src.fastapi_remedy_router import router as remedy_router
    app.include_router(remedy_router, prefix="/api", tags=["Remedy MonTMC Integration"])
o sin prefijo si el router ya define rutas absolutas.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
import sys
import time
from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, HTTPException, Query, Response
from fastapi.responses import JSONResponse

# Asegurar importación de módulos hermanos tanto en ejecución local como empaquetada
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

logger = logging.getLogger("fastapi_remedy_router")

router = APIRouter(tags=["Remedy MonTMC Integration"])

# Caché en memoria para detalle técnico de Remedy: {id_remedy: (timestamp, payload_dict, status_code)}
FASTAPI_REMEDY_CACHE: Dict[str, tuple[float, Dict[str, Any], int]] = {}
CACHE_TTL_SECONDS = 300  # 5 minutos


def _get_project_root() -> Path:
    """Resuelve la raíz del proyecto para localizar ficheros de datos y scripts."""
    env_root = os.environ.get("RELEASE_DASHBOARD_ROOT", "").strip()
    if env_root and Path(env_root).is_dir():
        return Path(env_root)

    # Entorno estándar de producción en VPS
    vps_current = Path("/infocodes/project/release-dashboard-application/current")
    if vps_current.is_dir():
        return vps_current

    # Raíz deducida a partir de este fichero
    repo_root = Path(__file__).resolve().parent.parent.parent
    if repo_root.is_dir():
        return repo_root

    return Path.cwd()


def _get_cache_dir() -> Path:
    """Obtiene o crea el directorio de caché persistente en disco para ficheros Remedy."""
    # 1. Almacenamiento persistente en VPS
    vps_storage = Path("/infocodes/var/storage/release-dashboard")
    if vps_storage.is_dir():
        target = vps_storage / ".remedy_cache"
        try:
            target.mkdir(parents=True, exist_ok=True)
            return target
        except Exception:
            pass

    # 2. Directorio data/.remedy_cache del proyecto
    root = _get_project_root()
    target = root / "data" / ".remedy_cache"
    try:
        target.mkdir(parents=True, exist_ok=True)
        return target
    except Exception:
        pass

    # 3. Directorio temporal del sistema
    tmp_target = Path("/tmp/.remedy_cache")
    tmp_target.mkdir(parents=True, exist_ok=True)
    return tmp_target


def clear_fastapi_remedy_cache() -> None:
    """Limpia la caché en memoria (útil tras sincronizaciones o en pruebas unitarias)."""
    FASTAPI_REMEDY_CACHE.clear()


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
    if sync_remedy_incidents is None:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": "Módulo de sincronización MonTMC no disponible"},
        )

    # Extraer parámetros dando prioridad al cuerpo JSON y fallback a query params
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

    root = _get_project_root()
    logger.info("Iniciando sync_remedy: dias=%d, usuario=%s, root=%s", target_dias, target_user, root)

    try:
        result = sync_remedy_incidents(
            dias=target_dias,
            usuario=target_user,
            project_root=root,
        )
        status_code = 200 if result.get("success") else 502
        return JSONResponse(status_code=status_code, content=result)
    except Exception as e:
        logger.exception("Error inesperado ejecutando sincronización Remedy: %s", e)
        return JSONResponse(
            status_code=502,
            content={"success": False, "error": f"Fallo en sincronización Remedy: {e}"},
        )


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
    now = time.time()

    # 1. Caché en memoria
    if not force_refresh and clean_id in FASTAPI_REMEDY_CACHE:
        cached_time, cached_payload, cached_status = FASTAPI_REMEDY_CACHE[clean_id]
        if now - cached_time < CACHE_TTL_SECONDS:
            resp_copy = dict(cached_payload)
            resp_copy["_cached"] = True
            return JSONResponse(
                status_code=cached_status,
                content=resp_copy,
                headers={"X-Cache-Status": "MEMORY_HIT"},
            )

    # 2. Consulta en vivo a la API MonTMC
    try:
        client = MonTMCClient()
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

        FASTAPI_REMEDY_CACHE[clean_id] = (now, payload, 200)

        # Persistencia en disco para fallback ante caídas de red
        try:
            cache_file = _get_cache_dir() / f"{clean_id}.json"
            cache_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as disk_err:
            logger.debug("No se pudo escribir caché en disco para %s: %s", clean_id, disk_err)

        return JSONResponse(
            status_code=200,
            content=payload,
            headers={"X-Cache-Status": "LIVE_SOPTMC_HIT"},
        )

    except RemedyNotFoundError as e:
        logger.info("Incidencia no encontrada en Remedy: %s (%s)", clean_id, e)
        return JSONResponse(
            status_code=404,
            content={"success": False, "error": str(e), "idRemedy": clean_id},
        )

    except Exception as e:
        logger.warning("Error consultando Remedy en MonTMC para %s: %s. Verificando caché en disco...", clean_id, e)

    # 3. Fallback a caché en disco previa
    cache_file = _get_cache_dir() / f"{clean_id}.json"
    if not force_refresh and cache_file.exists():
        try:
            disk_payload = json.loads(cache_file.read_text(encoding="utf-8"))
            disk_payload["_cached"] = True
            disk_payload["_source"] = "disk_fallback"
            return JSONResponse(
                status_code=200,
                content=disk_payload,
                headers={"X-Cache-Status": "DISK_FALLBACK"},
            )
        except Exception as read_err:
            logger.debug("Error leyendo caché en disco para %s: %s", clean_id, read_err)

    return JSONResponse(
        status_code=502,
        content={
            "success": False,
            "error": f"No se pudo consultar el detalle de Remedy para {clean_id} ni se dispone de copia local",
            "idRemedy": clean_id,
        },
    )
