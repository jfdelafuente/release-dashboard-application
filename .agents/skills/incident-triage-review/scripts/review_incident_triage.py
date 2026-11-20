#!/usr/bin/env python3
"""
review_incident_triage.py

Herramienta de soporte y auditoría determinista para la revisión de triaje de incidencias IT.
Integra los aprendizajes de incidencias con resoluciones planificadas (INC000004122710)
y resoluciones parciales multisede con prevención de falsos cierres (INC000004156790).

Audita:
1. Concordancia entre la prioridad nominal de Remedy y el impacto operativo real (Infratriaje / Sobretriaje).
2. Detección de soluciones planificadas / pases a producción comprometidos (calibración de urgencia, techo P2 y exención de aging).
3. Detección de afectación multisede / estado dispar (bloqueos activos en subsedes vs normalización parcial).
4. Coherencia del ciclo de vida en mensajes ejecutivos (detección crítica de LIFECYCLE_STATUS_MISMATCH).
5. Cumplimiento de límites de palabras (<= 90 completo monopárrafo, <= 30 breve línea única).
"""

import argparse
import glob
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def find_repo_root() -> Path:
    cur = Path(__file__).resolve().parent
    for p in [cur] + list(cur.parents):
        if (p / "VERSION").exists() and (p / "data").exists():
            return p
    return Path(__file__).resolve().parents[4]


def count_words(text: str) -> int:
    return len([w for w in (text or "").strip().split() if w])


def is_single_paragraph(text: str) -> bool:
    if not text:
        return True
    return "\n" not in text.strip()


def normalize_priority(val: str) -> str:
    if not val:
        return ""
    v = val.strip().upper()
    if "CRÍTICA" in v or "CRITICA" in v or "1" in v or "P1" in v:
        return "P1"
    if "ALTA" in v or "2" in v or "P2" in v:
        return "P2"
    if "MEDIA" in v or "3" in v or "P3" in v:
        return "P3"
    if "BAJA" in v or "4" in v or "P4" in v:
        return "P4"
    return val.strip()


