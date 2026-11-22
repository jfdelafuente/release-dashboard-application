---
name: release-project-communication
alias: comunicacion-proyectos-release
description: >-
  Estandariza, redacta y actualiza comunicaciones ejecutivas y operativas para Microsoft Teams
  y canales de Dirección sobre el despliegue de proyectos en releases mensuales IT: cierre de
  instalaciones, balance oficial GO/NoGO, inicio de pruebas de regresión/proyecto, avisos operativos
  y replanificaciones PaP, manteniendo sincronizado el catálogo en data/config/projects_catalog.json
  y enrutando siempre al dashboard de Mesa de Release (/dashboards/release-desk/).
domain: it-releases
version: 1.0.0
language: es
owner: Orange Tech Operations
metadata:
  role: release_communication_specialist
  pipeline_stage: release_window_communication
  security_level: internal_confidential
---

# Comunicación de Proyectos de Release (`release-project-communication`) — v1.0.0

Esta skill define las directrices, formatos estándar y reglas de negocio para elaborar comunicaciones ejecutivas y operativas sobre los proyectos de una **Release Mensual IT** en MasOrange / Orange Tech Operations, destinadas principalmente a canales de **Microsoft Teams** y correo de Dirección.

---

## 1. Principios y Reglas de Oro

1. **Destino Oficial de Seguimiento**:
   - El seguimiento operativo, incidencias post-release y acuerdos de proyectos se realiza **siempre en la consola de Mesa de Release** (`/dashboards/release-desk/`, URL: `http://10.132.26.96:8081/dashboards/release-desk/`).
   - **Regla Estricta**: Nunca referenciar genéricamente "Release Dashboard" ni enlazar a `release-kpis` cuando el contexto sea el seguimiento operativo de la ventana o post-instalación de la release; el enlace oficial es siempre **Mesa de Release**.

2. **Cuadre Numérico y Estadístico Estricto**:
   - Las cifras del balance deben cuadrar al 100%:
     $$\text{Total Proyectos} = \text{GO} (\text{Completo} + \text{Piloto} + \text{Modo Oculto}) + \text{PAP Técnico} + \text{Replanificados/NoGO}$$
   - Nunca inventar ni aproximar cifras. Si el usuario facilita una tabla o captura de GO/NoGO, extraer exactamente los valores y calcular los porcentajes correspondientes.

3. **Avisos Operativos Claros y Desacoplados**:
   - Si existe una incidencia, retraso en refresco de datos (ej. KRATOS) o bloqueo temporal que impacta a un subsistema (ej. frontales web):
     - Destacarlo explícitamente en un bloque de aviso (`> ⚠️`).
     - Indicar el tiempo estimado de demora.
     - Confirmar inmediatamente el estado positivo del resto de plataformas (**"El resto de aplicaciones y sistemas están OK"**).

4. **Sincronización Bidireccional de Datos**:
   - Siempre que se identifiquen cambios de estado, nuevos responsables o replanificaciones de PaP:
     - Actualizar `data/config/projects_catalog.json` (y el CSV `data/storage/projects/{YYYYRMM}.csv`).
     - Registrar los trabajos programados en `data/config/scheduled_changes_pap.json`.
     - Sincronizar con el almacenamiento persistente del VPS (`/infocodes/var/storage/release-dashboard/config/`).

---

## 2. Estructura Estándar del Mensaje para Microsoft Teams

Todo comunicado de cierre de instalaciones o inicio de pruebas debe seguir este orden y estilo visual:

