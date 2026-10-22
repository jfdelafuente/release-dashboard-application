#!/usr/bin/env python3
"""
Unit tests for converters/cli/build_agents_catalog.py.
Validates YAML frontmatter parsing, metadata extraction, bidirectional skill
correlation, KPI calculation and Envelope schema compliance.
"""

import json
from pathlib import Path
import sys

import pytest

# Ensure converters/cli/ is in sys.path
cli_path = Path(__file__).resolve().parent.parent.parent / "cli"
if str(cli_path) not in sys.path:
    sys.path.insert(0, str(cli_path))

from build_agents_catalog import (  # noqa: E402
    build_catalog_dict,
    extract_agents,
    extract_domains,
    extract_skills,
    parse_markdown_frontmatter,
    sanitize_description,
)


@pytest.fixture
def sample_library(tmp_path):
    """
    Creates an isolated mock library directory matching the structure
    of biblioteca-agentes with 2 domains, 3 agents, and 3 skills.
    """
    agents_dir = tmp_path / "agents"
    brand_dir = agents_dir / "brand-content"
    it_dir = agents_dir / "it-incidents"
    brand_dir.mkdir(parents=True)
    it_dir.mkdir(parents=True)

    skills_dir = tmp_path / ".agents" / "skills"
    skill1_dir = skills_dir / "estilo-orange"
    skill2_dir = skills_dir / "it-severity-matrix"
    skill3_dir = skills_dir / "postmortem-pir-workflow"
    skill1_dir.mkdir(parents=True)
    skill2_dir.mkdir(parents=True)
    skill3_dir.mkdir(parents=True)

    # 1. Agent in brand-content
    agent_brand = brand_dir / "orange-brand-generator.md"
    agent_brand.write_text(
        """---
name: orange-brand-generator
alias: estilo-orange
description: >-
  Genera presentaciones y activos visuales aplicando la identidad oficial de Orange.
domain: brand-content
version: 3.4.0-OE
recommended_skills:
  - estilo-orange
---

# Orange Brand Generator
Instrucciones detalladas de marca.
""",
        encoding="utf-8",
    )

    # 2. Agent 1 in it-incidents
    agent_analyzer = it_dir / "incident-analyzer.md"
    agent_analyzer.write_text(
        """---
name: incident-analyzer
alias: analizador-incidencias-it
description: Analiza incidencias IT y genera diagnósticos de causa raíz.
domain: it-incidents
version: 1.2.0
recommended_skills:
  - it-severity-matrix
  - postmortem-pir-workflow
tools:
  - read_file
---

# Propósito
Directrices de análisis de incidencias.
""",
        encoding="utf-8",
    )

    # 3. Agent 2 in it-incidents
    agent_reporter = it_dir / "incident-reporter.md"
    agent_reporter.write_text(
        """---
name: incident-reporter
alias: reporte-incidencias-it
description: Redacta mensajes ejecutivos de incidencias para Dirección.
domain: it-incidents
version: 1.0.0
recommended_skills:
  - it-severity-matrix
---

# Rol del Agente
Instrucciones del reporter.
""",
        encoding="utf-8",
    )

    # Skills
    (skill1_dir / "SKILL.md").write_text(
        """---
name: estilo-orange
description: Define y aplica el sistema oficial de identidad visual de Orange.
---
# Skill Estilo Orange
Contenido normativo de la skill.
""",
        encoding="utf-8",
    )

    (skill2_dir / "SKILL.md").write_text(
        """---
name: it-severity-matrix
description: Calcula y justifica el nivel de Severidad (P1 a P4).
---
# Matriz de Severidad
Criterios ITIL.
""",
        encoding="utf-8",
    )

    (skill3_dir / "SKILL.md").write_text(
        """---
name: postmortem-pir-workflow
description: Guía la elaboración de informes Post-Mortem Blameless.
---
# Flujo Postmortem
Directrices PIR.
""",
        encoding="utf-8",
    )

    return tmp_path


class TestParseMarkdownFrontmatter:
    def test_parses_valid_frontmatter(self, tmp_path):
        f = tmp_path / "test.md"
        f.write_text(
            """---
name: mi-agente
version: 2.0.0
alias: agente-test
---
# Contenido principal
Cuerpo de instrucciones.
""",
            encoding="utf-8",
        )
        fm, body = parse_markdown_frontmatter(f)
        assert fm["name"] == "mi-agente"
        assert fm["version"] == "2.0.0"
        assert fm["alias"] == "agente-test"
        assert "# Contenido principal" in body

    def test_handles_no_frontmatter(self, tmp_path):
        f = tmp_path / "plain.md"
        f.write_text("# Just a document\nNo frontmatter here.", encoding="utf-8")
        fm, body = parse_markdown_frontmatter(f)
        assert fm == {}
        assert "Just a document" in body

    def test_handles_multiline_and_spanish_accents(self, tmp_path):
        f = tmp_path / "accents.md"
        f.write_text(
            """---
name: análisis-gestión
description: >-
  Línea uno con tildes: información, clasificación, análisis.
  Línea dos con caracteres especiales: ñ, €, ¡atención!
---
# Cuerpo con acentos
""",
            encoding="utf-8",
        )
        fm, body = parse_markdown_frontmatter(f)
        assert fm["name"] == "análisis-gestión"
        assert "información, clasificación, análisis." in fm["description"]
        assert "ñ" in fm["description"]


class TestSanitizeDescription:
    def test_collapses_whitespace_and_newlines(self):
        raw = "  Primera línea  \n\n  Segunda línea\tcon tabs   "
        assert sanitize_description(raw) == "Primera línea Segunda línea con tabs"

    def test_handles_none_or_empty(self):
        assert sanitize_description(None) == ""
        assert sanitize_description("") == ""


