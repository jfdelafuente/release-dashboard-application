#!/usr/bin/env python3
"""
clean_system_data.py
====================
Script de purga y reseteo controlado de datos históricos para dejar el sistema
completamente limpio antes de subir nuevos ficheros de incidencias o postmortems.

Acciones realizadas:
1. Elimina todos los CSVs en data/input/
2. Elimina los ficheros *-massive.json y *-postmortem.json en data/output/
3. Vacía data/archive/ y data/errors/
4. Vacía la caché de IA corporativa data/.epsilon_cache/
5. Vacía la caché de detalle Remedy data/.remedy_cache/
6. Elimina los informes *.pptx generados dinámicamente en data/reports/ (preserva
   los pregenerados versionados en git como fallback de descarga inmediata)
7. Trunca a vacío data/logs/ingestion_audit.log
8. Resetea data/agent_executive_messages.json a {}
9. Resetea data/output/index.json a estructura vacía
10. Resetea data/output/high_priority_notifications.json a catálogo vacío
11. Resetea data/output/ingestion_audit_summary.json a estructura vacía
12. Resetea data/output/teams_delivery_audit.json a historial vacío ([])

Ficheros PROTEGIDOS (NUNCA se tocan):
- data/scheduled_changes_pap.json (Catálogo de Trabajos Programados / CRQs Remedy)
- data/output/agents_catalog.json (Catálogo de Agentes IA del repositorio)
- Archivos .gitkeep y .gitignore

Uso:
  python scripts/clean_system_data.py            # Modo interactivo con confirmación
  python scripts/clean_system_data.py --dry-run  # Simulación (solo muestra lo que borraría)
  python scripts/clean_system_data.py --yes      # Ejecución desatendida sin confirmación
"""

import os
import sys
import json
import shutil
import argparse
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple

_GIT_EXE = shutil.which('git') or r'C:\Program Files\Git\mingw64\bin\git.exe'

# Asegurar codificación utf-8 segura en Windows cmd/powershell
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Ficheros protegidos por su nombre o ruta relativa que NUNCA se deben borrar
PROTECTED_FILENAMES = {
    'scheduled_changes_pap.json',
    'agents_catalog.json',
    '.gitkeep',
    '.gitignore',
}

EMPTY_INDEX_TEMPLATE = {
    "postmortem": {
        "count": 0,
        "files": []
    },
    "massive": {
        "count": 0,
        "files": []
    }
}

EMPTY_HIGH_PRIORITY_TEMPLATE = {
    "_metadata": {
        "generated_at": None,
        "source_file": None,
        "kpis": {
            "total_tickets": 0,
            "p1_p2_count": 0,
            "discrepancias_count": 0,
            "criticos_count": 0,
            "con_resumen_ia_count": 0,
            "completas_count": 0,
            "parciales_count": 0,
            "incompletas_count": 0
        }
    },
    "data": []
}

EMPTY_INGESTION_AUDIT_TEMPLATE = {
    "_metadata": {
        "timestamp": None,
        "source_file": None,
        "elapsed_seconds": 0.0,
        "kpis": {
            "total_tickets": 0,
            "terminales_omitidas_count": 0,
            "con_resumen_ia_count": 0,
            "completas_count": 0,
            "parciales_count": 0,
            "incompletas_count": 0,
            "discrepancias_count": 0
        }
    },
    "incidents": []
}


def get_storage_dir(custom_path: str = None) -> Path:
    if custom_path:
        return Path(custom_path).resolve()
    env_dir = os.environ.get("RELEASE_DASHBOARD_STORAGE_DIR", "").strip()
    if env_dir:
        return Path(env_dir).resolve()
    vps_storage = Path("/infocodes/var/storage/release-dashboard")
    if vps_storage.is_dir():
        return vps_storage.resolve()
    return (PROJECT_ROOT / "data").resolve()


