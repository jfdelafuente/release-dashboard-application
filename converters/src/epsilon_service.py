#!/usr/bin/env python3
"""Servicio centralizado de Epsilon Resumen IA.

Desacopla la lógica de System Prompt, cliente multi-proveedor LLM,
validación estricta Pydantic y consulta de incidencias en volcados locales.
Utilizado tanto por el CLI (scripts/test_epsilon_prompt.py) como por el
servidor HTTP (serve_app.py) y las suites de pruebas unitarias.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

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
   - Homogeneización de zona horaria (`Europe/Madrid`): Los campos ISO-8601 con sufijo `+00:00` o `Z` (ej. `fechaCreacion`, `fechaInicial` o `worklog.fecha` como `2026-11-17T08:30:46.000+00:00`) vienen en UTC, mientras que las horas en texto libre de `detalle`/OTRS/notas están en hora local de España (`CET` = UTC+1 en invierno, `CEST` = UTC+2 en verano). Convierte SIEMPRE todas las marcas UTC (`+00:00` o `Z`) a hora local de España (`Europe/Madrid`) antes de escribirlas y compararlas; nunca mezcles horas UTC con horas locales CET/CEST.
   - Formato de marca temporal adaptativa según dato real (sin inventar ceros ni precisión ficticia):
     * Si el apunte incluye segundos: comienza obligatoriamente con `[DD/MM/YYYY HH:mm:ss]: ` seguido de la descripción.
     * Si el apunte solo incluye horas y minutos: comienza con `[DD/MM/YYYY HH:mm]: `.
     * Si el apunte solo incluye fecha: comienza con `[DD/MM/YYYY]: `.
     * Prohibido inventar segundos `:00` o medianoches artificiales `00:00:00` cuando no figuren en los datos.
   - Prohibido usar rangos en la fecha/hora (no usar intervalos como [DD-DD/MM/YYYY] ni [HH:mm a HH:mm]); si los datos abarcan un intervalo, usa siempre la marca temporal de inicio.
   - Si no hay fecha deducible en los datos, usa [S/F].
   - Orden cronológico ascendente OBLIGATORIO: Una vez seleccionados los 5-6 hitos y convertidas las horas UTC a `Europe/Madrid`, ORDENA el array `hitosTecnicos` estrictamente de más antiguo a más reciente según el timestamp escrito entre corchetes (`hito[0] <= hito[1] <= ... <= hito[n]`). Verifica antes de emitir el JSON que ninguna marca sea anterior a la del elemento precedente.

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


def find_duplicate_hitos(hitos: List[str]) -> List[str]:
    """Devuelve los textos (normalizados) de hitos repetidos textualmente dentro del array."""
    seen: set = set()
    duplicated: List[str] = []
    for hito in hitos:
        normalized = str(hito).strip()
        if normalized in seen and normalized not in duplicated:
            duplicated.append(normalized)
        seen.add(normalized)
    return duplicated


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
        duplicated = find_duplicate_hitos(v)
        if duplicated:
            raise ValueError(
                f"'hitosTecnicos' contiene hitos duplicados (texto idéntico): {duplicated}"
            )
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

    @field_validator("siguienteAccion", mode="before")
    @classmethod
    def sanitize_siguiente_accion(cls, v: Any) -> Optional[str]:
        if v is None:
            return None
        v_str = str(v).strip()
        if v_str in ("[]", "{}", "None", "null", "N/A", "-", "none", ""):
            return None
        return v_str

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
        hitos_duplicated = find_duplicate_hitos(hitos)
        hitos_no_dup_ok = not hitos_duplicated
        hitos_len_ok = count_hitos <= 6
        hitos_format_ok = True
        hitos_chrono_ok = True
        chrono_pair = ""
        prev_dt: Optional[datetime] = None

        for hito in hitos:
            h_str = str(hito).strip()
            if not TIMESTAMP_REGEX.match(h_str):
                hitos_format_ok = False
            cur_dt = parse_timestamp_dt(h_str)
            if cur_dt and prev_dt and cur_dt < prev_dt:
                hitos_chrono_ok = False
                if not chrono_pair:
                    chrono_pair = f"{cur_dt.strftime('%d/%m %H:%M:%S')} < {prev_dt.strftime('%d/%m %H:%M:%S')}"
            if cur_dt:
                prev_dt = cur_dt

        hitos_total_ok = hitos_no_dup_ok and hitos_len_ok and hitos_format_ok and hitos_chrono_ok
        detalle_hitos = []
        if not hitos_no_dup_ok:
            preview = hitos_duplicated[0][:60] + ("..." if len(hitos_duplicated[0]) > 60 else "")
            detalle_hitos.append(f"Hitos duplicados ({len(hitos_duplicated)}): \"{preview}\"")
        if not hitos_len_ok:
            detalle_hitos.append(f"Excede 6 hitos ({count_hitos})")
        if not hitos_format_ok:
            detalle_hitos.append("Formato timestamp adaptativo inválido en algún hito")
        if not hitos_chrono_ok:
            suffix = f": {chrono_pair}" if chrono_pair else ""
            detalle_hitos.append(f"Hitos no ordenados cronológicamente{suffix}")

        checks.append(
            EpsilonResumenValidationCheck(
                campo="hitosTecnicos",
                criterio="<= 6 hitos únicos, formato adaptativo y orden cronológico",
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
    if sig is not None and str(sig).strip() in ("[]", "{}", "None", "null", "N/A", "-", "none", ""):
        sig = None
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


_SYSTEM_PROMPT_TRUNCATION_MARKER = "## 5. Implementación en Código"


def build_epsilon_system_prompt() -> str:
    """Carga el System Prompt desde data/resumen_incidencia_epsilon.md (sin anexos de código/futuro) si existe."""
    spec_path = get_project_root() / "data" / "resumen_incidencia_epsilon.md"
    if spec_path.is_file():
        try:
            with open(spec_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    if _SYSTEM_PROMPT_TRUNCATION_MARKER not in content:
                        sys.stderr.write(
                            f"[Aviso] No se encontró el marcador '{_SYSTEM_PROMPT_TRUNCATION_MARKER}' en "
                            f"{spec_path}; se usará el documento completo como System Prompt (incluyendo "
                            "posibles anexos de código o secciones futuras).\n"
                        )
                        return content
                    prompt_only = content.split(_SYSTEM_PROMPT_TRUNCATION_MARKER)[0].strip()
                    return prompt_only or content
        except Exception:
            pass
    return EPSILON_SYSTEM_PROMPT


_MADRID_TZ = ZoneInfo("Europe/Madrid")

_ISO_UTC_REGEX = re.compile(
    r"^(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2}:\d{2}(?:\.\d+)?)(?:Z|\+00:?00)$"
)


def convert_utc_iso_to_madrid(value: Any) -> Any:
    """Convierte recursivamente cadenas ISO-8601 en UTC (+00:00/Z) a Europe/Madrid (+01:00/+02:00)."""
    if isinstance(value, dict):
        return {k: convert_utc_iso_to_madrid(v) for k, v in value.items()}
    if isinstance(value, list):
        return [convert_utc_iso_to_madrid(item) for item in value]
    if isinstance(value, str):
        m = _ISO_UTC_REGEX.match(value.strip())
        if m:
            try:
                utc_dt = datetime.fromisoformat(f"{m.group(1)}T{m.group(2)}").replace(
                    tzinfo=timezone.utc
                )
                local_dt = utc_dt.astimezone(_MADRID_TZ)
                return local_dt.isoformat()
            except ValueError:
                return value
    return value


def build_user_message(incident_data: Dict[str, Any]) -> str:
    """Encapsula los datos brutos de la incidencia homogeneizando marcas ISO UTC a Europe/Madrid."""
    normalized_data = convert_utc_iso_to_madrid(incident_data)
    return USER_PROMPT_TEMPLATE.format(
        remedy_json=json.dumps(normalized_data, ensure_ascii=False, indent=2)
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


def urlopen_with_ssl_fallback(req: "urllib.request.Request", timeout: int = 60) -> Any:
    """Invoca urlopen() reintentando sin verificación de certificado si falla la validación TLS.

    El reintento solo se activa ante CERTIFICATE_VERIFY_FAILED (típico de proxies corporativos
    con MITM de certificado propio) o si ANTHROPIC_VERIFY_SSL/PYTHONHTTPSVERIFY lo desactivan
    explícitamente. Avisa por stderr cuando degrada la verificación para que no pase inadvertido.
    """
    import ssl
    import urllib.error
    import urllib.request

    ssl_context = ssl.create_default_context()
    verify_ssl = os.environ.get("ANTHROPIC_VERIFY_SSL", "").lower() not in ("0", "false", "no")
    if not verify_ssl or os.environ.get("PYTHONHTTPSVERIFY") == "0":
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        sys.stderr.write(
            f"[Aviso] Verificación SSL deshabilitada explícitamente para '{req.full_url}'.\n"
        )

    try:
        return urllib.request.urlopen(req, timeout=timeout, context=ssl_context)
    except urllib.error.URLError as ssl_err:
        if "CERTIFICATE_VERIFY_FAILED" in str(ssl_err) or "certificate verify failed" in str(ssl_err):
            sys.stderr.write(
                f"[Aviso] Certificado TLS no verificable para '{req.full_url}'; "
                "reintentando sin verificación de certificado.\n"
            )
            insecure_context = ssl._create_unverified_context()
            return urllib.request.urlopen(req, timeout=timeout, context=insecure_context)
        raise


def _call_anthropic_native_http(
    token: str,
    model_name: str,
    user_prompt: str,
    system_prompt: str,
    base_url: Optional[str] = None,
) -> Tuple[Dict[str, Any], int, float]:
    """Fallback HTTP nativo (urllib) para Anthropic Claude y gateways corporativos (LiteLLM MasOrange)."""
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

    t0 = time.time()
    try:
        with urlopen_with_ssl_fallback(req, timeout=60) as resp:
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
        src = incident_data.get("remedy") if isinstance(incident_data.get("remedy"), dict) else incident_data
        titulo_mock = str(
            src.get("resumen")
            or src.get("Descripción")
            or src.get("titulo")
            or incident_data.get("resumen")
            or incident_data.get("titulo")
            or titulo_mock
        )[:100]
        raw_estado = (
            src.get("estadoDesc")
            or (src.get("estado") if not isinstance(src.get("estado"), int) else None)
            or incident_data.get("estadoDesc")
            or (incident_data.get("estado") if not isinstance(incident_data.get("estado"), int) else None)
            or src.get("Estatus")
            or src.get("estadoActual")
            or estado_mock
        )
        estado_mock = str(raw_estado)

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
def _invoke_llm_provider(
    resolved_provider: str,
    resolved_model: str,
    user_prompt: str,
    prompt_sys: str,
    mock_data_path: Optional[str] = None,
    incident_data: Optional[Dict[str, Any]] = None,
) -> Tuple[Dict[str, Any], int, float]:
    """Despacha la invocación al proveedor LLM configurado."""
    if resolved_provider == "mock":
        return call_mock(user_prompt, mock_data_path=mock_data_path, incident_data=incident_data)
    if resolved_provider == "anthropic":
        return call_anthropic(user_prompt, model_name=resolved_model, system_prompt=prompt_sys)
    if resolved_provider == "openai":
        return call_openai(user_prompt, model_name=resolved_model, system_prompt=prompt_sys)
    if resolved_provider == "gemini":
        return call_gemini(user_prompt, model_name=resolved_model, system_prompt=prompt_sys)
    raise ValueError(f"Proveedor no soportado: '{resolved_provider}'")


def _extract_validation_errors(exc: Exception) -> List[str]:
    """Formatea los errores de validación de Pydantic en mensajes legibles."""
    validation_errors: List[str] = []
    if hasattr(exc, "errors") and callable(exc.errors):
        for err in exc.errors():
            loc = " -> ".join(str(x) for x in err.get("loc", []))
            msg = err.get("msg", "")
            validation_errors.append(f"{loc}: {msg}" if loc else msg)
    else:
        validation_errors.append(str(exc))
    return validation_errors


def generate_epsilon_summary(
    incident_data: Dict[str, Any],
    provider: Optional[str] = None,
    model: Optional[str] = None,
    mock: bool = False,
    mock_data_path: Optional[str] = None,
    system_prompt: Optional[str] = None,
    max_retries: int = 1,
) -> Tuple[bool, Dict[str, Any], Dict[str, Any]]:
    """
    Genera, extrae y valida el resumen de una incidencia IT siguiendo el contrato Epsilon IA.
    Incluye autocorrección (1 reintento correctivo por defecto) si el LLM incumple el contrato Pydantic.

    Devuelve: (is_valid, data_or_errors, meta)
    - is_valid: True si supera la validación estricta de Pydantic.
    - data_or_errors: Diccionario con los campos del resumen validado, o lista de errores.
    - meta: Diccionario con estadísticas (proveedor, modelo, tokens, elapsed_seconds, retries, etc.).
    """
    load_project_env()

    if not isinstance(incident_data, dict) or not incident_data:
        return (
            False,
            {"error": "Datos de incidencia insuficientes o vacíos", "validation_errors": ["incident_data debe ser un dict no vacío"]},
            {"provider": "none", "elapsed_seconds": 0.0, "tokens": 0, "retries": 0},
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

    base_user_prompt = build_user_message(incident_data)
    prompt_sys = system_prompt or build_epsilon_system_prompt()

    effective_retries = 0 if resolved_provider == "mock" else max(0, int(max_retries))
    total_tokens = 0
    total_elapsed = 0.0
    current_user_prompt = base_user_prompt
    raw_dict: Dict[str, Any] = {}
    last_validation_errors: List[str] = []

    for attempt in range(effective_retries + 1):
        raw_dict, tokens, elapsed = _invoke_llm_provider(
            resolved_provider=resolved_provider,
            resolved_model=resolved_model,
            user_prompt=current_user_prompt,
            prompt_sys=prompt_sys,
            mock_data_path=mock_data_path,
            incident_data=incident_data,
        )
        total_tokens += tokens
        total_elapsed += elapsed

        meta = {
            "provider": resolved_provider,
            "model": resolved_model,
            "mock": resolved_provider == "mock",
            "tokens": total_tokens,
            "elapsed_seconds": round(total_elapsed, 3),
            "retries": attempt,
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }

        try:
            validated_model = EpsilonResumenModel(**raw_dict)
            validated_dict = validated_model.model_dump()
            validated_dict["meta"] = meta
            return True, validated_dict, meta
        except Exception as exc:
            last_validation_errors = _extract_validation_errors(exc)
            if attempt < effective_retries:
                current_user_prompt = (
                    f"{base_user_prompt}\n\n"
                    "IMPORTANTE - CORRECCIÓN DE VALIDACIÓN REQUERIDA:\n"
                    "Tu respuesta JSON previa incumplió las reglas estrictas del contrato Epsilon IA:\n"
                    + "\n".join(f"- {err}" for err in last_validation_errors)
                    + "\n\nRespuesta previa a corregir:\n"
                    + json.dumps(raw_dict, ensure_ascii=False, indent=2)
                    + "\n\nDevuelve ÚNICAMENTE el objeto JSON corregido respetando límites de palabras, "
                    "mención explícita de workaround/sin alternativa en `impacto`, prefijos válidos en `bloqueos` "
                    "y orden cronológico ascendente estricto en `hitosTecnicos`."
                )

    error_payload = {
        "error": "Error de validación de esquema Epsilon",
        "validation_errors": last_validation_errors,
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


# =====================================================================
# MOTOR INTERNO EPSILON IA + FINGERPRINT CACHE + PRE-GENERACIÓN (OPCIÓN 2)
# =====================================================================
CORPORATE_SOPTMC_EPSILON_URL = "https://soptmc.si.orange.es/MonTMC/api/epsilon/resumenIA"
VALID_PROVIDER_MODES = ("internal", "internal_with_soptmc_fallback", "soptmc")


def get_epsilon_provider_mode(explicit_mode: Optional[str] = None) -> str:
    """Devuelve el modo operativo del servicio Epsilon IA ('internal' por defecto)."""
    load_project_env()
    raw = (explicit_mode or os.environ.get("EPSILON_PROVIDER_MODE") or "internal").strip().lower()
    if raw in VALID_PROVIDER_MODES:
        return raw
    return "internal"


def has_live_llm_credentials() -> bool:
    """Indica si hay credenciales activas de algún proveedor LLM o modo mock explícito."""
    load_project_env()
    if os.environ.get("EPSILON_MOCK", "").lower() in ("1", "true", "yes"):
        return True
    return any(
        bool(os.environ.get(var, "").strip())
        for var in ("ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY")
    )


def get_prompt_hash(system_prompt: Optional[str] = None) -> str:
    """Calcula un hash corto determinista del System Prompt activo para invalidación automática."""
    prompt_text = system_prompt or build_epsilon_system_prompt()
    return hashlib.sha256(prompt_text.encode("utf-8")).hexdigest()[:12]


def extract_remedy_incident_node(payload: Any, fallback_id: str = "") -> Optional[Dict[str, Any]]:
    """Extrae y normaliza el nodo de incidencia Remedy desde respuestas de MonTMC o .remedy_cache."""
    if not isinstance(payload, dict) or not payload:
        return None

    node: Optional[Dict[str, Any]] = None
    if isinstance(payload.get("remedy"), dict) and payload["remedy"]:
        node = dict(payload["remedy"])
        if "worklogs" in payload and "worklog" not in node and isinstance(payload["worklogs"], list):
            node["worklog"] = payload["worklogs"]
    else:
        known_keys = (
            "idRemedy",
            "ID de incidencia",
            "resumen",
            "detalle",
            "Descripción",
            "worklog",
            "worklogs",
            "estadoDesc",
            "Estatus",
        )
        if any(k in payload for k in known_keys):
            node = dict(payload)

    if not node:
        return None

    if fallback_id and not (node.get("idRemedy") or node.get("ID de incidencia") or node.get("codigo")):
        node["idRemedy"] = fallback_id

    return node


def compute_remedy_fingerprint(remedy_node: Dict[str, Any]) -> str:
    """
    Calcula la huella digital (fingerprint) del estado técnico real del ticket en Remedy.
    Cambia únicamente cuando varía el estado, la fecha de última modificación, la solución
    o el número/último apunte de worklogs/PaPs.
    """
    worklogs = remedy_node.get("worklog")
    if not isinstance(worklogs, list):
        worklogs = remedy_node.get("worklogs") if isinstance(remedy_node.get("worklogs"), list) else []

    last_wl_sig = ""
    if worklogs:
        # Ordenar de forma estable o inspeccionar el más reciente por fecha/índice
        dates = [str(w.get("fecha") or w.get("date") or w.get("timestamp") or "") for w in worklogs if isinstance(w, dict)]
        max_date = max(dates) if dates else ""
        last_item = worklogs[-1] if isinstance(worklogs[-1], dict) else {}
        last_text = str(last_item.get("detalle") or last_item.get("texto") or "")[:120]
        last_wl_sig = f"{max_date}|{last_item.get('idWorklog', '')}|{last_text}"

    paps = remedy_node.get("paps") if isinstance(remedy_node.get("paps"), list) else []

    canonical = {
        "id": str(remedy_node.get("idRemedy") or remedy_node.get("ID de incidencia") or remedy_node.get("codigo") or ""),
        "estado": str(remedy_node.get("estadoDesc") or remedy_node.get("Estatus") or remedy_node.get("estado") or ""),
        "urgencia": str(remedy_node.get("urgenciaDesc") or remedy_node.get("Urgencia") or ""),
        "prioridad": str(remedy_node.get("prioridadDesc") or remedy_node.get("Prioridad") or ""),
        "grupo": str(remedy_node.get("grupoAsignado") or remedy_node.get("Grupo asignado") or ""),
        "last_mod": str(
            remedy_node.get("fechaUltimaModificacion")
            or remedy_node.get("Fecha de última modificación")
            or remedy_node.get("Fecha de última resolución")
            or ""
        ),
        "solucion": str(remedy_node.get("detalleSolucion") or remedy_node.get("Resolución") or ""),
        "worklog_count": len(worklogs),
        "last_worklog": last_wl_sig,
        "paps_count": len(paps),
    }
    raw_bytes = json.dumps(canonical, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw_bytes).hexdigest()[:16]


def _write_json_atomic(target_file: Path, payload: Dict[str, Any]) -> None:
    """Escribe un archivo JSON en disco creando directorios padre de forma segura."""
    target_file.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    tmp_file = target_file.with_name(f"{target_file.name}.tmp_{os.getpid()}_{int(time.time() * 1000)}")
    try:
        tmp_file.write_text(text, encoding="utf-8")
        tmp_file.replace(target_file)
    except Exception:
        if tmp_file.exists():
            try:
                tmp_file.unlink()
            except OSError:
                pass
        target_file.write_text(text, encoding="utf-8")


def _fetch_or_load_remedy_node(
    incident_code: str,
    root: Path,
    mock: bool = False,
    montmc_client: Any = None,
) -> Tuple[Optional[Dict[str, Any]], str]:
    """
    Obtiene el detalle crudo de Remedy para una incidencia:
    1. En vivo desde MonTMC API (/api/eps/remedyG/{id}) salvo si mock=True sin cliente explícito.
    2. Fallback a caché local de Remedy en data/.remedy_cache/{id}.json.
    """
    code = incident_code.strip().upper()
    remedy_cache_file = root / "data" / ".remedy_cache" / f"{code}.json"

    if not mock or montmc_client is not None:
        try:
            client = montmc_client
            if client is None:
                try:
                    from converters.src.montmc_client import MonTMCClient
                except ImportError:
                    from montmc_client import MonTMCClient  # type: ignore
                client = MonTMCClient(timeout=12)

            detail_resp = client.fetch_remedy_detail(code)
            remedy_node = extract_remedy_incident_node(detail_resp, fallback_id=code)
            if remedy_node:
                try:
                    remedy_snapshot = {
                        "success": True,
                        "idRemedy": code,
                        "estado": remedy_node.get("estadoDesc") or "",
                        "solucion": remedy_node.get("detalleSolucion") or "",
                        "detalle": remedy_node.get("detalle") or "",
                        "worklogs": remedy_node.get("worklog") or [],
                        "asignaciones": remedy_node.get("asignaciones") or [],
                        "remedy": remedy_node,
                        "fetched_at": datetime.now(timezone.utc).isoformat(),
                    }
                    _write_json_atomic(remedy_cache_file, remedy_snapshot)
                except Exception:
                    pass
                return remedy_node, "montmc_remedy_live"
        except Exception:
            pass

    if remedy_cache_file.is_file():
        try:
            cached_payload = json.loads(remedy_cache_file.read_text(encoding="utf-8"))
            remedy_node = extract_remedy_incident_node(cached_payload, fallback_id=code)
            if remedy_node:
                return remedy_node, "remedy_disk_cache"
        except Exception:
            pass

    return None, "none"


def _fetch_soptmc_summary(incident_code: str, timeout: int = 15) -> Optional[Dict[str, Any]]:
    """Consulta de contingencia al endpoint externo legado de SOPTMC."""
    import ssl
    import urllib.request

    code = incident_code.strip().upper()
    target_url = f"{CORPORATE_SOPTMC_EPSILON_URL}/{code}"
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(
        target_url,
        headers={"User-Agent": "ReleaseDashboard/2.0", "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp:
        if resp.status == 200:
            raw_bytes = resp.read()
            data = json.loads(raw_bytes.decode("utf-8"))
            if isinstance(data, dict) and data:
                return data
    return None


def resolve_or_generate_epsilon_summary(
    incident_code: str,
    force: bool = False,
    mock: bool = False,
    cache_dir: Optional[Path] = None,
    project_root: Optional[Path] = None,
    candidate_roots: Optional[List[Path]] = None,
    provider_mode: Optional[str] = None,
    montmc_client: Any = None,
    dump_finder: Any = None,
) -> Tuple[int, Dict[str, Any], str]:
    """
    Orquestador unificado del servicio propio Epsilon Resumen IA (Opción 1 + Opción 2):
    - En modo 'internal' (por defecto) o 'internal_with_soptmc_fallback':
      1. Obtiene el detalle crudo del ticket Remedy (MonTMC remedyG o .remedy_cache).
      2. Calcula el fingerprint de Remedy + hash del System Prompt (resumen_incidencia_epsilon.md).
         Si coincide con data/.epsilon_cache/{codigo}.json y force=False -> devuelve FINGERPRINT_HIT instantáneo.
      3. Si cambió o no existe caché -> sintetiza y valida el resumen con nuestro motor LLM interno -> INTERNAL_LLM_GENERATED.
      4. Contingencias progresivas: SOPTMC opcional (si internal_with_soptmc_fallback), caché previa en disco (DISK_HIT)
         y volcados locales massive/postmortem (LOCAL_DUMP_FALLBACK).
    - En modo 'soptmc': mantiene el comportamiento legado de proxy hacia SOPTMC primero.

    Devuelve: (http_status_code, payload_dict, cache_status_header)
    """
    code = str(incident_code or "").strip().upper()
    if not code:
        return 400, {"success": False, "error": "Código de incidencia vacío"}, "INVALID"

    root = Path(project_root) if project_root else get_project_root()
    roots_to_search = list(candidate_roots) if candidate_roots else [root]
    resolved_cache_dir = Path(cache_dir) if cache_dir else (root / "data" / ".epsilon_cache")
    cache_file = resolved_cache_dir / f"{code}.json"

    mode = get_epsilon_provider_mode(provider_mode)
    is_mock = mock or (os.environ.get("EPSILON_MOCK", "").lower() in ("1", "true", "yes"))
    can_generate_llm = is_mock or has_live_llm_credentials()
    current_prompt_hash = get_prompt_hash()

    # MODO LEGADO SOPTMC (contingencia explícita por variable de entorno)
    if mode == "soptmc" and not is_mock:
        try:
            soptmc_data = _fetch_soptmc_summary(code)
            if soptmc_data:
                try:
                    _write_json_atomic(cache_file, soptmc_data)
                except Exception:
                    pass
                return 200, soptmc_data, "LIVE_SOPTMC_HIT"
        except Exception:
            pass

    # MODO PROPIO INTERNO (por defecto)
    if mode in ("internal", "internal_with_soptmc_fallback"):
        remedy_node, remedy_source = _fetch_or_load_remedy_node(
            incident_code=code,
            root=root,
            mock=mock,
            montmc_client=montmc_client,
        )

        if remedy_node is not None:
            remedy_fp = compute_remedy_fingerprint(remedy_node)

            # Smart Fingerprint Cache: 0 coste LLM si el ticket y el prompt no han cambiado
            if not force and cache_file.is_file():
                try:
                    cached_data = json.loads(cache_file.read_text(encoding="utf-8"))
                    cached_meta = cached_data.get("meta") if isinstance(cached_data, dict) else None
                    if (
                        isinstance(cached_data, dict)
                        and isinstance(cached_meta, dict)
                        and cached_meta.get("remedy_fingerprint") == remedy_fp
                        and cached_meta.get("prompt_hash") == current_prompt_hash
                        and (cached_data.get("problema") or cached_data.get("impacto"))
                    ):
                        return 200, cached_data, "FINGERPRINT_HIT"
                except Exception:
                    pass

            # Generación con nuestro motor interno y prompt resumen_incidencia_epsilon.md
            if can_generate_llm:
                try:
                    is_valid, summary_or_err, llm_meta = generate_epsilon_summary(
                        incident_data=remedy_node,
                        mock=is_mock,
                    )
                    if is_valid:
                        worklogs_list = remedy_node.get("worklog") or remedy_node.get("worklogs") or []
                        summary_or_err["meta"] = {
                            "source": "internal_epsilon_engine",
                            "remedy_source": remedy_source,
                            "remedy_fingerprint": remedy_fp,
                            "prompt_hash": current_prompt_hash,
                            "remedy_last_modified": (
                                remedy_node.get("fechaUltimaModificacion")
                                or remedy_node.get("Fecha de última modificación")
                            ),
                            "worklog_count": len(worklogs_list) if isinstance(worklogs_list, list) else 0,
                            "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                            "is_stale_warning": remedy_source == "remedy_disk_cache",
                            "stale_reason": (
                                "El resumen se ha generado desde la caché local de Remedy por indisponibilidad temporal de MonTMC."
                                if remedy_source == "remedy_disk_cache"
                                else None
                            ),
                            "llm_meta": llm_meta,
                        }
                        try:
                            _write_json_atomic(cache_file, summary_or_err)
                        except Exception:
                            pass
                        return 200, summary_or_err, "INTERNAL_LLM_GENERATED"
                except Exception as gen_exc:
                    sys.stderr.write(f"[Aviso] Error en motor interno Epsilon para {code}: {gen_exc}\n")

        # Contingencia opcional hacia SOPTMC si está habilitado internal_with_soptmc_fallback
        if mode == "internal_with_soptmc_fallback" and not is_mock:
            try:
                soptmc_data = _fetch_soptmc_summary(code)
                if soptmc_data:
                    try:
                        _write_json_atomic(cache_file, soptmc_data)
                    except Exception:
                        pass
                    return 200, soptmc_data, "SOPTMC_FALLBACK_HIT"
            except Exception:
                pass

    # Resiliencia offline: Snapshot previo en disco si no se fuerza regeneración
    if not force and cache_file.is_file():
        try:
            disk_data = json.loads(cache_file.read_text(encoding="utf-8"))
            if isinstance(disk_data, dict) and disk_data:
                return 200, disk_data, "DISK_HIT"
        except Exception:
            pass

    # Fallback sobre volcados locales massive/postmortem
    finder_fn = dump_finder or find_incident_in_local_dumps
    found = None
    for candidate_root in roots_to_search:
        found = finder_fn(code, candidate_root)
        if found:
            break

    if found and can_generate_llm:
        incident_item, source_filename, file_mtime = found
        try:
            is_valid, summary_data, llm_meta = generate_epsilon_summary(
                incident_data=incident_item,
                mock=is_mock,
            )
            if is_valid:
                now = time.time()
                is_stale = (now - file_mtime) > 7200  # Más de 2 horas
                hours_ago = round((now - file_mtime) / 3600.0, 1)
                summary_data["meta"] = {
                    "source": "local_dump_fallback",
                    "dump_file": source_filename,
                    "dump_timestamp": datetime.fromtimestamp(file_mtime).isoformat(),
                    "is_stale_warning": is_stale,
                    "stale_reason": (
                        f"El resumen se ha generado a partir de un volcado local con {hours_ago} horas de antigüedad; "
                        "el estado en Remedy en vivo podría diferir."
                        if is_stale
                        else None
                    ),
                    "prompt_hash": current_prompt_hash,
                    "llm_meta": llm_meta,
                }
                try:
                    _write_json_atomic(cache_file, summary_data)
                except Exception:
                    pass
                return 200, summary_data, "LOCAL_DUMP_FALLBACK"
        except Exception as dump_exc:
            return (
                502,
                {"success": False, "error": f"Error generando resumen desde volcado local para '{code}': {dump_exc}"},
                "ERROR",
            )

    err_msg = (
        f"Incidencia '{code}' no disponible en el motor interno Epsilon, "
        "no disponible en SOPTMC corporativo ni en los volcados locales"
    )
    return 502, {"success": False, "error": err_msg}, "MISS"


def pregenerate_epsilon_summaries(
    incident_codes: List[str],
    project_root: Optional[Path] = None,
    force: bool = False,
    mock: bool = False,
    max_workers: int = 3,
    montmc_client: Any = None,
) -> Dict[str, Any]:
    """
    Pre-genera concurrentemente (Opción 2) los resúmenes IA de incidencias activas nuevas o actualizadas,
    aprovechando el Smart Fingerprint Cache para no invocar el LLM en tickets sin cambios reales.
    """
    t0 = time.time()
    root = Path(project_root) if project_root else get_project_root()

    dedup_codes: List[str] = []
    seen = set()
    for raw_code in incident_codes or []:
        c = str(raw_code or "").strip().upper()
        if c and c not in seen:
            seen.add(c)
            dedup_codes.append(c)

    summary: Dict[str, Any] = {
        "total": len(dedup_codes),
        "generated": [],
        "fingerprint_hits": [],
        "failed": [],
        "elapsed_sec": 0.0,
    }
    if not dedup_codes:
        return summary

    workers = max(1, min(int(max_workers), len(dedup_codes)))

    def _worker(code: str) -> Tuple[str, int, str, str]:
        try:
            status, payload, cache_status = resolve_or_generate_epsilon_summary(
                incident_code=code,
                force=force,
                mock=mock,
                project_root=root,
                montmc_client=montmc_client,
            )
            err = str(payload.get("error") or "") if status != 200 else ""
            return code, status, cache_status, err
        except Exception as exc:
            return code, 502, "EXCEPTION", str(exc)

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(_worker, code): code for code in dedup_codes}
        for fut in as_completed(futures):
            code, status, cache_status, err = fut.result()
            if status == 200:
                if cache_status in ("FINGERPRINT_HIT", "DISK_HIT"):
                    summary["fingerprint_hits"].append(code)
                else:
                    summary["generated"].append(code)
            else:
                summary["failed"].append({"id": code, "status": status, "error": err})

    summary["elapsed_sec"] = round(time.time() - t0, 2)
    return summary
