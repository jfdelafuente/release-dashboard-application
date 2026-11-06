#!/usr/bin/env python3
"""Servicio centralizado de Epsilon Resumen IA.

Desacopla la lógica de System Prompt, cliente multi-proveedor LLM,
validación estricta Pydantic y consulta de incidencias en volcados locales.
Utilizado tanto por el CLI (scripts/test_epsilon_prompt.py) como por el
servidor HTTP (serve_app.py) y las suites de pruebas unitarias.
"""

from __future__ import annotations

from datetime import datetime
import json
import os
from pathlib import Path
import re
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field, field_validator, model_validator


def get_project_root() -> Path:
    """Calcula la ruta raíz del repositorio."""
    current = Path(__file__).resolve().parent
    for p in [current, current.parent, current.parent.parent]:
        if (p / "data").exists() and (p / "converters").exists():
            return p
    return Path.cwd()


def load_project_env() -> None:
    """Carga variables desde el archivo .env si existe en el proyecto."""
    candidates = [
        get_project_root() / ".env",
        Path.cwd() / ".env",
        Path.cwd() / "backend" / ".env",
        Path.cwd().parent / ".env",
        Path("/infocodes/project/cso-incident-masivas-report/current/backend/.env"),
        Path("/infocodes/project/release-dashboard-application/current/.env"),
    ]
    try:
        from dotenv import load_dotenv

        for env_path in candidates:
            if env_path.is_file():
                load_dotenv(dotenv_path=env_path, override=False)
        return
    except ImportError:
        pass

    # Fallback simple sin requerir python-dotenv
    for env_path in candidates:
        if env_path.is_file():
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip().strip("\r\n")
                        if not line or line.startswith("#") or "=" not in line:
                            continue
                        k, v = line.split("=", 1)
                        k = k.strip().strip("\r\n \t")
                        v = v.strip().strip("'\"").strip("\r\n \t")
                        if k and k not in os.environ:
                            os.environ[k] = v
            except Exception:
                pass


load_project_env()