def _get_tracked_pptx_paths(reports_dir: Path) -> set:
    """Resuelve las rutas absolutas de los .pptx versionados en git bajo reports_dir.

    Solo tiene efecto cuando storage_dir vive dentro del repositorio (entorno local);
    en el VPS de producción, storage_dir está fuera del repo y git ls-files no devuelve
    nada, por lo que todos los .pptx se tratan como generados dinámicamente (sin
    cambio de comportamiento allí).
    """
    try:
        result = subprocess.run(
            [_GIT_EXE, 'ls-files', '--', '*.pptx'],
            cwd=reports_dir, capture_output=True, text=True, timeout=10, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return set()
    if result.returncode != 0:
        return set()
    return {(reports_dir / line.strip()).resolve() for line in result.stdout.splitlines() if line.strip()}


def collect_items_to_clean(storage_dir: Path, keep_cache: bool = False) -> Tuple[List[Path], List[Path], List[Path]]:
    """
    Identifica:
    - files_to_delete: Ficheros que se eliminarán por completo.
    - files_to_reset: Ficheros que se inicializarán a su plantilla vacía.
    - files_protected: Ficheros que se conservarán intactos.
    """
    files_to_delete: List[Path] = []
    files_to_reset: List[Path] = []
    files_protected: List[Path] = []

    # 1. data/input/ -> eliminar todos los CSV
    input_dir = storage_dir / 'input'
    if input_dir.exists():
        for p in input_dir.glob('*'):
            if p.is_file() and p.name not in PROTECTED_FILENAMES:
                files_to_delete.append(p)

    # 2. data/output/ -> eliminar *-massive.json y *-postmortem.json
    output_dir = storage_dir / 'output'
    if output_dir.exists():
        for p in output_dir.glob('*.json'):
            if p.name in PROTECTED_FILENAMES:
                files_protected.append(p)
            elif p.name.endswith('-massive.json') or p.name.endswith('-postmortem.json'):
                files_to_delete.append(p)
            elif p.name in ('index.json', 'high_priority_notifications.json', 'ingestion_audit_summary.json'):
                files_to_reset.append(p)

    # 3. data/archive/ y data/errors/ -> vaciar
    for folder_name in ('archive', 'errors'):
        folder = storage_dir / folder_name
        if folder.exists():
            for p in folder.glob('*'):
                if p.is_file() and p.name not in PROTECTED_FILENAMES:
                    files_to_delete.append(p)

    # 4. data/.epsilon_cache/ y data/.remedy_cache/ -> vaciar salvo que se pida conservar
    for cache_name in ('.epsilon_cache', '.remedy_cache'):
        cache_dir = storage_dir / cache_name
        if cache_dir.exists():
            for p in cache_dir.glob('*.json'):
                if keep_cache:
                    files_protected.append(p)
                else:
                    files_to_delete.append(p)

    # 5. data/reports/ -> eliminar *.pptx generados dinamicamente, preservando los
    # informes pregenerados versionados en git como fallback de descarga inmediata
    # (ver commit 37e474c, "incluir informes PPTX pregenerados y fallback resiliente")
    reports_dir = storage_dir / 'reports'
    if reports_dir.exists():
        tracked_pptx = _get_tracked_pptx_paths(reports_dir)
        for p in reports_dir.rglob('*.pptx'):
            if p.resolve() in tracked_pptx:
                files_protected.append(p)
            else:
                files_to_delete.append(p)

    # 6. data/agent_executive_messages.json -> resetear
    msg_file = storage_dir / 'agent_executive_messages.json'
    if msg_file.exists():
        files_to_reset.append(msg_file)

    # 7. data/logs/ingestion_audit.log -> truncar/resetear
    log_file = storage_dir / 'logs' / 'ingestion_audit.log'
    if log_file.exists():
        files_to_reset.append(log_file)

    # 7b. data/output/teams_delivery_audit.json -> resetear a historial vacío
    teams_audit_file = storage_dir / 'output' / 'teams_delivery_audit.json'
    if teams_audit_file.exists():
        files_to_reset.append(teams_audit_file)

    # 8. Ficheros protegidos en la raíz de data/
    pap_file = storage_dir / 'scheduled_changes_pap.json'
    if pap_file.exists():
        files_protected.append(pap_file)

    # Eliminar duplicados manteniendo orden
    files_to_delete = sorted(list(set(files_to_delete)))
    files_to_reset = sorted(list(set(files_to_reset)))
    files_protected = sorted(list(set(files_protected)))

    return files_to_delete, files_to_reset, files_protected


def format_bytes(size: int) -> str:
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} TB"


