#!/usr/bin/env python3
"""
CLI Helper para actualizar data/agent_executive_messages.json con las salidas
del Agente incident-reporter y regenerar automáticamente las notificaciones.

Uso:
  1. Pasando texto bruto (--raw) copiado directamente del chat/LLM:
     python converters/cli/update_agent_message.py --id INC000004159463 --phase apertura --raw "..."

  2. Leyendo desde un fichero de texto (--file):
     python converters/cli/update_agent_message.py --id INC000004159463 --phase apertura --file respuesta.txt

  3. Pasando versiones explícitas (--completo y --breve):
     python converters/cli/update_agent_message.py --id INC000004159463 --phase apertura --completo "..." --breve "..."

  4. Modo interactivo (-i):
     python converters/cli/update_agent_message.py -i
"""

import argparse
import datetime
import json
import logging
import re
import sys
from pathlib import Path
from typing import Any, Optional, Tuple

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("update_agent_message")


def parse_agent_raw_output(raw: str) -> Tuple[str, str]:
    """Extrae la Versión Completa y la Versión Breve de la salida del agente."""
    clean = (raw or "").strip()
    if not clean:
        return "", ""

    completo = ""
    breve = ""

    # 1. Regex para Versión Completa (Dirección)
    comp_pattern = re.compile(
        r"\*\*(?:Mensaje para Dirección|Versión Completa)[^\*]*\*\*[:\s]*([\s\S]*?)(?=\*\*(?:Versión aún más breve|Versión breve)[^\*]*\*\*|$)",
        re.IGNORECASE
    )
    comp_match = comp_pattern.search(clean)
    if comp_match:
        completo = comp_match.group(1).strip()

    # 2. Regex para Versión Breve
    brev_pattern = re.compile(
        r"\*\*(?:Versión aún más breve|Versión breve)[^\*]*\*\*[:\s]*([\s\S]*?)$",
        re.IGNORECASE
    )
    brev_match = brev_pattern.search(clean)
    if brev_match:
        breve = brev_match.group(1).strip()

    # 3. Fallback si no se usó el formato estándar de cabeceras en negrita
    if not completo and not breve:
        paragraphs = [p.strip() for p in clean.split("\n\n") if p.strip()]
        if len(paragraphs) >= 2:
            completo = paragraphs[0]
            breve = paragraphs[1]
        elif paragraphs:
            completo = paragraphs[0]
            first_sentence = clean.split(".")[0].strip()
            breve = (first_sentence + ".") if first_sentence else clean[:100]

    # Limpiar posibles restos de notas entre paréntesis al inicio: (único párrafo, máx 90 palabras)
    completo = re.sub(r"^\([^)]*\)\s*", "", completo)
    breve = re.sub(r"^\([^)]*\)\s*", "", breve)

    # Limpiar comillas exteriores
    completo = completo.strip("\"'` ")
    breve = breve.strip("\"'` ")

    # Asegurar monopárrafo estricto para Versión Completa
    completo = " ".join(completo.split())
    breve = " ".join(breve.split())

    return completo, breve


def resolve_default_paths() -> Tuple[Path, Path]:
    """Resuelve la ruta al almacén de mensajes y al script de evaluación."""
    root = Path(__file__).resolve().parent.parent.parent
    store_path = root / "data" / "agent_executive_messages.json"
    eval_script = root / "converters" / "cli" / "evaluate_incident_notifications.py"
    return store_path, eval_script