# =====================================================================
# SYSTEM PROMPT OFICIAL DE EPSILON
# =====================================================================
EPSILON_SYSTEM_PROMPT = """Eres un analista experto en fiabilidad y gestión de incidencias de sistemas IT en Orange (Epsilon Resumen IA).
Tu tarea es analizar el volcado JSON de la incidencia Remedy adjunta y generar un resumen técnico y ejecutivo riguroso en formato JSON.

Sigue estrictamente estas reglas:

1. CONCISIÓN Y LÍMITES POR CAMPO:
   - `problema`: máximo 40 palabras.
   - `impacto`: máximo 30 palabras. Debe cuantificar el alcance (volumen de usuarios, sedes o servicios afectados) y especificar explícitamente si existe método alternativo (workaround) o si no existe alternativa disponible.
   - `solucion`: máximo 45 palabras.
   - `hitosTecnicos`: máximo 5 a 6 hitos (ver regla 5).
   - Sé directo, técnico y conciso, sin fórmulas de cortesía ni redundancias.

2. ORTOGONALIDAD Y NO REDUNDANCIA:
   - No repitas contenido entre campos. Si un detalle se explica en `problema`, no lo dupliques en `impacto` ni en `hitosTecnicos`.

3. PRIVACIDAD Y DATOS PERSONALES (PII):
   - No incluyas datos personales sensibles (nombres completos de clientes particulares, DNIs, teléfonos o correos personales).
   - Solo se permiten identificadores técnicos, nombres de grupos resolutores, peticionario corporativo o usuarios asignados que ya vengan explícitos en los datos.

4. SISTEMAS AFECTADOS:
   - `sistemas` debe ser un array con los nombres normalizados de las aplicaciones o componentes afectados (ej. ["Siebel 8", "TIBCO", "MDG", "Ficha de Cliente"]).

5. HITOS TÉCNICOS (`hitosTecnicos`):
   - Debe contener únicamente acciones clave, diagnósticos, validaciones, errores de logs, reinicios o escalados relevantes.
   - NO incluyas la solución final aquí si ya va en el campo `solucion`.
   - Cantidad y priorización: Máximo 5 a 6 hitos clave. Si hay más eventos, PRIORIZA SIEMPRE los hitos más recientes y críticos sobre los antiguos (manteniendo el hito de detección inicial si es relevante).
   - Formato de marca temporal adaptativa según dato real (sin inventar ceros ni precisión ficticia):
     * Si el apunte incluye segundos: comienza obligatoriamente con `[DD/MM/YYYY HH:mm:ss]: ` seguido de la descripción.
     * Si el apunte solo incluye horas y minutos: comienza con `[DD/MM/YYYY HH:mm]: `.
     * Si el apunte solo incluye fecha: comienza con `[DD/MM/YYYY]: `.
     * Prohibido inventar segundos `:00` o medianoches artificiales `00:00:00` cuando no figuren en los datos.
   - Prohibido usar rangos en la fecha/hora (no usar intervalos como [DD-DD/MM/YYYY] ni [HH:mm a HH:mm]); si los datos abarcan un intervalo, usa siempre la marca temporal de inicio.
   - Si no hay fecha deducible en los datos, usa [S/F].
   - Los hitos seleccionados deben presentarse ordenados cronológicamente de más antiguo a más reciente (orden ascendente).

6. BLOQUEOS (`bloqueos`):
   - Debe listar dependencias externas, bloqueos por terceros proveedores, ventanas de release o escalados sin respuesta.
   - Estandarización de prefijos: Si hay bloqueo, inicia cada elemento categorizándolo con un prefijo entre corchetes para facilitar su clasificación:
     * `[Ventana Release]: ` (espera de despliegue/parche planificado).
     * `[Dependencia Terceros]: ` (proveedor externo, red, hardware).
     * `[Validación Negocio]: ` (esperando pruebas o visto bueno de usuario/peticionario).
     * `[Escalado Grupo]: ` (a la espera de respuesta de otro grupo resolutor interno).
   - Si no existe un bloqueo activo o dependencia explícita, devuelve un array vacío: [].

7. REGLAS CONDICIONALES DE CAMPOS:
   - `solucion`:
     * Debe reflejar la causa raíz técnica y las acciones correctoras, paliativas o intentadas.
     * Casos de inclusión obligatoria:
       a) Solución confirmada: Si la incidencia está RESUELTO o CERRADO con validación satisfactoria.
       b) Solución parcial o planificada: Si hay causa raíz identificada, workaround (contingencia) activo o parche en espera de release (incluso en estados ASIGNADO o PENDIENTE).
       c) Solución inefectiva / Reapertura por peticionario: Si se implementó una acción correctora o intento de cierre pero el peticionario/usuario no estuvo conforme, el fallo persistió o el ticket fue reabierto, DEBE documentarse con total transparencia la acción intentada y el motivo de ineficacia o rechazo reportado por el peticionario.
     * Criterio de omisión: OMITE la clave `solucion` del JSON ÚNICAMENTE si la incidencia está en fase de diagnóstico inicial y todavía no existe ninguna causa identificada, workaround ni intento previo de resolución en los datos.
   - `siguienteAccion`:
     * Debe reflejar ÚNICAMENTE un próximo paso técnico, prueba programada, ventana de despliegue o escalado explícitamente mencionado o acordado en los worklogs por los resolutores.
     * Prohibido inventar o inferir recomendaciones de ingeniería ("se recomienda reiniciar", "conviene monitorizar", etc.) que no consten textualmente en los apuntes.
     * Si la incidencia ya está resuelta/cerrada y validada, o si no existe ningún compromiso o próxima acción explícita en los datos, OMITE la clave `siguienteAccion` por completo del JSON.

8. REGLA ANTI-ALUCINACIÓN:
   - Apóyate únicamente en los datos proporcionados en el JSON de entrada.
   - Nunca inventes horas, causas raíz, componentes, métricas ni siguientes acciones que no estén estrictamente respaldadas por la evidencia del ticket.

Devuelve ÚNICAMENTE un objeto JSON válido según este esquema:
{
  "success": true,
  "titulo": "string",
  "estadoActual": "string",
  "problema": "string (máximo 40 palabras)",
  "impacto": "string (máximo 30 palabras; debe indicar si hay método alternativo o no)",
  "solucion": "string (máximo 45 palabras; omitir solo si está en diagnóstico sin datos de causa/solución)",
  "sistemas": ["string"],
  "hitosTecnicos": ["string (máximo 5-6 hitos ordenados cronológicamente con marca adaptativa)"],
  "bloqueos": ["string con prefijo de categoría o [] si no hay"],
  "siguienteAccion": "string (opcional - omitir si no hay compromiso explícito en notas)"
}
"""

USER_PROMPT_TEMPLATE = """Resume la siguiente incidencia de Remedy siguiendo las directrices del sistema y el esquema JSON establecido:

<INCIDENCIA_REMEDY>
{remedy_json}
</INCIDENCIA_REMEDY>
"""

# Constantes de validación
ALLOWED_BLOCK_PREFIXES = (
    "[Ventana Release]",
    "[Dependencia Terceros]",
    "[Validación Negocio]",
    "[Validacion Negocio]",
    "[Escalado Grupo]",
)

WORKAROUND_REGEX = re.compile(
    r"(m[eé]todo\s+alternativo|workaround|sin\s+alternativa|contingencia|alternativa\s+disponible)",
    re.IGNORECASE,
)

TIMESTAMP_REGEX = re.compile(
    r"^\[(?:(\d{2}/\d{2}/\d{4})(?:\s+(\d{2}:\d{2}(?::\d{2})?))?|S/F)\]:\s+.+"
)


def count_words(text: Optional[str]) -> int:
    """Cuenta el número de palabras de un texto."""
    if not text:
        return 0
    return len(text.strip().split())


def parse_timestamp_dt(item: str) -> Optional[datetime]:
    """Extrae la fecha/hora de un hito técnico si existe."""
    match = re.match(r"^\[(\d{2}/\d{2}/\d{4})(?:\s+(\d{2}:\d{2}(?::\d{2})?))?\]:", item)
    if not match:
        return None
    d_str = match.group(1)
    t_str = match.group(2)
    try:
        if t_str:
            if len(t_str.split(":")) == 3:
                return datetime.strptime(f"{d_str} {t_str}", "%d/%m/%Y %H:%M:%S")
            return datetime.strptime(f"{d_str} {t_str}", "%d/%m/%Y %H:%M")
        return datetime.strptime(d_str, "%d/%m/%Y")
    except ValueError:
        return None


