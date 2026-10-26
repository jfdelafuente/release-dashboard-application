#!/usr/bin/env python3
"""High Priority Incident Notifications Evaluator & Executive Reporter.

This CLI utility:
1. Reads massive incidents from data/output/index.json or a specified JSON file.
2. Fetches AI incident synthesis from Epsilon (/api/epsilon/resumenIA/{codigo}).
3. Evaluates real severity using ITIL/SRE matrix (it-severity-matrix skill).
4. Flags P1/P2 incidents and detects priority discrepancies (e.g. Ticket P3 -> IA P1).
5. Generates executive communications according to incident-reporter guidelines.
6. Writes results to data/output/high_priority_notifications.json.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import re
import sys
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("incident_evaluator")

# SLAs de referencia según ITIL (en minutos)
SLA_TARGET_MINUTES: dict[str, int] = {
    "P1": 15,
    "P2": 60,
    "P3": 240,
    "P4": 1440,
}

PRIORITY_RANKS: dict[str, int] = {
    "P1": 1,
    "P2": 2,
    "P3": 3,
    "P4": 4,
}


def normalize_priority(raw: Optional[str]) -> str:
    """Normalizes ticket priority string to standard P1, P2, P3, P4 code."""
    if not raw:
        return "P3"
    s = raw.strip().upper()
    if "P1" in s or "CRÍTICA" in s or "CRITICA" in s:
        return "P1"
    if "P2" in s or "ALTA" in s:
        return "P2"
    if "P3" in s or "MEDIA" in s:
        return "P3"
    if "P4" in s or "BAJA" in s:
        return "P4"
    return "P3"


def detect_priority_discrepancy(original_priority: Optional[str], calculated_priority: str) -> bool:
    """Returns True if calculated priority is higher severity than nominal ticket priority.
    
    Example: Ticket is 'Media' (P3) and calculated is 'P1' -> Subescalation detected.
    """
    norm_orig = normalize_priority(original_priority)
    norm_calc = normalize_priority(calculated_priority)
    orig_rank = PRIORITY_RANKS.get(norm_orig, 3)
    calc_rank = PRIORITY_RANKS.get(norm_calc, 3)
    # Lower rank number = Higher severity (P1=1 < P3=3)
    return calc_rank < orig_rank


class SeverityEvaluator:
    """Evaluates ITIL severity based on Impact and Urgency heuristics."""

    CRITICAL_IMPACT_KEYWORDS = (
        "caída total", "corte total", "indisponibilidad total", "caida total",
        "sin servicio", "afectación global", "afectacion global", "bloqueo general",
        "más del 50%", ">50%", "mas del 50%"
    )
    
    MODERATE_IMPACT_KEYWORDS = (
        "degradación", "degradacion", "lentitud", "retraso", "parcial",
        "afectación parcial", "afectacion parcial", "10%", "20%", "30%", "40%"
    )

    HIGH_URGENCY_KEYWORDS = (
        "en curso", "afectando en vivo", "sin solución temporal", "sin workaround",
        "urgente", "crítico", "critico", "intervención inmediata"
    )

    def evaluate(self, ticket: dict[str, Any], epsilon_data: Optional[dict[str, Any]]) -> dict[str, Any]:
        """Calculates suggested priority (P1-P4) and structured ITIL justification."""
        impact, impact_reason = self._evaluate_impact(ticket, epsilon_data)
        urgency, urgency_reason, has_workaround = self._evaluate_urgency(ticket, epsilon_data)

        priority = self._calculate_matrix(impact, urgency, has_workaround)
        is_high_priority = priority in ("P1", "P2")

        original_raw = ticket.get("Prioridad") or ticket.get("prioridad")
        is_discrepancy = detect_priority_discrepancy(original_raw, priority)

        sla_minutes = SLA_TARGET_MINUTES.get(priority, 240)

        return {
            "prioridad_sugerida": priority,
            "es_alta_prioridad": is_high_priority,
            "es_discrepancia": is_discrepancy,
            "evaluacion": {
                "impacto": impact,
                "impacto_justificacion": impact_reason,
                "urgencia": urgency,
                "urgencia_justificacion": urgency_reason,
                "workaround": has_workaround,
                "sla_objetivo_minutos": sla_minutes,
            }
        }

    def _evaluate_impact(self, ticket: dict[str, Any], epsilon: Optional[dict[str, Any]]) -> Tuple[str, str]:
        text_corpus = ""
        if epsilon:
            text_corpus += f" {epsilon.get('problema', '')} {epsilon.get('impacto', '')}"
        desc = ticket.get("Descripción") or ticket.get("descripcion") or ""
        text_corpus += f" {desc}"
        text_lower = text_corpus.lower()

        ticket_impact = (ticket.get("Impacto") or "").strip().lower()

        # 1. Regla Crítica (Impacto Alto)
        if any(kw in text_lower for kw in self.CRITICAL_IMPACT_KEYWORDS) or ticket_impact == "masiva":
            # Verificar si realmente es crítico o si solo menciona texto menor
            if "error tipográfico" in text_lower or "cosmético" in text_lower or "cosmetico" in text_lower:
                return "Bajo", "Fallo cosmético sin interrupción de servicio."
            return "Alto", "Afectación crítica o corte global sobre el servicio principal sin alternativa viable."

        # 2. Regla Moderada (Impacto Medio)
        if any(kw in text_lower for kw in self.MODERATE_IMPACT_KEYWORDS) or ticket_impact in ("alto", "medio"):
            return "Medio", "Degradación del servicio o afectación parcial con funcionalidad operativa."

        # 3. Regla Menor (Impacto Bajo)
        return "Bajo", "Afectación acotada a componentes secundarios o usuarios aislados."

    def _evaluate_urgency(self, ticket: dict[str, Any], epsilon: Optional[dict[str, Any]]) -> Tuple[str, str, str]:
        text_corpus = ""
        if epsilon:
            text_corpus += f" {epsilon.get('problema', '')} {epsilon.get('impacto', '')} {epsilon.get('solucion', '')}"
        desc = ticket.get("Descripción") or ticket.get("descripcion") or ""
        text_corpus += f" {desc}"
        text_lower = text_corpus.lower()

        status = (ticket.get("Estatus") or (epsilon.get("estadoActual") if epsilon else "") or "").lower()
        ticket_urgency = (ticket.get("Urgencia") or "").strip().lower()

        # Detectar Workaround
        has_workaround = "Desconocido"
        if "workaround" in text_lower or "solución temporal" in text_lower or "solucion alternativa" in text_lower or "export alternativo" in text_lower:
            has_workaround = "Sí"
        elif "sin alternativa" in text_lower or "sin workaround" in text_lower:
            has_workaround = "No"

        # Si el ticket ya está cerrado o resuelto
        if "cerrad" in status or "resuelt" in status:
            return "Baja", "Incidencia ya resuelta o estabilizada por el equipo resolutor.", has_workaround

        # Urgencia Alta
        if any(kw in text_lower for kw in self.HIGH_URGENCY_KEYWORDS) or ticket_urgency == "alta":
            return "Alta", "Impacto activo en vivo que requiere restablecimiento inmediato.", has_workaround

        # Urgencia Media
        if ticket_urgency == "media" or "en curso" in status or "asigna" in status:
            return "Media", "Incidencia en tratamiento con contención operativa transitoria.", has_workaround

        # Urgencia Baja
        return "Baja", "Incidencia de baja sensibilidad temporal o sin bloqueo activo.", has_workaround

    @staticmethod
    def _calculate_matrix(impact: str, urgency: str, has_workaround: str) -> str:
        """Applies ITIL Impact x Urgency cross-reference rules."""
        if impact == "Alto":
            if urgency == "Alta":
                return "P1"
            if urgency == "Media":
                return "P2" if has_workaround == "Sí" else "P1"
            return "P2"

        if impact == "Medio":
            if urgency == "Alta":
                return "P2"
            if urgency == "Media":
                return "P3" if has_workaround == "Sí" else "P2"
            return "P3"

        # Impacto Bajo
        if urgency in ("Alta", "Media"):
            return "P3"
        return "P4"


class ExecutiveMessageGenerator:
    """Generates standardized executive notifications conforming to incident-reporter."""

    @staticmethod
    def _clean_text(text: str) -> str:
        """Removes duplicate whitespace and ensures single paragraph formatting."""
        clean = re.sub(r"\s+", " ", text).strip()
        # Clean double periods
        clean = re.sub(r"\.\s*\.", ".", clean)
        return clean

    @staticmethod
    def _truncate_to_words(text: str, max_words: int) -> str:
        """Truncates text safely to max_words without leaving broken punctuation."""
        words = text.split()
        if len(words) <= max_words:
            return text
        truncated = " ".join(words[:max_words])
        if not truncated.endswith((".", "!", "?")):
            truncated += "..."
        return truncated

    @classmethod
    def generate_agent_prompt(
        cls,
        ticket: dict[str, Any],
        evaluation: dict[str, Any],
        resumen_ia: Optional[dict[str, Any]],
        phase: str = "apertura"
    ) -> str:
        """Constructs a complete structured prompt for the incident-reporter agent with Epsilon context."""
        inc_id = ticket.get("ID de incidencia") or ticket.get("id") or "INC"
        titulo = ticket.get("Descripción") or ticket.get("descripcion") or (resumen_ia.get("titulo") if resumen_ia else "")
        prio = evaluation.get("prioridad_sugerida", "P2")

        sistemas_list = []
        if resumen_ia and isinstance(resumen_ia.get("sistemas"), list):
            sistemas_list = [s for s in resumen_ia["sistemas"] if s]
        if not sistemas_list and ticket.get("Grupo asignado"):
            sistemas_list = [ticket["Grupo asignado"]]
        sistemas_str = ", ".join(sistemas_list) if sistemas_list else "Servicios Core"

        prompt_lines = [
            "Actúa como el agente incident-reporter (comunicación ejecutiva para Dirección, versión completa de hasta 90 palabras y versión breve de hasta 30 palabras).",
            f"Fase solicitada: {phase.upper()}",
            f"Incidencia: {inc_id} - {titulo}",
            f"Criticidad sugerida: {prio}",
            f"Sistemas involucrados: {sistemas_str}"
        ]

        if resumen_ia:
            prompt_lines.append("\n--- Contexto extraído de Epsilon Resumen IA ---")
            if resumen_ia.get("problema"):
                prompt_lines.append(f"• Problema detectado: {resumen_ia['problema']}")
            if resumen_ia.get("impacto"):
                prompt_lines.append(f"• Impacto en servicio/negocio: {resumen_ia['impacto']}")
            if resumen_ia.get("solucion"):
                prompt_lines.append(f"• Causa raíz / Solución: {resumen_ia['solucion']}")
            sig = resumen_ia.get("siguienteAccion") or resumen_ia.get("siguiente_accion")
            if sig:
                prompt_lines.append(f"• Siguiente acción: {sig}")
            if resumen_ia.get("estadoActual"):
                prompt_lines.append(f"• Estado actual reportado: {resumen_ia['estadoActual']}")
            bloqueos = resumen_ia.get("bloqueos")
            if bloqueos:
                blq = "; ".join(bloqueos) if isinstance(bloqueos, list) else str(bloqueos)
                if blq.strip():
                    prompt_lines.append(f"• Bloqueos identificados: {blq}")
        else:
            prompt_lines.append("\n--- Metadatos del ticket (Epsilon IA pendiente) ---")
            prompt_lines.append(f"• Descripción: {titulo}")
            prompt_lines.append(f"• Impacto ticket: {ticket.get('Impacto', 'N/D')}")
            prompt_lines.append(f"• Urgencia ticket: {ticket.get('Urgencia', 'N/D')}")

        prompt_lines.append("\nRedacta el mensaje en los dos niveles obligatorios:")
        prompt_lines.append("**Mensaje para Dirección (versión completa):** (único párrafo, máx 90 palabras)")
        prompt_lines.append("**Versión aún más breve:** (máx 30 palabras)")

        return "\n".join(prompt_lines)

    @classmethod
    def synthesize_ticket_title(cls, raw_title: str) -> tuple[str, str, str]:
        """Synthesizes a raw Remedy title (e.g. 'ALTAIR // LA FINCA // ERROR FUNCIONAL')
        into natural executive phrasing matching the incident-reporter agent style:
        returns: (problema_sintetizado, servicio_alcance, problema_breve)
        """
        raw = cls._clean_text(raw_title)
        if not raw:
            return "una incidencia técnica", "los servicios involucrados", "incidencia técnica"

        parts = [p.strip() for p in re.split(r"//|\|", raw) if p.strip()]
        if len(parts) >= 2:
            system = parts[0]
            issue = ""
            location = ""
            for p in parts[1:]:
                p_lower = p.lower()
                if any(k in p_lower for k in ["error", "fallo", "caida", "caída", "degradac", "lento", "corte", "bloqueo", "indispon"]):
                    issue = p_lower
                elif not location:
                    location = p
            if not issue and len(parts) == 3:
                location = parts[1]
                issue = parts[2].lower()
            elif not issue:
                issue = "error funcional"

            loc_str = ""
            if location:
                loc_words = []
                for idx, w in enumerate(location.split()):
                    if (len(w) <= 3 or w.upper() in ["TLP", "ICP", "MM", "ISGF", "CAU", "RED", "ATAC", "PRDIA", "OEST"]) and w.upper() in ["TLP", "ICP", "MM", "ISGF", "CAU", "RED", "ATAC", "PRDIA", "OEST"]:
                        loc_words.append(w.upper())
                    elif idx > 0 and len(w) == 2 and w.lower() in ["de", "la", "el", "en"]:
                        loc_words.append(w.lower())
                    else:
                        loc_words.append(w.capitalize())
                loc_str = " (" + " ".join(loc_words) + ")"

            problema_sintetizado = f"un {issue} detectado en el servicio {system}{loc_str}"
            servicio_alcance = f"{system}{loc_str}"
            problema_breve = f"{issue} en {system}{loc_str}"
            return problema_sintetizado, servicio_alcance, problema_breve
        else:
            clean = raw[:-1] if raw.endswith(".") else raw
            clean_clean = clean.capitalize() if clean.isupper() else clean
            problema_sintetizado = f"un problema por {clean_clean}"
            servicio_alcance = clean_clean
            problema_breve = clean_clean[:45]
            return problema_sintetizado, servicio_alcance, problema_breve

    def __init__(self, agent_store_path: Optional[Path] = None):
        if agent_store_path is not None:
            self.agent_store_path = agent_store_path
        else:
            root = Path(__file__).resolve().parent.parent.parent
            candidate = root / "data" / "agent_executive_messages.json"
            if candidate.exists():
                self.agent_store_path = candidate
            else:
                self.agent_store_path = Path("data/agent_executive_messages.json")
        self.agent_store = self._load_agent_store()

    def _load_agent_store(self) -> dict[str, Any]:
        if self.agent_store_path and self.agent_store_path.exists():
            try:
                with open(self.agent_store_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("incidents", {})
            except Exception as e:
                logger.debug("No se pudo cargar el almacén de agentes: %s", e)
        return {}

    def generate(
        self,
        ticket: dict[str, Any],
        evaluation: dict[str, Any],
        resumen_ia: Optional[dict[str, Any]]
    ) -> dict[str, dict[str, Any]]:
        """Generates executive messages conforming to the incident-reporter agent persona.
        VIA A DISCARDED: Fixed template string concatenations are no longer used.
        Messages come exclusively from the official agent output store. If not yet processed by
        the agent, messages are marked as pending with the structured prompt ready to run.
        """
        inc_id = ticket.get("ID de incidencia") or ticket.get("id") or "INC"
        agent_msgs = self.agent_store.get(inc_id)

        messages = {}
        for phase in ["apertura", "seguimiento", "cierre"]:
            prompt = self.generate_agent_prompt(ticket, evaluation, resumen_ia, phase)
            if agent_msgs and phase in agent_msgs:
                phase_data = agent_msgs[phase]
                comp = self._clean_text(phase_data.get("completo") or "")
                brev = self._clean_text(phase_data.get("breve") or "")
                messages[phase] = {
                    "completo": comp,
                    "breve": brev,
                    "conteo_palabras_completo": len(comp.split()),
                    "conteo_palabras_breve": len(brev.split()),
                    "generado_por_agente": True,
                    "origen": phase_data.get("origen", "incident-reporter"),
                    "prompt_agente": prompt,
                }
            else:
                # Vía A descartada: Sin textos automáticos de plantilla robótica
                messages[phase] = {
                    "completo": None,
                    "breve": None,
                    "conteo_palabras_completo": 0,
                    "conteo_palabras_breve": 0,
                    "generado_por_agente": False,
                    "estado": "pendiente",
                    "prompt_agente": prompt,
                }

        return messages

        return messages


class EpsilonClient:
    """Client for Epsilon Resumen IA service with local file caching and graceful offline handling."""

    CACHE_TTL_SECONDS = 900  # 15 minutes

    def __init__(self, base_url: str = "http://127.0.0.1:8081/api/epsilon/resumenIA", cache_dir: Optional[Path] = None, max_consecutive_failures: int = 3):
        self.base_url = base_url.rstrip("/")
        self.cache_dir = cache_dir or Path("data/.epsilon_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_consecutive_failures = max_consecutive_failures
        self._server_offline = False
        self._consecutive_failures = 0

    def _get_cache_path(self, incident_code: str) -> Path:
        return self.cache_dir / f"{incident_code}.json"

    def get_resumen_ia(self, incident_code: str, force_refresh: bool = False) -> Optional[dict[str, Any]]:
        """Fetches AI summary for an incident, using local cache when valid."""
        cache_file = self._get_cache_path(incident_code)

        if not force_refresh and cache_file.exists():
            try:
                stat = cache_file.stat()
                age = time.time() - stat.st_mtime
                if age < self.CACHE_TTL_SECONDS:
                    with open(cache_file, "r", encoding="utf-8") as f:
                        return json.load(f)
            except Exception as e:
                logger.debug("Error leyendo caché de %s: %s", incident_code, e)

        # Si el servidor ya falló repetidamente, evitar timeouts en bucle
        if self._server_offline:
            return None

        url = f"{self.base_url}/{incident_code}"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "ReleaseDashboard-Evaluator/1.0", "Accept": "application/json"}
        )

        try:
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                if resp.status == 200:
                    self._consecutive_failures = 0
                    payload = json.loads(resp.read().decode("utf-8"))
                    data = payload.get("data") if isinstance(payload, dict) and "data" in payload else payload
                    if data:
                        try:
                            with open(cache_file, "w", encoding="utf-8") as f:
                                json.dump(data, f, ensure_ascii=False, indent=2)
                        except Exception as write_err:
                            logger.debug("No se pudo escribir caché para %s: %s", incident_code, write_err)
                        return data
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as net_err:
            self._consecutive_failures += 1
            if self._consecutive_failures >= self.max_consecutive_failures:
                self._server_offline = True
                logger.warning(
                    "Servicio Epsilon no disponible en %s (%s). Se continuará la evaluación usando los metadatos de los tickets.",
                    self.base_url,
                    net_err
                )
            else:
                logger.debug("Epsilon no disponible o error para %s (%s)", incident_code, net_err)

        return None


# Estados finales que no requieren notificación para no sobrecargar el sistema
TERMINAL_STATUSES = {
    "cerrado", "cerrada", "closed",
    "resuelto", "resuelta", "resolved",
    "cancelado", "cancelada", "cancelled", "canceled"
}


def is_terminal_status(status: Optional[str]) -> bool:
    """Indica si el estado de una incidencia es terminal (Cerrado, Resuelto, Cancelado)."""
    if not status:
        return False
    return str(status).strip().lower() in TERMINAL_STATUSES


def evaluate_incidents_batch(
    tickets: list[dict[str, Any]],
    epsilon_client: Optional[EpsilonClient] = None,
    limit: Optional[int] = None,
    source_file_name: str = ""
) -> dict[str, Any]:
    """Processes a batch of massive incidents and constructs the High Priority catalog."""
    evaluator = SeverityEvaluator()
    msg_generator = ExecutiveMessageGenerator()

    processed_tickets = tickets[:limit] if limit else tickets
    total_scanned = len(processed_tickets)

    high_priority_items: list[dict[str, Any]] = []
    p1_count = 0
    p2_count = 0
    discrepancies_count = 0
    terminal_skipped_count = 0

    for item in processed_tickets:
        inc_id = item.get("ID de incidencia") or item.get("id") or ""
        if not inc_id:
            continue

        # Filtrar incidencias en estado terminal (Cerrado, Resuelto, Cancelado)
        status_val = item.get("Estatus") or item.get("estatus") or item.get("Estado") or item.get("estado") or ""
        if is_terminal_status(status_val):
            terminal_skipped_count += 1
            continue

        epsilon_data = epsilon_client.get_resumen_ia(inc_id) if epsilon_client else None
        evaluation = evaluator.evaluate(item, epsilon_data)

        prio_sugerida = evaluation["prioridad_sugerida"]
        es_alta = evaluation["es_alta_prioridad"]
        es_disc = evaluation["es_discrepancia"]

        if es_disc:
            discrepancies_count += 1

        if prio_sugerida == "P1":
            p1_count += 1
        elif prio_sugerida == "P2":
            p2_count += 1

        # Construir mensajes ejecutivos para alta prioridad o discrepancias
        if es_alta or es_disc:
            mensajes = msg_generator.generate(item, evaluation, epsilon_data)
            
            sistemas = []
            if epsilon_data and isinstance(epsilon_data.get("sistemas"), list):
                sistemas = epsilon_data["sistemas"]
            elif item.get("Grupo asignado"):
                sistemas = [item["Grupo asignado"]]

            resumen_ia_block = None
            if epsilon_data:
                resumen_ia_block = {
                    "problema": epsilon_data.get("problema", ""),
                    "impacto": epsilon_data.get("impacto", ""),
                    "solucion": epsilon_data.get("solucion", ""),
                    "bloqueos": "; ".join(epsilon_data.get("bloqueos", [])) if isinstance(epsilon_data.get("bloqueos"), list) else str(epsilon_data.get("bloqueos", "")),
                    "siguiente_accion": epsilon_data.get("siguienteAccion", "")
                }

            high_priority_items.append({
                "id": inc_id,
                "titulo": item.get("Descripción") or item.get("descripcion") or (epsilon_data.get("titulo") if epsilon_data else ""),
                "sistemas": sistemas,
                "prioridad_original": item.get("Prioridad") or "Media",
                "prioridad_sugerida": prio_sugerida,
                "es_alta_prioridad": es_alta,
                "es_discrepancia": es_disc,
                "estatus": item.get("Estatus") or "Asignado",
                "fecha_envio": item.get("Fecha de envío") or item.get("fecha_envio") or "",
                "evaluacion": evaluation["evaluacion"],
                "resumen_ia": resumen_ia_block,
                "mensajes_ejecutivos": mensajes
            })

    # Ordenar: primero P1, luego discrepancias, luego P2
    def sort_key(doc: dict[str, Any]) -> tuple[int, int]:
        prio_val = 0 if doc["prioridad_sugerida"] == "P1" else (1 if doc["prioridad_sugerida"] == "P2" else 2)
        disc_val = 0 if doc["es_discrepancia"] else 1
        return (prio_val, disc_val)

    high_priority_items.sort(key=sort_key)

    catalog = {
        "_metadata": {
            "type": "high_priority_notifications",
            "version": "1.0.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source_file": source_file_name,
            "kpis": {
                "total_scanned": total_scanned,
                "terminal_skipped_count": terminal_skipped_count,
                "active_evaluated_count": total_scanned - terminal_skipped_count,
                "total_high_priority": p1_count + p2_count,
                "p1_critical_count": p1_count,
                "p2_high_count": p2_count,
                "discrepancies_count": discrepancies_count
            }
        },
        "data": high_priority_items
    }

    return catalog


def resolve_default_input_file(project_root: Path, index_path: Optional[Path] = None) -> Optional[Path]:
    """Finds the latest massive incident JSON file from index.json."""
    if index_path is None:
        index_path = project_root / "data" / "output" / "index.json"
    if not index_path.exists():
        return None

    try:
        with open(index_path, "r", encoding="utf-8") as f:
            idx = json.load(f)
        massive_entry = idx.get("massive", {})
        files = massive_entry.get("files", [])
        if files:
            name = files[0].get("name")
            rel_path = files[0].get("path")
            candidates = []
            if rel_path:
                candidates.append(project_root / rel_path)
            if name:
                candidates.append(index_path.parent / name)
            for candidate in candidates:
                if candidate.exists():
                    return candidate
    except Exception as e:
        logger.warning("Error resolviendo fichero masivo de index.json: %s", e)

    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate massive incidents for high-priority executive alerts.")
    parser.add_argument("--input", "-i", type=str, help="Input massive JSON file path")
    parser.add_argument("--index", type=str, help="Alternative index.json path to resolve input file")
    parser.add_argument("--output", "-o", type=str, default="data/output/high_priority_notifications.json", help="Output JSON path")
    parser.add_argument("--limit", "-l", type=int, help="Limit number of incidents evaluated")
    parser.add_argument("--base-url", type=str, default="http://127.0.0.1:8081/api/epsilon/resumenIA", help="Epsilon proxy base URL")
    parser.add_argument("--force", action="store_true", help="Force refresh ignoring local Epsilon cache")
    parser.add_argument("--dry-run", action="store_true", help="Perform evaluation without writing to output file")

    args = parser.parse_args()
    project_root = Path.cwd()

    index_override = Path(args.index) if args.index else None
    input_file = Path(args.input) if args.input else resolve_default_input_file(project_root, index_override)
    if not input_file or not input_file.exists():
        logger.error("No se encontró el fichero de incidencias masivas de entrada: %s", input_file)
        return 1

    logger.info("Cargando incidencias masivas desde: %s", input_file)
    try:
        with open(input_file, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
        tickets = raw_data.get("data", []) if isinstance(raw_data, dict) else raw_data
        if not isinstance(tickets, list):
            logger.error("El formato del fichero de entrada no contiene una lista en 'data'.")
            return 1
    except Exception as e:
        logger.error("Error leyendo %s: %s", input_file, e)
        return 1

    epsilon_client = EpsilonClient(base_url=args.base_url)
    catalog = evaluate_incidents_batch(
        tickets=tickets,
        epsilon_client=epsilon_client,
        limit=args.limit,
        source_file_name=input_file.name
    )

    kpis = catalog["_metadata"]["kpis"]
    logger.info(
        "Evaluación completada: %d escaneadas (%d omitidas por estado final/cerrado, %d activas), %d de alta prioridad (P1: %d, P2: %d), %d discrepancias.",
        kpis["total_scanned"],
        kpis["terminal_skipped_count"],
        kpis["active_evaluated_count"],
        kpis["total_high_priority"],
        kpis["p1_critical_count"],
        kpis["p2_high_count"],
        kpis["discrepancies_count"],
    )

    if not args.dry_run:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(catalog, f, ensure_ascii=False, indent=2)
        logger.info("Catálogo guardado en: %s", out_path)
    else:
        logger.info("[Dry Run] No se guardó ningún archivo en disco.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