class IncidentTriageReviewer:
    def __init__(self, root: Path):
        self.root = root
        self.massive_data = self._load_massive_data()
        self.notifications_data = self._load_notifications()
        self.executive_messages = self._load_executive_messages()

    def _load_massive_data(self) -> Dict[str, Dict[str, Any]]:
        massive_files = sorted(
            glob.glob(str(self.root / "data" / "output" / "*-massive.json")),
            reverse=True
        )
        if not massive_files:
            return {}
        try:
            with open(massive_files[0], "r", encoding="utf-8") as f:
                raw = json.load(f)
            data_list = raw.get("data", raw) if isinstance(raw, dict) else raw
            result = {}
            for item in data_list:
                inc_id = (
                    item.get("ID de incidencia")
                    or item.get("ID")
                    or item.get("id")
                    or item.get("Incidencia")
                )
                if inc_id:
                    result[inc_id.strip()] = item
            return result
        except Exception:
            return {}

    def _load_notifications(self) -> Dict[str, Dict[str, Any]]:
        p = self.root / "data" / "output" / "high_priority_notifications.json"
        if not p.exists():
            return {}
        try:
            with open(p, "r", encoding="utf-8") as f:
                raw = json.load(f)
            data_list = raw.get("data", []) if isinstance(raw, dict) else raw
            return {item["id"]: item for item in data_list if "id" in item}
        except Exception:
            return {}

    def _load_executive_messages(self) -> Dict[str, Dict[str, Any]]:
        p = self.root / "data" / "agent_executive_messages.json"
        if not p.exists():
            return {}
        try:
            with open(p, "r", encoding="utf-8") as f:
                raw = json.load(f)
            return raw.get("incidents", {})
        except Exception:
            return {}

    def _load_epsilon_cache(self, inc_id: str) -> Optional[Dict[str, Any]]:
        p = self.root / "data" / ".epsilon_cache" / f"{inc_id}.json"
        if not p.exists():
            return None
        try:
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def review_incident(self, inc_id: str) -> Dict[str, Any]:
        remedy_record = self.massive_data.get(inc_id, {})
        notif_record = self.notifications_data.get(inc_id, {})
        messages_record = self.executive_messages.get(inc_id, {})
        epsilon_record = self._load_epsilon_cache(inc_id)

        # 1. Remedy fields
        remedy_status = (
            remedy_record.get("Estatus")
            or notif_record.get("estatus")
            or "Desconocido"
        )
        remedy_priority_raw = (
            remedy_record.get("Prioridad")
            or notif_record.get("prioridad_original")
            or ""
        )
        remedy_priority = normalize_priority(remedy_priority_raw)
        title = (
            remedy_record.get("Descripcin")
            or remedy_record.get("Descripción")
            or notif_record.get("titulo")
            or ""
        )
        assigned_group = (
            remedy_record.get("Grupo asignado")
            or remedy_record.get("Grupo Resolutor")
            or ""
        )

        # 2. Evaluation fields
        evaluated_priority = notif_record.get("prioridad_sugerida", "")
        is_planned = notif_record.get("es_planificada", False)
        plan_detail = notif_record.get("detalle_planificacion", "")
        is_aging_escalated = notif_record.get("aging_escalated", False)
        is_discrepancy = notif_record.get("es_discrepancia", False)
        discrepancy_reason = notif_record.get("discrepancia_motivo", "")

        # 3. Textual inspection for planned resolutions & multi-site
        text_corpus = " ".join([
            title,
            json.dumps(epsilon_record or {}, ensure_ascii=False),
            json.dumps(notif_record.get("resumen_ia") or {}, ensure_ascii=False),
        ]).lower()

        planned_keywords = [
            "pase a produccion", "pase a producción", "subida prevista",
            "despliegue previsto", "pr en desarrollo", "pr validada",
            "mantenimiento programado", "ventana de intervencion", "ventana de intervención",
            "conciliacion bscs", "conciliación bscs", "proceso batch", "batch planificado", "lunes 06h"
        ]
        text_suggests_planned = any(k in text_corpus for k in planned_keywords)

        is_zombie = notif_record.get("es_zombi", False)
        zombie_detail = notif_record.get("detalle_zombi", "")
        if not is_zombie:
            zombie_match = re.search(r"(?:ticket\s+cancelado\s+en\s+jira|resuelto\s+cancelado\/no\s+aplica|marcado\s+como\s+resuelto\/cerrado\s+en\s+jira)", text_corpus)
            if zombie_match:
                is_zombie = True
                zombie_detail = "Ticket cancelado/resuelto en Jira"

        multisite_keywords = ["madison", "valladolid", "bosch", "vigo", "oviedo", "sede", "sedes"]
        text_suggests_multisite = any(k in text_corpus for k in multisite_keywords)
        partial_resolution_detected = False
        if "no resuelto" in text_corpus and ("normalizad" in text_corpus or "resuelto" in text_corpus):
            partial_resolution_detected = True

        # 4. Consistency checks and anomalies
        anomalies: List[Dict[str, str]] = []
        is_remedy_terminal = remedy_status.lower() in ["resuelto", "cerrado", "resolved", "closed"]
        is_remedy_active = remedy_status.lower() in ["asignado", "en curso", "pendiente", "assigned", "in progress", "pending"]
        has_cierre_msg = "cierre" in messages_record

        # Check A: LIFECYCLE_STATUS_MISMATCH
        if is_remedy_active and has_cierre_msg:
            anomalies.append({
                "code": "LIFECYCLE_STATUS_MISMATCH",
                "severity": "CRITICAL",
                "message": (
                    f"Falso Cierre Prematuro Detectado: El ticket se encuentra activo en Remedy "
                    f"('{remedy_status}'), pero data/agent_executive_messages.json contiene una "
                    f"fase 'cierre' oficial."
                ),
                "mitigation": "Eliminar la fase 'cierre' de agent_executive_messages.json y mantener la fase 'seguimiento'."
            })
        elif is_remedy_terminal and not has_cierre_msg and inc_id in self.executive_messages:
            anomalies.append({
                "code": "LIFECYCLE_PENDING_CLOSURE",
                "severity": "WARNING",
                "message": (
                    f"Ticket resuelto en Remedy ('{remedy_status}'), pero data/agent_executive_messages.json "
                    f"no contiene mensaje de cierre oficial para Dirección."
                ),
                "mitigation": "Redactar y registrar el mensaje de cierre con incident-reporter."
            })

        # Check B: AGING_ESCALATION_INDEBIDO vs SOLUCION_PLANIFICADA
        if (is_planned or text_suggests_planned) and is_aging_escalated and evaluated_priority == "P1":
            anomalies.append({
                "code": "AGING_ESCALATION_INDEBIDO",
                "severity": "HIGH",
                "message": (
                    "Escalado ciego por Aging a P1 en ticket con resolución planificada / despliegue programado. "
                    "Las resoluciones en espera de ventana de release deben tener urgencia planificada y tope P2."
                ),
                "mitigation": "Calibrar urgencia a Urgencia Planificada/Baja en evaluate_incident_notifications.py y aplicar tope P2."
            })

        # Check C: TICKET_ZOMBI_DESYNC
        if is_zombie and is_remedy_active:
            anomalies.append({
                "code": "TICKET_ZOMBI_DESYNC",
                "severity": "WARNING",
                "message": (
                    f"Ticket cancelado o resuelto en Jira ({zombie_detail or 'Resolución en Jira no sincronizada'}), "
                    f"pero continúa activo en BMC Remedy ('{remedy_status}'). Requiere Cierre Administrativo formal."
                ),
                "mitigation": "Solicitar a la Mesa de Seguimiento el cierre administrativo formal en BMC Remedy y retirar de la cola de emergencias vivas de Dirección."
            })

        # Check D: INFRATRIAJE_REMEDY (Excluye tickets zombi con cierre pendiente)
        if not is_zombie and evaluated_priority in ["P1", "P2"] and remedy_priority in ["P3", "P4"]:
            anomalies.append({
                "code": "INFRATRIAJE_REMEDY",
                "severity": "HIGH",
                "message": (
                    f"Infratriaje en Remedy: Clasificado como {remedy_priority} en BMC Remedy, pero la evaluación "
                    f"técnica determina criticidad {evaluated_priority} por impacto en procesos críticos / sedes."
                ),
                "mitigation": f"Recomendar a la Mesa de Incidencias e Incident Manager elevar la prioridad en Remedy a {evaluated_priority}."
            })

        # Check D: SOBRETIAJE_REMEDY
        if remedy_priority == "P1" and evaluated_priority in ["P3", "P4"]:
            anomalies.append({
                "code": "SOBRETIAJE_REMEDY",
                "severity": "MEDIUM",
                "message": (
                    f"Sobretriaje en Remedy: Clasificado nominalmente como P1 pero evaluado como {evaluated_priority}. "
                    "Posible sobreclasificación administrativa sin impacto operativo real."
                ),
                "mitigation": "Verificar telemetría y contrastar con catálogo CORE++ de it-severity-matrix."
            })

        # Check E: CIERRE_PREMATURO_MULTI_SEDE
        if partial_resolution_detected and has_cierre_msg:
            anomalies.append({
                "code": "CIERRE_PREMATURO_MULTI_SEDE",
                "severity": "CRITICAL",
                "message": (
                    "Resolución parcial detectada entre sedes (una sede normalizada, pero otra reporta NO RESUELTO). "
                    "Prohibido emitir cierre mientras persista afectación en alguna sede."
                ),
                "mitigation": "Retirar fase 'cierre' y reflejar estado mixto en fase 'seguimiento'."
            })

        # Check F: Mensajes ejecutivos límites y formato
        for phase, content in messages_record.items():
            if not isinstance(content, dict):
                continue
            comp = content.get("completo", "")
            brev = content.get("breve", "")
            cw = count_words(comp)
            bw = count_words(brev)
            if cw > 90:
                anomalies.append({
                    "code": "EXCESSIVE_WORD_COUNT_COMPLETO",
                    "severity": "WARNING",
                    "message": f"Fase '{phase}' excede el límite oficial de 90 palabras ({cw} palabras).",
                    "mitigation": "Resumir versión completa para que sea <= 90 palabras."
                })
            if not is_single_paragraph(comp):
                anomalies.append({
                    "code": "MULTI_PARAGRAPH_COMPLETO",
                    "severity": "WARNING",
                    "message": f"Fase '{phase}' versión completa contiene múltiples párrafos. Debe ser monopárrafo.",
                    "mitigation": "Eliminar saltos de línea intermedios en versión completa."
                })
            if bw > 30:
                anomalies.append({
                    "code": "EXCESSIVE_WORD_COUNT_BREVE",
                    "severity": "WARNING",
                    "message": f"Fase '{phase}' excede el límite oficial de 30 palabras ({bw} palabras).",
                    "mitigation": "Resumir versión breve para que sea <= 30 palabras en una sola línea."
                })

        return {
            "id": inc_id,
            "titulo": title,
            "grupo_asignado": assigned_group,
            "estatus_remedy": remedy_status,
            "prioridad_remedy": remedy_priority,
            "prioridad_evaluada": evaluated_priority or remedy_priority,
            "es_alta_prioridad": notif_record.get("es_alta_prioridad", False),
            "es_discrepancia": is_discrepancy,
            "discrepancia_motivo": discrepancy_reason,
            "es_planificada": is_planned or text_suggests_planned,
            "detalle_planificacion": plan_detail,
            "es_zombi": is_zombie,
            "detalle_zombi": zombie_detail,
            "guia_operador": notif_record.get("guia_operador"),
            "aging_escalated": is_aging_escalated,
            "multisede": text_suggests_multisite,
            "resolucion_parcial": partial_resolution_detected,
            "fases_mensajes": list(messages_record.keys()),
            "anomalias": anomalies,
            "es_conforme": len([a for a in anomalies if a["severity"] in ["CRITICAL", "HIGH"]]) == 0
        }

    def review_all_active(self) -> List[Dict[str, Any]]:
        target_ids = list(self.notifications_data.keys())
        # Also include any active incidents in massive data or executive messages
        for inc_id, rec in self.massive_data.items():
            st = (rec.get("Estatus") or "").lower()
            if st not in ["resuelto", "cerrado", "resolved", "closed"] and inc_id not in target_ids:
                target_ids.append(inc_id)
        for inc_id in self.executive_messages.keys():
            if inc_id not in target_ids:
                target_ids.append(inc_id)

        results = []
        for inc_id in sorted(set(target_ids)):
            results.append(self.review_incident(inc_id))
        return results


