# Especificación: CLI de Prueba y Calibración del Prompt Epsilon (`test-epsilon-prompt`)

## Objetivo

Proporcionar una herramienta CLI en Python (`scripts/test_epsilon_prompt.py`) que permita a ingenieros y operadores probar, calibrar y validar empíricamente la efectividad y el cumplimiento de directrices del System Prompt oficial de Epsilon Resumen IA (`data/resumen_incidencia_epsilon.md`) sobre volcados de incidencias Remedy (reales o simuladas), verificando automáticamente las restricciones de contrato de datos, longitud de campos, marcas temporales y categorización antes de su despliegue productivo.

## Requisitos

### Requisitos Obligatorios
1. **Entrada de datos flexible:**
   - Debe aceptar la ruta de un archivo JSON con los datos del ticket Remedy mediante el argumento `--file <ruta.json>`.
   - Debe permitir la lectura de datos mediante tubería estándar (`stdin`) si no se proporciona `--file`.
   - Debe incluir un modo `--mock` (o `--dry-run`) que utilice un volcado de ticket Remedy y respuesta de ejemplo incorporados, permitiendo pruebas completas sin conectividad ni coste de API.

2. **Invocación Multi-Proveedor de LLM:**
   - Soporte configurable mediante el argumento `--provider {openai,gemini,anthropic}` (valor por defecto: `openai`).
   - Autenticación mediante variables de entorno estándar:
     * OpenAI: `OPENAI_API_KEY` (compatible con proxies o endpoints locales/Azure mediante `OPENAI_BASE_URL`).
     * Google Gemini: `GEMINI_API_KEY`.
     * Anthropic: `ANTHROPIC_API_KEY`.
   - Configuración de llamada determinista: `temperature=0.0` y modo de salida en objeto JSON estructurado.
   - Inyección rigurosa del System Prompt de `data/resumen_incidencia_epsilon.md` y encapsulación del ticket entre etiquetas `<INCIDENCIA_REMEDY>...</INCIDENCIA_REMEDY>`.

3. **Validación Estricta de Esquema con Pydantic:**
   - `success`: booleano obligatorio.
   - `titulo`: texto obligatorio y no vacío.
   - `estadoActual`: texto obligatorio con el estado de la incidencia.
   - `problema`: texto obligatorio con un máximo de 40 palabras.
   - `impacto`: texto obligatorio con un máximo de 30 palabras; debe verificarse que mencione explícitamente la presencia o ausencia de método alternativo o contingencia ("método alternativo", "workaround" o "sin alternativa").
   - `solucion`: texto opcional con un máximo de 45 palabras. Debe marcarse como error de validación si está ausente o vacío cuando el `estadoActual` sea `RESUELTO` o `CERRADO`.
   - `sistemas`: lista de textos con al menos un sistema identificado.
   - `hitosTecnicos`: lista de textos (máximo de 5 a 6 hitos). Cada elemento debe comenzar con una marca temporal adaptativa válida (`[DD/MM/YYYY HH:mm:ss]: `, `[DD/MM/YYYY HH:mm]: `, `[DD/MM/YYYY]: ` o `[S/F]: `). Debe verificarse que los hitos mantengan un orden cronológico ascendente.
   - `bloqueos`: lista de textos donde cada elemento comience obligatoriamente con uno de los prefijos de categoría estandarizados (`[Ventana Release]`, `[Dependencia Terceros]`, `[Validación Negocio]`, `[Escalado Grupo]`) o bien una lista vacía `[]`.
   - `siguienteAccion`: texto opcional (debe omitirse si la incidencia está resuelta o no hay compromiso explícito).

4. **Salida y Reporte Visual en Consola:**
   - Mostrar el JSON devuelto con formato estructurado e indentado.
   - Presentar una tabla de diagnóstico campo por campo indicando para cada regla:
     * Nombre del campo.
     * Criterio evaluado (conteo de palabras, formato de marcas, prefijos, presencia requerida).
     * Valor o métrica real obtenida.
     * Estado de cumplimiento (marcador de éxito o fallo).
   - Indicar métricas de la ejecución: tiempo total transcurrido (en segundos) y conteo de tokens consumidos (cuando la API del proveedor lo reporte).

5. **Comportamiento del Código de Salida (Exit Code):**
   - Por defecto: Finalizar con código de salida `0` siempre que la ejecución técnica concluya y se emita el informe, permitiendo inspeccionar fallos de validación en la tabla visual sin abortar pipelines.
   - Modo estricto (`--strict`): Finalizar con código de salida `1` si cualquiera de las reglas de validación del esquema resulta incumplida.
   - Errores fatales: Finalizar con código de salida `1` ante fallos de conexión de red, credenciales ausentes, JSON malformado o error irrecuperable de entrada.

### Requisitos Opcionales (Fase 2)
- Modo de evaluación por lotes (`--batch <directorio_jsons>`) para evaluar suites completas de tickets de prueba y calcular tasas porcentuales de cumplimiento global.
- Exportación del informe de validación a formato JSON o Markdown (`--output-report <ruta>`).

## Restricciones

- **Entorno de ejecución:** Compatible con Python 3.12 en entornos Windows y Linux.
- **Ubicación del ejecutable:** El script debe ubicarse exactamente en `scripts/test_epsilon_prompt.py`.
- **Datos de prueba:** Incluir archivo fixture de ejemplo en `data/samples/remedy_incident_sample.json`.
- **Aislamiento de dependencias:** El modo `--mock` no debe requerir librerías cliente de APIs remotas ni conexión a internet para funcionar. Si una librería externa opcional (`openai`, `google-genai`, `anthropic`, `rich`) no está instalada al invocar un proveedor real, el script debe informar de forma amigable la dependencia faltante sin generar un traceback incontrolado.

## Casos límite

- **Cuando la entrada esté vacía o no sea un JSON válido:** El sistema debe capturar el error, emitir un mensaje descriptivo por `stderr` y finalizar con código de salida `1` sin intentar llamar al LLM.
- **Cuando el LLM devuelva la respuesta dentro de un bloque markdown (ej. ````json ... ````):** El sistema debe extraer limpiamente el contenido JSON interno antes de proceder a la validación.
- **Cuando falte la variable de entorno de la API Key requerida por el proveedor seleccionado:** El sistema debe emitir un mensaje indicando el nombre exacto de la variable de entorno necesaria y salir con código `1`.
- **Cuando los hitos técnicos contengan fechas con orden cronológico alterado:** El validador debe detectar la discrepancia y marcarla en rojo como violación en el informe de cumplimiento.
- **Cuando un bloqueo no empiece por un prefijo válido:** El validador debe listar los prefijos admitidos y marcar el elemento como no conforme.

## Definición de terminado

1. Existe el archivo `scripts/test_epsilon_prompt.py` ejecutable desde terminal.
2. Existe el archivo de ejemplo `data/samples/remedy_incident_sample.json`.
3. La ejecución de `python scripts/test_epsilon_prompt.py --mock` devuelve código de salida `0`, imprime el JSON generado y la tabla de cumplimiento con todos los campos validados.
4. La ejecución de `python scripts/test_epsilon_prompt.py --mock --strict` finaliza con código de salida `0` para el caso conforme de prueba.
5. Se verifica que `--strict` produce código de salida `1` ante una respuesta simulada con violaciones (ej. exceso de palabras o formato de hito inválido).
6. Existe una suite de pruebas automatizadas con `pytest` en `converters/tests/unit/test_epsilon_prompt_cli.py` que comprueba los validadores Pydantic y la ejecución CLI con cobertura completa de los casos límite.
