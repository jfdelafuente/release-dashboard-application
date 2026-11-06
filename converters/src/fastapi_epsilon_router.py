# -*- coding: utf-8 -*-
"""
fastapi_epsilon_router.py
-------------------------
Router oficial de FastAPI para los endpoints de Epsilon IA en Producción.

Rutas expuestas:
  - POST /api/epsilon/generate (alias: POST /api/epsilon/resumen)
  - GET  /api/epsilon/resumenIA/{codigo}

Puede montarse directamente en la aplicación FastAPI corporativa (cso-incident-masivas-report
o cualquier microservicio FastAPI) mediante:
    from converters.src.fastapi_epsilon_router import router as epsilon_router
    app.include_router(epsilon_router, prefix="/api/epsilon", tags=["Epsilon IA"])
"""

import os
import sys
import time
import json
import ssl
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any, Dict, Optional
from datetime import datetime

from fastapi import APIRouter, Body, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse

# Asegurar importación de epsilon_service tanto si se ejecuta en el paquete como en local
try:
    from converters.src.epsilon_service import (
        generate_epsilon_summary,
        find_incident_in_local_dumps,
    )
except ImportError:
    _curr = Path(__file__).resolve()
    for parent in (_curr.parent, _curr.parent.parent, _curr.parent.parent.parent):
        if str(parent) not in sys.path:
            sys.path.insert(0, str(parent))
    from converters.src.epsilon_service import (
        generate_epsilon_summary,
        find_incident_in_local_dumps,
    )

router = APIRouter()

# Caché en memoria para mitigar ráfagas y proteger el servicio corporativo
# {codigo: (timestamp, data_dict, status_code)}
FASTAPI_EPSILON_CACHE: Dict[str, tuple[float, Dict[str, Any], int]] = {}


def _get_candidate_roots() -> list[Path]:
    """Devuelve las rutas base candidatas para datos y cachés (VPS y local)."""
    roots = []
    # 1. VPS persistente
    vps_storage = Path("/infocodes/var/storage/release-dashboard")
    if vps_storage.exists():
        roots.append(vps_storage)

    # 2. VPS current release
    vps_current = Path("/infocodes/project/release-dashboard-application/current")
    if vps_current.exists():
        roots.append(vps_current)

    # 3. Raíz del proyecto local deducida del archivo
    repo_root = Path(__file__).resolve().parent.parent.parent
    if repo_root.exists():
        roots.append(repo_root)

    # 4. Directorio de trabajo actual
    cwd = Path.cwd()
    if cwd not in roots:
        roots.append(cwd)

    return roots


def _get_cache_dir() -> Path:
    """Obtiene o inicializa el directorio de caché en disco."""
    for root in _get_candidate_roots():
        target = root / "data" / ".epsilon_cache" if (root / "data").exists() else root / ".epsilon_cache"
        try:
            target.mkdir(parents=True, exist_ok=True)
            return target
        except Exception:
            continue
    # Fallback temporal si no hubiera permisos
    tmp_target = Path("/tmp/.epsilon_cache")
    tmp_target.mkdir(parents=True, exist_ok=True)
    return tmp_target


def clear_fastapi_cache() -> None:
    """Invalida la caché en memoria (usado en uploads o re-ingestas)."""
    FASTAPI_EPSILON_CACHE.clear()


@router.post("/generate")
@router.post("/resumen")
def generate_summary(
    payload: Optional[Dict[str, Any]] = Body(default=None),
    mock: bool = Query(False, description="Forzar modo mock determinista sin llamada LLM"),
):
    """
    Genera y valida un resumen técnico de incidencia IT ejecutando el motor
    oficial de Epsilon IA con validación estricta Pydantic.
    """
    if payload is None or not isinstance(payload, dict) or not payload:
        raise HTTPException(
            status_code=400,
            detail={"success": False, "error": "Datos de incidencia insuficientes para generar resumen"},
        )

    # Manejo seguro si se invoca como función directa o vía FastAPI DI
    is_mock_query = mock if isinstance(mock, bool) else False

    # Detección de formato (Directo vs Wrapper)
    if "incident_data" in payload:
        incident_data = payload.get("incident_data", {})
        is_mock = is_mock_query or bool(payload.get("mock", False))
        model = payload.get("model")
        provider = payload.get("provider")
    else:
        incident_data = payload
        is_mock = is_mock_query
        model = None
        provider = None

    if not isinstance(incident_data, dict) or not incident_data:
        raise HTTPException(
            status_code=400,
            detail={"success": False, "error": "Datos de incidencia insuficientes para generar resumen"},
        )

    try:
        is_valid, data_or_errors, meta = generate_epsilon_summary(
            incident_data=incident_data,
            provider=provider,
            model=model,
            mock=is_mock,
        )
    except Exception as err:
        return JSONResponse(
            status_code=502,
            content={"success": False, "error": f"Fallo en el servicio LLM: {err}"},
        )

    if not is_valid:
        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "error": data_or_errors.get("error", "Error de validación de esquema Epsilon"),
                "validation_errors": data_or_errors.get("validation_errors", []),
                "raw_output": data_or_errors.get("raw_output", {}),
                "meta": meta,
            },
        )

    # Cacheo si incluye código de incidencia INC...
    code = (
        incident_data.get("codigo")
        or incident_data.get("id")
        or incident_data.get("ID de incidencia")
        or incident_data.get("id_incidencia")
        or ""
    )
    code_str = str(code).strip().upper()
    if code_str.startswith("INC"):
        try:
            cache_dir = _get_cache_dir()
            cache_file = cache_dir / f"{code_str}.json"
            cache_file.write_text(json.dumps(data_or_errors, ensure_ascii=False, indent=2), encoding="utf-8")
            FASTAPI_EPSILON_CACHE[code_str] = (time.time(), data_or_errors, 200)
        except Exception:
            pass

    response_payload = {
        "success": True,
        "data": data_or_errors,
        "meta": meta,
        **data_or_errors,
    }
    return JSONResponse(status_code=200, content=response_payload)


