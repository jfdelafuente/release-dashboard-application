"""
Cliente para las APIs corporativas de MonTMC / Epsilon (Orange).

Permite consultar:
1. GET /api/epsilon/masivas?usuario={user}&dias={dias}: Listado de incidencias masivas recientes.
2. GET /api/eps/remedyG/{idRemedy}: Detalle técnico profundo y worklogs de resolutores de Remedy.
"""

from __future__ import annotations

import json
import logging
import os
import re
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger("montmc_client")

DEFAULT_MON_TMC_BASE_URL = "https://soptmc.si.orange.es/MonTMC"
DEFAULT_MON_TMC_USER = "jdelat"
DEFAULT_TIMEOUT = 15


class MonTMCError(Exception):
    """Excepción base para errores de comunicación o respuesta de MonTMC."""
    pass


class RemedyNotFoundError(MonTMCError):
    """Excepción cuando una incidencia no existe en Remedy (codigoResp != 0)."""
    pass


def _iso_to_dashboard_date(iso_str: Optional[str]) -> Optional[str]:
    """
    Convierte una fecha ISO-8601 (ej. '2026-11-11T16:22:43.000+00:00' o '2026-11-09T08:15:23Z')
    al formato canónico del dashboard ('DD/MM/YYYY HH:MM') en horario local de Madrid (Europe/Madrid).
    Si la fecha incluye zona horaria (UTC / Z / offset), se convierte automáticamente a CET/CEST.
    """
    if not iso_str or not isinstance(iso_str, str):
        return None
    val = iso_str.strip()
    if not val:
        return None

    try:
        from zoneinfo import ZoneInfo
        MADRID_TZ = ZoneInfo("Europe/Madrid")
    except Exception:
        from datetime import timezone, timedelta
        MADRID_TZ = timezone(timedelta(hours=1))

    # 1. Si es formato ISO (con T o con guiones YYYY-MM-DD)
    if "T" in val or (len(val) >= 10 and val[4] == "-" and val[7] == "-"):
        try:
            clean_iso = val.replace("Z", "+00:00")
            dt = datetime.fromisoformat(clean_iso)
            if dt.tzinfo is not None:
                dt = dt.astimezone(MADRID_TZ)
            return dt.strftime("%d/%m/%Y %H:%M")
        except Exception:
            pass

    # 2. Si ya es o parece DD/MM/YYYY o formatos sin T
    val_clean = re.sub(r'\.\d+', '', val)
    val_clean = val_clean.replace('Z', '').replace('T', ' ')

    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(val_clean[:19], fmt)
            return dt.strftime("%d/%m/%Y %H:%M")
        except ValueError:
            continue

    return val


def _normalize_priority(prioridad_p: Optional[str], prioridad: Optional[str]) -> str:
    """Normaliza la prioridad devolviendo un código estándar P1..P4 o valor legible."""
    if prioridad_p and isinstance(prioridad_p, str):
        p_clean = prioridad_p.strip().upper()
        if p_clean in ("P1", "P2", "P3", "P4"):
            return p_clean
    if prioridad and isinstance(prioridad, str):
        p_str = prioridad.strip().lower()
        if "crítica" in p_str or "critica" in p_str:
            return "P1"
        if "alta" in p_str:
            return "P2"
        if "media" in p_str:
            return "P3"
        if "baja" in p_str:
            return "P4"
        return prioridad.strip().title()
    return "P3"


def _normalize_status(estado_desc: Optional[str]) -> str:
    """Normaliza el estado textual a la nomenclatura canónica del dashboard."""
    if not estado_desc or not isinstance(estado_desc, str):
        return "Asignado"
    st = estado_desc.strip().upper()
    mapping = {
        "ASIGNADO": "Asignado",
        "EN CURSO": "En Curso",
        "EN PROGRESO": "En Progreso",
        "PENDIENTE": "Pendiente",
        "RESUELTO": "Resuelto",
        "CERRADO": "Cerrado",
        "CANCELADO": "Cancelado",
        "ABIERTO": "Abierto",
    }
    return mapping.get(st, estado_desc.strip().title())


def _normalize_urgency(urgencia: Optional[str]) -> str:
    """Normaliza la urgencia a Baja, Medio, Alta o Crítica."""
    if not urgencia or not isinstance(urgencia, str):
        return "Medio"
    u = urgencia.strip().lower()
    if "crit" in u:
        return "Crítica"
    if "alt" in u:
        return "Alta"
    if "baj" in u:
        return "Baja"
    if "med" in u:
        return "Medio"
    # Quitar posibles prefijos '1-', '2-', etc.
    m = re.match(r'^\d+\s*-\s*(.+)$', urgencia.strip())
    if m:
        return m.group(1).strip().title()
    return urgencia.strip().title()