def execute_clean(storage_dir: Path, dry_run: bool = False, keep_cache: bool = False) -> Dict:
    to_delete, to_reset, protected = collect_items_to_clean(storage_dir, keep_cache=keep_cache)

    total_bytes_freed = 0
    deleted_count = 0
    reset_count = 0

    # Calcular tamaño de borrados
    for p in to_delete:
        try:
            total_bytes_freed += p.stat().st_size
        except OSError:
            pass

    if not dry_run:
        # 1. Borrar ficheros
        for p in to_delete:
            try:
                p.unlink()
                deleted_count += 1
            except Exception as e:
                print(f"  [ERROR] No se pudo borrar {p.name}: {e}", file=sys.stderr)

        # 2. Resetear ficheros estructurados
        index_file = storage_dir / 'output' / 'index.json'
        index_file.parent.mkdir(parents=True, exist_ok=True)
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(EMPTY_INDEX_TEMPLATE, f, indent=2, ensure_ascii=False)
        reset_count += 1

        hp_file = storage_dir / 'output' / 'high_priority_notifications.json'
        hp_file.parent.mkdir(parents=True, exist_ok=True)
        with open(hp_file, 'w', encoding='utf-8') as f:
            json.dump(EMPTY_HIGH_PRIORITY_TEMPLATE, f, indent=2, ensure_ascii=False)
        reset_count += 1

        audit_file = storage_dir / 'output' / 'ingestion_audit_summary.json'
        audit_file.parent.mkdir(parents=True, exist_ok=True)
        with open(audit_file, 'w', encoding='utf-8') as f:
            json.dump(EMPTY_INGESTION_AUDIT_TEMPLATE, f, indent=2, ensure_ascii=False)
        reset_count += 1

        msg_file = storage_dir / 'agent_executive_messages.json'
        with open(msg_file, 'w', encoding='utf-8') as f:
            f.write("{}\n")
        reset_count += 1

        log_file = storage_dir / 'logs' / 'ingestion_audit.log'
        log_file.parent.mkdir(parents=True, exist_ok=True)
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write("")  # Truncar a vacío
        reset_count += 1

        teams_audit_file = storage_dir / 'output' / 'teams_delivery_audit.json'
        teams_audit_file.parent.mkdir(parents=True, exist_ok=True)
        with open(teams_audit_file, 'w', encoding='utf-8') as f:
            json.dump([], f, indent=2, ensure_ascii=False)
        reset_count += 1

    else:
        deleted_count = len(to_delete)
        reset_count = len(to_reset)

    return {
        'dry_run': dry_run,
        'deleted_count': deleted_count,
        'reset_count': reset_count,
        'protected_count': len(protected),
        'bytes_freed': total_bytes_freed,
        'to_delete': to_delete,
        'to_reset': to_reset,
        'protected': protected
    }