# =====================================================================
# MODELO PYDANTIC Y VALIDADORES ESTRICTOS
# =====================================================================
class EpsilonResumenValidationCheck:
    """Representa el resultado individual de una verificación de regla."""

    def __init__(self, campo: str, criterio: str, metrica: str, cumple: bool, detalle: str = ""):
        self.campo = campo
        self.criterio = criterio
        self.metrica = metrica
        self.cumple = cumple
        self.detalle = detalle

    def to_dict(self) -> Dict[str, Any]:
        return {
            "campo": self.campo,
            "criterio": self.criterio,
            "metrica": self.metrica,
            "cumple": self.cumple,
            "detalle": self.detalle,
        }


class EpsilonResumenModel(BaseModel):
    """Modelo Pydantic estricto para validar el contrato Epsilon Resumen IA."""

    success: bool
    titulo: str
    estadoActual: str
    problema: str
    impacto: str
    solucion: Optional[str] = None
    sistemas: List[str] = Field(default_factory=list)
    hitosTecnicos: List[str] = Field(default_factory=list)
    bloqueos: List[str] = Field(default_factory=list)
    siguienteAccion: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None

    @field_validator("titulo", "estadoActual")
    @classmethod
    def validate_non_empty(cls, v: str, info) -> str:
        if not v or not v.strip():
            raise ValueError(f"El campo '{info.field_name}' no puede estar vacío.")
        return v.strip()

    @field_validator("problema")
    @classmethod
    def validate_problema_words(cls, v: str) -> str:
        words = count_words(v)
        if words > 40:
            raise ValueError(f"'problema' excede el límite de 40 palabras (obtenidas: {words}).")
        return v.strip()

    @field_validator("impacto")
    @classmethod
    def validate_impacto(cls, v: str) -> str:
        words = count_words(v)
        if words > 30:
            raise ValueError(f"'impacto' excede el límite de 30 palabras (obtenidas: {words}).")
        if not WORKAROUND_REGEX.search(v):
            raise ValueError(
                "'impacto' debe indicar explícitamente si existe método alternativo/workaround o sin alternativa."
            )
        return v.strip()

    @field_validator("solucion")
    @classmethod
    def validate_solucion_words(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            words = count_words(v)
            if words > 45:
                raise ValueError(f"'solucion' excede el límite de 45 palabras (obtenidas: {words}).")
            return v.strip()
        return v

    @field_validator("sistemas")
    @classmethod
    def validate_sistemas(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("'sistemas' debe contener al menos un sistema afectado.")
        return [s.strip() for s in v if s.strip()]

    @field_validator("hitosTecnicos")
    @classmethod
    def validate_hitos(cls, v: List[str]) -> List[str]:
        if len(v) > 6:
            raise ValueError(f"'hitosTecnicos' permite un máximo de 5-6 hitos (recibidos: {len(v)}).")
        prev_dt: Optional[datetime] = None
        for idx, hito in enumerate(v):
            if not TIMESTAMP_REGEX.match(hito.strip()):
                raise ValueError(
                    f"Hito {idx+1} no cumple el formato adaptativo '[DD/MM/YYYY (HH:mm[:ss])]: desc' o '[S/F]: desc': '{hito}'"
                )
            cur_dt = parse_timestamp_dt(hito.strip())
            if cur_dt and prev_dt and cur_dt < prev_dt:
                raise ValueError(
                    f"Violación de orden cronológico en hitos: '{cur_dt}' es anterior a '{prev_dt}'."
                )
            if cur_dt:
                prev_dt = cur_dt
        return [h.strip() for h in v]

    @field_validator("bloqueos")
    @classmethod
    def validate_bloqueos(cls, v: List[str]) -> List[str]:
        for idx, b in enumerate(v):
            b_clean = b.strip()
            if not any(b_clean.startswith(prefix) for prefix in ALLOWED_BLOCK_PREFIXES):
                raise ValueError(
                    f"Bloqueo {idx+1} no inicia con un prefijo válido {ALLOWED_BLOCK_PREFIXES}: '{b_clean}'"
                )
        return [b.strip() for b in v]

    @model_validator(mode="after")
    def validate_solucion_on_resolved(self) -> EpsilonResumenModel:
        estado_upper = self.estadoActual.upper()
        if any(term in estado_upper for term in ("RESUELTO", "CERRADO")):
            if not self.solucion or not self.solucion.strip():
                raise ValueError(
                    f"'solucion' es obligatoria cuando el estado es '{self.estadoActual}'."
                )
        return self


def evaluate_contract(data: Dict[str, Any]) -> Tuple[List[EpsilonResumenValidationCheck], bool]:
    """Evalúa exhaustivamente cada regla de negocio y devuelve la lista de comprobaciones."""
    checks: List[EpsilonResumenValidationCheck] = []

    # 1. success
    is_success = bool(data.get("success", False))
    checks.append(
        EpsilonResumenValidationCheck(
            campo="success",
            criterio="Booleano true",
            metrica=str(is_success),
            cumple=is_success,
            detalle="" if is_success else "El campo success no es True",
        )
    )

    # 2. titulo
    titulo = str(data.get("titulo", "") or "").strip()
    titulo_ok = len(titulo) > 0
    checks.append(
        EpsilonResumenValidationCheck(
            campo="titulo",
            criterio="No vacío",
            metrica=f"{len(titulo)} caracteres",
            cumple=titulo_ok,
            detalle="" if titulo_ok else "Título ausente o vacío",
        )
    )

    # 3. estadoActual
    estado = str(data.get("estadoActual", "") or "").strip()
    estado_ok = len(estado) > 0
    checks.append(
        EpsilonResumenValidationCheck(
            campo="estadoActual",
            criterio="No vacío",
            metrica=estado or "<vacío>",
            cumple=estado_ok,
            detalle="" if estado_ok else "Estado actual ausente",
        )
    )

    # 4. problema
    problema = str(data.get("problema", "") or "").strip()
    words_prob = count_words(problema)
    prob_ok = 0 < words_prob <= 40
    checks.append(
        EpsilonResumenValidationCheck(
            campo="problema",
            criterio="1 a 40 palabras",
            metrica=f"{words_prob} palabras",
            cumple=prob_ok,
            detalle="" if prob_ok else ("Excede 40 palabras" if words_prob > 40 else "Vacío"),
        )
    )

    # 5. impacto
    impacto = str(data.get("impacto", "") or "").strip()
    words_imp = count_words(impacto)
    has_wa = bool(WORKAROUND_REGEX.search(impacto))
    imp_ok = (0 < words_imp <= 30) and has_wa
    metrica_imp = f"{words_imp} palabras | workaround: {'SÍ' if has_wa else 'NO'}"
    detalle_imp = []
    if words_imp == 0:
        detalle_imp.append("Vacío")
    elif words_imp > 30:
        detalle_imp.append("Excede 30 palabras")
    if not has_wa:
        detalle_imp.append("No indica explícitamente workaround / sin alternativa")
    checks.append(
        EpsilonResumenValidationCheck(
            campo="impacto",
            criterio="<= 30 palabras con indicación de workaround",
            metrica=metrica_imp,
            cumple=imp_ok,
            detalle=", ".join(detalle_imp),
        )
    )

    # 6. solucion
    solucion = data.get("solucion")
    sol_str = str(solucion).strip() if solucion is not None else ""
    words_sol = count_words(sol_str) if solucion is not None else 0
    estado_resuelto = any(term in estado.upper() for term in ("RESUELTO", "CERRADO"))

    if solucion is None:
        sol_ok = not estado_resuelto
        checks.append(
            EpsilonResumenValidationCheck(
                campo="solucion",
                criterio="Opcional en curso; obligatoria si resuelto/cerrado",
                metrica="<Omitida>",
                cumple=sol_ok,
                detalle="" if sol_ok else f"Obligatoria en estado '{estado}'",
            )
        )
    else:
        sol_ok = (words_sol <= 45) and (not estado_resuelto or words_sol > 0)
        detalle_sol = []
        if words_sol > 45:
            detalle_sol.append("Excede 45 palabras")
        if estado_resuelto and words_sol == 0:
            detalle_sol.append(f"Obligatoria en estado '{estado}'")
        checks.append(
            EpsilonResumenValidationCheck(
                campo="solucion",
                criterio="<= 45 palabras (obligatoria si resuelto/cerrado)",
                metrica=f"{words_sol} palabras",
                cumple=sol_ok,
                detalle=", ".join(detalle_sol),
            )
        )

    # 7. sistemas
    sistemas = data.get("sistemas", [])
    if isinstance(sistemas, list):
        sistemas_count = len(sistemas)
        sis_ok = sistemas_count >= 1
        checks.append(
            EpsilonResumenValidationCheck(
                campo="sistemas",
                criterio="Array con al menos 1 sistema",
                metrica=f"{sistemas_count} sistemas ({', '.join(map(str, sistemas))[:40]})",
                cumple=sis_ok,
                detalle="" if sis_ok else "Array vacío o sin sistemas",
            )
        )
    else:
        checks.append(
            EpsilonResumenValidationCheck(
                campo="sistemas",
                criterio="Array con al menos 1 sistema",
                metrica=type(sistemas).__name__,
                cumple=False,
                detalle="El campo sistemas debe ser una lista",
            )
        )

    # 8. hitosTecnicos
    hitos = data.get("hitosTecnicos", [])
    if isinstance(hitos, list):
        count_hitos = len(hitos)
        hitos_len_ok = count_hitos <= 6
        hitos_format_ok = True
        hitos_chrono_ok = True
        prev_dt: Optional[datetime] = None

        for hito in hitos:
            h_str = str(hito).strip()
            if not TIMESTAMP_REGEX.match(h_str):
                hitos_format_ok = False
            cur_dt = parse_timestamp_dt(h_str)
            if cur_dt and prev_dt and cur_dt < prev_dt:
                hitos_chrono_ok = False
            if cur_dt:
                prev_dt = cur_dt

        hitos_total_ok = hitos_len_ok and hitos_format_ok and hitos_chrono_ok
        detalle_hitos = []
        if not hitos_len_ok:
            detalle_hitos.append(f"Excede 6 hitos ({count_hitos})")
        if not hitos_format_ok:
            detalle_hitos.append("Formato timestamp adaptativo inválido en algún hito")
        if not hitos_chrono_ok:
            detalle_hitos.append("Hitos no ordenados cronológicamente")

        checks.append(
            EpsilonResumenValidationCheck(
                campo="hitosTecnicos",
                criterio="<= 6 hitos, formato adaptativo y orden cronológico",
                metrica=f"{count_hitos} hitos",
                cumple=hitos_total_ok,
                detalle=", ".join(detalle_hitos),
            )
        )
    else:
        checks.append(
            EpsilonResumenValidationCheck(
                campo="hitosTecnicos",
                criterio="Lista de hitos técnicos",
                metrica=type(hitos).__name__,
                cumple=False,
                detalle="hitosTecnicos debe ser una lista",
            )
        )

    # 9. bloqueos
    bloqueos = data.get("bloqueos", [])
    if isinstance(bloqueos, list):
        bloqueos_prefixes_ok = True
        for b in bloqueos:
            b_str = str(b).strip()
            if not any(b_str.startswith(p) for p in ALLOWED_BLOCK_PREFIXES):
                bloqueos_prefixes_ok = False
                break
        checks.append(
            EpsilonResumenValidationCheck(
                campo="bloqueos",
                criterio="[] o elementos con prefijos estándar",
                metrica=f"{len(bloqueos)} bloqueos",
                cumple=bloqueos_prefixes_ok,
                detalle="" if bloqueos_prefixes_ok else "Elemento sin prefijo estándar",
            )
        )
    else:
        checks.append(
            EpsilonResumenValidationCheck(
                campo="bloqueos",
                criterio="Lista de bloqueos",
                metrica=type(bloqueos).__name__,
                cumple=False,
                detalle="bloqueos debe ser una lista",
            )
        )

    # 10. siguienteAccion
    sig = data.get("siguienteAccion")
    if sig is not None:
        words_sig = count_words(str(sig))
        checks.append(
            EpsilonResumenValidationCheck(
                campo="siguienteAccion",
                criterio="Opcional (compromiso explícito acordado)",
                metrica=f"{words_sig} palabras",
                cumple=True,
                detalle="",
            )
        )
    else:
        checks.append(
            EpsilonResumenValidationCheck(
                campo="siguienteAccion",
                criterio="Opcional (omitida si no hay compromiso explícito)",
                metrica="<Omitida>",
                cumple=True,
                detalle="",
            )
        )

    all_passed = all(c.cumple for c in checks)
    return checks, all_passed


# =====================================================================
# LIMPIEZA DE RESPUESTAS LLM (MARKDOWN EXTRACTOR)
# =====================================================================
def extract_json_content(raw_text: str) -> str:
    """Extrae de forma limpia el bloque JSON de la respuesta del LLM."""
    text = raw_text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        return text[first_brace : last_brace + 1].strip()

    return text


def build_epsilon_system_prompt() -> str:
    """Carga el System Prompt desde data/resumen_incidencia_epsilon.md si existe."""
    spec_path = get_project_root() / "data" / "resumen_incidencia_epsilon.md"
    if spec_path.is_file():
        try:
            with open(spec_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    return content
        except Exception:
            pass
    return EPSILON_SYSTEM_PROMPT


def build_user_message(incident_data: Dict[str, Any]) -> str:
    """Encapsula los datos brutos de la incidencia en el formato de entrada esperado."""
    return USER_PROMPT_TEMPLATE.format(
        remedy_json=json.dumps(incident_data, ensure_ascii=False, indent=2)
    )


def normalize_anthropic_model_name(model_name: Optional[str]) -> str:
    """Normaliza el nombre de modelo eliminando prefijos que rompen LiteLLM router."""
    raw = (
        model_name
        or os.environ.get("ANTHROPIC_DEFAULT_SONNET_MODEL")
        or os.environ.get("ANTHROPIC_MODEL")
        or os.environ.get("ANTHROPIC_SONNET_MODEL")
        or "claude-3-5-sonnet-20241022"
    ).strip()
    if raw.startswith("anthropic/"):
        return raw[len("anthropic/"):]
    return raw


# =====================================================================
# INVOCACION A PROVEEDORES LLM
# =====================================================================
def _call_openai_native_http(
    api_key: str, base_url: str, model_name: str, user_prompt: str, system_prompt: str
) -> Tuple[Dict[str, Any], int, float]:
    """Fallback HTTP nativo (urllib) para OpenAI/Azure/proxies sin requerir paquete openai."""
    import urllib.error
    import urllib.request

    endpoint = base_url.rstrip("/")
    if not endpoint.endswith("/chat/completions"):
        endpoint = f"{endpoint}/chat/completions"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    payload = {
        "model": model_name or "gpt-4o",
        "temperature": 0.0,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }

    req = urllib.request.Request(endpoint, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            elapsed = time.time() - t0
            resp_body = json.loads(resp.read().decode("utf-8"))
            raw_content = resp_body["choices"][0]["message"]["content"]
            tokens = resp_body.get("usage", {}).get("total_tokens", 0)
            data = json.loads(extract_json_content(raw_content))
            return data, tokens, elapsed
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Error HTTP {e.code} desde OpenAI endpoint ({endpoint}): {err_msg}")
    except Exception as e:
        raise RuntimeError(f"Error de conexión con OpenAI endpoint ({endpoint}): {e}")


def call_openai(user_prompt: str, model_name: str, system_prompt: Optional[str] = None) -> Tuple[Dict[str, Any], int, float]:
    """Invoca la API de OpenAI (compatible con Azure o proxy local vía OPENAI_BASE_URL)."""
    api_key = os.environ.get("OPENAI_API_KEY")
    base_url = os.environ.get("OPENAI_BASE_URL") or os.environ.get("OPENAI_ENDPOINT") or "https://api.openai.com/v1"
    prompt_sys = system_prompt or build_epsilon_system_prompt()

    if not api_key:
        raise RuntimeError("Falta la variable de entorno 'OPENAI_API_KEY'.")

    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key, base_url=base_url) if base_url else OpenAI(api_key=api_key)
        t0 = time.time()
        response = client.chat.completions.create(
            model=model_name or "gpt-4o",
            temperature=0.0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": prompt_sys},
                {"role": "user", "content": user_prompt},
            ],
        )
        elapsed = time.time() - t0
        raw_content = response.choices[0].message.content or "{}"
        tokens = getattr(response.usage, "total_tokens", 0) if response.usage else 0
        data = json.loads(extract_json_content(raw_content))
        return data, tokens, elapsed
    except ImportError:
        return _call_openai_native_http(api_key, base_url, model_name, user_prompt, prompt_sys)


def call_gemini(user_prompt: str, model_name: str, system_prompt: Optional[str] = None) -> Tuple[Dict[str, Any], int, float]:
    """Invoca la API de Google Gemini."""
    api_key = os.environ.get("GEMINI_API_KEY")
    prompt_sys = system_prompt or build_epsilon_system_prompt()
    if not api_key:
        raise RuntimeError("Falta la variable de entorno 'GEMINI_API_KEY'.")

    t0 = time.time()
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=model_name or "gemini-2.5-pro",
            contents=f"{prompt_sys}\n\n{user_prompt}",
            config=types.GenerateContentConfig(
                temperature=0.0,
                response_mime_type="application/json",
            ),
        )
        elapsed = time.time() - t0
        raw_text = response.text or "{}"
        data = json.loads(extract_json_content(raw_text))
        tokens = getattr(response.usage_metadata, "total_token_count", 0) if hasattr(response, "usage_metadata") else 0
        return data, tokens, elapsed
    except ImportError:
        pass

    try:
        import google.generativeai as gai

        gai.configure(api_key=api_key)
        model = gai.GenerativeModel(
            model_name=model_name or "gemini-1.5-pro",
            system_instruction=prompt_sys,
            generation_config={"temperature": 0.0, "response_mime_type": "application/json"},
        )
        response = model.generate_content(user_prompt)
        elapsed = time.time() - t0
        raw_text = response.text or "{}"
        data = json.loads(extract_json_content(raw_text))
        tokens = getattr(response.usage_metadata, "total_token_count", 0) if hasattr(response, "usage_metadata") else 0
        return data, tokens, elapsed
    except ImportError:
        raise RuntimeError("Ningún SDK de Gemini instalado ('google-genai' o 'google-generativeai').")


def _call_anthropic_native_http(
    token: str,
    model_name: str,
    user_prompt: str,
    system_prompt: str,
    base_url: Optional[str] = None,
) -> Tuple[Dict[str, Any], int, float]:
    """Fallback HTTP nativo (urllib) para Anthropic Claude y gateways corporativos (LiteLLM MasOrange)."""
    import ssl
    import urllib.error
    import urllib.request

    raw_base = base_url or os.environ.get("ANTHROPIC_BASE_URL") or "https://api.anthropic.com"
    base = raw_base.strip("\r\n \t").rstrip("/")
    if base.endswith("/messages"):
        endpoint = base
    elif base.endswith("/v1"):
        endpoint = f"{base}/messages"
    else:
        endpoint = f"{base}/v1/messages"

    clean_token = token.strip("\r\n \t")
    headers = {
        "x-api-key": clean_token,
        "Authorization": f"Bearer {clean_token}",
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    clean_model = normalize_anthropic_model_name(model_name)

    payload = {
        "model": clean_model,
        "max_tokens": 2048,
        "temperature": 0.0,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_prompt}],
    }

    req = urllib.request.Request(endpoint, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")

    ssl_context = ssl.create_default_context()
    verify_ssl = os.environ.get("ANTHROPIC_VERIFY_SSL", "").lower() not in ("0", "false", "no")
    if not verify_ssl or os.environ.get("PYTHONHTTPSVERIFY") == "0":
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

    t0 = time.time()
    try:
        try:
            resp_cm = urllib.request.urlopen(req, timeout=60, context=ssl_context)
        except urllib.error.URLError as ssl_err:
            if "CERTIFICATE_VERIFY_FAILED" in str(ssl_err) or "certificate verify failed" in str(ssl_err):
                insecure_context = ssl._create_unverified_context()
                resp_cm = urllib.request.urlopen(req, timeout=60, context=insecure_context)
            else:
                raise ssl_err

        with resp_cm as resp:
            elapsed = time.time() - t0
            resp_bytes = resp.read()
            resp_body = json.loads(resp_bytes.decode("utf-8"))

            raw_text = ""
            if "content" in resp_body:
                content = resp_body.get("content")
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict):
                            raw_text += block.get("text", "")
                        elif isinstance(block, str):
                            raw_text += block
                elif isinstance(content, str):
                    raw_text = content
            elif "choices" in resp_body and len(resp_body["choices"]) > 0:
                raw_text = resp_body["choices"][0].get("message", {}).get("content", "")

            usage = resp_body.get("usage", {})
            tokens = usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
            if not tokens and "total_tokens" in usage:
                tokens = usage.get("total_tokens", 0)

            data = json.loads(extract_json_content(raw_text))
            return data, tokens, elapsed
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Error HTTP {e.code} desde Anthropic API ({endpoint}): {err_msg}")
    except Exception as e:
        raise RuntimeError(f"Error de conexión con Anthropic API ({endpoint}): {e}")


