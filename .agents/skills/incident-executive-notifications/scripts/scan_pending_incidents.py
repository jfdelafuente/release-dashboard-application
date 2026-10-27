#!/usr/bin/env python3
"""
Escanea data/output/high_priority_notifications.json y data/agent_executive_messages.json
para detectar qué incidencias activas de alta prioridad carecen de redacción oficial
del agente incident-reporter o se encuentran en estado 'pendiente'.
"""

import argparse
import json
import sys
from pathlib import Path

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


def main():
    parser = argparse.ArgumentParser(description="Escanea incidencias activas pendientes de redacción de agente.")
    parser.add_argument("--json", action="store_true", help="Salida en formato JSON compacto de las pendientes.")
    parser.add_argument("--id", help="Detalle completo de una incidencia concreta (prompt context listo para el agente).")
    args = parser.parse_args()

    root = find_repo_root()
    notif_path = root / "data" / "output" / "high_priority_notifications.json"
    store_path = root / "data" / "agent_executive_messages.json"

    if not notif_path.exists():
        print(f"[ERROR] No existe {notif_path}. Ejecuta primero evaluate_incident_notifications.py.")
        sys.exit(1)

    try:
        with open(notif_path, "r", encoding="utf-8") as f:
            notif_data = json.load(f)
    except Exception as e:
        print(f"[ERROR] No se pudo leer {notif_path}: {e}")
        sys.exit(1)

    agent_store = {}
    if store_path.exists():
        try:
            with open(store_path, "r", encoding="utf-8") as f:
                store_data = json.load(f)
                agent_store = store_data.get("incidents", {})
        except Exception as e:
            print(f"[AVISO] No se pudo leer el almacén de agentes: {e}")

    items = notif_data.get("data", [])
    total_active = len(items)

    if args.id:
        match = next((it for it in items if it.get("id") == args.id), None)
        if not match:
            print(f"[ERROR] Incidencia {args.id} no encontrada entre las activas de alta prioridad.")
            sys.exit(1)
        print(json.dumps(match, ensure_ascii=False, indent=2))
        return

    pending_items = []
    completed_items = []

    for it in items:
        inc_id = it.get("id", "N/D")
        msgs = it.get("mensajes_ejecutivos", {})
        apertura = msgs.get("apertura", {})

        in_store = inc_id in agent_store and bool(agent_store[inc_id].get("apertura", {}).get("completo"))
        is_pending = apertura.get("estado") == "pendiente" or not apertura.get("completo") or not in_store

        if is_pending:
            pending_items.append(it)
        else:
            completed_items.append(it)

    if args.json:
        out = {
            "total_active": total_active,
            "completed_count": len(completed_items),
            "pending_count": len(pending_items),
            "pending": [
                {
                    "id": it.get("id"),
                    "prioridad": it.get("prioridad_sugerida"),
                    "titulo": it.get("titulo"),
                    "sistemas": it.get("sistemas"),
                    "has_epsilon": bool((it.get("resumen_ia") or {}).get("problema") or (it.get("resumen_ia") or {}).get("impacto"))
                }
                for it in pending_items
            ]
        }
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return

    print("=" * 70)
    print(" ESTADO DE REDACCIONES EJECUTIVAS DE AGENTE (incident-reporter)")
    print("=" * 70)
    print(f"Total incidencias activas de alta prioridad: {total_active}")
    print(f"  • Con mensaje oficial generado:           {len(completed_items)}")
    print(f"  • Pendientes de redacción de agente:       {len(pending_items)}")
    print("=" * 70)

    if not pending_items:
        print("\n✅ Todas las incidencias activas disponen de mensajes ejecutivos oficiales.")
        print("   No se requiere redacción adicional.")
        return

    print("\n⚠️  INCIDENCIAS PENDIENTES DE REDACCIÓN:")
    print("-" * 70)

    for idx, it in enumerate(pending_items, 1):
        inc_id = it.get("id")
        prio = it.get("prioridad_sugerida")
        sistemas = ", ".join(it.get("sistemas", [])) if isinstance(it.get("sistemas"), list) else (it.get("sistemas") or "-")
        res = it.get("resumen_ia") or {}
        has_epsilon = bool(res.get("problema") or res.get("impacto"))

        ev = it.get("evaluacion") or {}
        proceso = ev.get("proceso") or "-"
        criterio = ev.get("criterio") or "-"
        print(f"[{idx}] {inc_id} ({prio}) - {it.get('titulo')}")
        print(f"    Proceso:  {proceso} | Criterio: {criterio}")
        print(f"    Sistemas: {sistemas}")
        print(f"    Epsilon IA: {'✨ Disponible' if has_epsilon else 'ℹ️ Solo metadatos Remedy'}")
        if has_epsilon:
            if res.get("problema"):
                print(f"    • Problema:  {res.get('problema')[:80]}...")
            if res.get("impacto"):
                print(f"    • Impacto:   {res.get('impacto')[:80]}...")
            if res.get("solucion"):
                print(f"    • Solución:  {res.get('solucion')[:80]}...")
        print()

    print("-" * 70)
    print("💡 Para redactar una de estas incidencias:")
    print("   1. Activa la skill 'incident-executive-notifications' o invoca el rol incident-reporter.")
    print("   2. Guarda cada redacción con:")
    print("      python converters/cli/update_agent_message.py --id <INC> --phase apertura --raw \"<salida>\"")


if __name__ == "__main__":
    main()

