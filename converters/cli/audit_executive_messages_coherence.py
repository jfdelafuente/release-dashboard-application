#!/usr/bin/env python3
"""
Audit Executive Messages Coherence & Quality Assurance Tool.

Verifies that executive communications in data/agent_executive_messages.json:
1. Comply strictly with length and single-paragraph constraints (<= 90 words for completo, <= 30 for breve).
2. Adhere to Anti-Hallucination rules (no ungrounded technical claims like database bottlenecks,
   latencies or unverified components when absent from Epsilon IA telemetry).
3. Preserve Ground Truth fidelity with cached Epsilon IA data (key systems, error codes, impact metrics).
4. Respect Timezone integrity (Madrid CET reference time for executive messages).
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import re
import sys
from typing import Any, Optional

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


@dataclass
class CoherenceIssue:
    incident_id: str
    phase: str
    level: str  # "ERROR" or "WARNING"
    rule: str
    message: str


SUSPICIOUS_UNGROUNDED_PATTERNS = [
    (r"\b(consultas?\s+a\s+base\s+de\s+datos|cuello\s+de\s+botella|latencias?\s+est[aá]ndar|capa\s+de\s+aplicaci[oó]n)\b",
     "Posible alucinación técnica genérica ('{}') no respaldada por telemetría Epsilon ni Remedy."),
    (r"\b(microservicios?|reinicio\s+de\s+pod|reinicio\s+de\s+nodo)\b",
     "Mención de componente de infraestructura ('{}') que debe estar contrastado en telemetría."),
]


def count_words(text: str) -> int:
    """Counts words in a text snippet."""
    if not text:
        return 0
    return len([w for w in text.split() if w.strip()])


def audit_incident_messages(
    incident_id: str,
    stored_phases: dict[str, Any],
    epsilon_data: Optional[dict[str, Any]] = None,
    remedy_title: str = ""
) -> list[CoherenceIssue]:
    """
    Audits executive messages for a single incident across all phases (apertura, seguimiento, cierre).
    """
    issues: list[CoherenceIssue] = []

    # Combined evidence corpus for anti-hallucination checking
    evidence_text = (remedy_title or "").lower()
    if epsilon_data:
        evidence_text += " " + (epsilon_data.get("problema") or "").lower()
        evidence_text += " " + (epsilon_data.get("impacto") or "").lower()
        evidence_text += " " + (epsilon_data.get("solucion") or "").lower()
        hitos = epsilon_data.get("hitosTecnicos") or []
        evidence_text += " " + " ".join(hitos).lower()
        bloqueos = epsilon_data.get("bloqueos") or []
        evidence_text += " " + " ".join(bloqueos).lower()
        sistemas = epsilon_data.get("sistemas") or []
        evidence_text += " " + " ".join(sistemas).lower()

    for phase in ("apertura", "seguimiento", "cierre"):
        phase_data = stored_phases.get(phase)
        if not phase_data or not isinstance(phase_data, dict):
            continue

        completo = phase_data.get("completo", "")
        breve = phase_data.get("breve", "")

        # 1. Structural Checks: Word counts and single paragraph
        if completo:
            w_comp = count_words(completo)
            if w_comp > 90:
                issues.append(CoherenceIssue(
                    incident_id=incident_id,
                    phase=phase,
                    level="ERROR",
                    rule="WORD_COUNT_COMPLETO",
                    message=f"Versión completa excede límite de 90 palabras ({w_comp} palabras)."
                ))
            if "\n" in completo.strip():
                issues.append(CoherenceIssue(
                    incident_id=incident_id,
                    phase=phase,
                    level="ERROR",
                    rule="MONOPARRAFO_COMPLETO",
                    message="Versión completa contiene múltiples párrafos o saltos de línea."
                ))

        if breve:
            w_brev = count_words(breve)
            if w_brev > 30:
                issues.append(CoherenceIssue(
                    incident_id=incident_id,
                    phase=phase,
                    level="ERROR",
                    rule="WORD_COUNT_BREVE",
                    message=f"Versión breve excede límite de 30 palabras ({w_brev} palabras)."
                ))
            if "\n" in breve.strip():
                issues.append(CoherenceIssue(
                    incident_id=incident_id,
                    phase=phase,
                    level="ERROR",
                    rule="MONOPARRAFO_BREVE",
                    message="Versión breve contiene múltiples párrafos o saltos de línea."
                ))

        # 2. Anti-Hallucination & Evidence Grounding
        combined_msg = f"{completo} {breve}".lower()
        if epsilon_data and combined_msg.strip():
            for pat, desc in SUSPICIOUS_UNGROUNDED_PATTERNS:
                match = re.search(pat, combined_msg)
                if match:
                    term = match.group(0)
                    # Check if this term was actually grounded in evidence
                    if term not in evidence_text:
                        issues.append(CoherenceIssue(
                            incident_id=incident_id,
                            phase=phase,
                            level="WARNING",
                            rule="UNGROUNDED_TECHNICAL_CLAIM",
                            message=desc.format(term)
                        ))

            # Check if incident ID is mentioned in apertura
            if phase == "apertura" and incident_id not in (completo + breve):
                issues.append(CoherenceIssue(
                    incident_id=incident_id,
                    phase=phase,
                    level="WARNING",
                    rule="MISSING_INCIDENT_ID",
                    message=f"El mensaje de apertura no cita explícitamente el identificador {incident_id}."
                ))

            # Check if key error code or unique identifier from Epsilon is preserved
            # Example: clusterID=0
            if "clusterid=0" in evidence_text or "clusterid" in evidence_text:
                if "clusterid" not in combined_msg and "cluster" not in combined_msg:
                    issues.append(CoherenceIssue(
                        incident_id=incident_id,
                        phase=phase,
                        level="WARNING",
                        rule="MISSING_KEY_TELEMETRY",
                        message="La telemetría Epsilon contiene 'clusterID' pero no se menciona en el mensaje."
                    ))

            # 3. Timezone Coherence: Remote site detection time vs Madrid time
            if any(k in evidence_text for k in ["medellin", "medellín", "bogota", "bogotá"]):
                # If message specifies a morning hour < 09:00 without CET/Madrid qualification
                time_matches = re.findall(r"\b(0[4-8]:\d{2})\b", combined_msg)
                if time_matches:
                    issues.append(CoherenceIssue(
                        incident_id=incident_id,
                        phase=phase,
                        level="WARNING",
                        rule="UNCONVERTED_REMOTE_TIMEZONE",
                        message=f"Se detectó hora local de Colombia ({time_matches[0]}) en el mensaje sin convertir a hora Madrid (CET)."
                    ))

    return issues


def find_repo_root() -> Path:
    cur = Path(__file__).resolve().parent
    for p in [cur] + list(cur.parents):
        if (p / "VERSION").exists() and (p / "data").exists():
            return p
    return Path(__file__).resolve().parents[2]


def run_audit(root: Optional[Path] = None, target_id: Optional[str] = None) -> dict[str, Any]:
    if root is None:
        root = find_repo_root()

    store_path = root / "data" / "agent_executive_messages.json"
    cache_dir = root / "data" / ".epsilon_cache"
    notif_path = root / "data" / "output" / "high_priority_notifications.json"

    if not store_path.exists():
        return {
            "success": False,
            "error": f"No se encontró {store_path}",
            "issues": []
        }

    try:
        with open(store_path, "r", encoding="utf-8") as f:
            store_data = json.load(f)
    except Exception as e:
        return {"success": False, "error": f"Error leyendo {store_path}: {e}", "issues": []}

    incidents_store = store_data.get("incidents", {})

    # Load notifications for remedy metadata if available
    remedy_titles = {}
    if notif_path.exists():
        try:
            with open(notif_path, "r", encoding="utf-8") as f:
                n_data = json.load(f)
                for it in n_data.get("data", []):
                    remedy_titles[it.get("id")] = it.get("titulo", "")
        except Exception:
            pass

    all_issues: list[CoherenceIssue] = []
    audited_count = 0

    for inc_id, phases in incidents_store.items():
        if target_id and inc_id != target_id:
            continue

        audited_count += 1
        # Try loading epsilon cache
        eps_data = None
        eps_file = cache_dir / f"{inc_id}.json"
        if eps_file.exists():
            try:
                with open(eps_file, "r", encoding="utf-8") as f:
                    eps_data = json.load(f)
            except Exception:
                pass

        remedy_t = remedy_titles.get(inc_id, "")
        issues = audit_incident_messages(inc_id, phases, eps_data, remedy_t)
        all_issues.extend(issues)

    errors = [asdict(i) for i in all_issues if i.level == "ERROR"]
    warnings = [asdict(i) for i in all_issues if i.level == "WARNING"]

    return {
        "success": len(errors) == 0,
        "audited_count": audited_count,
        "error_count": len(errors),
        "warning_count": len(warnings),
        "errors": errors,
        "warnings": warnings,
        "all_issues": [asdict(i) for i in all_issues]
    }


def main():
    parser = argparse.ArgumentParser(description="Audita coherencia y calidad de redacciones ejecutivas.")
    parser.add_argument("--id", help="Filtrar por identificador de incidencia específico.")
    parser.add_argument("--json", action="store_true", help="Salida en formato JSON.")
    parser.add_argument("--strict", action="store_true", help="Falla si existen errores o advertencias.")
    args = parser.parse_args()

    results = run_audit(target_id=args.id)

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
        sys.exit(0 if results["success"] and (not args.strict or results["warning_count"] == 0) else 1)

    print("=" * 70)
    print(" AUDITORÍA DE COHERENCIA Y FIDELIDAD DE MENSAJES EJECUTIVOS")
    print("=" * 70)
    print(f"Incidencias auditadas:  {results.get('audited_count', 0)}")
    print(f"Errores estructurales: {results.get('error_count', 0)}")
    print(f"Advertencias fidelidad: {results.get('warning_count', 0)}")
    print("=" * 70)

    if results.get("error_count", 0) > 0:
        print("\n❌ ERRORES DETECTADOS (Incumplimiento de normas ITIL / Límites):")
        for err in results["errors"]:
            print(f"  • [{err['incident_id']}] ({err['phase'].upper()}) - {err['rule']}: {err['message']}")

    if results.get("warning_count", 0) > 0:
        print("\n⚠️  ADVERTENCIAS DE FIDELIDAD O ALUCINACIÓN:")
        for w in results["warnings"]:
            print(f"  • [{w['incident_id']}] ({w['phase'].upper()}) - {w['rule']}: {w['message']}")

    if results.get("error_count", 0) == 0 and results.get("warning_count", 0) == 0:
        print("\n✅ Todos los mensajes ejecutivos cumplen con los límites de palabras, monopárrafo,")
        print("   fidelidad con Epsilon IA y coherencia horaria.")

    if not results["success"] or (args.strict and results.get("warning_count", 0) > 0):
        sys.exit(1)


if __name__ == "__main__":
    main()