def call_anthropic(
    user_prompt: str,
    model_name: Optional[str] = None,
    base_url: Optional[str] = None,
    system_prompt: Optional[str] = None,
) -> Tuple[Dict[str, Any], int, float]:
    """Invoca la API de Anthropic Claude (compatible con API oficial y proxy LiteLLM MasOrange)."""
    token = os.environ.get("ANTHROPIC_AUTH_TOKEN") or os.environ.get("ANTHROPIC_API_KEY")
    if not token:
        raise RuntimeError("Falta la variable de entorno 'ANTHROPIC_AUTH_TOKEN' o 'ANTHROPIC_API_KEY'.")

    resolved_base_url = base_url or os.environ.get("ANTHROPIC_BASE_URL")
    resolved_model = normalize_anthropic_model_name(model_name)
    prompt_sys = system_prompt or build_epsilon_system_prompt()

    try:
        import anthropic

        client_kwargs: Dict[str, Any] = {}
        if resolved_base_url:
            client_kwargs["base_url"] = resolved_base_url
        if os.environ.get("ANTHROPIC_AUTH_TOKEN"):
            client_kwargs["auth_token"] = token
        else:
            client_kwargs["api_key"] = token

        client = anthropic.Anthropic(**client_kwargs)
        t0 = time.time()
        response = client.messages.create(
            model=resolved_model,
            max_tokens=2048,
            temperature=0.0,
            system=prompt_sys,
            messages=[{"role": "user", "content": user_prompt}],
        )
        elapsed = time.time() - t0
        raw_text = "".join([block.text for block in response.content if hasattr(block, "text")])
        data = json.loads(extract_json_content(raw_text))
        tokens = (response.usage.input_tokens + response.usage.output_tokens) if response.usage else 0
        return data, tokens, elapsed
    except ImportError:
        return _call_anthropic_native_http(
            token=token,
            model_name=resolved_model,
            user_prompt=user_prompt,
            system_prompt=prompt_sys,
            base_url=resolved_base_url,
        )


