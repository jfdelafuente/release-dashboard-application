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
import ssl
import sys
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

try:
    from converters.src.csv_to_json.timezone_utils import reconcile_milestones
except ImportError:
    try:
        from src.csv_to_json.timezone_utils import reconcile_milestones
    except ImportError:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
        from converters.src.csv_to_json.timezone_utils import reconcile_milestones

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
    details = compute_discrepancy_details(original_priority, calculated_priority)
    return details["es_discrepancia"]


def compute_discrepancy_details(
    original_priority: Optional[str],
    calculated_priority: str,
    reasons: Optional[list[str]] = None
) -> dict[str, Any]:
    """Computes detailed discrepancy delta level, gravity classification, and explainable root cause for N1 feedback.
    
    Delta levels:
    - Delta = 0: Sin discrepancia (Prio Remedy alineada con evaluación ITIL)
    - Delta = 1: Moderada (ej. P3 -> P2 o P2 -> P1)
    - Delta = 2: Mayor Severa (ej. P3 -> P1 o P4 -> P2)
    - Delta >= 3: Crítica Extrema (ej. P4 -> P1 subescalación masiva)
    """
    norm_orig = normalize_priority(original_priority)
    norm_calc = normalize_priority(calculated_priority)
    orig_rank = PRIORITY_RANKS.get(norm_orig, 3)
    calc_rank = PRIORITY_RANKS.get(norm_calc, 3)

    delta = max(0, orig_rank - calc_rank)
    es_discrepancia = delta > 0

    if delta == 0:
        gravedad = "Sin discrepancia"
        motivo = f"Prioridad Remedy ({norm_orig}) alineada con evaluación ITIL ({norm_calc})."
    elif delta == 1:
        gravedad = "Moderada"
        motivo = f"Subescalación moderada (+1 nivel): Ticket registrado como {norm_orig} y evaluado como {norm_calc}."
    elif delta == 2:
        gravedad = "Mayor Severa"
        motivo = f"Subescalación severa (+2 niveles): Ticket registrado como {norm_orig} y evaluado como {norm_calc}."
    else:
        gravedad = "Crítica Extrema"
        motivo = f"Subescalación crítica extrema (+{delta} niveles): Ticket registrado como {norm_orig} y evaluado como {norm_calc}."

    if es_discrepancia and reasons:
        reasons_clean = [r.strip() for r in reasons if r and r.strip()]
        if reasons_clean:
            motivo += " Causa determinante: " + "; ".join(reasons_clean)

    return {
        "es_discrepancia": es_discrepancia,
        "delta": delta,
        "gravedad": gravedad,
        "motivo": motivo,
        "prioridad_original_normalizada": norm_orig,
        "prioridad_calculada_normalizada": norm_calc,
    }


def is_phrase_negated(text: str, match_span: tuple[int, int]) -> bool:
    """Detects if a keyword match is syntactically negated in Spanish.
    
    Examples: 'sin corte total', 'descartada caída', 'no se aprecia afectación',
    'no hay interrupción', 'se descarta caída'.
    """
    start, _ = match_span
    prefix = text[max(0, start - 35):start].lower()
    return bool(re.search(
        r"\b(?:sin|no(?:\s+hay|\s+se\s+aprecian?|\s+se\s+observan?|\s+presentan?)?|descartad[ao]s?|se\s+descarta|descarte)\s+(?:de\s+|un\s+|una\s+|el\s+|la\s+|ning[uú]n\s+)?$",
        prefix
    ))


def extract_quantitative_metrics(text: str) -> dict[str, Any]:
    """Extracts quantifiable magnitude metrics from incident texts or Epsilon IA.
    
    Extracts:
    - Sedes / Tiendas / Call Centers (threshold >= 3 for SL1)
    - Usuarios / Clientes afectados (threshold >= 500 for SL1)
    - Desviación / Error % (threshold >= 20% for SL1)
    """
    metrics: dict[str, Any] = {
        "sedes": None,
        "usuarios": None,
        "desviacion_pct": None,
        "detalles": [],
    }
    if not text:
        return metrics

    # 1. Sedes / Tiendas / Call Centers / Circuitos (umbral SL1 >= 3)
    sede_pattern = re.compile(
        r"(?:afectad[ao]s?\s+a\s+|afecta\s+a\s+|impacto\s+en\s+)?(?:>\s*|m[aá]s\s+de\s+|~\s*)?(\d+)\+?\s*(?:sedes?|tiendas?|call\s*centers?|oficinas?)",
        re.I
    )
    sede_match = sede_pattern.search(text)
    if sede_match:
        val = int(sede_match.group(1))
        metrics["sedes"] = val
        metrics["detalles"].append(f"{val} sedes/tiendas/centros")

    # 2. Usuarios / Clientes / Líneas / Afectados (umbral SL1 >= 500)
    user_pattern = re.compile(
        r"(?:afectad[ao]s?\s+a\s+|afecta\s+a\s+|impacto\s+en\s+)?(?:>\s*|m[aá]s\s+de\s+|~\s*)?(\d{1,3}(?:\.\d{3})+|\d+)\+?\s*(?:usuarios?|clientes?|l[íi]neas?|afectados?|abonados?)",
        re.I
    )
    user_match = user_pattern.search(text)
    if user_match:
        raw_val = user_match.group(1).replace(".", "").replace(",", "")
        try:
            val = int(raw_val)
            metrics["usuarios"] = val
            metrics["detalles"].append(f"{val} usuarios/clientes")
        except ValueError:
            pass

    # 3. Desviación / Porcentaje (umbral SL1 >= 20%)
    pct_pattern = re.compile(
        r"(?:(?:afectaci[oó]n|desviaci[oó]n|ca[íi]da|errores?|fallos?|tr[áa]fico)\s+(?:de[nl]?\s+)?(?:>\s*|m[aá]s\s+de\s+|~\s*)?(\d+(?:[.,]\d+)?)\s*%|(?:>\s*|m[aá]s\s+de\s+|~\s*)?(\d+(?:[.,]\d+)?)\s*%\s*(?:de\s+)?(?:desviaci[oó]n|errores?|ca[íi]das?|afectaci[oó]n|fallos?|tr[áa]fico))",
        re.I
    )
    pct_match = pct_pattern.search(text)
    if pct_match:
        raw_pct = (pct_match.group(1) or pct_match.group(2)).replace(",", ".")
        try:
            val = float(raw_pct)
            metrics["desviacion_pct"] = val
            metrics["detalles"].append(f"{val}% afectación/desviación")
        except ValueError:
            pass

    return metrics


