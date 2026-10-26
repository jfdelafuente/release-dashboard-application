# Contract: Executive Notification Generation Contract

**Feature**: `012-high-priority-incident-notifications` | **Date**: 2026-10-26  
**Reference Agent**: [`agents/it-incidents/incident-reporter.md`](../../../agents/it-incidents/incident-reporter.md)  
**Reference Skill**: [`.agents/skills/it-severity-matrix/SKILL.md`](../../../.agents/skills/it-severity-matrix/SKILL.md)

Este contrato define las especificaciones técnicas, esquemas y reglas de generación de mensajes ejecutivos para Dirección aplicados a las incidencias masivas de alta prioridad (`P1` y `P2`).

---

## 1. Esquema de Salida (JSON Schema)

Cada incidencia evaluada genera un objeto `mensajes_ejecutivos` con tres fases operativas (`apertura`, `seguimiento`, `cierre`):

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "ExecutiveNotificationsMap",
  "type": "object",
  "required": ["apertura", "seguimiento", "cierre"],
  "properties": {
    "apertura": { "$ref": "#/definitions/ExecutiveMessage" },
    "seguimiento": { "$ref": "#/definitions/ExecutiveMessage" },
    "cierre": { "$ref": "#/definitions/ExecutiveMessage" }
  },
  "definitions": {
    "ExecutiveMessage": {
      "type": "object",
      "required": ["completo", "breve", "conteo_palabras_completo", "conteo_palabras_breve"],
      "properties": {
        "completo": {
          "type": "string",
          "description": "Un único párrafo formal para Dirección de hasta 90 palabras."
        },
        "breve": {
          "type": "string",
          "description": "Texto ultracondensado de hasta 30 palabras para asunto de email, SMS o alerta push."
        },
        "conteo_palabras_completo": {
          "type": "integer",
          "minimum": 1,
          "maximum": 90
        },
        "conteo_palabras_breve": {
          "type": "integer",
          "minimum": 1,
          "maximum": 30
        }
      }
    }
  }
}
```

---

## 2. Insumos Requeridos para la Generación

| Campo de Entrada | Origen | Obligatoriedad | Descripción |
| :--- | :--- | :--- | :--- |
| `id` | Ticket masivo (`ID de incidencia`) | Sí | Identificador oficial (ej. `INC10408544`). |
| `titulo` | Ticket masivo (`Descripción`) | Sí | Título o descripción sintética del problema. |
| `sistemas` | Ticket masivo (`Grupo asignado` / Sistemas) | Sí | Lista de plataformas/servicios impactados. |
| `prioridad_sugerida` | Evaluación ITIL | Sí | Nivel de severidad inferido (`P1`, `P2`, `P3`, `P4`). |
| `estatus` | Ticket masivo (`Estatus`) | Sí | Estado operativo (`Asignado`, `En curso`, `Resuelto`, etc.). |
| `fecha_envio` | Ticket masivo (`Fecha de envío`) | Opcional | Fecha/hora de detección o reporte. |
| `resumen_ia` | Epsilon `/api/epsilon/resumenIA/{codigo}` | Opcional | Bloque estructurado con `problema`, `impacto`, `solucion`, `bloqueos`, `siguiente_accion`. |

---

## 3. Reglas Específicas por Fase de Notificación

### 3.1. Fase `apertura` (Primera comunicación)
* **Objetivo**: Transmitir qué ha ocurrido, sistemas y clientes afectados, severidad y primeras acciones en curso.
* **Versión Completa ($\le$ 90 palabras)**:
  - Formato: Un único párrafo.
  - Estructura: `[Criticidad] detectada en [Sistemas]. Se identifica [Problema / Impacto inicial]. Los equipos operativos se encuentran [Acción en curso]. Se informará de la evolución en la próxima actualización operativa.`
* **Versión Breve ($\le$ 30 palabras)**:
  - Formato: Frase ejecutiva única.
  - Estructura: `[Apertura P1/P2] [ID]: [Problema sintetizado] afectando a [Sistemas]. Equipos técnicos interviniendo.`

### 3.2. Fase `seguimiento` (Actualización intermedia)
* **Objetivo**: Reflejar evolución del servicio, avances técnicos, mitigaciones temporales (workarounds) y próximos hitos.
* **Versión Completa ($\le$ 90 palabras)**:
  - Formato: Un único párrafo.
  - Estructura: `Seguimiento de la incidencia [ID] en [Sistemas]. El impacto se mantiene [o se acota], registrando [Estado actual / Bloqueos]. Se ha ejecutado [Acciones realizadas / Workaround] y se continúa trabajando en [Siguiente acción prioritaria]. Próxima comunicación tras validación.`
* **Versión Breve ($\le$ 30 palabras)**:
  - Formato: Frase ejecutiva única.
  - Estructura: `[Seguimiento] [ID]: Trabajo en curso en [Sistemas]. Mitigación aplicada / Próximo hito: [Siguiente paso].`

### 3.3. Fase `cierre` (Resolución de servicio)
* **Objetivo**: Confirmar estabilización y restauración del servicio, causa a alto nivel sin tecnicismos y medidas preventivas.
* **Versión Completa ($\le$ 90 palabras)**:
  - Formato: Un único párrafo.
  - Estructura: `Incidencia [ID] en [Sistemas] resuelta y servicio estabilizado. La degradación se originó por [Causa raíz simplificada] y ha quedado subsanada tras [Solución aplicada]. Se mantiene monitorización preventiva sobre los flujos afectados.`
* **Versión Breve ($\le$ 30 palabras)**:
  - Formato: Frase ejecutiva única.
  - Estructura: `[Cierre] [ID] resuelta: Servicio estabilizado en [Sistemas] tras [Solución aplicada]. Monitorización activa.`

---

## 4. Guardrails Obligatorios (Anti-Alucinación y Estilo)

1. **Límite Estricto de Palabras**:
   - `conteo_palabras_completo <= 90`
   - `conteo_palabras_breve <= 30`
   - La función generadora debe validar y truncar/reformular determinísticamente antes de persistir.
2. **Estructura Monopárrafo**:
   - La versión completa debe contener exactamente **1 párrafo** (sin saltos de línea intermedios `\n\n`).
3. **Cero Invención de Datos (Regla de Oro Anti-Alucinación)**:
   - Prohibido inventar volúmenes exactos de usuarios, horas de corte no documentadas, direcciones IP, servidores o causas técnicas hipotéticas.
   - Si no hay datos detallados de clientes, utilizar expresiones genéricas respaldadas (*"afectando a clientes del servicio"*, *"degradación en la plataforma"*).
4. **Cultura Sin Culpa (*Blameless*)**:
   - Nunca señalar personas, áreas culpables o proveedores específicos de forma acusatoria.
5. **Idioma**:
   - Redacción 100% en español ejecutivo formal.

---

## 5. Algoritmo Determinístico de Generación (Python)

```python
import re