def main():
    parser = argparse.ArgumentParser(
        description="Script de purga y reseteo de datos temporales (Release Dashboard Application)."
    )
    parser.add_argument(
        '--yes', '-y',
        action='store_true',
        help="Ejecutar el borrado sin solicitar confirmación interactiva."
    )
    parser.add_argument(
        '--dry-run', '-n',
        action='store_true',
        help="Simulación: muestra la lista de ficheros a borrar y resetear sin modificar nada."
    )
    parser.add_argument(
        '--keep-cache',
        action='store_true',
        help="Conservar las cachés de Epsilon (.epsilon_cache/) y Remedy (.remedy_cache/) en lugar de vaciarlas."
    )
    parser.add_argument(
        '--storage-dir',
        type=str,
        default=None,
        help="Ruta personalizada del directorio de almacenamiento (por defecto: data/)."
    )

    args = parser.parse_args()
    storage_dir = get_storage_dir(args.storage_dir)

    print("=" * 68)
    print("🧹 RELEASE DASHBOARD - PURGA Y RESETEO DE DATOS")
    print("=" * 68)
    print(f"Directorio de Almacenamiento: {storage_dir}")
    print(f"Modo de ejecución:           {'SIMULACIÓN (--dry-run)' if args.dry_run else 'REAL'}")
    if args.keep_cache:
        print("Opción activa:               Conservar .epsilon_cache/")
    print("-" * 68)

    to_delete, to_reset, protected = collect_items_to_clean(storage_dir, keep_cache=args.keep_cache)

    print(f"\n📦 Archivos a ELIMINAR ({len(to_delete)} ficheros):")
    if to_delete:
        for p in to_delete:
            try:
                rel = p.relative_to(PROJECT_ROOT)
            except ValueError:
                rel = p
            size_str = format_bytes(p.stat().st_size) if p.exists() else "0 B"
            print(f"  ❌ {rel} ({size_str})")
    else:
        print("  (Ninguno)")

    print(f"\n🔄 Archivos a REINICIALIZAR / TRUNCAR ({len(to_reset)} ficheros):")
    for p in to_reset:
        try:
            rel = p.relative_to(PROJECT_ROOT)
        except ValueError:
            rel = p
        print(f"  🔄 {rel} ➔ Reseteado a estado inicial limpio")

    print(f"\n🛡️  Archivos PROTEGIDOS (NO se tocan) ({len(protected)} ficheros):")
    for p in protected:
        try:
            rel = p.relative_to(PROJECT_ROOT)
        except ValueError:
            rel = p
        print(f"  🔒 {rel}")

    total_bytes = sum(p.stat().st_size for p in to_delete if p.exists())
    print("-" * 68)
    print(f"Resumen: {len(to_delete)} a borrar, {len(to_reset)} a resetear. Espacio a liberar: ~{format_bytes(total_bytes)}")
    print("=" * 68)

    if args.dry_run:
        print("\n[OK] Simulación finalizada. No se ha modificado ningún archivo.")
        sys.exit(0)

    if not args.yes:
        print("\n⚠️  ATENCIÓN: Esta acción eliminará permanentemente los datos anteriores indicados.")
        try:
            confirm = input("¿Confirmas la limpieza y reseteo del sistema? [s/N]: ").strip().lower()
        except KeyboardInterrupt:
            print("\nOperación cancelada por el usuario.")
            sys.exit(1)

        if confirm not in ('s', 'si', 'sí', 'y', 'yes'):
            print("\n[INFO] Operación cancelada. No se ha modificado ningún archivo.")
            sys.exit(0)

    print("\n⏳ Ejecutando limpieza...")
    result = execute_clean(storage_dir, dry_run=False, keep_cache=args.keep_cache)

    print(f"\n✅ LIMPIEZA COMPLETADA CON ÉXITO:")
    print(f"   - Ficheros eliminados:      {result['deleted_count']}")
    print(f"   - Ficheros reinicializados: {result['reset_count']}")
    print(f"   - Ficheros protegidos:      {result['protected_count']}")
    print(f"   - Espacio total liberado:   {format_bytes(result['bytes_freed'])}")
    print("\n🚀 El sistema ha quedado 100% limpio y listo para recibir nuevos ficheros CSV.")
    print("   Puedes subir un nuevo archivo desde la interfaz o colocarlo en 'data/input/'.\n")


if __name__ == '__main__':
    main()
