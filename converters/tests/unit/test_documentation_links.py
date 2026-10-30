"""
Test de integridad y resolución de enlaces de la documentación del proyecto.

Valida:
1. Existencia de los 6 directorios temáticos estructurados de docs/.
2. Existencia de los archivos core del visor Docsify (index.html, _sidebar.md, README.md).
3. Resolución al 100% de todos los enlaces relativos dentro de docs/*.md.
4. Resolución válida de los enlaces a docs/ desde README.md, CONTRIBUTING.md y SECURITY.md.
"""

from pathlib import Path
import re
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DOCS_DIR = PROJECT_ROOT / "docs"

THEMATIC_DIRS = [
    "01-primeros-pasos",
    "02-gestion-emergencias",
    "03-arquitectura-y-datos",
    "04-conversores",
    "05-postmortem-y-reportes",
    "06-operaciones-y-gobernanza",
]

MARKDOWN_LINK_REGEX = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def test_thematic_directories_exist():
    """Verifica que existen los 6 directorios temáticos de documentación."""
    assert DOCS_DIR.exists() and DOCS_DIR.is_dir(), f"No existe el directorio {DOCS_DIR}"
    for thematic in THEMATIC_DIRS:
        subdir = DOCS_DIR / thematic
        assert subdir.exists() and subdir.is_dir(), f"Directorio temático faltante: {subdir}"
        readme = subdir / "README.md"
        assert readme.exists(), f"Falta README.md en el directorio temático: {subdir}"


def test_docsify_interactive_viewer_assets():
    """Verifica que el visor interactivo Docsify cuenta con sus archivos de arranque."""
    index_html = DOCS_DIR / "index.html"
    sidebar_md = DOCS_DIR / "_sidebar.md"
    readme_md = DOCS_DIR / "README.md"

    assert index_html.exists(), "Falta docs/index.html para el visor Docsify"
    assert sidebar_md.exists(), "Falta docs/_sidebar.md para la navegación lateral de Docsify"
    assert readme_md.exists(), "Falta docs/README.md como portada principal de documentación"

    sidebar_content = sidebar_md.read_text(encoding="utf-8")
    for thematic in THEMATIC_DIRS:
        assert thematic in sidebar_content, f"{thematic} no está indexado en docs/_sidebar.md"


def test_internal_docs_relative_links_resolve():
    """
    Escanea todos los ficheros .md dentro de docs/ y comprueba que
    ningún enlace relativo a archivos locales esté roto.
    """
    broken_links = []
    total_links_checked = 0

    for md_path in DOCS_DIR.rglob("*.md"):
        content = md_path.read_text(encoding="utf-8", errors="ignore")
        for match in MARKDOWN_LINK_REGEX.finditer(content):
            raw_url = match.group(2).strip()
            # Omitir anclas puras, URLs externas, correos y enlaces file:
            clean_url = raw_url.split("#")[0].split("?")[0].strip()
            if not clean_url or clean_url.startswith(("http://", "https://", "mailto:", "file:", "#")):
                continue

            target_path = (md_path.parent / clean_url).resolve()
            total_links_checked += 1
            if not target_path.exists():
                broken_links.append(f"{md_path.relative_to(PROJECT_ROOT)} -> {raw_url} (resuelto: {target_path})")

    assert not broken_links, (
        f"Se encontraron {len(broken_links)} enlaces rotos de {total_links_checked} comprobados:\n"
        + "\n".join(broken_links)
    )
    assert total_links_checked > 0, "No se encontraron enlaces para comprobar en docs/"


@pytest.mark.parametrize("root_doc", ["README.md", "CONTRIBUTING.md", "SECURITY.md"])
def test_root_documents_docs_links_resolve(root_doc):
    """
    Comprueba que los enlaces a docs/ desde los documentos de la raíz
    apunten a ficheros existentes tras la reorganización.
    """
    doc_path = PROJECT_ROOT / root_doc
    if not doc_path.exists():
        pytest.skip(f"{root_doc} no existe en la raíz del proyecto")

    content = doc_path.read_text(encoding="utf-8", errors="ignore")
    broken = []
    for match in MARKDOWN_LINK_REGEX.finditer(content):
        raw_url = match.group(2).strip()
        clean_url = raw_url.split("#")[0].split("?")[0].strip()
        if "docs/" not in clean_url or clean_url.startswith(("http://", "https://", "mailto:", "file:")):
            continue

        target_path = (doc_path.parent / clean_url).resolve()
        if not target_path.exists():
            broken.append(f"{root_doc} -> {raw_url} (resuelto: {target_path})")

    assert not broken, f"Enlaces rotos hacia docs/ encontrados en {root_doc}:\n" + "\n".join(broken)