def count_words(text: str) -> int:
    return len(re.findall(r'\b\w+\b', text))

def generate_executive_messages(incident: dict, evaluation: dict, resumen_ia: dict | None) -> dict:
    inc_id = incident.get("ID de incidencia") or incident.get("id") or "INC"
    sistemas = incident.get("sistemas", ["Sistemas Core"])
    sistemas_str = ", ".join(sistemas) if isinstance(sistemas, list) else str(sistemas)
    prio = evaluation.get("prioridad_sugerida", "P2")
    
    # Extraer variables con fallback si Epsilon no tiene resumen
    problema = (resumen_ia.get("problema") if resumen_ia else None) or incident.get("Descripción", "Incidencia de servicio")
    impacto = (resumen_ia.get("impacto") if resumen_ia else None) or evaluation.get("impacto_justificacion", "Degradación en el servicio")
    solucion = (resumen_ia.get("solucion") if resumen_ia else None) or "intervención técnica del equipo resolutor"
    sig_accion = (resumen_ia.get("siguiente_accion") if resumen_ia else None) or "diagnóstico y restablecimiento del servicio"
    
    # 1. Apertura
    apertura_comp = (
        f"Incidencia de criticidad {prio} detectada en {sistemas_str} ({inc_id}). "
        f"Se registra {problema}, con impacto en {impacto}. Los equipos operativos "
        f"se encuentran interviniendo de forma prioritaria en {sig_accion}. "
        f"Se remitirá nueva actualización tras la evolución técnica."
    )
    apertura_breve = f"[{prio} Apertura] {inc_id}: {problema[:50]} en {sistemas_str}. Intervención en curso."
    
    # 2. Seguimiento
    seguimiento_comp = (
        f"Seguimiento de la incidencia {inc_id} ({prio}) en {sistemas_str}. "
        f"Se mantienen labores de estabilización sobre {problema}. "
        f"El equipo especializado avanza en {solucion} y ejecuta {sig_accion}. "
        f"Continuamos monitorizando la evolución hasta su restablecimiento."
    )
    seguimiento_breve = f"[Seguimiento] {inc_id}: Avance en {sistemas_str}. Acción en curso: {sig_accion[:45]}."
    
    # 3. Cierre
    cierre_comp = (
        f"Incidencia {inc_id} en {sistemas_str} resuelta y servicio restablecido. "
        f"La afectación sobre {problema} ha quedado subsanada tras {solucion}. "
        f"Se mantiene monitorización preventiva sobre los flujos operativos para asegurar la estabilidad."
    )
    cierre_breve = f"[Cierre] {inc_id} resuelta: Servicio estabilizado en {sistemas_str} tras {solucion[:40]}."
    
    # Ajuste y validación de palabras
    messages = {
        "apertura": {
            "completo": apertura_comp.strip(),
            "breve": apertura_breve.strip(),
            "conteo_palabras_completo": count_words(apertura_comp),
            "conteo_palabras_breve": count_words(apertura_breve)
        },
        "seguimiento": {
            "completo": seguimiento_comp.strip(),
            "breve": seguimiento_breve.strip(),
            "conteo_palabras_completo": count_words(seguimiento_comp),
            "conteo_palabras_breve": count_words(seguimiento_breve)
        },
        "cierre": {
            "completo": cierre_comp.strip(),
            "breve": cierre_breve.strip(),
            "conteo_palabras_completo": count_words(cierre_comp),
            "conteo_palabras_breve": count_words(cierre_breve)
        }
    }
    
    for phase, item in messages.items():
        assert item["conteo_palabras_completo"] <= 90, f"{phase} completo supera 90 palabras"
        assert item["conteo_palabras_breve"] <= 30, f"{phase} breve supera 30 palabras"
        
    return messages
```