def parse_incident_datetime(raw: Optional[str]) -> Optional[datetime]:
    """Parses incident timestamp from Remedy and various ISO/localized formats.
    
    Supports Remedy exports with Spanish/English indicators (e.g. '14/10/2026 13:26 a').
    """
    if not raw or not isinstance(raw, str):
        return None
    s = raw.strip()
    if not s:
        return None

    # Clean Remedy trailing indicators like ' a', ' p', ' a. m.', ' p. m.'
    clean_s = re.sub(r"\s+[ap]\.?\s*m?\.?$", "", s, flags=re.IGNORECASE).strip()

    formats = [
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S%z",
        "%d/%m/%Y",
        "%Y-%m-%d",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(clean_s, fmt)
        except ValueError:
            continue
    return None


def format_operational_duration(minutes: Optional[int]) -> str:
    """Formats an operational duration in minutes into a human-readable string.
    
    Examples:
    - None -> "En curso (reciente)"
    - 15 -> "15m"
    - 105 -> "1h 45m (105m)"
    - 74616 -> "51d 19h (74616m)"
    """
    if minutes is None:
        return "En curso (reciente)"
    if minutes < 0:
        return "0m"
    if minutes < 60:
        return f"{minutes}m"
    
    hours = minutes // 60
    rem_mins = minutes % 60
    if hours < 24:
        return f"{hours}h {rem_mins}m ({minutes}m)"
    
    days = hours // 24
    rem_hours = hours % 24
    return f"{days}d {rem_hours}h ({minutes}m)"


def compute_emergency_sla_status(
    created_at: Optional[datetime],
    reference_time: Optional[datetime] = None
) -> dict[str, Any]:
    """Computes operational elapsed time and Orange IT Emergency Management SLA & Escalation triggers.
    
    Rules (orange-it-emergency-management):
    - SLA 1ª Notificación a Dirección: < 20 minutos desde la identificación/apertura.
    - Escalado 1 (Telefónico a N3 / Proveedor): >= 45 minutos sin avances significativos.
    - Escalado 2 (Estamentos Superiores con IM-CSO): >= 105 minutos (45 min + 1h).
    - Frecuencia de Actualizaciones: Cada 60 minutos (o <30m ante cambios críticos).
    """
    if not created_at:
        return {
            "minutos_desde_apertura": None,
            "sla_primera_notificacion_vencido": False,
            "requiere_escalado_telefonico": False,
            "escalado_estamentos_superiores": False,
            "proxima_ventana_update_minutos": 60,
        }

    ref = reference_time or datetime.now()
    if ref.tzinfo is not None and created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=ref.tzinfo)
    elif ref.tzinfo is None and created_at.tzinfo is not None:
        ref = ref.replace(tzinfo=created_at.tzinfo)

    delta = ref - created_at
    minutes = max(0, int(delta.total_seconds() // 60))

    sla_1a_notif_vencido = minutes > 20
    req_escalado_tel = minutes >= 45
    esc_superior = minutes >= 105
    proximo_update = 60 - (minutes % 60) if minutes > 0 else 60

    return {
        "minutos_desde_apertura": minutes,
        "sla_primera_notificacion_vencido": sla_1a_notif_vencido,
        "requiere_escalado_telefonico": req_escalado_tel,
        "escalado_estamentos_superiores": esc_superior,
        "proxima_ventana_update_minutos": proximo_update,
    }


PROCESS_PATTERNS: dict[str, list[re.Pattern]] = {
    "Conectividad de Sedes, Call Centers y Tiendas": [
        re.compile(r"\brtv-tecse\b", re.I),
        re.compile(r"\bred\s+datos\b", re.I),
        re.compile(r"\bulises\b", re.I),
        re.compile(r"\bmeneses\b", re.I),
        re.compile(r"\bca[íi]da\s+de\s+tienda\b", re.I),
        re.compile(r"\baislamiento\s+de\s+sede\b", re.I),
        re.compile(r"\bcircuito\s+(?:backup|principal|ambos)\b", re.I),
        re.compile(r"\bcircuito\b.*\b(?:sede|msc|plataforma|tienda|wan|mpls)\b", re.I),
    ],
    "Infraestructura Core IT, BBDD y Cloud": [
        re.compile(r"\besx\b", re.I),
        re.compile(r"\bvmware\b", re.I),
        re.compile(r"\bpseries\b", re.I),
        re.compile(r"\bpower9\b", re.I),
        re.compile(r"\bexadata\b", re.I),
        re.compile(r"\bhwsan\b", re.I),
        re.compile(r"\bspain\s+almacenamiento\b", re.I),
        re.compile(r"\bitx\s+oci\b", re.I),
        re.compile(r"\boci/gcp\b", re.I),
        re.compile(r"\bdata\s+mart\s+fiscal\b", re.I),
        re.compile(r"\bbackup\s+osp\b", re.I),
        re.compile(r"\bhipervisor\b", re.I),
        re.compile(r"\bcabina\s+san\b", re.I),
        re.compile(r"\brac\b", re.I),  # Boundary regex: never matches 'operaciones'
    ],
    "Identidad (GDU/EVIDIAN) y Automatización": [
        re.compile(r"\bgdu\b", re.I),
        re.compile(r"\bevidian\b", re.I),
        re.compile(r"\bgdu/acm\b", re.I),
        re.compile(r"\brobotfactory\b", re.I),
        re.compile(r"\bsso\s+corporativo\b", re.I),
        re.compile(r"\biam\b", re.I),
    ],
    "Middleware e Integración Transversal": [
        re.compile(r"\bapigee\b", re.I),
        re.compile(r"\bopenapi\b", re.I),
        re.compile(r"\btibco\b", re.I),
        re.compile(r"\bgc\s+middleware\b", re.I),
        re.compile(r"\bdatapower\b", re.I),
        re.compile(r"\bocci\b", re.I),
        re.compile(r"\bsbl_eai\b", re.I),
        re.compile(r"\bbus\s+de\s+integraci[oó]n\b", re.I),
        re.compile(r"\bapi\s+gateway\b", re.I),
    ],
    "Facturación y Cobros": [
        re.compile(r"\bhpfms\b", re.I),
        re.compile(r"\bbscs\b", re.I),
        re.compile(r"\bopen\s+cobros\b", re.I),
        re.compile(r"\bexcalibur\b", re.I),
        re.compile(r"\bsga\b", re.I),  # Boundary regex: never matches 'desglose'
        re.compile(r"\bmediaci[oó]n\b", re.I),
        re.compile(r"\bhp-ium\b", re.I),
        re.compile(r"\bsap\b", re.I),  # Boundary regex: never matches 'pasaporte'
        re.compile(r"\bcobros?\b", re.I),
        re.compile(r"\bfacturas?\b", re.I),
        re.compile(r"\bfacturaci[oó]n\b", re.I),
        re.compile(r"\btarificaci[oó]n\b", re.I),
        re.compile(r"\btarifica\b", re.I),
        re.compile(r"\babonos?\b", re.I),
        re.compile(r"\bpenalizaci[oó]n\b", re.I),
        re.compile(r"\bsop_bss\b", re.I),
        re.compile(r"\bsop_smc_bscs\b", re.I),
        re.compile(r"\bsop_tmc_excalibur\b", re.I),
    ],
    "Prepago": [
        re.compile(r"\bprepago\b", re.I),
        re.compile(r"\brecargas?\b", re.I),
        re.compile(r"\brecargas\s+aprs\b", re.I),
        re.compile(r"\baprs\b", re.I),
        re.compile(r"\bocs\b", re.I),
        re.compile(r"\bsop_ocs\b", re.I),
        re.compile(r"\baltas?\s+prepago\b", re.I),
        re.compile(r"\balta\s+de\s+l[íi]neas\s+prepago\b", re.I),
    ],
    "Portabilidad": [
        re.compile(r"\bportabilidad(?:es)?\b", re.I),
        re.compile(r"\bflujo\s+2\s*am\b", re.I),
        re.compile(r"\bentidad\s+de\s+referencia\b", re.I),
        re.compile(r"\bnodo\s+portabilidad\b", re.I),
        re.compile(r"\bpomv\b", re.I),
        re.compile(r"\bncrn\b", re.I),
    ],
    "Ventas": [
        re.compile(r"\bcomprobantes?\s+de\s+venta\b", re.I),
        re.compile(r"\bteleventa\b", re.I),
        re.compile(r"\bcanal\s+comercial\b", re.I),
        re.compile(r"\bneg_camp_ceres\b", re.I),
        re.compile(r"\bceres\b", re.I),
        re.compile(r"\bupdatecommercialactspa\b", re.I),
        re.compile(r"\becontrato\b", re.I),
        re.compile(r"\bpangea\b", re.I),
        re.compile(r"\brenove\b", re.I),
        re.compile(r"\brenovaci[oó]n\s+de\s+terminales\b", re.I),
        re.compile(r"\bventas?\b", re.I),
        re.compile(r"\bcontrataci[oó]n\b", re.I),
    ],
    "Provisión": [
        re.compile(r"\bprovisi[oó]n\b", re.I),
        re.compile(r"\baprovisionamiento\b", re.I),
        re.compile(r"\b[oó]rdenes?(?:\s+de\s+(?:m[oó]vil|fijo))?\b", re.I),
        re.compile(r"\balta\s+de\s+(?:fijo|m[oó]vil)\b", re.I),
        re.compile(r"\brenovaci[oó]n\s+de\s+beneficios\b", re.I),
        re.compile(r"\bsop_smc_teide\b", re.I),
        re.compile(r"\bteide\b", re.I),
        re.compile(r"\bfijo\s+apl\b", re.I),
        re.compile(r"\bip24\b", re.I),
        re.compile(r"\bsigma\b", re.I),
        re.compile(r"\bluna\b", re.I),
        re.compile(r"\bmyaddress\b", re.I),
        re.compile(r"\baltair\s+a\s+br[uú]jula\b", re.I),
        re.compile(r"\bbr[uú]jula\b", re.I),
        re.compile(r"\bgis\s+fibra\b", re.I),
        re.compile(r"\bactivateorder\b", re.I),
    ],
    "Atención al Cliente (ATC)": [
        re.compile(r"\bficha\s+de?\s+cliente\b", re.I),
        re.compile(r"\bdes_soe_ficha\b", re.I),
        re.compile(r"\bapl_mov_soe\b", re.I),
        re.compile(r"\bivr\b", re.I),
        re.compile(r"\bcti\b", re.I),
        re.compile(r"\bfrontales\b", re.I),
        re.compile(r"\bcrm\b", re.I),
        re.compile(r"\bcrm\s+jazztel\b", re.I),
        re.compile(r"\bcrm4telco\b", re.I),
        re.compile(r"\bsiebel(?:\s+8)?\b", re.I),
        re.compile(r"\bpolar\b", re.I),
        re.compile(r"\basistente\b", re.I),
        re.compile(r"\bdes_asistente\b", re.I),
        re.compile(r"\bdjingo\b", re.I),
        re.compile(r"\bliveperson\b", re.I),
        re.compile(r"\bsop_djingo\b", re.I),
        re.compile(r"\bonuris\b", re.I),
        re.compile(r"\bsop_onuris\b", re.I),
        re.compile(r"\bonconnect\b", re.I),
        re.compile(r"\bnaboo\b", re.I),
        re.compile(r"\bboreal\b", re.I),
        re.compile(r"\bapp\s+mi\s+orange\b", re.I),
        re.compile(r"\bmijazztel\b", re.I),
        re.compile(r"\boperadores?\b", re.I),
        re.compile(r"\bcall\s+center\b", re.I),
        re.compile(r"\bgenesys\b", re.I),
        re.compile(r"\baltitude\b", re.I),
        re.compile(r"\batenci[oó]n\s+al\s+cliente\b", re.I),
        re.compile(r"\batc\b", re.I),
    ],
    "Operación y Monitorización (O&M)": [
        re.compile(r"\baltair\b", re.I),
        re.compile(r"\bgnoc\b", re.I),
        re.compile(r"\bcpe\b", re.I),
        re.compile(r"\bcortes\s+cpe\b", re.I),
        re.compile(r"\bvtemip\b", re.I),
        re.compile(r"\bzte\b", re.I),
        re.compile(r"\buca\b", re.I),  # Boundary regex: never matches 'comunicación'
        re.compile(r"\bsupervisi[oó]n\b", re.I),
        re.compile(r"\bmonitorizaci[oó]n\b", re.I),
        re.compile(r"\bcau\b", re.I),  # Boundary regex: never matches 'precaución'
        re.compile(r"\bcep\s+cau\s+agi\b", re.I),
        re.compile(r"\bftth\b", re.I),
        re.compile(r"\bfibra\b", re.I),
        re.compile(r"\bnodo\s+central\b", re.I),
        re.compile(r"\benlace\b", re.I),
        re.compile(r"\brouting\s+core\b", re.I),
    ],
}

BUSINESS_PROCESS_CATEGORIES = {
    "Atención al Cliente (ATC)",
    "Ventas",
    "Portabilidad",
    "Prepago",
    "Provisión",
    "Facturación y Cobros",
    "Conectividad de Sedes, Call Centers y Tiendas",
}

TECHNICAL_DOMAIN_CATEGORIES = {
    "Middleware e Integración Transversal",
    "Infraestructura Core IT, BBDD y Cloud",
    "Identidad (GDU/EVIDIAN) y Automatización",
    "Operación y Monitorización (O&M)",
}


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

    def evaluate(
        self,
        ticket: dict[str, Any],
        epsilon_data: Optional[dict[str, Any]],
        reference_time: Optional[datetime] = None
    ) -> dict[str, Any]:
        """Calculates suggested priority (P1-P4) and structured ITIL justification."""
        impact, impact_reason, quant_metrics = self._evaluate_impact(ticket, epsilon_data)
        urgency, urgency_reason, has_workaround = self._evaluate_urgency(ticket, epsilon_data)

        priority = self._calculate_matrix(impact, urgency, has_workaround)

        # Regla de Etiquetado Operativo Explícito (/SL1 y /SL2) en Nomenclatura de N1 (it-severity-matrix v2)
        title_raw = str(ticket.get("Descripción") or ticket.get("descripcion") or (epsilon_data.get("titulo") if epsilon_data else "") or "")
        status_raw = str(ticket.get("Estatus") or (epsilon_data.get("estadoActual") if epsilon_data else "") or "").lower()
        is_closed = "cerrad" in status_raw or "resuelt" in status_raw or "cancelad" in status_raw
        if not is_closed:
            if re.search(r"(?:^|/|\s|\|)SL1(?:/|\s|\||$|:)", title_raw, flags=re.IGNORECASE):
                priority = "P1"
                impact = "Alto"
                impact_reason = "Etiquetado explícito /SL1 por N1 en apertura (Emergencia Crítica)."
                if urgency == "Baja":
                    urgency = "Alta"
                    urgency_reason = "Emergencia /SL1 activa en tratamiento prioritario."
            elif re.search(r"(?:^|/|\s|\|)SL2(?:/|\s|\||$|:)", title_raw, flags=re.IGNORECASE) and priority not in ("P1", "P2"):
                priority = "P2"
                if impact == "Bajo":
                    impact = "Medio"
                    impact_reason = "Etiquetado explícito /SL2 por N1 (Incidencia Mayor / Pérdida de redundancia o degradación)."

        # Regla Operativa de Aging Escalation:
        # P2 activa por >= 120 minutos sin workaround autorizado escala preventivamente a P1
        raw_date = ticket.get("Fecha de envío") or ticket.get("fecha_envio") or ""
        parsed_date = parse_incident_datetime(raw_date)
        sla_info = compute_emergency_sla_status(parsed_date, reference_time=reference_time)
        mins_open = sla_info.get("minutos_desde_apertura")

        aging_escalated = False
        aging_criterion_prefix = ""
        if not is_closed and priority == "P2" and has_workaround != "Sí" and mins_open is not None and mins_open >= 120:
            priority = "P1"
            aging_escalated = True
            aging_criterion_prefix = f"Aging Escalation (>120m en P2 sin workaround - {mins_open}m) | "
            urgency_reason = f"Escalado operativo a P1 por tiempo transcurrido ({mins_open} min >= 120 min) sin mitigación ni workaround."

        is_high_priority = priority in ("P1", "P2")

        original_raw = ticket.get("Prioridad") or ticket.get("prioridad")
        disc_details = compute_discrepancy_details(original_raw, priority, reasons=[impact_reason, urgency_reason])
        is_discrepancy = disc_details["es_discrepancia"]

        proceso, proceso_negocio, dominio_tecnico = self._classify_process_multi_domain(ticket, epsilon_data)
        criterio = self._determine_criterion(proceso, priority, impact, urgency, ticket, epsilon_data, quant_metrics)
        if aging_criterion_prefix:
            criterio = aging_criterion_prefix + criterio

        sla_minutes = SLA_TARGET_MINUTES.get(priority, 240)

        # Reglas de Oro 2 y 3 (orange-it-emergency-management): Gobernanza de Workarounds
        if has_workaround == "Sí":
            workaround_gobernanza = "Pendiente autorización IM-CSO (SL1 activa)"
        elif has_workaround == "No":
            workaround_gobernanza = "Sin workaround (Resolución directa requerida)"
        else:
            workaround_gobernanza = "No identificado"

        return {
            "prioridad_sugerida": priority,
            "es_alta_prioridad": is_high_priority,
            "es_discrepancia": is_discrepancy,
            "discrepancia_delta": disc_details["delta"],
            "discrepancia_gravedad": disc_details["gravedad"],
            "discrepancia_motivo": disc_details["motivo"],
            "aging_escalated": aging_escalated,
            "evaluacion": {
                "proceso": proceso,
                "proceso_negocio": proceso_negocio,
                "dominio_tecnico": dominio_tecnico,
                "criterio": criterio,
                "impacto": impact,
                "impacto_justificacion": impact_reason,
                "urgencia": urgency,
                "urgencia_justificacion": urgency_reason,
                "workaround": has_workaround,
                "workaround_gobernanza": workaround_gobernanza,
                "sla_objetivo_minutos": sla_minutes,
                "metricas_cuantitativas": quant_metrics,
                "es_discrepancia": is_discrepancy,
                "discrepancia_delta": disc_details["delta"],
                "discrepancia_gravedad": disc_details["gravedad"],
                "discrepancia_motivo": disc_details["motivo"],
                "aging_escalated": aging_escalated,
            }
        }

    @staticmethod
    def _score_patterns(patterns: list[re.Pattern], text: str) -> int:
        if not text:
            return 0
        return sum(len(p.findall(text)) for p in patterns)

    @classmethod
    def _classify_process_multi_domain(
        cls,
        ticket: dict[str, Any],
        epsilon: Optional[dict[str, Any]]
    ) -> tuple[str, str, str]:
        """Performs multi-domain weighted scoring and produces dual ITIL labeling.
        
        Weights:
        - Grupo Resolutor / Asignado: 4.0
        - Epsilon Sistemas: 3.0
        - Título / Incidencia: 2.0
        - Descripción / Problema / Impacto: 1.0
        
        Returns:
            (proceso_principal, proceso_negocio, dominio_tecnico)
        """
        group = str(ticket.get("Grupo asignado") or ticket.get("Grupo Resolutor") or "")
        title = str(ticket.get("Descripción") or ticket.get("descripcion") or (epsilon.get("titulo") if epsilon else "") or "")
        
        sistemas_text = ""
        if epsilon and isinstance(epsilon.get("sistemas"), list):
            sistemas_text = " ".join(str(s) for s in epsilon.get("sistemas", []) if s)
        
        desc = str(ticket.get("Descripción") or ticket.get("descripcion") or "")
        problem_text = ""
        if epsilon:
            problem_text = f"{epsilon.get('problema', '')} {epsilon.get('impacto', '')}"
        detail_corpus = f"{desc} {problem_text}"

        scores: dict[str, float] = {}
        for category, patterns in PROCESS_PATTERNS.items():
            g_score = cls._score_patterns(patterns, group) * 4.0
            s_score = cls._score_patterns(patterns, sistemas_text) * 3.0
            t_score = cls._score_patterns(patterns, title) * 2.0
            d_score = cls._score_patterns(patterns, detail_corpus) * 1.0
            total = g_score + s_score + t_score + d_score
            scores[category] = total

        sorted_categories = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        top_cat, top_score = sorted_categories[0]

        if top_score <= 0.0:
            top_cat = "Sistemas Core"

        business_candidates = [
            (c, s) for c, s in sorted_categories if c in BUSINESS_PROCESS_CATEGORIES and s > 0.0
        ]
        top_business = business_candidates[0][0] if business_candidates else (
            top_cat if top_cat in BUSINESS_PROCESS_CATEGORIES else "Operación IT"
        )

        technical_candidates = [
            (c, s) for c, s in sorted_categories if c in TECHNICAL_DOMAIN_CATEGORIES and s > 0.0
        ]
        top_technical = technical_candidates[0][0] if technical_candidates else (
            top_cat if top_cat in TECHNICAL_DOMAIN_CATEGORIES else "Sistemas Core"
        )

        return top_cat, top_business, top_technical

    @staticmethod
    def _classify_process(ticket: dict[str, Any], epsilon: Optional[dict[str, Any]]) -> str:
        """Classifies incident into one of the 10 Critical Business / Technical Blocks (it-severity-matrix v2: 3.1 to 3.10)."""
        top_cat, _, _ = SeverityEvaluator._classify_process_multi_domain(ticket, epsilon)
        return top_cat

    @staticmethod
    def _determine_criterion(
        process: str,
        priority: str,
        impact: str,
        urgency: str,
        ticket: dict[str, Any],
        epsilon: Optional[dict[str, Any]],
        quant_metrics: Optional[dict[str, Any]] = None,
    ) -> str:
        """Determines the specific threshold or ITIL rule applied from the it-severity-matrix skill (3.1 to 3.10)."""
        crit = "Regla de Oro N1: Triaje preventivo SL1/P1 en apertura por riesgo de impacto"
        if priority == "P1":
            if process == "Atención al Cliente (ATC)":
                crit = "ATC (3.1): Frontales/CRM (>20% desviación en 30m) o Regla de Oro N1"
            elif process == "Ventas":
                crit = "Ventas (3.2): Afectación canal comercial (>30% volumen) o bloqueo contratación"
            elif process == "Portabilidad":
                crit = "Portabilidad (3.2/3.4): Flujo 2 AM o entidad de referencia (>2h retraso)"
            elif process == "Prepago":
                crit = "Prepago (3.3): >10% errores o >30 min sin altas/recargas (APRS/OCS)"
            elif process == "Provisión":
                crit = "Provisión (3.4): Órdenes en error (>20% móvil / >30% fijo) o Regla de Oro N1"
            elif process == "Facturación y Cobros":
                crit = "Facturación/Cobros (3.5/3.6): >3h sin tarificación online o bloqueo ciclo activo"
            elif process == "Middleware e Integración Transversal":
                crit = "Middleware (3.7): Caída o bloqueo transversal en bus/API (APIGEE/TIBCO/Datapower/OCCI)"
            elif process == "Conectividad de Sedes, Call Centers y Tiendas":
                crit = "Conectividad Sedes (3.8): Caída simultánea de circuitos (principal + backup) o aislamiento MSC"
            elif process == "Infraestructura Core IT, BBDD y Cloud":
                crit = "Infraestructura Core/Cloud (3.9): Corte troncal Cloud (OCI/GCP) o servidor/clúster sin absorción HA"
            elif process == "Identidad (GDU/EVIDIAN) y Automatización":
                crit = "Identidad y Automatización (3.10): Caída global de autenticación (GDU/EVIDIAN) o ROBOTFACTORY"
            elif process == "Operación y Monitorización (O&M)":
                crit = "O&M: Compromiso en herramienta esencial de supervisión (Regla de Oro N1)"

        elif priority == "P2":
            if process == "Conectividad de Sedes, Call Centers y Tiendas":
                crit = "Conectividad Sedes/Tiendas (3.8 SL2): Caída de circuito único con backup activo o tienda individual"
            elif process == "Infraestructura Core IT, BBDD y Cloud":
                crit = "Infraestructura Core/Cloud (3.9 SL2): Caída de nodo (ESX/PSeries/Exadata) o alerta SAN absorbida por HA"
            elif process == "Identidad (GDU/EVIDIAN) y Automatización":
                crit = "Identidad y Automatización (3.10 SL2): Degradación parcial en GDU/EVIDIAN o fallo acotado en ROBOTFACTORY"
            elif process == "Middleware e Integración Transversal":
                crit = "Middleware (3.7 SL2): Latencia elevada o errores intermitentes en pasarela API/bus con reintentos"
            else:
                crit = "SL2 Mayor: Degradación funcional o afectación en sede sin indisponibilidad global"

        elif priority == "P3":
            crit = "SL3 Menor: Bajo impacto en procesos secundarios o alarmas menores"
        else:
            crit = "SL4 Informativa: Seguimiento sin afectación directa a servicios"

        if quant_metrics:
            if quant_metrics.get("sedes") is not None and quant_metrics["sedes"] >= 3:
                return f"Umbral Cuantitativo (>=3 sedes: {quant_metrics['sedes']}) | {crit}"
            if quant_metrics.get("usuarios") is not None and quant_metrics["usuarios"] >= 500:
                return f"Umbral Cuantitativo (>=500 usuarios: {quant_metrics['usuarios']}) | {crit}"
            if quant_metrics.get("desviacion_pct") is not None and quant_metrics["desviacion_pct"] >= 20.0:
                return f"Umbral Cuantitativo (>={quant_metrics['desviacion_pct']}%) | {crit}"

        return crit

    def _evaluate_impact(self, ticket: dict[str, Any], epsilon: Optional[dict[str, Any]]) -> Tuple[str, str, dict[str, Any]]:
        text_corpus = ""
        epsilon_impact = ""
        epsilon_problema = ""
        if epsilon:
            epsilon_impact = str(epsilon.get("impacto") or "").strip()
            epsilon_problema = str(epsilon.get("problema") or "").strip()
            text_corpus += f" {epsilon_problema} {epsilon_impact}"
        desc = ticket.get("Descripción") or ticket.get("descripcion") or ""
        text_corpus += f" {desc}"
        text_lower = text_corpus.lower()

        ticket_impact = (ticket.get("Impacto") or ticket.get("impacto") or "").strip().lower()

        # Extraer métricas cuantitativas deterministas
        quant_metrics = extract_quantitative_metrics(text_corpus)

        # -1. Fallo cosmético o sin afectación de servicio
        if any(k in text_lower for k in [
            "error tipográfico", "error tipografico", "cosmético", "cosmetico",
            "sin afectación", "sin afectacion", "problema cosmético", "problema cosmetico"
        ]):
            return "Bajo", "Fallo cosmético sin interrupción de servicio.", quant_metrics

        # 0. Umbrales Cuantitativos Directos (SL1)
        # Nota: Si el servicio cuenta con respaldo activo o el tráfico principal cursa normalmente (ej. enlaces secundarios),
        # se clasifica como degradación funcional parcial SL2 (it-severity-matrix 3.8/3.9).
        is_secondary_or_redundant = any(k in text_lower for k in [
            "secundari", "tráfico principal cursando", "trafico principal cursando",
            "backup activo", "respaldo activo", "enlace secundario"
        ])

        if not is_secondary_or_redundant:
            reasons = []
            if quant_metrics["sedes"] is not None and quant_metrics["sedes"] >= 3:
                reasons.append(f"{quant_metrics['sedes']} sedes/tiendas afectadas (umbral crítico >= 3)")
            if quant_metrics["usuarios"] is not None and quant_metrics["usuarios"] >= 500:
                reasons.append(f"{quant_metrics['usuarios']} usuarios/clientes afectados (umbral crítico >= 500)")
            if quant_metrics["desviacion_pct"] is not None and quant_metrics["desviacion_pct"] >= 20.0:
                reasons.append(f"{quant_metrics['desviacion_pct']}% de afectación/desviación (umbral crítico >= 20%)")

            if reasons:
                return "Alto", f"Umbral cuantitativo superado: {', '.join(reasons)}.", quant_metrics

        # 1. Regla Crítica (Impacto Alto con filtro de negación sintáctica en texto)
        found_critical_kw = None
        for kw in self.CRITICAL_IMPACT_KEYWORDS:
            for match in re.finditer(re.escape(kw), text_lower):
                if not is_phrase_negated(text_lower, match.span()):
                    found_critical_kw = kw
                    break
            if found_critical_kw:
                break

        # 2. Diagnóstico de Epsilon Resumen IA (si está disponible)
        epsilon_evaluated_high = False
        if epsilon_impact:
            ep_imp_lower = epsilon_impact.lower()
            if any(ep_imp_lower.startswith(prefix) for prefix in ["alto", "crítico", "critico", "urgente"]) or \
               ("afecta a todos los clientes" in ep_imp_lower or "100% en operativa" in ep_imp_lower or "15+ sedes" in ep_imp_lower):
                epsilon_evaluated_high = True

        # Decisión de Impacto Alto
        if found_critical_kw or epsilon_evaluated_high:
            if epsilon_impact and epsilon_evaluated_high:
                clean_ep = re.sub(r"\s+", " ", epsilon_impact).strip()
                return "Alto", f"Epsilon IA: {clean_ep[:180]}", quant_metrics
            if found_critical_kw:
                return "Alto", f"Afectación crítica detectada ('{found_critical_kw}') sobre el servicio principal sin alternativa viable.", quant_metrics
            return "Alto", "Afectación crítica o corte global sobre el servicio principal sin alternativa viable.", quant_metrics

        # 3. Regla Moderada (Impacto Medio con filtro de negación)
        found_moderate_kw = None
        for kw in self.MODERATE_IMPACT_KEYWORDS:
            for match in re.finditer(re.escape(kw), text_lower):
                if not is_phrase_negated(text_lower, match.span()):
                    found_moderate_kw = kw
                    break
            if found_moderate_kw:
                break

        # Si Epsilon está disponible con diagnóstico de afectación acotada o degradación
        if epsilon_impact:
            clean_ep = re.sub(r"\s+", " ", epsilon_impact).strip()
            return "Medio", f"Epsilon IA: {clean_ep[:180]}", quant_metrics

        if found_moderate_kw:
            return "Medio", f"Degradación funcional reportada ('{found_moderate_kw}') con servicio parcialmente operativo.", quant_metrics

        # 4. Inferencia cuando Remedy marca "Masiva" o "Alto" o "Medio"
        # En el export de Remedy todas las incidencias vienen con "Impacto: Masiva", lo que indica un ticket
        # registrado en la mesa de seguimiento de incidencias de servicio.
        # Al no presentar corte total ni superar umbrales de caída masiva (>=3 sedes, >=500 usuarios),
        # se clasifica de forma determinista como Impacto Medio (degradación funcional / servicio alternativo / incidente mayor P2).
        if ticket_impact in ("masiva", "alto", "medio"):
            return "Medio", "Incidencia catalogada Masiva en Remedy evaluada como degradación funcional parcial sin corte total de servicio.", quant_metrics

        # 5. Regla Menor (Impacto Bajo)
        return "Bajo", "Afectación acotada a componentes secundarios o usuarios aislados.", quant_metrics

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
        elif "sin alternativa" in text_lower or "sin workaround" in text_lower or "sin solución temporal" in text_lower:
            has_workaround = "No"

        # Epsilon bloqueos
        epsilon_bloqueos_str = ""
        if epsilon:
            raw_blq = epsilon.get("bloqueos")
            if isinstance(raw_blq, list):
                epsilon_bloqueos_str = "; ".join(str(b) for b in raw_blq if b).strip()
            elif isinstance(raw_blq, str):
                epsilon_bloqueos_str = raw_blq.strip()

        if epsilon_bloqueos_str:
            blq_lower = epsilon_bloqueos_str.lower()
            if any(k in blq_lower for k in ["sin alternativa", "sin workaround", "sin método", "sin metodo", "bloqueo", "esperando", "dependencia"]):
                if has_workaround != "Sí":
                    has_workaround = "No"

        # Si el ticket ya está cerrado o resuelto
        if "cerrad" in status or "resuelt" in status:
            return "Baja", "Incidencia ya resuelta o estabilizada por el equipo resolutor.", has_workaround

        # Elevación de urgencia por bloqueos reportados por Epsilon IA sin workaround
        if epsilon_bloqueos_str and has_workaround == "No":
            return "Alta", f"Bloqueo operativo activo reportado por Epsilon IA: {epsilon_bloqueos_str[:100]}.", has_workaround

        # Urgencia Alta (Remedy exporta "Crítica" o "Alta")
        if any(kw in text_lower for kw in self.HIGH_URGENCY_KEYWORDS) or ticket_urgency in ("crítica", "critica", "alta"):
            return "Alta", "Impacto activo en vivo que requiere restablecimiento inmediato.", has_workaround

        # Urgencia Media (En curso / Asignado, o Urgencia Media/Medio activa sin bloqueo por espera Pendiente)
        if "en curso" in status or "asigna" in status or (ticket_urgency in ("media", "medio") and "pendiente" not in status):
            return "Media", "Incidencia en tratamiento con contención operativa transitoria.", has_workaround

        # Urgencia Baja
        return "Baja", "Incidencia de baja sensibilidad temporal o sin bloqueo activo.", has_workaround

    @staticmethod
    def _calculate_matrix(impact: str, urgency: str, has_workaround: str) -> str:
        """Applies ITIL Impact x Urgency cross-reference rules with Orange Emergency Golden Rules.
        
        Regla de Oro 3 (orange-it-emergency-management):
        Un workaround NO reduce automáticamente la severidad del ticket. Una Emergencia SL1 solo
        se da por resuelta cuando el impacto sobre el negocio o servicio ha desaparecido por completo.
        """
        if impact == "Alto":
            if urgency in ("Alta", "Media"):
                return "P1"
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

        eval_data = evaluation.get("evaluacion") if isinstance(evaluation.get("evaluacion"), dict) else evaluation
        proceso = eval_data.get("proceso")
        criterio = eval_data.get("criterio")
        if proceso:
            prompt_lines.append(f"Proceso de Negocio: {proceso}")
        if criterio:
            prompt_lines.append(f"Criterio / Umbral: {criterio}")

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
            hitos = resumen_ia.get("hitosTecnicos") or resumen_ia.get("hitos_tecnicos")
            if hitos and isinstance(hitos, list):
                context_for_tz = f"{resumen_ia.get('impacto', '')} {resumen_ia.get('problema', '')} {titulo}"
                reconciled = reconcile_milestones(hitos, context_text=context_for_tz)
                prompt_lines.append("• Hitos cronológicos / técnicos:")
                for r in reconciled:
                    prompt_lines.append(f"  - {r['reconciled']}")
                remote_item = next((r for r in reconciled if r.get("has_remote_tz")), None)
                if remote_item:
                    prompt_lines.append(f"  ℹ️ NOTA HORARIA ({remote_item['source_label']}): La detección técnica se registró a las {remote_item['source_str']} local ({remote_item['madrid_str']}). Usa siempre hora Madrid (CET) en las comunicaciones para Dirección.")
        else:
            prompt_lines.append("\n--- Metadatos del ticket (Epsilon IA pendiente) ---")
            prompt_lines.append(f"• Descripción: {titulo}")
            prompt_lines.append(f"• Impacto ticket: {ticket.get('Impacto') or ticket.get('impacto') or 'N/D'}")
            prompt_lines.append(f"• Urgencia ticket: {ticket.get('Urgencia', 'N/D')}")
            prompt_lines.append("• ⚠️ REGLA ANTI-ALUCINACIÓN (Modo Restringido): Al no disponer de telemetría Epsilon IA, queda TERMINANTEMENTE PROHIBIDO conjeturar causas técnicas (bases de datos, cuellos de botella, microservicios, etc.). Redacta indicando que el equipo resolutor se encuentra investigando el origen de la anomalía.")

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

    @classmethod
    def generate_emergency_4blocks_report(
        cls,
        ticket: dict[str, Any],
        evaluation: dict[str, Any],
        resumen_ia: Optional[dict[str, Any]] = None,
        sla_status: Optional[dict[str, Any]] = None,
    ) -> str:
        """Generates the standardized 4-block emergency report mandated by orange-it-emergency-management."""
        inc_id = ticket.get("ID de incidencia") or ticket.get("id") or "INC"
        titulo = ticket.get("Descripción") or ticket.get("descripcion") or (resumen_ia.get("titulo") if resumen_ia else "")
        prio = evaluation.get("prioridad_sugerida", "P1")
        sl_level = "SL1 (Emergencia Crítica)" if prio == "P1" else ("SL2 (Incidencia Mayor)" if prio == "P2" else f"SL{prio[-1]}")

        eval_data = evaluation.get("evaluacion") if isinstance(evaluation.get("evaluacion"), dict) else evaluation
        proceso = eval_data.get("proceso", "Sistemas Core")
        dominio_tecnico = eval_data.get("dominio_tecnico")
        criterio = eval_data.get("criterio", "Regla de Oro N1")
        impacto = eval_data.get("impacto", "Alto")
        impacto_just = eval_data.get("impacto_justificacion", "Afectación crítica en servicio.")
        urgencia = eval_data.get("urgencia", "Alta")
        urgencia_just = eval_data.get("urgencia_justificacion", "Impacto activo en vivo.")
        workaround = eval_data.get("workaround", "No")
        workaround_gob = eval_data.get("workaround_gobernanza", "Pendiente autorización IM-CSO (SL1 activa)" if workaround == "Sí" else "Sin workaround")
        disc_motivo = evaluation.get("discrepancia_motivo") or eval_data.get("discrepancia_motivo")
        disc_gravedad = evaluation.get("discrepancia_gravedad") or eval_data.get("discrepancia_gravedad")
        aging_esc = evaluation.get("aging_escalated") or eval_data.get("aging_escalated")

        sistemas_list = []
        if resumen_ia and isinstance(resumen_ia.get("sistemas"), list):
            sistemas_list = [s for s in resumen_ia["sistemas"] if s]
        if not sistemas_list and ticket.get("Grupo asignado"):
            sistemas_list = [ticket["Grupo asignado"]]
        sistemas_str = ", ".join(sistemas_list) if sistemas_list else "Servicios Core"

        # Detección de Estado del Ticket (Cerrado/Resuelto vs Activo)
        status_raw = str(ticket.get("Estatus") or (resumen_ia.get("estadoActual") if resumen_ia else "") or "").lower()
        is_closed = any(s in status_raw for s in ["cerrad", "resuelt", "cancelad"])

        # Tiempos operativos y formato legible
        sla_data = sla_status or {}
        mins = sla_data.get("minutos_desde_apertura")
        mins_str = format_operational_duration(mins)
        sla_notif_vencido = sla_data.get("sla_primera_notificacion_vencido", False)
        req_tel = sla_data.get("requiere_escalado_telefonico", False)
        esc_sup = sla_data.get("escalado_estamentos_superiores", False)

        # Reglas de Gobernanza de Workaround (orange-it-emergency-management)
        if workaround == "Sí":
            workaround_gob = "APLICADO - Pendiente autorización IM-CSO (No desescala la severidad activa)"
        elif workaround == "No":
            workaround_gob = "SIN WORKAROUND (Requiere resolución directa en servicio/infraestructura)"
        else:
            workaround_gob = "No identificado"

        # Protocolo de Escalado: Normal vs Paralelo (Estructural)
        requires_parallel = (
            proceso in ("Middleware e Integración Transversal", "Infraestructura Core IT, BBDD y Cloud")
            or dominio_tecnico in ("Middleware e Integración Transversal", "Infraestructura Core IT, BBDD y Cloud")
        )

        problema = (resumen_ia.get("problema") if resumen_ia else None) or titulo
        solucion = (resumen_ia.get("solucion") if resumen_ia else None) or "Diagnóstico y contención técnica en curso por equipos resolutores"
        siguiente = (resumen_ia.get("siguienteAccion") or resumen_ia.get("siguiente_accion") if resumen_ia else None) or "Auditoría preventiva PaP y restablecimiento de servicio"

        lines = [
            "🚨 REPORTE DE EMERGENCIA IT - ORANGE TECH OPERATIONS",
            "────────────────────────────────────────────────────────────",
            "[1] CLASIFICACIÓN DEL TICKET",
            f"• Incidencia: {inc_id} ({sl_level})",
            f"• Proceso Crítico: {proceso}",
        ]
        if dominio_tecnico and dominio_tecnico != proceso:
            lines.append(f"• Dominio Técnico: {dominio_tecnico}")
        if disc_motivo:
            lines.append(f"• Alerta de Subescalación: {disc_motivo} [{disc_gravedad}]")
        if aging_esc:
            lines.append("• Escalado por Envejecimiento: Elevado a P1 tras >=120 min activo sin workaround")
        lines.extend([
            f"• Umbral de Emergencia: {criterio}",
            f"• Alcance y Sistemas: {sistemas_str}",
            f"• Impacto: {impacto} ({impacto_just})",
            f"• Urgencia: {urgencia} ({urgencia_just})",
            "",
            "[2] ESTADO DE COMUNICACIONES Y SLAS",
        ])

        if is_closed:
            lines.extend([
                f"• Estado Operativo: ✅ INCIDENCIA RESUELTA / ESTABILIZADA",
                f"• Duración Total: {mins_str} hasta restablecimiento",
                "• Notificación de Cierre: Emitida a Dirección y partes interesadas",
                "• War Room / Teams: Concluida y desconvocada por Incident Manager",
            ])
        else:
            if mins is None:
                estado_1a_notif = "En ventana (<20 min)"
            else:
                estado_1a_notif = (
                    f"⚠️ SLA 1ª Notificación VENCIDO (>20 min - {mins_str} transcurridos)"
                    if sla_notif_vencido
                    else f"✅ En SLA 1ª Notificación (<20 min - {mins_str} transcurridos)"
                )

            lines.extend([
                f"• Tiempo desde Apertura: {mins_str}",
                f"• 1ª Notificación a Dirección: {estado_1a_notif}",
                "• Frecuencia de Actualizaciones: Cada 60 min (o <30m ante cambios críticos)",
                "• War Room / Teams: Liderado por Incident Manager (IM)",
            ])

        lines.extend([
            "",
            "[3] PLAN DE ACCIÓN Y GOBERNANZA DE WORKAROUNDS",
            f"• Diagnóstico Técnico: {problema}",
            f"• Acciones en Curso: {solucion}",
            f"• Siguiente Hito: {siguiente}",
            f"• Workaround: {workaround} | Gobernanza: {workaround_gob}",
            "• Regla de Oro: Prohibida la desescalada automática sin erradicación total del impacto",
            "• Revisión Trabajos Programados (PaP): Auditoría preventiva de Rollback en curso",
            "",
            "[4] ESTADO DE ESCALADO TELEFÓNICO",
        ])

        if is_closed:
            lines.extend([
                "• Protocolo de Tiempos: ✅ Proceso de escalado concluido por resolución",
                "• Transición Operativa: Paso a Post-Incident Review (PIR) / Problem Management",
                "• Regla de Oro 3: Confirmada erradicación total del impacto en servicio y negocio",
            ])
        else:
            if mins is None:
                estado_escalado = "Ventana operativa inicial (<45 min)"
            elif mins >= 120 and prio == "P1":
                estado_escalado = f"🚨 ALARMA POR ESTANCAMIENTO (>2h): Escalado a Dirección IM-CSO y reevaluación técnica ({mins_str})"
            elif esc_sup:
                estado_escalado = f"🚨 2º Escalado Requerido a Estamentos Superiores (+{mins_str} transcurridos)"
            elif req_tel:
                estado_escalado = f"📞 1er Escalado Telefónico Requerido a N3/Proveedor (+{mins_str} transcurridos)"
            else:
                estado_escalado = f"🟢 En plazo de intervención inicial ({mins}/45 min)"

            lines.append(f"• Protocolo de Tiempos: {estado_escalado}")

            if requires_parallel:
                lines.append("• Directiva de Escalado: ⚡ ESCALADO EN PARALELO ACTIVADO (Convocatoria simultánea obligatoria a todos los grupos resolutores)")
            else:
                lines.append("• Canal de Escalado: Vía Telefónica obligatoria (Regla de Oro)")

        lines.extend([
            "• Matrices de Contacto: GRIAL (entornos Orange/Jazztel) | Confluence (entornos MasMóvil/KRT)",
            "• Gobernanza RACI: Incident Manager (R) / Customer & Service Ops IM-CSO (A)",
            "────────────────────────────────────────────────────────────"
        ])
        return "\n".join(lines)


class EpsilonClient:
    """Client for Epsilon Resumen IA service with local file caching and graceful offline handling."""

    CACHE_TTL_SECONDS = 900  # 15 minutes
    CORPORATE_URL = "https://soptmc.si.orange.es/MonTMC/api/epsilon/resumenIA"
    DEFAULT_CANDIDATE_URLS = [
        "http://127.0.0.1:8081/api/epsilon/resumenIA",
        "http://127.0.0.1:8080/api/epsilon/resumenIA",
        "https://soptmc.si.orange.es/MonTMC/api/epsilon/resumenIA",
    ]

    def __init__(self, base_url: str = "http://127.0.0.1:8081/api/epsilon/resumenIA", cache_dir: Optional[Path] = None, max_consecutive_failures: int = 3):
        self.base_url = base_url.rstrip("/")
        self.cache_dir = cache_dir or Path("data/.epsilon_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_consecutive_failures = max_consecutive_failures
        self._server_offline = False
        self._consecutive_failures = 0
        self._allow_fallback = (base_url.rstrip("/") == "http://127.0.0.1:8081/api/epsilon/resumenIA")
        self._fallback_urls = [u for u in self.DEFAULT_CANDIDATE_URLS if u != self.base_url]

    def _get_cache_path(self, incident_code: str) -> Path:
        return self.cache_dir / f"{incident_code}.json"

    def _fetch_from_url(self, target_base: str, incident_code: str) -> Optional[dict[str, Any]]:
        url = f"{target_base}/{incident_code}"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "ReleaseDashboard-Evaluator/1.0", "Accept": "application/json"}
        )
        ssl_ctx = None
        if url.startswith("https://"):
            ssl_ctx = ssl.create_default_context()
            ssl_ctx.check_hostname = False
            ssl_ctx.verify_mode = ssl.CERT_NONE

        with urllib.request.urlopen(req, timeout=5.0, context=ssl_ctx) as resp:
            if resp.status == 200:
                payload = json.loads(resp.read().decode("utf-8"))
                data = payload.get("data") if isinstance(payload, dict) and "data" in payload else payload
                if data:
                    return data
        return None

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

        try:
            data = self._fetch_from_url(self.base_url, incident_code)
            if data:
                self._consecutive_failures = 0
                try:
                    with open(cache_file, "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                except Exception as write_err:
                    logger.debug("No se pudo escribir caché para %s: %s", incident_code, write_err)
                return data
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as net_err:
            if self._allow_fallback and self._fallback_urls:
                for candidate in list(self._fallback_urls):
                    try:
                        cand_data = self._fetch_from_url(candidate, incident_code)
                        if cand_data:
                            logger.info("Conectado con éxito a endpoint alternativo de Epsilon: %s", candidate)
                            self.base_url = candidate
                            self._fallback_urls.remove(candidate)
                            self._consecutive_failures = 0
                            try:
                                with open(cache_file, "w", encoding="utf-8") as f:
                                    json.dump(cand_data, f, ensure_ascii=False, indent=2)
                            except Exception as write_err:
                                logger.debug("No se pudo escribir caché para %s: %s", incident_code, write_err)
                            return cand_data
                    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError):
                        pass

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
    source_file_name: str = "",
    reference_time: Optional[datetime] = None
) -> dict[str, Any]:
    """Processes a batch of massive incidents and constructs the High Priority catalog with Orange IT Emergency Management."""
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
        evaluation = evaluator.evaluate(item, epsilon_data, reference_time=reference_time)

        prio_sugerida = evaluation["prioridad_sugerida"]
        es_alta = evaluation["es_alta_prioridad"]
        es_disc = evaluation["es_discrepancia"]

        if es_disc:
            discrepancies_count += 1

        if prio_sugerida == "P1":
            p1_count += 1
        elif prio_sugerida == "P2":
            p2_count += 1

        # Construir mensajes ejecutivos y reporte de emergencia para alta prioridad o discrepancias
        if es_alta or es_disc:
            raw_date = item.get("Fecha de envío") or item.get("fecha_envio") or ""
            parsed_date = parse_incident_datetime(raw_date)
            sla_status = compute_emergency_sla_status(parsed_date, reference_time=reference_time)

            eval_dict = dict(evaluation["evaluacion"])
            eval_dict["fecha_apertura"] = raw_date
            eval_dict["minutos_desde_apertura"] = sla_status["minutos_desde_apertura"]
            eval_dict["sla_primera_notificacion_vencido"] = sla_status["sla_primera_notificacion_vencido"]
            eval_dict["requiere_escalado_telefonico"] = sla_status["requiere_escalado_telefonico"]
            eval_dict["escalado_estamentos_superiores"] = sla_status["escalado_estamentos_superiores"]
            eval_dict["proxima_ventana_update_minutos"] = sla_status["proxima_ventana_update_minutos"]
            evaluation["evaluacion"] = eval_dict

            mensajes = msg_generator.generate(item, evaluation, epsilon_data)
            reporte_emergencia = msg_generator.generate_emergency_4blocks_report(
                ticket=item,
                evaluation=evaluation,
                resumen_ia=epsilon_data,
                sla_status=sla_status,
            )
            # reporte_emergencia se expone exclusivamente en la raíz de la incidencia (evitando duplicidad en mensajes_ejecutivos)
            
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
                "discrepancia_delta": evaluation.get("discrepancia_delta", 0),
                "discrepancia_gravedad": evaluation.get("discrepancia_gravedad", "Sin discrepancia"),
                "discrepancia_motivo": evaluation.get("discrepancia_motivo", ""),
                "aging_escalated": evaluation.get("aging_escalated", False),
                "estatus": item.get("Estatus") or "Asignado",
                "fecha_envio": raw_date,
                "fecha_apertura": raw_date,
                "evaluacion": eval_dict,
                "resumen_ia": resumen_ia_block,
                "mensajes_ejecutivos": mensajes,
                "reporte_emergencia": reporte_emergencia,
            })

    # Ordenar: primero P1, luego discrepancias, luego P2
    def sort_key(doc: dict[str, Any]) -> tuple[int, int]:
        prio_val = 0 if doc["prioridad_sugerida"] == "P1" else (1 if doc["prioridad_sugerida"] == "P2" else 2)
        disc_val = 0 if doc["es_discrepancia"] else 1
        return (prio_val, disc_val)

    high_priority_items.sort(key=sort_key)

    sla_vencidos_count = sum(1 for it in high_priority_items if it.get("evaluacion", {}).get("sla_primera_notificacion_vencido"))
    escalados_tel_count = sum(1 for it in high_priority_items if it.get("evaluacion", {}).get("requiere_escalado_telefonico"))
    workaround_pendientes_count = sum(1 for it in high_priority_items if "Pendiente" in str(it.get("evaluacion", {}).get("workaround_gobernanza", "")))
    disc_delta1_count = sum(1 for it in high_priority_items if it.get("discrepancia_delta") == 1)
    disc_delta2_count = sum(1 for it in high_priority_items if it.get("discrepancia_delta") == 2)
    disc_delta3_count = sum(1 for it in high_priority_items if it.get("discrepancia_delta") == 3)
    aging_escaladas_p1_count = sum(1 for it in high_priority_items if it.get("aging_escalated"))

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
                "discrepancies_count": discrepancies_count,
                "discrepancias_delta1_moderada_count": disc_delta1_count,
                "discrepancias_delta2_mayor_count": disc_delta2_count,
                "discrepancias_delta3_critica_count": disc_delta3_count,
                "aging_escaladas_p1_count": aging_escaladas_p1_count,
                "sla_primera_notificacion_vencidos_count": sla_vencidos_count,
                "requiere_escalado_telefonico_count": escalados_tel_count,
                "workaround_pendientes_cso_count": workaround_pendientes_count,
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
        "Evaluación completada: %d escaneadas (%d omitidas por estado final/cerrado, %d activas), %d de alta prioridad (P1: %d, P2: %d), %d discrepancias. SLA 1ª notif vencidos: %d, Escalados telefónicos req: %d, Workarounds pend. CSO: %d.",
        kpis["total_scanned"],
        kpis["terminal_skipped_count"],
        kpis["active_evaluated_count"],
        kpis["total_high_priority"],
        kpis["p1_critical_count"],
        kpis["p2_high_count"],
        kpis["discrepancies_count"],
        kpis.get("sla_primera_notificacion_vencidos_count", 0),
        kpis.get("requiere_escalado_telefonico_count", 0),
        kpis.get("workaround_pendientes_cso_count", 0),
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
