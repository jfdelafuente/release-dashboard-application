#!/usr/bin/env python3
"""
build_agents_catalog.py
Extractor y generador del catálogo de agentes y skills IA para Release Dashboard Application.

Lee la biblioteca local en C:\\Users\\jose.delafuente\\Claude\\Projects\\biblioteca-agentes
(o la ruta configurada en --library-path o AGENTS_LIBRARY_PATH), parsea el frontmatter
YAML y cuerpo Markdown de agentes y skills, calcula la correlación bidireccional y KPIs,
y genera data/output/agents_catalog.json siguiendo el patrón Envelope (_metadata + data).
"""

import argparse
import datetime
import io
import json
import os
from pathlib import Path
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

import yaml

# Ruta canónica predeterminada
DEFAULT_LIBRARY_PATH = Path(r"C:\Users\jose.delafuente\Claude\Projects\biblioteca-agentes")

# Mapeo de identificadores de dominio a etiquetas descriptivas
DOMAIN_LABELS = {
    "brand-content": "Contenido y Marca",
    "it-incidents": "Incidencias IT",
}


def parse_markdown_frontmatter(file_path: Path) -> Tuple[Dict[str, Any], str]:
    """
    Parsea un fichero Markdown con frontmatter YAML delimitado por '---'.
    
    Retorna:
        Tuple[Dict[str, Any], str]: (metadatos_del_frontmatter, cuerpo_markdown)
    """
    try:
        content = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        content = file_path.read_text(encoding="latin-1")

    # Separar por delimitador inicial de frontmatter
    # El frontmatter debe comenzar al principio del archivo con '---'
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            raw_frontmatter = parts[1]
            markdown_body = parts[2].strip()
            try:
                data = yaml.safe_load(raw_frontmatter)
                if isinstance(data, dict):
                    return data, markdown_body
            except yaml.YAMLError as exc:
                print(f"[WARN] Error parseando YAML en {file_path}: {exc}", file=sys.stderr)
                return {}, content

    return {}, content.strip()


def sanitize_description(desc: Optional[str]) -> str:
    """Normaliza texto de descripción eliminando saltos de línea superfluos."""
    if not desc:
        return ""
    # Reemplazar múltiples espacios y normalizar saltos de línea
    clean = re.sub(r"\s+", " ", str(desc).strip())
    return clean


def extract_agents(library_path: Path) -> List[Dict[str, Any]]:
    """
    Escanea agents/<domain>/*.md y extrae la lista de agentes.
    """
    agents_dir = library_path / "agents"
    agents: List[Dict[str, Any]] = []

    if not agents_dir.is_dir():
        print(f"[WARN] Directorio de agentes no encontrado: {agents_dir}", file=sys.stderr)
        return agents

    for md_file in sorted(agents_dir.glob("*/*.md")):
        # Evitar ficheros auxiliares o READMEs
        if md_file.name.lower().startswith("readme"):
            continue

        frontmatter, body = parse_markdown_frontmatter(md_file)
        if not frontmatter:
            continue

        domain_key = frontmatter.get("domain") or md_file.parent.name
        domain_label = DOMAIN_LABELS.get(domain_key, domain_key.replace("-", " ").title())

        name = frontmatter.get("name") or md_file.stem
        alias = frontmatter.get("alias") or ""
        version = str(frontmatter.get("version") or "1.0.0")
        description = sanitize_description(frontmatter.get("description"))

        raw_skills = frontmatter.get("recommended_skills") or []
        if isinstance(raw_skills, str):
            recommended_skills = [s.strip() for s in raw_skills.split(",") if s.strip()]
        elif isinstance(raw_skills, list):
            recommended_skills = [str(s).strip() for s in raw_skills if str(s).strip()]
        else:
            recommended_skills = []

        raw_tools = frontmatter.get("tools") or []
        tools = [str(t).strip() for t in raw_tools] if isinstance(raw_tools, list) else []

        rel_path = md_file.relative_to(library_path).as_posix()

        agents.append({
            "id": name,
            "name": name,
            "alias": alias,
            "version": version,
            "domain": domain_key,
            "domain_label": domain_label,
            "description": description,
            "recommended_skills": recommended_skills,
            "tools": tools,
            "output_schema": frontmatter.get("output_schema", ""),
            "language": frontmatter.get("language", "es"),
            "owner": frontmatter.get("owner", "Orange"),
            "file_path": rel_path,
            "markdown_content": body,
        })

    return agents