def call_mock(
    user_prompt: str,
    mock_data_path: Optional[str] = None,
    incident_data: Optional[Dict[str, Any]] = None,
) -> Tuple[Dict[str, Any], int, float]:
    """Genera una respuesta simulada determinista y conforme para pruebas offline."""
    time.sleep(0.02)
    if mock_data_path and os.path.isfile(mock_data_path):
        with open(mock_data_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data, 450, 0.02

    titulo_mock = "Ficha de Cliente - Error en sincronización de teléfono en recogidas de fijo"
    estado_mock = "Pendiente"
    if incident_data:
        titulo_mock = str(
            incident_data.get("resumen")
            or incident_data.get("Descripción")
            or incident_data.get("titulo")
            or titulo_mock
        )[:100]
        estado_mock = str(
            incident_data.get("estado")
            or incident_data.get("Estatus")
            or incident_data.get("estadoActual")
            or estado_mock
        )

    mock_response = {
        "success": True,
        "titulo": titulo_mock,
        "estadoActual": estado_mock,
        "problema": "El módulo de recogidas de equipamiento fijo no propaga el teléfono de contacto modificado hacia PS y Siebel 8 debido a un fallo en el microservicio MDG.",
        "impacto": "Medio. Afecta a la logística inversa de routers en bajas de fibra, con riesgo de envíos fallidos al transportista. Sin método alternativo disponible.",
        "solucion": "Bug identificado en microservicio de sincronización MDG. Parche de corrección por proveedor comprometido para despliegue en release del 12/11/2026.",
        "sistemas": ["Ficha de Cliente", "Siebel 8", "MDG", "PS"],
        "hitosTecnicos": [
            "[02/11/2026 09:15:00]: Detección de inconsistencia entre Ficha de Cliente y sistemas downstream al actualizar contacto.",
            "[03/11/2026 14:00:00]: N2 aísla el error en el microservicio MDG y traslada requerimiento al equipo de desarrollo.",
        ],
        "bloqueos": [
            "[Ventana Release]: Dependencia de entrega y despliegue de parche por proveedor planificado para release del 12/11/2026."
        ],
        "siguienteAccion": "Despliegue y validación del parche en ventana del 12/11/2026.",
    }
    return mock_response, 597, 0.02


def resolve_llm_provider(explicit_provider: Optional[str] = None) -> str:
    """Resuelve el proveedor de LLM a utilizar según variables de entorno."""
    load_project_env()
    if explicit_provider:
        return explicit_provider.lower().strip()
    if os.environ.get("ANTHROPIC_AUTH_TOKEN") or os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    if os.environ.get("OPENAI_API_KEY"):
        return "openai"
    if os.environ.get("GEMINI_API_KEY"):
        return "gemini"
    return "mock"


# =====================================================================
# FUNCIÓN PRINCIPAL DE SERVICIO
# =====================================================================
def generate_epsilon_summary(
    incident_data: Dict[str, Any],
    provider: Optional[str] = None,
    model: Optional[str] = None,
    mock: bool = False,
    mock_data_path: Optional[str] = None,
    system_prompt: Optional[str] = None,
) -> Tuple[bool, Dict[str, Any], Dict[str, Any]]:
    """
    Genera, extrae y valida el resumen de una incidencia IT siguiendo el contrato Epsilon IA.

    Devuelve: (is_valid, data_or_errors, meta)
    - is_valid: True si supera la validación estricta de Pydantic.
    - data_or_errors: Diccionario con los campos del resumen validado, o lista de errores.
    - meta: Diccionario con estadísticas (proveedor, modelo, tokens, elapsed_seconds, etc.).
    """
    load_project_env()

    if not isinstance(incident_data, dict) or not incident_data:
        return (
            False,
            {"error": "Datos de incidencia insuficientes o vacíos", "validation_errors": ["incident_data debe ser un dict no vacío"]},
            {"provider": "none", "elapsed_seconds": 0.0, "tokens": 0},
        )

    is_mock = mock or (os.environ.get("EPSILON_MOCK", "").lower() in ("1", "true", "yes"))
    resolved_provider = "mock" if is_mock else resolve_llm_provider(provider)

    if resolved_provider == "mock":
        resolved_model = "mock-epsilon"
    elif resolved_provider == "anthropic":
        resolved_model = normalize_anthropic_model_name(model)
    elif resolved_provider == "openai":
        resolved_model = model or os.environ.get("OPENAI_MODEL", "gpt-4o")
    elif resolved_provider == "gemini":
        resolved_model = model or os.environ.get("GEMINI_MODEL", "gemini-2.5-pro")
    else:
        resolved_provider = "mock"
        resolved_model = "mock-epsilon"

    user_prompt = build_user_message(incident_data)
    prompt_sys = system_prompt or build_epsilon_system_prompt()

    # Invocación al proveedor seleccionado
    if resolved_provider == "mock":
        raw_dict, tokens, elapsed = call_mock(user_prompt, mock_data_path=mock_data_path, incident_data=incident_data)
    elif resolved_provider == "anthropic":
        raw_dict, tokens, elapsed = call_anthropic(user_prompt, model_name=resolved_model, system_prompt=prompt_sys)
    elif resolved_provider == "openai":
        raw_dict, tokens, elapsed = call_openai(user_prompt, model_name=resolved_model, system_prompt=prompt_sys)
    elif resolved_provider == "gemini":
        raw_dict, tokens, elapsed = call_gemini(user_prompt, model_name=resolved_model, system_prompt=prompt_sys)
    else:
        raise ValueError(f"Proveedor no soportado: '{resolved_provider}'")

    meta = {
        "provider": resolved_provider,
        "model": resolved_model,
        "mock": resolved_provider == "mock",
        "tokens": tokens,
        "elapsed_seconds": round(elapsed, 3),
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }

    # Validación Pydantic estricta
    try:
        validated_model = EpsilonResumenModel(**raw_dict)
        validated_dict = validated_model.model_dump()
        validated_dict["meta"] = meta
        return True, validated_dict, meta
    except Exception as exc:
        validation_errors: List[str] = []
        if hasattr(exc, "errors") and callable(exc.errors):
            for err in exc.errors():
                loc = " -> ".join(str(x) for x in err.get("loc", []))
                msg = err.get("msg", "")
                validation_errors.append(f"{loc}: {msg}" if loc else msg)
        else:
            validation_errors.append(str(exc))

        error_payload = {
            "error": "Error de validación de esquema Epsilon",
            "validation_errors": validation_errors,
            "raw_output": raw_dict,
        }
        return False, error_payload, meta


# =====================================================================
# BÚSQUEDA DE INCIDENCIAS EN VOLCADOS LOCALES
# =====================================================================
def find_incident_in_local_dumps(
    incident_code: str,
    project_root: Optional[Path] = None,
) -> Optional[Tuple[Dict[str, Any], str, float]]:
    """
    Busca los datos de una incidencia en los volcados locales data/output/*-massive.json y *-postmortem.json.

    Devuelve: (incident_dict, source_filename, file_mtime) o None si no se encuentra.
    """
    root = project_root or get_project_root()
    output_dir = root / "data" / "output"
    if not output_dir.is_dir():
        return None

    code_clean = incident_code.strip().upper()

    # Patrones de búsqueda ordenados por frescura (más recientes primero)
    candidate_files = sorted(
        list(output_dir.glob("*-massive.json")) + list(output_dir.glob("*-postmortem.json")),
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )

    for filepath in candidate_files:
        try:
            mtime = filepath.stat().st_mtime
            with open(filepath, "r", encoding="utf-8") as f:
                content = json.load(f)

            incidents_list: List[Dict[str, Any]] = []
            if isinstance(content, dict):
                if isinstance(content.get("data"), list):
                    incidents_list = content["data"]
                elif isinstance(content.get("incidencias"), list):
                    incidents_list = content["incidencias"]
            elif isinstance(content, list):
                incidents_list = content

            for item in incidents_list:
                if not isinstance(item, dict):
                    continue
                # Revisar posibles campos identificadores
                item_code = (
                    item.get("ID de incidencia")
                    or item.get("id")
                    or item.get("codigo")
                    or item.get("id_incidencia")
                    or item.get("incident_id")
                    or ""
                )
                if str(item_code).strip().upper() == code_clean:
                    return item, filepath.name, mtime
        except Exception:
            continue

    return None