```markdown
✅ **Cierre de Instalaciones e Inicio de Pruebas – Release {YYYYRMM}**

Se comunica que han **finalizado con éxito las instalaciones de los proyectos de la release {YYYYRMM} sin incidencias reseñables**, encontrándose los sistemas estables y operativos.

🧪 **A partir de este momento dan comienzo las pruebas de regresión y validación de proyectos** (con **{N} proyectos** con pruebas activas).

> ⚠️ **Aviso Operativo de Pruebas (si aplica):**
> [Detalle del impacto, ej. Refresco de KRATOS con retraso de 20 min que afecta a frontales web].
> 🟢 **El resto de aplicaciones y sistemas están OK** e inician pruebas con normalidad.

---

### 📊 Balance Definitivo del Despliegue ({Total} Proyectos)

* 🟢 **GO: {N_GO} proyectos ({%_GO}%)**
  * **{N_Comp} en Despliegue Completo** (Operativos para el 100% de canales)
  * **{N_Pil} en Piloto** (Apertura progresiva y controlada)
  * **{N_Ocult} en Modo Oculto** (Capacidad técnica preparatoria)
* ⚙️ **PAP Técnico: {N_PAP} proyectos ({%_PAP}%)**
  * `{JIRA}` – *{Título}* ({Responsable} / {Metodología})
* 🔄 **Replanificación PaP (si aplica):**
  * `{JIRA}` – *{Título}*: Replanificado PAP para el **{Día DD/MM a las HH:MMh}**.

---

### 🚀 Principales Hitos Desplegados

* ☁️ **Cloud & Arquitectura:**
  * [Proyectos GCP, AWS, migraciones, optimizaciones core]
* 🏢 **Empresas, B2B & SOHO:**
  * [Operaciones móviles, terminales, coberturas, flujos comerciales]
* 📱 **Residencial, Digital & Seguridad:**
  * [Ciberprotección, plataformas streaming, canales de venta, seguros]

---
🔍 *El seguimiento operativo y la evolución de las incidencias pueden consultarse en directo en el [Dashboard de Mesa de Release](http://10.132.26.96:8081/dashboards/release-desk/).*
```

---

## 3. Matriz de Clasificación de Proyectos

Al procesar listados de proyectos (hojas de cálculo, CSV, texto copiado de correo o capturas de pantalla):

| Campo | Valores Esperados | Normalización / Comportamiento |
|---|---|---|
| **JIRA** | `PRJ-XXXXX` | Clave unívoca en el catálogo `by_release[YYYYRMM]`. |
| **Summary** | Texto | Nombre oficial del proyecto o iniciativa. |
| **Pruebas** | `Si` / `No` | Identifica si el proyecto realiza pruebas de regresión/funcionales en la ventana. |
| **Responsable** | Nombre y Apellidos | Lead IT / Delivery Manager asignado. |
| **Metodología** | `Agile E2E`, `Bimodal`, `WF`, vacía | Metodología de gestión de entrega. |
| **Decisión** | `GO`, `PaP Tecnico`, `NoGO` | `GO` habilita despliegue en ventana; `PaP Tecnico` se despliega en ventana técnica posterior. |
| **Despliegue** | `Completo`, `Piloto`, `Oculto` | Alcance comercial/técnico. Si la decisión es `PaP Tecnico`, se cataloga como `PAP Técnico`. |

---

## 4. Procedimiento de Sincronización en el Repositorio

Cuando el usuario confirme los datos de los proyectos:

1. **Actualizar `data/config/projects_catalog.json`**:
   - Actualizar las propiedades de cada proyecto en `by_release[YYYYRMM]`.
2. **Actualizar `data/storage/projects/{YYYYRMM}.csv`**:
   - Mantener el CSV con columnas: `JIRA;Summary;Despliegue;Descripcion;Pruebas;Responsable;Metodologia;Decision`.
3. **Actualizar `data/config/scheduled_changes_pap.json`**:
   - Si hay proyectos catalogados como `PAP Técnico` o con fecha de replanificación, registrarlos como cambio planificado (`crq: "PAP-{JIRA}"`).
4. **Sincronizar VPS (`10.132.26.96`)**:
   - Subir ficheros mediante `scp` a `/infocodes/var/storage/release-dashboard/config/` y `/storage/projects/`.
   - Verificar respuesta `HTTP 200 OK` en Nginx (`/data/projects_catalog.json` y `/data/scheduled_changes_pap.json`).
5. **Git Commit & Push**:
   - Versionar los cambios en la rama `production`.
