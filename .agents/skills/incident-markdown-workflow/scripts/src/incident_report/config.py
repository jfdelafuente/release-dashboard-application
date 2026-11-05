"""
Configuración centralizada y resolución de rutas portable para cualquier proyecto.
"""

import os
from dataclasses import dataclass
from typing import Optional


def _load_env_files() -> None:
    """
    Carga variables de entorno desde `.env` buscando primero en el directorio de trabajo actual
    del proyecto destino (`os.getcwd()`) y luego en la carpeta del script.
    Soporta fallback nativo si `python-dotenv` no está instalado.
    """
    script_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    candidates = [
        os.path.join(os.getcwd(), ".env"),
        os.path.join(script_root, ".env"),
    ]
    try:
        from dotenv import load_dotenv
        for env_path in candidates:
            if os.path.exists(env_path):
                load_dotenv(env_path, override=False)
        load_dotenv(override=False)
    except ImportError:
        for env_path in candidates:
            if os.path.exists(env_path):
                with open(env_path, "r", encoding="utf-8") as f:
                    for raw_line in f:
                        line = raw_line.strip()
                        if not line or line.startswith("#") or "=" not in line:
                            continue
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip('"').strip("'")
                        if k and k not in os.environ:
                            os.environ[k] = v


_load_env_files()

# Directorio raíz del paquete/script y directorio de trabajo del proyecto actual
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
WORK_DIR = os.getcwd()
ASSETS_DIR = os.path.join(PROJECT_ROOT, "assets")
TEMPLATES_DIR = os.path.join(ASSETS_DIR, "templates")
REPORTS_DIR = os.path.join(WORK_DIR, "reports")

DEFAULT_TEMPLATE_FILENAME = "20260609 Incidencia IVR ExMM.pptx"
DEFAULT_EXECUTIVE_ALIAS = "default_executive.pptx"

TEMPLATE_ALIASES = {
    "default": DEFAULT_EXECUTIVE_ALIAS,
    "default_executive": DEFAULT_EXECUTIVE_ALIAS,
    "executive": DEFAULT_EXECUTIVE_ALIAS,
    "ivr": DEFAULT_TEMPLATE_FILENAME,
}


def resolve_template_path(template_arg: Optional[str] = None) -> str:
    """
    Resuelve la ruta de una plantilla PowerPoint soportando:
    1. Claves cortas / alias (ej. 'default', 'default_executive').
    2. Rutas directas absolutas o relativas existentes.
    3. Búsqueda en `assets/templates/` del proyecto de trabajo o de la skill.
    4. Fallback al directorio raíz del proyecto por retrocompatibilidad.
    """
    search_dirs = [
        os.path.join(WORK_DIR, "assets", "templates"),
        TEMPLATES_DIR,
        WORK_DIR,
        PROJECT_ROOT,
    ]

    if not template_arg:
        for d in search_dirs:
            for candidate_name in (DEFAULT_TEMPLATE_FILENAME, DEFAULT_EXECUTIVE_ALIAS):
                candidate = os.path.join(d, candidate_name)
                if os.path.exists(candidate):
                    return candidate
        return os.path.join(TEMPLATES_DIR, DEFAULT_TEMPLATE_FILENAME)

    clean_key = template_arg.strip().lower()
    if clean_key in TEMPLATE_ALIASES:
        mapped_name = TEMPLATE_ALIASES[clean_key]
        for d in search_dirs:
            candidate = os.path.join(d, mapped_name)
            if os.path.exists(candidate):
                return candidate
            fallback = os.path.join(d, DEFAULT_TEMPLATE_FILENAME)
            if os.path.exists(fallback):
                return fallback

    if os.path.exists(template_arg):
        return template_arg

    basename = os.path.basename(template_arg)
    for d in search_dirs:
        in_dir = os.path.join(d, basename)
        if os.path.exists(in_dir):
            return in_dir

    return template_arg


@dataclass
class Settings:
    """
    Configuración tipada cargada desde variables de entorno (.env).
    """
    confluence_token: Optional[str] = None
    confluence_user: Optional[str] = None
    confluence_verify_ssl: bool = True
    confluence_timeout: int = 15
    gemini_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None

    @classmethod
    def from_env(cls, verify_ssl_override: Optional[bool] = None) -> "Settings":
        token = (
            os.getenv("CONFLUENCE_TOKEN")
            or os.getenv("CONFLUENCE_API_TOKEN")
            or os.getenv("ATLASSIAN_TOKEN")
        )
        user = os.getenv("CONFLUENCE_USER") or os.getenv("CONFLUENCE_EMAIL")

        if verify_ssl_override is not None:
            verify_ssl = verify_ssl_override
        else:
            env_verify = os.getenv("CONFLUENCE_VERIFY_SSL", "true").strip().lower()
            verify_ssl = env_verify not in ("false", "0", "no", "off")

        return cls(
            confluence_token=token,
            confluence_user=user,
            confluence_verify_ssl=verify_ssl,
            gemini_api_key=os.getenv("GEMINI_API_KEY"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        )

    @property
    def has_llm_key(self) -> bool:
        return bool(self.gemini_api_key or self.openai_api_key or self.anthropic_api_key)