class MonTMCClient:
    """Cliente HTTP desacoplado para endpoints corporativos de MonTMC / Epsilon."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        default_user: Optional[str] = None,
        timeout: int = DEFAULT_TIMEOUT,
    ):
        self.base_url = (base_url or os.environ.get("MON_TMC_BASE_URL", DEFAULT_MON_TMC_BASE_URL)).rstrip('/')
        self.default_user = default_user or os.environ.get("MON_TMC_USER", DEFAULT_MON_TMC_USER)
        self.timeout = timeout

        # Contexto SSL seguro pero tolerante con certificados intranet internos
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        self._ssl_context = ctx

    def _open_url(self, url: str) -> bytes:
        """Realiza una petición HTTP GET con reintento automático ante fallos transitorios."""
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "ReleaseDashboard-MonTMCClient/1.0",
                "Accept": "application/json",
            },
        )
        last_err: Optional[Exception] = None
        for attempt in range(2):
            try:
                with urllib.request.urlopen(req, context=self._ssl_context, timeout=self.timeout) as resp:
                    if resp.status != 200:
                        raise MonTMCError(f"HTTP status {resp.status} al consultar {url}")
                    return resp.read()
            except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as e:
                last_err = e
                if attempt == 0:
                    time.sleep(1.0)
                    continue
        raise MonTMCError(f"Fallo al conectar con MonTMC en {url}: {last_err}") from last_err

    def fetch_masivas(self, dias: int = 3, usuario: Optional[str] = None) -> Dict[str, Any]:
        """
        Consulta el listado de incidencias masivas de los últimos N días.

        GET /api/epsilon/masivas?usuario={user}&dias={dias}
        """
        user = usuario or self.default_user
        query = urllib.parse.urlencode({"usuario": user, "dias": dias})
        url = f"{self.base_url}/api/epsilon/masivas?{query}"
        logger.info("Consultando incidencias masivas MonTMC: %s", url)

        raw_bytes = self._open_url(url)
        try:
            data = json.loads(raw_bytes.decode("utf-8"))
        except Exception as e:
            raise MonTMCError(f"Respuesta JSON inválida de MonTMC masivas: {e}") from e

        if not isinstance(data, dict):
            raise MonTMCError(f"Formato inesperado devuelto por MonTMC (se esperaba objeto dict): {type(data)}")

        if not data.get("success", False) and "incidencias" not in data:
            msg = data.get("message") or data.get("error") or "Respuesta success=false sin datos"
            raise MonTMCError(f"Error devuelto por API MonTMC: {msg}")

        return data

    def fetch_remedy_detail(self, id_remedy: str) -> Dict[str, Any]:
        """
        Consulta el detalle profundo, eventos y worklogs técnicos de una incidencia.

        GET /api/eps/remedyG/{idRemedy}
        """
        clean_id = (id_remedy or "").strip().upper()
        if not clean_id:
            raise ValueError("id_remedy no puede estar vacío")

        url = f"{self.base_url}/api/eps/remedyG/{urllib.parse.quote(clean_id)}"
        logger.info("Consultando detalle Remedy MonTMC: %s", url)

        raw_bytes = self._open_url(url)
        try:
            data = json.loads(raw_bytes.decode("utf-8"))
        except Exception as e:
            raise MonTMCError(f"Respuesta JSON inválida de Remedy detail: {e}") from e

        if not isinstance(data, dict):
            raise MonTMCError(f"Formato inesperado devuelto por Remedy detail: {type(data)}")

        codigo_resp = data.get("codigoResp")
        if codigo_resp is not None and codigo_resp != 0:
            msg = data.get("descResp") or f"codigoResp={codigo_resp}"
            raise RemedyNotFoundError(f"Incidencia {clean_id} no encontrada en Remedy: {msg}")

        return data

    def normalize_mon_tmc_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transforma un registro devuelto por MonTMC /api/epsilon/masivas al esquema
        canónico del dataset masivo del Release Dashboard.
        """
        if not isinstance(record, dict):
            return {}

        incident_id = str(record.get("idRemedy") or "").strip()
        prioridad_p = record.get("prioridadP")
        prioridad_text = record.get("prioridad")
        prioridad_norm = _normalize_priority(prioridad_p, prioridad_text)

        desc = record.get("resumen") or record.get("detalle") or ""
        estatus = _normalize_status(record.get("estadoDesc"))

        fecha_envio = _iso_to_dashboard_date(record.get("fechaCreacion"))
        if not fecha_envio:
            fecha_envio = datetime.now().strftime("%d/%m/%Y %H:%M")

        fecha_resolucion = _iso_to_dashboard_date(record.get("fechaResolucion"))
        grupo_asignado = (record.get("grupoAsignado") or "").strip()
        grupo_resolutor = (record.get("grupoResolutor") or "").strip()
        urgencia = _normalize_urgency(record.get("urgencia"))

        peticionario = (record.get("peticionarioNombre") or "").strip()

        # Mapeo canónico exacto requerido por schemas.py
        normalized: Dict[str, Any] = {
            "ID de incidencia": incident_id,
            "Prioridad": prioridad_norm,
            "Descripción": desc.strip(),
            "Estatus": estatus,
            "Fecha de envío": fecha_envio,
            "Grupo asignado": grupo_asignado,
            "Urgencia": urgencia,
            "Impacto": "Masiva",
        }

        if fecha_resolucion:
            normalized["Fecha de última resolución"] = fecha_resolucion

        if grupo_resolutor:
            normalized["Grupo Resolutor"] = grupo_resolutor

        if peticionario:
            normalized["Grupo Remitente"] = peticionario

        # Atributos suplementarios enriquecidos
        if record.get("fechaUltimaModificacion"):
            normalized["fechaUltimaModificacion"] = record["fechaUltimaModificacion"]
        if record.get("solucion"):
            normalized["detalleSolucion"] = record["solucion"]
        if record.get("producto"):
            normalized["producto"] = record["producto"]

        return normalized