def update_agent_store(
    store_path: Path,
    incident_id: str,
    phase: str,
    completo: str,
    breve: str,
    origen: str = "incident-reporter"
) -> dict[str, Any]:
    """Carga, actualiza y guarda el almacén oficial de mensajes ejecutivos de agente."""
    incident_id = incident_id.strip().upper()
    phase = phase.strip().lower()

    if phase not in ("apertura", "seguimiento", "cierre"):
        raise ValueError(f"Fase no válida: '{phase}'. Debe ser 'apertura', 'seguimiento' o 'cierre'.")

    data: dict[str, Any] = {
        "_metadata": {
            "version": "1.0.0",
            "description": "Almacén oficial de redacciones ejecutivas generadas por el Agente incident-reporter",
            "source": "agents/it-incidents/incident-reporter.md",
            "updated_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        },
        "incidents": {}
    }

    if store_path.exists():
        try:
            with open(store_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict):
                    data = loaded
        except Exception as e:
            logger.warning("No se pudo leer el archivo existente %s (%s). Se creará nuevo.", store_path, e)

    if "_metadata" not in data or not isinstance(data["_metadata"], dict):
        data["_metadata"] = {}
    data["_metadata"]["updated_at"] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    if "incidents" not in data or not isinstance(data["incidents"], dict):
        data["incidents"] = {}

    if incident_id not in data["incidents"]:
        data["incidents"][incident_id] = {}

    words_comp = len(completo.split()) if completo else 0
    words_brev = len(breve.split()) if breve else 0

    entry = {
        "completo": completo,
        "breve": breve,
        "generado_por_agente": True,
        "origen": origen,
        "conteo_palabras_completo": words_comp,
        "conteo_palabras_breve": words_brev
    }

    data["incidents"][incident_id][phase] = entry

    # Guardar atómicamente
    store_path.parent.mkdir(parents=True, exist_ok=True)
    with open(store_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return entry


def run_re_evaluation(eval_script: Path) -> bool:
    """Ejecuta evaluate_incident_notifications.py para regenerar high_priority_notifications.json."""
    if not eval_script.exists():
        logger.warning("No se encontró evaluate_incident_notifications.py en %s", eval_script)
        return False

    import subprocess
    logger.info("Regenerando catálogo de notificaciones de alta prioridad...")
    res = subprocess.run([sys.executable, str(eval_script)], capture_output=True, text=True)
    if res.returncode == 0:
        logger.info("Notificaciones actualizadas con éxito.")
        return True
    else:
        logger.error("Error al actualizar notificaciones:\n%s", res.stderr or res.stdout)
        return False


def interactive_mode(store_path: Path, eval_script: Path) -> None:
    """Solicita los datos interactivamente en la terminal."""
    print("=" * 60)
    print(" Actualizador de Salidas de Agente incident-reporter")
    print("=" * 60)
    inc_id = input("ID de Incidencia (ej. INC000004159463): ").strip()
    if not inc_id:
        print("ID de incidencia requerido. Cancelado.")
        return

    phase = input("Fase [apertura / seguimiento / cierre] (def: apertura): ").strip().lower()
    if not phase:
        phase = "apertura"

    print("\nPega a continuación la salida completa devuelta por el Agente.")
    print("Finaliza la entrada escribiendo 'EOF' en una línea vacía o pulsando Ctrl+Z / Ctrl+D:")
    lines = []
    try:
        while True:
            line = input()
            if line.strip() == "EOF":
                break
            lines.append(line)
    except EOFError:
        pass

    raw_text = "\n".join(lines).strip()
    if not raw_text:
        print("No se introdujo texto. Cancelado.")
        return

    completo, breve = parse_agent_raw_output(raw_text)

    print("\n" + "-" * 50)
    print(f"Versión Completa ({len(completo.split())}/90 palabras):")
    print(completo)
    print("\n" + "-" * 50)
    print(f"Versión Breve ({len(breve.split())}/30 palabras):")
    print(breve)
    print("-" * 50)

    confirm = input("\n¿Guardar en data/agent_executive_messages.json? (S/n): ").strip().lower()
    if confirm in ("", "s", "si", "y", "yes"):
        entry = update_agent_store(store_path, inc_id, phase, completo, breve)
        print(f"\n[OK] Guardado correctamente para {inc_id} ({phase}).")
        run_re_evaluation(eval_script)
    else:
        print("Operación cancelada.")


def main():
    default_store, default_eval = resolve_default_paths()

    parser = argparse.ArgumentParser(
        description="Actualiza data/agent_executive_messages.json con las salidas oficiales del Agente incident-reporter."
    )
    parser.add_argument("--id", "-i", dest="incident_id", help="ID de la incidencia (ej. INC000004159463)")
    parser.add_argument("--phase", "-p", default="apertura", choices=["apertura", "seguimiento", "cierre"], help="Fase (apertura, seguimiento, cierre)")
    parser.add_argument("--raw", "-r", help="Texto bruto copiado directamente del chat/LLM")
    parser.add_argument("--file", "-f", help="Ruta a un archivo que contiene la respuesta del LLM")
    parser.add_argument("--completo", help="Versión completa de Dirección explícita")
    parser.add_argument("--breve", help="Versión breve explícita")
    parser.add_argument("--interactive", action="store_true", help="Modo interactivo en consola")
    parser.add_argument("--store", help="Ruta alternativa a agent_executive_messages.json")
    parser.add_argument("--no-eval", action="store_true", help="No regenerar high_priority_notifications.json tras guardar")

    args = parser.parse_args()

    store_path = Path(args.store) if args.store else default_store
    eval_script = default_eval

    if args.interactive or (len(sys.argv) == 1):
        interactive_mode(store_path, eval_script)
        return

    if not args.incident_id:
        parser.error("El argumento --id es obligatorio a menos que se use --interactive.")

    completo = ""
    breve = ""

    if args.completo or args.breve:
        completo = (args.completo or "").strip()
        breve = (args.breve or "").strip()
    elif args.file:
        file_path = Path(args.file)
        if not file_path.exists():
            parser.error(f"El archivo especificado no existe: {file_path}")
        content = file_path.read_text(encoding="utf-8")
        completo, breve = parse_agent_raw_output(content)
    elif args.raw:
        completo, breve = parse_agent_raw_output(args.raw)
    else:
        parser.error("Debes proporcionar --raw, --file, o (--completo y --breve).")

    if not completo and not breve:
        parser.error("No se pudo extraer ni la versión completa ni la breve del texto proporcionado.")

    words_comp = len(completo.split()) if completo else 0
    words_brev = len(breve.split()) if breve else 0

    if words_comp > 90:
        logger.warning("ADVERTENCIA: La versión completa tiene %d palabras (límite: 90).", words_comp)
    if words_brev > 30:
        logger.warning("ADVERTENCIA: La versión breve tiene %d palabras (límite: 30).", words_brev)

    entry = update_agent_store(store_path, args.incident_id, args.phase, completo, breve)
    logger.info("Guardado con éxito en %s para %s (%s).", store_path, args.incident_id.upper(), args.phase)
    logger.info("  Versión Completa (%d palabras): %s", words_comp, completo[:80] + "..." if len(completo) > 80 else completo)
    logger.info("  Versión Breve (%d palabras): %s", words_brev, breve)

    if not args.no_eval:
        run_re_evaluation(eval_script)


if __name__ == "__main__":
    main()