class TestExtractCollections:
    def test_extract_agents(self, sample_library):
        agents = extract_agents(sample_library)
        assert len(agents) == 3

        agent_ids = [a["id"] for a in agents]
        assert "orange-brand-generator" in agent_ids
        assert "incident-analyzer" in agent_ids
        assert "incident-reporter" in agent_ids

        analyzer = next(a for a in agents if a["id"] == "incident-analyzer")
        assert analyzer["domain"] == "it-incidents"
        assert analyzer["domain_label"] == "Incidencias IT"
        assert analyzer["version"] == "1.2.0"
        assert "it-severity-matrix" in analyzer["recommended_skills"]
        assert "postmortem-pir-workflow" in analyzer["recommended_skills"]
        assert analyzer["tools"] == ["read_file"]

    def test_extract_skills_correlates_used_by(self, sample_library):
        agents = extract_agents(sample_library)
        skills = extract_skills(sample_library, agents)
        assert len(skills) == 3

        skill_map = {s["id"]: s for s in skills}
        assert "estilo-orange" in skill_map
        assert "it-severity-matrix" in skill_map
        assert "postmortem-pir-workflow" in skill_map

        # estilo-orange is used only by orange-brand-generator
        assert skill_map["estilo-orange"]["used_by_agents"] == ["orange-brand-generator"]

        # it-severity-matrix is used by both incident-analyzer and incident-reporter
        assert sorted(skill_map["it-severity-matrix"]["used_by_agents"]) == [
            "incident-analyzer",
            "incident-reporter",
        ]

        # postmortem-pir-workflow is used only by incident-analyzer
        assert skill_map["postmortem-pir-workflow"]["used_by_agents"] == ["incident-analyzer"]

    def test_extract_domains_counts(self, sample_library):
        agents = extract_agents(sample_library)
        domains = extract_domains(agents)
        assert len(domains) == 2

        domain_map = {d["id"]: d for d in domains}
        assert domain_map["brand-content"]["agent_count"] == 1
        assert domain_map["brand-content"]["label"] == "Contenido y Marca"
        assert domain_map["it-incidents"]["agent_count"] == 2
        assert domain_map["it-incidents"]["label"] == "Incidencias IT"


class TestBuildCatalogDict:
    def test_envelope_schema_and_kpis(self, sample_library):
        catalog = build_catalog_dict(sample_library)

        assert "_metadata" in catalog
        assert "data" in catalog

        meta = catalog["_metadata"]
        assert meta["schema_version"] == "1.0.0"
        assert meta["type"] == "agents_catalog"
        assert meta["source_library"] == str(sample_library)
        assert meta["kpis"]["total_agents"] == 3
        assert meta["kpis"]["total_domains"] == 2
        assert meta["kpis"]["total_skills"] == 3

        data = catalog["data"]
        assert len(data["agents"]) == 3
        assert len(data["skills"]) == 3
        assert len(data["domains"]) == 2


class TestServeAppAgentsCatalog:
    def test_handle_agents_catalog_success(self, monkeypatch, tmp_path):
        import io
        project_root = Path(__file__).resolve().parent.parent.parent.parent
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))
        import serve_app

        sample_data = {
            "_metadata": {"schema_version": "1.0.0", "kpis": {"total_agents": 5}},
            "data": {"agents": [{"id": "test-agent"}]}
        }

        mock_root = tmp_path / "proj"
        out_dir = mock_root / "data" / "output"
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "agents_catalog.json").write_text(json.dumps(sample_data), encoding="utf-8")

        monkeypatch.setattr(serve_app, "PROJECT_ROOT", mock_root)

        class DummyHandler:
            def __init__(self):
                self.path = "/api/agents-catalog"
                self.response_status = None
                self.response_headers = {}
                self.wfile = io.BytesIO()

            def send_response(self, status):
                self.response_status = status

            def send_header(self, key, val):
                self.response_headers[key] = val

            def end_headers(self):
                pass

            _send_json = serve_app.CustomHTTPHandler._send_json
            handle_agents_catalog = serve_app.CustomHTTPHandler.handle_agents_catalog

        handler = DummyHandler()
        handler.handle_agents_catalog()

        assert handler.response_status == 200
        assert handler.response_headers["Content-Type"] == "application/json; charset=utf-8"
        body = json.loads(handler.wfile.getvalue().decode("utf-8"))
        assert body["_metadata"]["kpis"]["total_agents"] == 5
        assert len(body["data"]["agents"]) == 1

    def test_handle_agents_catalog_missing_file_returns_404(self, monkeypatch, tmp_path):
        import io
        project_root = Path(__file__).resolve().parent.parent.parent.parent
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))
        import serve_app

        empty_root = tmp_path / "empty_proj"
        empty_root.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(serve_app, "PROJECT_ROOT", empty_root)

        class DummyHandler:
            def __init__(self):
                self.path = "/api/agents-catalog"
                self.response_status = None
                self.response_headers = {}
                self.wfile = io.BytesIO()

            def send_response(self, status):
                self.response_status = status

            def send_header(self, key, val):
                self.response_headers[key] = val

            def end_headers(self):
                pass

            _send_json = serve_app.CustomHTTPHandler._send_json
            handle_agents_catalog = serve_app.CustomHTTPHandler.handle_agents_catalog

        handler = DummyHandler()
        handler.handle_agents_catalog()

        assert handler.response_status == 404
        body = json.loads(handler.wfile.getvalue().decode("utf-8"))
        assert "no encontrado" in body["error"]

