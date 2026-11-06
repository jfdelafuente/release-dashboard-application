# Guía de Configuración y Uso: CLI de Calibración Epsilon Resumen IA

Esta guía documenta la configuración del entorno, opciones de ejecución, integración multi-proveedor y casos prácticos de la herramienta CLI [`scripts/test_epsilon_prompt.py`](file:///c:/Users/jose.delafuente/proyectos/release-dashboard-application/scripts/test_epsilon_prompt.py) para evaluar el System Prompt de **Epsilon Resumen IA**.

---

## 🎯 Objetivo de la Herramienta

La CLI permite a los ingenieros de soporte, Incident Managers y desarrolladores:

1. **Calibrar empíricamente** el System Prompt contra volcados reales de tickets Remedy antes de desplegarlos a producción.
2. **Auditar el cumplimiento estricto** de las restricciones del contrato de datos JSON (longitud por campo, marcas temporales adaptativas, prefijos estandarizados de bloqueos y exigencia de métodos alternativos/workaround).
3. **Validar multi-proveedor**: Soporta de forma nativa e integrada llamadas deterministas (`temperature=0.0`) a **Anthropic Claude**, **OpenAI** (compatible con Azure/proxies) y **Google Gemini**, además de un modo **Mock offline** sin consumo de tokens.

---

## ⚙️ 1. Configuración de Proveedores y Credenciales

El script incorpora **clientes HTTP nativos (`urllib.request`)** para Anthropic y OpenAI, lo que permite su funcionamiento inmediato en cualquier terminal Python 3.12 estándar **sin requerir paquetes externos obligatorios**.

### 1.1 Configurar Anthropic Claude (Recomendado — Proxy MasOrange o API Directa)

El script carga automáticamente el archivo `.env` situado en la raíz del proyecto. Puedes configurarlo mediante un archivo `.env` o mediante variables de entorno de consola.

#### Opción A: Archivo `.env` en la raíz del proyecto (Proxy LiteLLM Corporativo MasOrange)

Crea o edita el archivo `.env` en la raíz de `release-dashboard-application`:

```dotenv
# ---------------------------------------------------------------------------
# MODELO LLM (LiteLLM proxy — por defecto Claude via proxy corporativo MasOrange)
# ---------------------------------------------------------------------------
ANTHROPIC_AUTH_TOKEN=sk-wkjyNyl8...
ANTHROPIC_BASE_URL=https://llm.tools.cloud.masorange.es
ANTHROPIC_MODEL=anthropic/claude-sonnet-4-5
ANTHROPIC_DEFAULT_SONNET_MODEL=claude-sonnet-4-5

# Opcional: si tu red corporativa realiza inspección SSL y certificados internos
# ANTHROPIC_VERIFY_SSL=false
```

#### Opción B: Variables de Entorno en Sesión (PowerShell / Bash)

```powershell
# En PowerShell:
$env:ANTHROPIC_AUTH_TOKEN = "sk-wkjyNyl8..."
$env:ANTHROPIC_BASE_URL   = "https://llm.tools.cloud.masorange.es"
$env:ANTHROPIC_MODEL      = "anthropic/claude-sonnet-4-5"

# O en API directa Anthropic (sin proxy):
$env:ANTHROPIC_API_KEY = "sk-ant-api03-tu-clave-aqui"
```

* **Prioridad de modelos resuelta por la CLI:**
  1. Flag `--model <nombre>` pasado explícitamente en la línea de comandos.
  2. Variable de entorno `ANTHROPIC_MODEL` (ej. `anthropic/claude-sonnet-4-5`).
  3. Variable de entorno `ANTHROPIC_DEFAULT_SONNET_MODEL` (ej. `claude-sonnet-4-5`).
  4. Valor por defecto: `claude-3-5-sonnet-20241022`.
* **Autodetección:** Si se define `ANTHROPIC_AUTH_TOKEN` o `ANTHROPIC_API_KEY` en `.env` o en el entorno, la CLI selecciona automáticamente a Anthropic como proveedor sin necesidad de pasar `--provider anthropic`.
* **Soporte de Gateway/Proxy:** El script añade automáticamente `/v1/messages` a `ANTHROPIC_BASE_URL` y envía tanto la cabecera `Authorization: Bearer <token>` como `x-api-key: <token>`. Además, cuenta con reconexión transparente ante inspección de certificados SSL corporativos.

---

### 1.2 Configurar OpenAI / Azure / Proxies Locales

Para utilizar OpenAI o endpoints compatibles (Azure OpenAI, Ollama, vLLM, LiteLLM):

```powershell
# API oficial de OpenAI:
$env:OPENAI_API_KEY = "sk-proj-tu-clave-aqui"

# Opcional (para endpoints compatibles, Azure o proxies internos):
$env:OPENAI_BASE_URL = "https://tu-proxy-corporativo.orange.es/v1"
```

* **Modelo predeterminado:** `gpt-4o`
* **Modelos alternativos admitidos:** `gpt-4o-mini`, `o1-preview`, etc.

---

### 1.3 Configurar Google Gemini

Para invocar la API de Google Gemini (requiere instalar el SDK oficial `google-genai` o `google-generativeai`):

```powershell
$env:GEMINI_API_KEY = "AIzaSy-tu-clave-aqui"
pip install google-genai
```

* **Modelo predeterminado:** `gemini-2.5-pro`
* **Modelos alternativos admitidos:** `gemini-1.5-pro`, `gemini-1.5-flash`.

---

## 🚀 2. Guía de Uso y Comandos

### Sintaxis General

```bash
python scripts/test_epsilon_prompt.py [--file RUTA] [--provider {openai,gemini,anthropic}] [--model MODELO] [--mock] [--strict] [--json-only]
```

### Tabla de Parámetros

| Parámetro | Tipo | Por Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `--file`, `-f` | Ruta | `stdin` | Ruta al archivo JSON con el volcado en bruto del ticket Remedy. |
| `--provider`, `-p` | Opción | *Auto* (`openai`) | Proveedor LLM a invocar (`anthropic`, `openai`, `gemini`). Si se omite, autodetecta la clave configurada en el entorno (`ANTHROPIC_API_KEY` o `GEMINI_API_KEY`). |
| `--model`, `-m` | Texto | *(Automático)* | Nombre del modelo a invocar según el proveedor (`claude-3-5-sonnet-20241022`, `gpt-4o`, `gemini-2.5-pro`). |
| `--mock`, `--dry-run` | Flag | `False` | Modo simulado local: no conecta a internet ni consume API. |
| `--strict` | Flag | `False` | Devuelve código de salida `1` ante cualquier fallo de validación de contrato o esquema Pydantic. |
| `--json-only` | Flag | `False` | Muestra exclusivamente el JSON devuelto, omitiendo la tabla visual. |
| `--list-models` | Flag | `False` | Consulta y muestra los modelos disponibles en el endpoint o proxy corporativo (`/v1/models`). |

---

## 📋 3. Casos de Uso Prácticos

### Caso 0: Consultar Modelos Disponibles en el Proxy MasOrange (`--list-models`)

Permite comprobar la conectividad con el proxy corporativo y listar los modelos admitidos para tu token:

```powershell
python scripts/test_epsilon_prompt.py --list-models
```

### Caso 1: Prueba Real con Anthropic Claude (vía `.env` o Entorno)

```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-tu-clave"
python scripts/test_epsilon_prompt.py --file .\data\samples\remedy_incident_sample2.json --provider anthropic
```

### Caso 2: Prueba Rápida con Modelo Ligero (Claude 3.5 Haiku)

```powershell
python scripts/test_epsilon_prompt.py --file .\data\samples\remedy_incident_sample2.json --provider anthropic --model claude-3-5-haiku-20241022
```

### Caso 3: Evaluación Offline sin Coste de API (`--mock`)

Permite validar el formato del archivo de entrada y ver el aspecto de la tabla de diagnóstico sin requerir credenciales ni red:

```powershell
python scripts/test_epsilon_prompt.py --file .\data\samples\remedy_incident_sample.json --mock
```

### Caso 4: Integración en CI/CD con Modo Estricto (`--strict`)

En pipelines automatizados, `--strict` asegura que el script falle con código de salida `1` si el modelo excede palabras o genera marcas de tiempo erróneas:

```powershell
python scripts/test_epsilon_prompt.py --file .\data\samples\remedy_incident_sample.json --provider anthropic --strict
```

### Caso 5: Pasar Datos por Tubería (`stdin`)

```powershell
# En PowerShell:
Get-Content .\data\samples\remedy_incident_sample.json -Raw | python scripts/test_epsilon_prompt.py --provider anthropic

# En Bash:
cat data/samples/remedy_incident_sample.json | python scripts/test_epsilon_prompt.py --provider anthropic
```

---

## 🔍 4. Formato del Archivo de Entrada Remedy

El script acepta cualquier volcado JSON de ticket Remedy. Para obtener resultados óptimos, se recomiendan los siguientes campos:

```json
{
  "id": "INC000004141215",
  "resumen": "Servicio multisim no se activa en Ficha Cliente (fichadecliente.si.orange.es)",
  "estado": "Pendiente",
  "urgencia": "Urgencia 2 - Alta",
  "impacto": "Impacto 2 - Afectación Parcial",
  "sistema": "Ficha Cliente",
  "grupoAsignado": "SISTEMAS-SOPORTE-N2",
  "notas": "28/09/2026: Detección incidencia en Ficha Cliente a las 05:30. 29/09/2026: Relacionada con INC000004141215 cerrada por error; N3 solicita casos actualizados con capturas de pantalla del problema en APP."
}
```

* Archivos de ejemplo provistos en el repositorio:
  * [`data/samples/remedy_incident_sample.json`](file:///c:/Users/jose.delafuente/proyectos/release-dashboard-application/data/samples/remedy_incident_sample.json) (Incidencia de integración MDG/Siebel en logística inversa).
  * [`data/samples/remedy_incident_sample2.json`](file:///c:/Users/jose.delafuente/proyectos/release-dashboard-application/data/samples/remedy_incident_sample2.json) (Incidencia de activación MultiSIM en Ficha Cliente).

---

## 📊 5. Interpretación del Reporte de Diagnóstico

Tras la ejecución, el script imprime el JSON generado y una tabla de auditoría con la siguiente información:

```text
--- INFORME DE CALIBRACIÓN EPSILON RESUMEN IA (ANTHROPIC - claude-3-5-sonnet-20241022) ---
---------------------------------------------------------------------------------------------------------
Campo            | Criterio Evaluado                        | Métrica Real                       | Estado  
---------------------------------------------------------------------------------------------------------
success          | Booleano true                            | True                               | [OK]    
titulo           | No vacío                                 | 62 caracteres                      | [OK]    
estadoActual     | No vacío                                 | Pendiente                          | [OK]    
problema         | 1 a 40 palabras                          | 23 palabras                        | [OK]    
impacto          | <= 30 palabras con indicación de workaro | 19 palabras | workaround: SÍ       | [OK]    
solucion         | <= 45 palabras (obligatoria si resuelto/ | 18 palabras                        | [OK]    
sistemas         | Array con al menos 1 sistema             | 2 sistemas (Ficha Cliente, MultiS  | [OK]    
hitosTecnicos    | <= 6 hitos, formato adaptativo y orden c | 2 hitos                            | [OK]    
bloqueos         | [] o elementos con prefijos estándar     | 1 bloqueos                         | [OK]    
siguienteAccion  | Opcional (compromiso explícito acordado) | 12 palabras                        | [OK]    
---------------------------------------------------------------------------------------------------------
Resultado Final: TODAS LAS REGLAS CUMPLIDAS
Tiempo: 2.14s | Tokens: 620
---------------------------------------------------------------------------------------------------------
```

### Reglas Clave Evaluadas

* **`impacto`**: Comprueba que no supere 30 palabras y que mencione explícitamente la presencia o ausencia de método alternativo (`workaround`, `método alternativo` o `sin alternativa disponible`).
* **`solucion`**: Verifica que no supere 45 palabras. Si la incidencia está en estado `RESUELTO` o `CERRADO`, la ausencia de este campo se marca como fallo.
* **`hitosTecnicos`**: Verifica que no supere 6 hitos, que cumpla la marca temporal adaptativa (`[DD/MM/YYYY HH:mm:ss]:`, `[DD/MM/YYYY HH:mm]:`, `[DD/MM/YYYY]:` o `[S/F]:`) y que mantenga orden cronológico ascendente.
* **`bloqueos`**: Si existen elementos, cada uno debe iniciar con uno de los prefijos reglamentarios: `[Ventana Release]`, `[Dependencia Terceros]`, `[Validación Negocio]` o `[Escalado Grupo]`.

---

## 🛠️ 6. Diagnóstico y Resolución de Problemas

| Síntoma | Causa Probable | Solución |
| :--- | :--- | :--- |
| `Error: Falta la variable de entorno 'ANTHROPIC_API_KEY'` | No se ha definido la variable en la sesión actual. | Ejecutar `$env:ANTHROPIC_API_KEY = "tu_clave"` en PowerShell. |
| `Error HTTP 401 desde Anthropic API` | Clave API incorrecta o expirada. | Verificar que la clave comience por `sk-ant-` y esté activa. |
| `[X] impacto: No indica explícitamente workaround` | El modelo omitió indicar si hay método alternativo. | Reforzar las notas del ticket indicando si existe o no workaround, o ajustar la temperatura a `0.0`. |
| `[X] hitosTecnicos: Formato timestamp inválido` | El LLM usó corchetes libres o inventó formatos. | El extractor del script tolera corchetes; verificar que la marca inicial comience exactamente por `[DD/MM/YYYY...]:`. |
| `Error: La entrada no es un JSON válido` | Archivo de ticket con sintaxis JSON errónea. | Validar la sintaxis del fichero `.json` con un linter o editor. |