def format_markdown_report(result: Dict[str, Any]) -> str:
    inc_id = result["id"]
    status_icon = "✅ CONFORME" if result["es_conforme"] else "⚠️ INCONSISTENCIAS DETECTADAS"
    lines = [
        f"### Ficha de Revisión de Triaje: `{inc_id}` — {status_icon}",
        "",
        f"- **Título / Resumen:** {result['titulo']}",
        f"- **Grupo Asignado:** `{result['grupo_asignado'] or 'N/A'}`",
        f"- **Estado en Remedy:** `{result['estatus_remedy']}`",
        f"- **Prioridad Remedy:** `{result['prioridad_remedy']}` | **Prioridad Evaluada:** `{result['prioridad_evaluada']}`",
        f"- **Resolución Planificada / Despliegue:** `{'SÍ' if result['es_planificada'] else 'NO'}`" + (f" ({result['detalle_planificacion']})" if result['detalle_planificacion'] else ""),
        f"- **Escalado por Aging:** `{'SÍ' if result['aging_escalated'] else 'NO'}`",
        f"- **Afectación Multisede / Parcial:** `{'SÍ' if result['multisede'] else 'NO'}`" + (" (Resolución parcial dispar detectada)" if result['resolucion_parcial'] else ""),
        f"- **Ticket Zombi (Jira/Remedy):** `{'SÍ' if result.get('es_zombi') else 'NO'}`" + (f" ({result.get('detalle_zombi')})" if result.get('detalle_zombi') else ""),
        f"- **Fases Registradas en Mensajes Ejecutivos:** `{', '.join(result['fases_mensajes']) if result['fases_mensajes'] else 'Ninguna'}`",
    ]

    if result.get("guia_operador"):
        g = result["guia_operador"]
        lines.extend([
            f"- **Guía Operador de Consola:** `{g.get('categoria_operativa')}` | **Alerta:** {g.get('alerta_consola')}",
            f"  - **Acción Recomendada:** {g.get('accion_recomendada')}",
            f"  - **Canal:** `{g.get('canal_escalado')}` | **Prioridad Operativa:** `{g.get('prioridad_operativa_consola')}`",
        ])

    lines.extend([
        "",
        "#### Hallazgos y Anomalías Auditadas:"
    ])

    if not result["anomalias"]:
        lines.append("- *No se han detectado anomalías de triaje ni discrepancias de ciclo de vida.*")
    else:
        for a in result["anomalias"]:
            badge = f"**[{a['severity']}] {a['code']}**"
            lines.append(f"- {badge}: {a['message']}")
            lines.append(f"  - *Acción recomendada:* {a['mitigation']}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Revisor y Auditor de Triaje de Incidencias IT.")
    parser.add_argument("--id", help="Identificador de la incidencia Remedy (p. ej. INC000004156790).")
    parser.add_argument("--all", action="store_true", help="Auditar todas las incidencias activas en el catálogo.")
    parser.add_argument("--json", action="store_true", help="Salida en formato JSON estructurado.")
    parser.add_argument("--markdown", action="store_true", help="Salida formateada en Markdown para informes ejecutivos.")
    args = parser.parse_args()

    root = find_repo_root()
    reviewer = IncidentTriageReviewer(root)

    if args.id:
        result = reviewer.review_incident(args.id.strip())
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        elif args.markdown:
            print(format_markdown_report(result))
        else:
            print("=" * 70)
            print(f" REVISIÓN DE TRIAJE: {result['id']} - {'CONFORME' if result['es_conforme'] else 'INCONSISTENCIAS'}")
            print("=" * 70)
            print(f"Título:              {result['titulo']}")
            print(f"Estatus Remedy:      {result['estatus_remedy']}")
            print(f"Prioridad Remedy:    {result['prioridad_remedy']} -> Evaluada: {result['prioridad_evaluada']}")
            print(f"Planificada / Release: {result['es_planificada']} | Aging Escalated: {result['aging_escalated']}")
            print(f"Multisede:           {result['multisede']} | Parcial: {result['resolucion_parcial']}")
            print(f"Mensajes oficiales:  {result['fases_mensajes']}")
            print("-" * 70)
            if not result["anomalias"]:
                print("✅ Sin anomalías detectadas.")
            else:
                for a in result["anomalias"]:
                    print(f"[{a['severity']}] {a['code']}: {a['message']}")
                    print(f"   -> Acción: {a['mitigation']}")
            print("=" * 70)
        sys.exit(0 if result["es_conforme"] else 1)

    elif args.all:
        results = reviewer.review_all_active()
        total = len(results)
        conformes = sum(1 for r in results if r["es_conforme"])
        con_anomalias = total - conformes

        if args.json:
            print(json.dumps(results, indent=2, ensure_ascii=False))
        elif args.markdown:
            for r in results:
                print(format_markdown_report(r))
                print("\n---\n")
        else:
            print("=" * 70)
            print(f" AUDITORÍA DE TRIAJE EN LOTE ({total} incidencias analizadas)")
            print(f" Conformes: {conformes} | Con anomalías o inconsistencias: {con_anomalias}")
            print("=" * 70)
            for r in results:
                icon = "✅" if r["es_conforme"] else "❌"
                anom_summary = f"({len(r['anomalias'])} anomalías)" if r["anomalias"] else "(Conforme)"
                print(f"{icon} {r['id']:<17} | Remedy: {r['prioridad_remedy']:<3} -> Eval: {r['prioridad_evaluada']:<3} | {r['estatus_remedy']:<10} {anom_summary}")
                for a in r["anomalias"]:
                    if a["severity"] in ["CRITICAL", "HIGH"]:
                        print(f"    - [{a['severity']}] {a['code']}: {a['message']}")
            print("=" * 70)
        sys.exit(0 if con_anomalias == 0 else 1)
    else:
        parser.print_help()
        sys.exit(0)


if __name__ == "__main__":
    main()