def extract_skills(library_path: Path, agents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Escanea .agents/skills/*/SKILL.md y correlaciona agentes que las usan.
    """
    skills_dir = library_path / ".agents" / "skills"
    skills: List[Dict[str, Any]] = []

    if not skills_dir.is_dir():
        print(f"[WARN] Directorio de skills no encontrado: {skills_dir}", file=sys.stderr)
        return skills

    # Crear mapa skill -> lista de agentes que la usan
    skill_usage_map: Dict[str, List[str]] = {}
    for agent in agents:
        agent_id = agent["id"]
        for skill_id in agent.get("recommended_skills", []):
            skill_usage_map.setdefault(skill_id, []).append(agent_id)

    for skill_file in sorted(skills_dir.glob("*/SKILL.md")):
        frontmatter, body = parse_markdown_frontmatter(skill_file)
        if not frontmatter:
            continue

        skill_id = frontmatter.get("name") or skill_file.parent.name
        desc = sanitize_description(frontmatter.get("description"))
        rel_path = skill_file.relative_to(library_path).as_posix()

        used_by = sorted(list(set(skill_usage_map.get(skill_id, []))))

        skills.append({
            "id": skill_id,
            "name": skill_id,
            "description": desc,
            "file_path": rel_path,
            "used_by_agents": used_by,
            "markdown_content": body,
        })

    return skills


def extract_domains(agents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Agrupa los dominios representados en los agentes y calcula sus contadores.
    """
    domain_counts: Dict[str, int] = {}
    for agent in agents:
        dom = agent["domain"]
        domain_counts[dom] = domain_counts.get(dom, 0) + 1

    domains: List[Dict[str, Any]] = []
    for dom_id, count in domain_counts.items():
        label = DOMAIN_LABELS.get(dom_id, dom_id.replace("-", " ").title())
        domains.append({
            "id": dom_id,
            "label": label,
            "agent_count": count,
        })

    domains.sort(key=lambda d: d["id"])
    return domains


def build_catalog_dict(library_path: Path) -> Dict[str, Any]:
    """
    Construye el diccionario completo del catálogo respetando el contrato Envelope.
    """
    agents = extract_agents(library_path)
    skills = extract_skills(library_path, agents)
    domains = extract_domains(agents)

    kpis = {
        "total_agents": len(agents),
        "total_domains": len(domains),
        "total_skills": len(skills),
    }

    now_iso = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    envelope = {
        "_metadata": {
            "schema_version": "1.0.0",
            "type": "agents_catalog",
            "generated_at": now_iso,
            "source_library": str(library_path),
            "kpis": kpis,
        },
        "data": {
            "domains": domains,
            "agents": agents,
            "skills": skills,
        },
    }
    return envelope


def build_and_save_catalog(
    library_path: Optional[Path] = None,
    output_path: Optional[Path] = None,
) -> bool:
    """
    Ejecuta el ciclo de extracción y guarda el archivo en data/output/agents_catalog.json.
    """
    if library_path is None:
        env_path = os.environ.get("AGENTS_LIBRARY_PATH", "").strip()
        library_path = Path(env_path) if env_path else DEFAULT_LIBRARY_PATH

    project_root = Path(__file__).resolve().parent.parent.parent
    if output_path is None:
        output_path = project_root / "data" / "output" / "agents_catalog.json"

    print(f"[INFO] Leyendo biblioteca desde: {library_path}")
    if not library_path.exists():
        print(f"[ERROR] Ruta no encontrada: {library_path}", file=sys.stderr)
        return False

    catalog_data = build_catalog_dict(library_path)
    kpis = catalog_data["_metadata"]["kpis"]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(catalog_data, f, ensure_ascii=False, indent=2)

    print(f"[INFO] Procesados {kpis['total_agents']} agentes y {kpis['total_skills']} skills en {kpis['total_domains']} dominios.")
    print(f"[SUCCESS] Catálogo generado con éxito en: {output_path}")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generador del catálogo de agentes y skills IA para Release Dashboard Application."
    )
    parser.add_argument(
        "--library-path",
        type=Path,
        default=None,
        help=f"Ruta a biblioteca-agentes (por defecto: {DEFAULT_LIBRARY_PATH})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Ruta de salida del JSON (por defecto: data/output/agents_catalog.json)",
    )
    args = parser.parse_args()

    success = build_and_save_catalog(args.library_path, args.output)
    return 0 if success else 1


if __name__ == "__main__":
    if sys.platform == "win32":
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
        except Exception:
            pass
    sys.exit(main())
