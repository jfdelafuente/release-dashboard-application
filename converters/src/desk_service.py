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

import csv
import io
import json
import logging
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from converters.src.montmc_client import MonTMCClient, MonTMCError, RemedyNotFoundError
from converters.src.release_desk_overrides import (
    add_nota_override,
    delete_nota_override,
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
    from converters.cli.generate_release_report_html import build_release_report_html
except ImportError:
    try:
        from generate_release_report_html import build_release_report_html
    except ImportError:
        build_release_report_html = None

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
    """Guarda un override (fecha prevista o nota de seguimiento) de forma atómica y concurrente."""
    target_storage = resolve_storage_dir(storage_dir, project_root)
    rel = str(payload.get("release_name") or "")
    inc_id = str(payload.get("incident_id") or "")
    action = str(payload.get("action") or "").lower().strip()

    try:
        if action == "add_nota" or "nota_texto" in payload or ("texto" in payload and action != "delete_nota"):
            texto = str(payload.get("texto") or payload.get("nota_texto") or "")
            fecha = str(payload.get("fecha") or "") or None
            result = add_nota_override(
                storage_dir=target_storage,
                release_name=rel,
                incident_id=inc_id,
                texto=texto,
                fecha=fecha,
            )
            return 200, result
        elif action == "delete_nota" or "delete_nota_id" in payload:
            nota_id = str(payload.get("nota_id") or payload.get("delete_nota_id") or "")
            result = delete_nota_override(
                storage_dir=target_storage,
                release_name=rel,
                incident_id=inc_id,
                nota_id=nota_id,
            )
            return 200, result
        else:
            result = set_fecha_prevista_override(
                storage_dir=target_storage,
                release_name=rel,
                incident_id=inc_id,
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


# =============================================================================
# Servicio: Carga de CSV de Grafana Argos (Pruebas PaP) y Regeneración de Reporte
# =============================================================================

ARGOS_PAP_COLUMNS: List[str] = [
    "mv_id", "prj", "key_test_plan", "proyecto_test", "test_plan",
    "tribu_id", "resumen_test_plan", "sistema_test", "release_planificada_test_plan",
    "test_environment_test_plan", "test_layer_test_plan", "fix_versions_test_plan",
    "prioridad_test_plan", "tipologia_prueba", "agrupacion_funcional",
    "blocking_comment", "num_test", "pass", "pending", "block", "verify", "executing"
]


def _read_argos_csv_content(content_str: str, filename: str = "") -> List[Dict[str, Any]]:
    """Parsea el contenido de texto de un CSV de Argos y normaliza las columnas."""
    rows: List[Dict[str, Any]] = []
    lines = [line for line in content_str.splitlines() if line.strip()]
    if not lines:
        return rows

    header_line = lines[0]
    delimiter = ";" if header_line.count(";") > header_line.count(",") else ","
    reader = csv.DictReader(lines, delimiter=delimiter)

    fn_lower = (filename or "").lower()

    for raw_row in reader:
        # Normalizar claves de columnas a minúsculas
        norm_row = {}
        for k, v in raw_row.items():
            if k is not None:
                norm_row[k.strip().lower()] = (v or "").strip()

        prj = (norm_row.get("prj") or "").strip().upper()
        test_plan = (norm_row.get("test_plan") or norm_row.get("key_test_plan") or "").strip()
        resumen = (norm_row.get("resumen_test_plan") or "").strip()

        # Descartar filas sin identificación de plan o resumen
        if not test_plan and not resumen:
            continue

        raw_tip = (norm_row.get("tipologia_prueba") or "").strip().upper()
        if "REGRE" in raw_tip:
            tipologia = "REGRESION"
        elif "PROGRE" in raw_tip:
            tipologia = "PROGRESION"
        elif "regres" in fn_lower and not prj.startswith("PRJ-"):
            tipologia = "REGRESION"
        elif "progres" in fn_lower or prj.startswith("PRJ-"):
            tipologia = "PROGRESION"
        else:
            tipologia = "PROGRESION" if prj.startswith("PRJ-") else "REGRESION"

        row_dict: Dict[str, Any] = {}
        for col in ARGOS_PAP_COLUMNS:
            row_dict[col] = norm_row.get(col, "")
        row_dict["prj"] = prj
        row_dict["tipologia_prueba"] = tipologia

        # Asegurar campos numéricos
        for int_col in ["num_test", "pass", "pending", "block", "verify", "executing"]:
            try:
                row_dict[int_col] = int(float(norm_row.get(int_col) or 0))
            except (ValueError, TypeError):
                row_dict[int_col] = 0

        rows.append(row_dict)

    return rows


def service_upload_argos_csv(
    payload: Any,
    storage_dir: Optional[Path] = None,
    project_root: Optional[Path] = None,
) -> Tuple[int, Dict[str, Any]]:
    """
    Recibe uno o varios archivos CSV de Grafana Argos (Progresión y/o Regresión),
    los valida, consolida en data/storage/projects/{release}_grafana_pap.csv
    y regenera de forma inmediata el informe ejecutivo HTML 360°.
    """
    root = resolve_project_root(project_root)
    storage = resolve_storage_dir(storage_dir, root)

    if not isinstance(payload, dict):
        return 400, {"success": False, "error": "Cuerpo de solicitud inválido (debe ser JSON dict)"}

    release_name = (payload.get("release_name") or payload.get("release") or "").strip().upper()
    if not release_name:
        return 400, {"success": False, "error": "Falta el parámetro 'release_name' o 'release'"}

    raw_files = payload.get("files")
    if not isinstance(raw_files, list) or len(raw_files) == 0:
        return 400, {"success": False, "error": "Se requiere al menos un archivo CSV en 'files'"}

    new_rows: List[Dict[str, Any]] = []
    processed_files: List[str] = []
    uploaded_typologies = set()

    for item in raw_files:
        if not isinstance(item, dict):
            continue
        fname = (item.get("filename") or "").strip()
        content = item.get("content") or ""
        if not content:
            continue
        parsed_rows = _read_argos_csv_content(content, filename=fname)
        if parsed_rows:
            processed_files.append(fname or "unnamed.csv")
            for r in parsed_rows:
                uploaded_typologies.add(r.get("tipologia_prueba"))
            new_rows.extend(parsed_rows)

    if not new_rows:
        return 400, {
            "success": False,
            "error": "No se encontraron filas válidas en los archivos CSV suministrados. Verifica las columnas de Grafana Argos.",
        }

    projects_dir = storage / "storage" / "projects"
    projects_dir.mkdir(parents=True, exist_ok=True)
    target_csv = projects_dir / f"{release_name}_grafana_pap.csv"

    # Preservar tipologías existentes si la carga actual sólo actualizó una de ellas
    final_rows: List[Dict[str, Any]] = []
    if target_csv.is_file():
        try:
            existing_content = target_csv.read_text(encoding="utf-8-sig", errors="ignore")
            existing_rows = _read_argos_csv_content(existing_content, filename=target_csv.name)
            for ex_row in existing_rows:
                ex_tip = ex_row.get("tipologia_prueba")
                # Si la tipología existente no vino en esta subida, la conservamos
                if ex_tip not in uploaded_typologies:
                    final_rows.append(ex_row)
        except Exception as exc:
            logger.warning("No se pudieron leer filas previas de %s: %s", target_csv, exc)

    final_rows.extend(new_rows)

    # Deduplicar filas por clave compuesta (tipologia, test_plan/resumen, prj)
    dedup_map: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
    for r in final_rows:
        key = (
            str(r.get("tipologia_prueba") or ""),
            str(r.get("test_plan") or r.get("key_test_plan") or r.get("resumen_test_plan") or ""),
            str(r.get("prj") or ""),
        )
        dedup_map[key] = r

    consolidated_rows = list(dedup_map.values())

    # Escribir archivo CSV de forma atómica
    lock = get_path_lock(target_csv)
    with lock:
        try:
            fd, tmp_path_str = tempfile.mkstemp(dir=str(projects_dir), prefix="argos_pap_", suffix=".tmp")
            os.close(fd)
            tmp_path = Path(tmp_path_str)
            with open(tmp_path, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=ARGOS_PAP_COLUMNS, extrasaction="ignore")
                writer.writeheader()
                for r in consolidated_rows:
                    writer.writerow(r)
            tmp_path.replace(target_csv)
        except Exception as exc:
            logger.exception("Error al guardar CSV de Argos en %s: %s", target_csv, exc)
            return 500, {"success": False, "error": f"Error al guardar archivo CSV de Argos: {exc}"}

    # Regenerar informe ejecutivo HTML inmediatamente
    report_generated = False
    report_rel_url = f"/dashboards/informes/comunicado-release-{release_name}/"
    output_html = root / "dashboards" / "informes" / f"comunicado-release-{release_name}" / "index.html"

    if build_release_report_html is not None:
        try:
            output_html.parent.mkdir(parents=True, exist_ok=True)
            build_release_report_html(
                release=release_name,
                output_path=output_html,
                grafana_csv=target_csv,
            )
            report_generated = True
        except Exception as exc:
            logger.exception("Error compilando informe HTML tras subida de Argos para %s: %s", release_name, exc)

    # Calcular métricas para retroalimentación al usuario
    total_tests = sum(int(r.get("num_test") or 0) for r in consolidated_rows)
    pass_count = sum(int(r.get("pass") or 0) for r in consolidated_rows)
    block_count = sum(int(r.get("block") or 0) for r in consolidated_rows)
    pending_count = sum(int(r.get("pending") or 0) for r in consolidated_rows)
    pass_rate = round((pass_count / total_tests * 100), 1) if total_tests > 0 else 0.0
    prog_rows = [r for r in consolidated_rows if r.get("tipologia_prueba") == "PROGRESION"]
    reg_rows = [r for r in consolidated_rows if r.get("tipologia_prueba") == "REGRESION"]

    return 200, {
        "success": True,
        "release": release_name,
        "processed_files": processed_files,
        "total_test_plans": len(consolidated_rows),
        "total_tests": total_tests,
        "pass_count": pass_count,
        "block_count": block_count,
        "pending_count": pending_count,
        "pass_rate": pass_rate,
        "progression_plans": len(prog_rows),
        "regression_plans": len(reg_rows),
        "report_generated": report_generated,
        "report_url": report_rel_url,
        "message": (
            f"Resultados PaP de Argos actualizados ({total_tests} pruebas, {pass_rate}% pass). "
            f"Informe HTML de release {release_name} regenerado con éxito."
        ),
    }


def service_generate_release_report(
    payload: Any,
    storage_dir: Optional[Path] = None,
    project_root: Optional[Path] = None,
) -> Tuple[int, Dict[str, Any]]:
    """
    Regenera bajo demanda el Informe Ejecutivo HTML 360° para la release indicada.
    """
    root = resolve_project_root(project_root)
    storage = resolve_storage_dir(storage_dir, root)

    if not isinstance(payload, dict):
        return 400, {"success": False, "error": "Cuerpo de solicitud inválido (debe ser JSON dict)"}

    release_name = (payload.get("release_name") or payload.get("release") or "").strip().upper()
    if not release_name:
        return 400, {"success": False, "error": "Falta el parámetro 'release' o 'release_name'"}

    if build_release_report_html is None:
        return 500, {"success": False, "error": "Módulo generate_release_report_html no disponible en el servidor"}

    output_html = root / "dashboards" / "informes" / f"comunicado-release-{release_name}" / "index.html"
    grafana_csv = storage / "storage" / "projects" / f"{release_name}_grafana_pap.csv"
    if not grafana_csv.is_file():
        grafana_csv = None

    try:
        output_html.parent.mkdir(parents=True, exist_ok=True)
        build_release_report_html(
            release=release_name,
            output_path=output_html,
            grafana_csv=grafana_csv,
        )
        return 200, {
            "success": True,
            "release": release_name,
            "report_url": f"/dashboards/informes/comunicado-release-{release_name}/",
            "message": f"Informe ejecutivo HTML para {release_name} regenerado con éxito.",
        }
    except Exception as exc:
        logger.exception("Error al regenerar informe HTML para %s: %s", release_name, exc)
        return 500, {"success": False, "error": f"Error al regenerar informe HTML: {exc}"}
