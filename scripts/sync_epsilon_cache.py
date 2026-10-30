#!/usr/bin/env python3
"""
Sincronizador de Caché de Epsilon Resumen IA para Incidencias IT de Orange.

Descarga y actualiza de forma previa la síntesis técnica oficial desde la API corporativa
de Orange (https://soptmc.si.orange.es/MonTMC/api/epsilon/resumenIA/{codigo}) hacia la
caché local persistente en data/.epsilon_cache/{codigo}.json.

Uso:
    python scripts/sync_epsilon_cache.py --all-active
    python scripts/sync_epsilon_cache.py --id INC000004171670
    python scripts/sync_epsilon_cache.py --verify
    python scripts/sync_epsilon_cache.py --all-active --force
"""

import argparse
import json
import logging
import os
import ssl
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("sync_epsilon")

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
    return Path(__file__).resolve().parent.parent


ENDPOINTS = [
    "https://soptmc.si.orange.es/MonTMC/api/epsilon/resumenIA",
    "http://127.0.0.1:8081/api/epsilon/resumenIA",
    "http://127.0.0.1:8080/api/epsilon/resumenIA",
]


def fetch_epsilon_payload(incident_code: str, timeout: float = 6.0) -> Optional[dict[str, Any]]:
    headers = {
        "User-Agent": "ReleaseDashboard-Prefetcher/1.0",
        "Accept": "application/json"
    }
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE

    for base in ENDPOINTS:
        url = f"{base}/{incident_code}"
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=ssl_ctx if url.startswith("https") else None) as resp:
                if resp.status == 200:
                    payload = json.loads(resp.read().decode("utf-8"))
                    data = payload.get("data") if isinstance(payload, dict) and "data" in payload else payload
                    if data and isinstance(data, dict):
                        return data
        except Exception:
            continue
    return None


def get_active_incident_ids(root: Path) -> list[str]:
    notif_file = root / "data" / "output" / "high_priority_notifications.json"
    ids = []
    if notif_file.exists():
        try:
            with open(notif_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                items = data.get("data", [])
                for it in items:
                    inc_id = it.get("id")
                    if inc_id and inc_id not in ids:
                        ids.append(inc_id)
        except Exception as e:
            logger.warning("Error leyendo notificaciones de alta prioridad: %s", e)

    # Si hay menos de 1, buscar en ficheros masivos
    if not ids:
        massive_dir = root / "data" / "output"
        for massive_file in massive_dir.glob("*-massive.json"):
            try:
                with open(massive_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    records = data.get("data", [])
                    for r in records:
                        st = str(r.get("Estatus") or r.get("estatus") or "").lower()
                        if st not in ("cerrado", "cerrada", "closed", "resuelto", "resuelta", "resolved", "cancelado"):
                            inc_id = r.get("ID de incidencia") or r.get("id")
                            if inc_id and inc_id not in ids:
                                ids.append(inc_id)
            except Exception:
                pass
    return ids


def sync_incident(root: Path, inc_id: str, force: bool = False) -> tuple[str, Optional[dict[str, Any]]]:
    cache_dir = root / "data" / ".epsilon_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / f"{inc_id}.json"

    if cache_file.exists() and not force:
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return "CACHED", data
        except Exception:
            pass

    data = fetch_epsilon_payload(inc_id)
    if data:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return "DOWNLOADED", data
    return "UNAVAILABLE", None


def main():
    parser = argparse.ArgumentParser(description="Sincronizador de caché Epsilon IA de incidencias.")
    parser.add_argument("--all-active", action="store_true", help="Sincroniza todas las incidencias activas detectadas.")
    parser.add_argument("--id", type=str, help="Sincroniza una incidencia específica por su código.")
    parser.add_argument("--force", action="store_true", help="Fuerza la descarga remota ignorando la caché local.")
    parser.add_argument("--verify", action="store_true", help="Comprueba el estado de la caché para incidencias activas sin descargar.")
    args = parser.parse_args()

    root = find_repo_root()
    cache_dir = root / "data" / ".epsilon_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    if args.id:
        targets = [args.id.strip().upper()]
    elif args.all_active or args.verify:
        targets = get_active_incident_ids(root)
    else:
        parser.print_help()
        return

    if not targets:
        logger.info("No se detectaron incidencias activas para sincronizar.")
        return

    logger.info("Analizando %d incidencias...", len(targets))
    cached_count = 0
    downloaded_count = 0
    missing_count = 0

    print("=" * 72)
    print(" SINCRONIZACIÓN DE TELEMETRÍA EPSILON IA (ORANGE IT EMERGENCY MANAGEMENT)")
    print("=" * 72)

    for idx, inc_id in enumerate(targets, 1):
        cache_file = cache_dir / f"{inc_id}.json"
        has_cache = cache_file.exists()

        if args.verify:
            if has_cache:
                try:
                    with open(cache_file, "r", encoding="utf-8") as f:
                        d = json.load(f)
                        prob = (d.get("problema") or "-")[:55]
                        print(f"[{idx:02d}] {inc_id} -> ✅ CACHED | {prob}...")
                        cached_count += 1
                except Exception:
                    print(f"[{idx:02d}] {inc_id} -> ⚠️ CORRUPT CACHE")
                    missing_count += 1
            else:
                print(f"[{idx:02d}] {inc_id} -> ❌ MISSING CACHE")
                missing_count += 1
            continue

        status, payload = sync_incident(root, inc_id, force=args.force)
        if status == "CACHED":
            cached_count += 1
            print(f"[{idx:02d}] {inc_id} -> ⚡ CACHED (Local)")
        elif status == "DOWNLOADED":
            downloaded_count += 1
            prob = (payload.get("problema") or "-")[:50]
            print(f"[{idx:02d}] {inc_id} -> 🚀 DOWNLOADED | {prob}...")
        else:
            missing_count += 1
            print(f"[{idx:02d}] {inc_id} -> ⚠️ NO DISPONIBLE EN EPSILON (Red restringida o ticket no indexado)")

    print("-" * 72)
    print(f"Resumen: {cached_count} en caché local, {downloaded_count} descargadas, {missing_count} no disponibles.")
    print("=" * 72)


if __name__ == "__main__":
    main()