@router.get("/resumenIA/{codigo}")
def get_resumen_ia(
    codigo: str,
    force: bool = Query(False, description="Forzar refresco omitiendo caché"),
    refresh: bool = Query(False, description="Alias de force"),
    mock: bool = Query(False, description="Generar resumen mock offline"),
):
    """
    Proxy y generador de Resumen IA para una incidencia dada:
    1. Consulta caché en memoria o disco (si no se especifica force/refresh).
    2. Consulta en vivo al endpoint corporativo SOPTMC.
    3. Si SOPTMC falla, ejecuta fallback inteligente buscando en los volcados locales
       y generando el resumen mediante Epsilon Service con aviso de obsolescencia si > 2h.
    """
    codigo_clean = codigo.strip().upper()
    force_val = force if isinstance(force, bool) else False
    refresh_val = refresh if isinstance(refresh, bool) else False
    is_mock = mock if isinstance(mock, bool) else False
    force_refresh = force_val or refresh_val
    now = time.time()

    # 1. Caché en memoria
    if not force_refresh and codigo_clean in FASTAPI_EPSILON_CACHE:
        cached_time, cached_content, cached_status = FASTAPI_EPSILON_CACHE[codigo_clean]
        if now - cached_time < 900:  # 15 min TTL
            return JSONResponse(
                status_code=cached_status,
                content=cached_content,
                headers={"X-Cache-Status": "MEMORY_HIT"},
            )

    # 2. Consulta en vivo a SOPTMC si no es mock
    if not is_mock:
        target_url = f"https://soptmc.si.orange.es/MonTMC/api/epsilon/resumenIA/{codigo_clean}"
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            req = urllib.request.Request(
                target_url,
                headers={"User-Agent": "ReleaseDashboardFastAPI/1.0", "Accept": "application/json"},
            )
            with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
                content_bytes = resp.read()
                if resp.status == 200:
                    data = json.loads(content_bytes.decode("utf-8"))
                    FASTAPI_EPSILON_CACHE[codigo_clean] = (now, data, 200)
                    try:
                        cache_file = _get_cache_dir() / f"{codigo_clean}.json"
                        cache_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
                    except Exception:
                        pass
                    return JSONResponse(
                        status_code=200,
                        content=data,
                        headers={"X-Cache-Status": "LIVE_SOPTMC_HIT"},
                    )
        except Exception:
            pass  # Continuar a fallbacks

    # 3. Caché en disco previa
    cache_file = _get_cache_dir() / f"{codigo_clean}.json"
    if not force_refresh and cache_file.exists():
        try:
            data = json.loads(cache_file.read_text(encoding="utf-8"))
            FASTAPI_EPSILON_CACHE[codigo_clean] = (now, data, 200)
            return JSONResponse(
                status_code=200,
                content=data,
                headers={"X-Cache-Status": "DISK_HIT"},
            )
        except Exception:
            pass

    # 4. Fallback inteligente: buscar en volcados locales y generar al vuelo
    found = None
    for root_candidate in _get_candidate_roots():
        found = find_incident_in_local_dumps(codigo_clean, root_candidate)
        if found:
            break

    if found:
        incident_item, source_filename, file_mtime = found
        try:
            is_valid, summary_data, meta = generate_epsilon_summary(
                incident_data=incident_item,
                mock=is_mock,
            )
            if is_valid:
                is_stale = (now - file_mtime) > 7200  # Más de 2 horas
                hours_ago = round((now - file_mtime) / 3600.0, 1)
                summary_data["meta"] = {
                    "source": "local_dump_fallback",
                    "dump_file": source_filename,
                    "dump_timestamp": datetime.fromtimestamp(file_mtime).isoformat(),
                    "is_stale_warning": is_stale,
                    "stale_reason": (
                        f"El resumen se ha generado a partir de un volcado local con {hours_ago} horas de antigüedad; "
                        "el estado en Remedy en vivo podría diferir."
                        if is_stale
                        else None
                    ),
                    "llm_meta": meta,
                }
                FASTAPI_EPSILON_CACHE[codigo_clean] = (now, summary_data, 200)
                try:
                    cache_file.write_text(json.dumps(summary_data, ensure_ascii=False, indent=2), encoding="utf-8")
                except Exception:
                    pass
                return JSONResponse(
                    status_code=200,
                    content=summary_data,
                    headers={"X-Cache-Status": "LOCAL_DUMP_FALLBACK"},
                )
        except Exception as e:
            return JSONResponse(
                status_code=502,
                content={"success": False, "error": f"Error generando resumen desde volcado local: {e}"},
            )

    return JSONResponse(
        status_code=502,
        content={
            "success": False,
            "error": f"No se pudo obtener ni generar el resumen de Epsilon IA para la incidencia {codigo_clean}.",
        },
    )
