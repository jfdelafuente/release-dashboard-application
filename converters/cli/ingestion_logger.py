#!/usr/bin/env python3
"""
Módulo de Trazabilidad y Auditoría de Ingesta y Evaluación de Incidencias.
Registra trazas persistentes de la carga de ficheros CSV, conversión a JSON,
llamadas a Epsilon IA, redacción de mensajes ejecutivos y auditoría de completitud
por incidencia en data/logs/ingestion_audit.log y data/output/ingestion_audit_summary.json.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional


LOG_RELATIVE_PATH = Path("data") / "logs" / "ingestion_audit.log"
AUDIT_SUMMARY_RELATIVE_PATH = Path("data") / "output" / "ingestion_audit_summary.json"


def get_log_file_path(project_root: Optional[Path] = None) -> Path:
    root = Path(project_root) if project_root else Path.cwd()
    path = root / LOG_RELATIVE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def get_summary_file_path(project_root: Optional[Path] = None) -> Path:
    root = Path(project_root) if project_root else Path.cwd()
    path = root / AUDIT_SUMMARY_RELATIVE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def append_to_log(text: str, project_root: Optional[Path] = None) -> None:
    """Escribe o anexa texto directamente en el fichero de log de auditoría."""
    log_file = get_log_file_path(project_root)
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(text.rstrip() + "\n")
    except Exception as e:
        print(f"[WARN] No se pudo escribir en log de auditoría {log_file}: {e}")


def log_upload_start(filename: str, size_bytes: int, dashboard_type: str, project_root: Optional[Path] = None) -> None:
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    header = (
        f"\n{'=' * 80}\n"
        f"PROCESO DE INGESTA DE INCIDENCIAS - {now_str}\n"
        f"{'=' * 80}\n"
        f"[{now_str}] [UPLOAD_START] Fichero recibido: {filename} ({size_bytes:,} bytes) | Tipo: {dashboard_type}\n"
    )
    append_to_log(header, project_root)


def log_conversion_result(
    filename: str,
    success: bool,
    elapsed_sec: float,
    output_file: Optional[str] = None,
    record_count: Optional[int] = None,
    error_details: Optional[str] = None,
    project_root: Optional[Path] = None,
) -> None:
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if success:
        rec_info = f" ({record_count} registros)" if record_count is not None else ""
        out_info = f" -> Generado: {output_file}" if output_file else ""
        msg = f"[{now_str}] [CONVERT_OK] Conversión CSV a JSON completada en {elapsed_sec:.3f}s{rec_info}{out_info}\n"
    else:
        msg = (
            f"[{now_str}] [CONVERT_ERROR] Falló la conversión de {filename} tras {elapsed_sec:.3f}s\n"
            f"  Detalles del error: {error_details or 'Desconocido'}\n"
        )
    append_to_log(msg, project_root)


def log_background_start(task_name: str, pid: Optional[int] = None, project_root: Optional[Path] = None) -> None:
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    pid_str = f" (PID {pid})" if pid else ""
    msg = f"[{now_str}] [BACKGROUND_TASK] Disparada tarea asíncrona '{task_name}'{pid_str} desacoplada del ciclo HTTP.\n"
    append_to_log(msg, project_root)


def audit_incident_completeness(
    item: dict[str, Any],
    epsilon_data: Optional[dict[str, Any]],
    epsilon_reason: Optional[str],
    agent_msgs: Optional[dict[str, Any]],
    evaluation: Optional[dict[str, Any]] = None,
    is_terminal: bool = False,
) -> dict[str, Any]:
    """Audita una incidencia específica determinando si tiene información completa

    (resumen_ia y mensajes_ejecutivos) y justificando la causa exacta de faltantes.
    """
    inc_id = item.get("ID de incidencia") or item.get("id") or "DESCONOCIDO"
    title = item.get("Descripción") or item.get("descripcion") or item.get("titulo") or ""
    status = item.get("Estatus") or item.get("estatus") or item.get("Estado") or item.get("estado") or "Asignado"
    nominal_prio = item.get("Prioridad") or item.get("prioridad") or "Media"
    sistemas = item.get("Grupo asignado") or item.get("sistemas") or ""

    # 1. Auditoría de Resumen IA
    has_resumen_ia = False
    ia_origen = None
    ia_causa_falta = None

    if is_terminal:
        ia_causa_falta = f"Incidencia en estado terminal '{status}' (Cerrado/Resuelto): omitida según ITIL/SRE"
    elif epsilon_data and isinstance(epsilon_data, dict):
        prob = epsilon_data.get("problema") or ""
        imp = epsilon_data.get("impacto") or ""
        sol = epsilon_data.get("solucion") or ""
        causa = epsilon_data.get("causa_raiz") or ""
        if prob or imp or sol or causa:
            has_resumen_ia = True
            ia_origen = epsilon_reason or "Epsilon Telemetría IA"
        else:
            ia_causa_falta = "Epsilon devolvió respuesta vacía o sin campos estructurados (problema/impacto/solución)"
    else:
        ia_causa_falta = epsilon_reason or "Epsilon no devolvió resumen IA para esta incidencia"

    # 2. Auditoría de Mensajes Ejecutivos
    has_mensajes_ejecutivos = False
    fases_aprobadas = []
    msgs_causa_falta = None

    if is_terminal:
        msgs_causa_falta = f"Incidencia en estado terminal '{status}': no requiere comunicación oficial urgente"
    elif agent_msgs and isinstance(agent_msgs, dict):
        for phase in ["apertura", "seguimiento", "cierre"]:
            pdata = agent_msgs.get(phase)
            if isinstance(pdata, dict) and pdata.get("completo") and pdata.get("estado") != "pendiente":
                fases_aprobadas.append(phase)
        if fases_aprobadas:
            has_mensajes_ejecutivos = True
        else:
            msgs_causa_falta = (
                "Pendiente de redacción/aprobación por el agente incident-reporter "
                "(registro en data/agent_executive_messages.json sin mensaje definitivo)"
            )
    else:
        msgs_causa_falta = (
            "Pendiente de redacción oficial por el agente incident-reporter "
            "(sin entrada en data/agent_executive_messages.json)"
        )

    # 3. Auditoría de Severidad y Criticidad
    eval_info = evaluation or {}
    sug_prio = eval_info.get("prioridad_sugerida") or nominal_prio
    es_disc = bool(eval_info.get("es_discrepancia"))
    disc_delta = eval_info.get("discrepancia_delta", 0)
    disc_motivo = eval_info.get("discrepancia_motivo") or ""
    proceso = (eval_info.get("evaluacion") or {}).get("proceso_negocio") or "General"

    # 4. Dictamen de Estado de Información
    if is_terminal:
        estado_info = "NO_APLICA"
        causa_global = f"Incidencia en estado terminal ({status})"
    elif has_resumen_ia and has_mensajes_ejecutivos:
        estado_info = "COMPLETA"
        causa_global = "Información completa (Resumen IA y Mensajes Ejecutivos oficiales listos)"
    elif has_resumen_ia and not has_mensajes_ejecutivos:
        estado_info = "PARCIAL"
        causa_global = f"Resumen IA OK | Mensajes ejecutivos faltantes: {msgs_causa_falta}"
    elif not has_resumen_ia and has_mensajes_ejecutivos:
        estado_info = "PARCIAL"
        causa_global = f"Mensajes ejecutivos OK | Resumen IA faltante: {ia_causa_falta}"
    else:
        estado_info = "INCOMPLETA"
        causa_global = f"Falta Resumen IA ({ia_causa_falta}) y Faltan Mensajes Ejecutivos ({msgs_causa_falta})"

    return {
        "id": inc_id,
        "titulo": title[:120],
        "estatus": status,
        "is_terminal": is_terminal,
        "sistemas": sistemas,
        "prioridad_nominal": nominal_prio,
        "prioridad_sugerida": sug_prio,
        "es_discrepancia": es_disc,
        "discrepancia_delta": disc_delta,
        "discrepancia_motivo": disc_motivo,
        "proceso_critico": proceso,
        "resumen_ia": {
            "disponible": has_resumen_ia,
            "origen": ia_origen,
            "causa_falta": ia_causa_falta,
        },
        "mensajes_ejecutivos": {
            "disponible": has_mensajes_ejecutivos,
            "fases_aprobadas": fases_aprobadas,
            "causa_falta": msgs_causa_falta,
        },
        "estado_informacion": estado_info,
        "causa_global": causa_global,
    }


def write_batch_audit(
    source_file: str,
    audit_records: list[dict[str, Any]],
    elapsed_sec: float,
    project_root: Optional[Path] = None,
) -> Path:
    """Escribe el informe detallado de auditoría en el log y el resumen JSON en data/output/."""
    root = Path(project_root) if project_root else Path.cwd()
    now = datetime.now()
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")

    total = len(audit_records)
    completas = sum(1 for r in audit_records if r["estado_informacion"] == "COMPLETA")
    parciales = sum(1 for r in audit_records if r["estado_informacion"] == "PARCIAL")
    incompletas = sum(1 for r in audit_records if r["estado_informacion"] == "INCOMPLETA")
    terminales = sum(1 for r in audit_records if r["estado_informacion"] == "NO_APLICA")
    con_ia = sum(1 for r in audit_records if r["resumen_ia"]["disponible"])
    con_msgs = sum(1 for r in audit_records if r["mensajes_ejecutivos"]["disponible"])
    discrepancias = sum(1 for r in audit_records if r["es_discrepancia"])

    # 1. Construir texto para el log persistente
    lines = [
        f"\n{'-' * 80}",
        f"AUDITORÍA DETALLADA DE INCIDENCIAS ({total} tickets) - {now_str}",
        f"Origen: {source_file}",
        f"{'-' * 80}",
    ]

    for idx, r in enumerate(audit_records, start=1):
        status_tag = f"[{r['estado_informacion']}]"
        disc_tag = f" -> SUGERIDA {r['prioridad_sugerida']} (DISCREPANCIA)" if r['es_discrepancia'] else ""
        lines.append(
            f"{idx:02d}. {r['id']} | Estatus: {r['estatus']} | Remedy: {r['prioridad_nominal']}{disc_tag} | {status_tag}"
        )
        if r.get("titulo"):
            lines.append(f"    Título: {r['titulo']}")

        # Resumen IA
        if r["resumen_ia"]["disponible"]:
            lines.append(f"    * Resumen IA: [OK] ({r['resumen_ia']['origen']})")
        else:
            lines.append(f"    * Resumen IA: [FALTA] Causa: {r['resumen_ia']['causa_falta']}")

        # Mensajes ejecutivos
        if r["mensajes_ejecutivos"]["disponible"]:
            fases_txt = ", ".join(r["mensajes_ejecutivos"]["fases_aprobadas"]) or "completado"
            lines.append(f"    * Mensajes Ejecutivos: [OK] (Fases aprobadas: {fases_txt} | Origen: incident-reporter)")
        else:
            lines.append(f"    * Mensajes Ejecutivos: [PENDIENTE] Causa: {r['mensajes_ejecutivos']['causa_falta']}")

        # Criticidad / Discrepancia si aplica
        if r["es_discrepancia"]:
            lines.append(f"    * Criticidad ITIL: {r['prioridad_sugerida']} (Proceso: {r['proceso_critico']} | Motivo: {r['discrepancia_motivo']})")

        lines.append(f"    * Dictamen: {r['causa_global']}\n")

    lines.extend([
        f"{'=' * 80}",
        f"BALANCE GLOBAL DE INFORMACIÓN DE INGESTA",
        f"{'=' * 80}",
        f"  Total incidencias analizadas:    {total}",
        f"  * Información COMPLETA (IA+Comms): {completas}",
        f"  * Información PARCIAL:            {parciales}",
        f"  * Información INCOMPLETA:         {incompletas}",
        f"  * Omitidas por Estado Terminal:   {terminales}",
        f"  ------------------------------------------------",
        f"  * Con Resumen IA disponible:      {con_ia} / {total}",
        f"  * Con Mensajes Ejecutivos listos: {con_msgs} / {total}",
        f"  * Con Discrepancias de severidad: {discrepancias} / {total}",
        f"  Tiempo total de evaluación:       {elapsed_sec:.2f}s",
        f"{'=' * 80}\n"
    ])

    append_to_log("\n".join(lines), project_root)

    # 2. Generar el resumen estructurado JSON
    summary_data = {
        "_metadata": {
            "type": "ingestion_audit_summary",
            "version": "1.0.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source_file": source_file,
            "elapsed_seconds": round(elapsed_sec, 3),
            "kpis": {
                "total_tickets": total,
                "completas_count": completas,
                "parciales_count": parciales,
                "incompletas_count": incompletas,
                "terminales_omitidas_count": terminales,
                "con_resumen_ia_count": con_ia,
                "sin_resumen_ia_count": total - con_ia,
                "con_mensajes_ejecutivos_count": con_msgs,
                "sin_mensajes_ejecutivos_count": total - con_msgs,
                "discrepancias_count": discrepancias,
            }
        },
        "incidents": audit_records
    }

    summary_file = get_summary_file_path(project_root)
    try:
        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(summary_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[WARN] No se pudo escribir resumen JSON en {summary_file}: {e}")

    return summary_file
