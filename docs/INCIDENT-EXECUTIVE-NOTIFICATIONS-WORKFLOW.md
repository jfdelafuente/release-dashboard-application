# Guía Operativa: Redacción y Despliegue de Notificaciones Ejecutivas de Incidencias

Esta guía describe el procedimiento paso a paso que debes seguir **cada vez que recibas un nuevo fichero CSV de incidencias Remedy**, para redactar las comunicaciones oficiales de alta prioridad para Dirección (P1, P2 y discrepancias) y publicarlas de forma 100% segura y coherente en producción.

---

## 🎯 Principios y Reglas Clave

1. **El operador manda sobre los datos (Single Source of Truth):**
   * El CSV se procesa **primero en local** para redactar y revisar los mensajes sin prisa.
   * La publicación en producción es una **acción controlada y desacoplada** de la redacción.
2. **Estándar Ejecutivo Estricto:**
   * **Mensaje para Dirección:** Exactamente **1 único párrafo**, máximo **90 palabras**.
   * **Versión breve (SMS / Guardia):** Máximo **30 palabras**.
   * **Regla Anti-Alucinación:** No inventar horas, causas técnicas ni cifras de afectados no presentes en el ticket.
3. **Persistencia Acumulativa:**
   * Todos los mensajes redactados por la IA se guardan de por vida en `data/agent_executive_messages.json` para que nunca se pierdan ni se sobreescriban al subir nuevos ficheros.

---

## 🗺️ Mapa Visual de Procesos

### ESCENARIO 1: Flujo Habitual (Local Primero -> Producción)

```mermaid
flowchart TD
    subgraph E1_LOCAL["1. Entorno Local (:8080) [Con Skill y Asistente IA]"]
        E1_A["Subir CSV (web local o data/input/)"] --> E1_B["Evaluación ITIL y detección de pendientes"]
        E1_B --> E1_C["Skill incident-executive-notifications<br/>(Redacta mensajes oficiales)"]
        E1_C --> E1_D["Persistencia local en<br/>data/agent_executive_messages.json"]
    end
    subgraph E1_PROD["2. Servidor de Producción (:8081) [Sin Skill ni IA]"]
        E1_E["Subida CSV por web de producción"] --> E1_F["Despliegue de almacén (deploy-production.ps1)"]
        E1_F --> E1_G["Dashboard en Vivo: 100% Oficiales"]
    end
    E1_D --> E1_E
```

---

### ESCENARIO 2: Subida Directa por Web en Producción

```mermaid
flowchart TD
    subgraph E2_PROD_INI["Fase A: Servidor Producción (:8081) [¡Sin Skill ni IA!]"]
        E2_A["Operador sube CSV por formulario web"] --> E2_B["Servidor procesa CSV y calcula severidad"]
        E2_B --> E2_C{"¿Existe en almacén persistente?"}
        E2_C -- Sí --> E2_D["Muestra texto oficial existente"]
        E2_C -- No --> E2_E["Queda en estado 'PENDIENTE'<br/>(¡En prod NO hay skill para redactarlo!)"]
    end

    subgraph E2_LOCAL["Fase B: Resolución en Entorno Local [Con Skill e IA]"]
        E2_F["Copiar CSV al entorno local (data/input/)"] --> E2_G["Ejecutar Skill incident-executive-notifications<br/>(Agente redacta tickets pendientes)"]
        E2_G --> E2_H["Guardar en data/agent_executive_messages.json"]
    end

    subgraph E2_PROD_FIN["Fase C: Sincronización al VPS"]
        E2_I["deploy-production.ps1<br/>(Sincroniza almacén persistente al VPS)"] --> E2_J["Dashboard en Vivo:<br/>Todos los tickets pasan a OFICIALES"]
    end

    E2_E -.->|"Requiere intervención local"| E2_F
    E2_H --> E2_I
```

---

## 🛠️ Procedimiento Paso a Paso

### ESCENARIO 1: Flujo Habitual (Preparación en Local -> Publicación en Producción)

#### FASE 1: Entorno Local (Preparación y Redacción)

#### Paso 1: Ingesta del nuevo CSV en Local (Elige una opción)

* **Opción A (Recomendada: A través del Formulario Web Local):**
  1. Asegúrate de tener arrancado el servidor local: `python serve_app.py` (puerto `8080`).
  2. Abre en tu navegador el dashboard local de incidencias masivas:  
     **[http://localhost:8080/dashboards/massive-incidents/](http://localhost:8080/dashboards/massive-incidents/)**  
     *(o el Portal Central: [http://localhost:8080/dashboards/portal/](http://localhost:8080/dashboards/portal/))*.
  3. En la barra superior, haz clic en **"Seleccionar archivo"** (o arrastra el CSV).
  4. La aplicación web local automáticamente:
     * Guarda el CSV en `data/input/`.
     * Convierte el archivo a JSON masivo en `data/output/`.
     * Dispara en segundo plano `evaluate_incident_notifications.py` actualizando el catálogo de alertas.
  * *¡Listo! Si usas esta opción, puedes saltar directamente al Paso 3.*

* **Opción B (Alternativa manual por terminal):**
  1. Copia tu nuevo archivo CSV a la carpeta:
     ```text
     data/input/CS-Informe incidencias P1,  P2 y P3 - 2026 - <FECHA>.csv
     ```
  2. Ejecuta manualmente la evaluación de prioridades:
     ```powershell
     python converters/evaluate_incident_notifications.py
     ```

#### Paso 2: Escanear incidencias pendientes de redacción
Comprueba qué tickets de alta prioridad no disponen aún de mensaje oficial:
```powershell
python .agents/skills/incident-executive-notifications/scripts/scan_pending_incidents.py
```
*Si faltan tickets por redactar, el script listará los IDs, sistemas y el estado de enriquecimiento de Epsilon IA.*

#### Paso 3: Invocar la Skill de Asistente (Redacción IA)
Pide a Antigravity en el chat:
> *"He cargado un nuevo CSV de incidencias. Activa la skill incident-executive-notifications para redactar las comunicaciones oficiales pendientes."*

El asistente:
1. Inspeccionará los datos técnicos y resúmenes de Epsilon IA de cada ticket pendiente.
2. Adoptará el rol `incident-reporter` y redactará los dos niveles obligatorios ($\le 90$ palabras monopárrafo y $\le 30$ palabras breve).
3. Guardará automáticamente las salidas validadas en `data/agent_executive_messages.json` usando `update_agent_message.py`.

#### Paso 4: Revisión de Textos y Validación Humana (*Human-in-the-Loop*)
1. El asistente te presentará en el chat el resumen de todos los mensajes generados.
2. Si deseas ajustar manualmente la redacción de alguna incidencia concreta:
   ```powershell
   python converters/cli/update_agent_message.py --id INC000004XXXXXX --phase apertura --raw "**Mensaje para Dirección (versión completa):**
   Tu nuevo texto formal aquí...

   **Versión aún más breve:**
   P1: Alerta breve ajustada."
   ```
3. Verifica que el escáner informe que todo está listo:
   ```powershell
   python .agents/skills/incident-executive-notifications/scripts/scan_pending_incidents.py
   ```
   *(Debe mostrar: `✅ Todas las incidencias activas disponen de mensajes ejecutivos oficiales`)*

---

#### FASE 2: Servidor de Producción (Publicación y Sincronización)

Una vez que los mensajes y los datos están validados en local, sigue este orden para evitar desincronizaciones:

#### Paso 5: Subir el CSV en la web de producción
1. Abre tu navegador y accede al dashboard de incidencias masivas en producción:
   **[http://infocodes.si.orange.es:8081/dashboards/massive-incidents/](http://infocodes.si.orange.es:8081/dashboards/massive-incidents/)**
2. Haz clic en **"Seleccionar archivo"** y sube el mismo fichero CSV que procesaste en local.
3. Espera a que termine la barra de carga y la conversión a JSON en el servidor.

#### Paso 6: Desplegar y sincronizar el almacén al servidor
Ejecuta el script de despliegue desde PowerShell:
```powershell
powershell -ExecutionPolicy Bypass -File scripts/deploy-production.ps1 -AgentsLibraryPath . -SkipPush
```
*(Si deseas subir además los commits a Git, retira el flag `-SkipPush`)*.

**¿Qué hace este script en este paso?**
* Empaqueta el runtime y los catálogos actualizados.
* Sube el paquete al servidor VPS (`10.132.26.96`).
* **Sincroniza `agent_executive_messages.json`** y `high_priority_notifications.json` en el almacenamiento persistente `/infocodes/var/storage/release-dashboard/`.
* Reinicia el backend y realiza las comprobaciones de salud HTTP (todas en `200 OK`).

#### Paso 7: Verificación en Vivo
Accede al portal y comprueba que la campana de notificaciones y los modales ejecutivos muestran los textos redactados:
* **Portal Principal:** [http://infocodes.si.orange.es:8081/dashboards/portal/](http://infocodes.si.orange.es:8081/dashboards/portal/)
* **Incidencias Masivas:** [http://infocodes.si.orange.es:8081/dashboards/massive-incidents/](http://infocodes.si.orange.es:8081/dashboards/massive-incidents/)

---

### ESCENARIO 2: Subida Directa del CSV a través del Formulario Web en Producción

Este escenario ocurre cuando un operador o usuario **sube un nuevo CSV directamente desde el formulario web de producción** ([http://infocodes.si.orange.es:8081](http://infocodes.si.orange.es:8081)) antes de que los mensajes hayan sido procesados en local.

> [!IMPORTANT]
> **En el servidor de producción NO existen skills ni agentes de IA.**
> El VPS de producción (`10.132.26.96`) opera de manera puramente determinista (Python y Nginx). No tiene conexión a modelos de lenguaje (LLM), no dispone del asistente Antigravity, ni tiene desplegada la carpeta de skills (`.agents/`).
> Por este motivo, **la subida web en producción por sí sola NUNCA redacta comunicaciones oficiales**. Su único cometido es convertir el CSV, evaluar la severidad ITIL por reglas fijas y consultar si los tickets ya existen en el almacén persistente.

---

#### Fase A: Lo que ocurre automáticamente en Producción (¡Sin Skill ni IA!)

1. El backend web guarda el archivo en `/infocodes/var/storage/release-dashboard/input/` y genera el JSON masivo.
2. Automáticamente ejecuta `evaluate_incident_notifications.py` en el VPS.
3. **Comportamiento según el almacén persistente**:
   * **Incidencias ya redactadas previamente:** Se cargan desde `/infocodes/var/storage/release-dashboard/agent_executive_messages.json` mostrando su **texto oficial**.
   * **Incidencias nuevas:** Dado que en el VPS no hay ninguna skill para redactarlas, quedan marcadas con **`"estado": "pendiente"`** (con un badge de alerta y su prompt técnico preparado a la espera de redacción).

---

#### Fase B: Resolución de Tickets Pendientes en Local (Donde SÍ reside la Skill y el Asistente)

Para convertir esas incidencias pendientes en comunicaciones oficiales validadas, debes intervenir desde tu entorno de desarrollo local:

#### Paso 1: Disponer del fichero CSV en tu entorno local
Si ya tienes el fichero CSV en tu máquina:
* Cópialo a tu carpeta local `data/input/`.

*(Si no dispones del fichero localmente, descárgalo directamente del VPS por SCP)*:
```powershell
scp infocodes@10.132.26.96:"/infocodes/var/storage/release-dashboard/input/CS-Informe*.csv" data/input/
```

#### Paso 2: Evaluar y escanear los tickets pendientes en local
Ejecuta la evaluación ITIL local para identificar exactamente los tickets que quedaron pendientes en el servidor:
```powershell
python converters/evaluate_incident_notifications.py
python .agents/skills/incident-executive-notifications/scripts/scan_pending_incidents.py
```
El escáner listará las incidencias nuevas que requieren redacción.

#### Paso 3: Redactar los tickets pendientes con la Skill en Local
Pide al asistente en el chat local de Antigravity:
> *"He sincronizado el CSV subido a producción. Activa la skill incident-executive-notifications para redactar las incidencias pendientes."*

El asistente ejecutará la skill en local, adoptará el rol `incident-reporter`, redactará los mensajes (≤ 90 palabras para Dirección y ≤ 30 palabras versión breve) y los guardará en el almacén acumulativo local `data/agent_executive_messages.json`.

---

#### Fase C: Sincronización y Publicación en Producción

#### Paso 4: Desplegar el almacén actualizado a Producción
Sincroniza el almacén de mensajes con el servidor ejecutando el script de despliegue desde PowerShell:
```powershell
powershell -ExecutionPolicy Bypass -File scripts/deploy-production.ps1 -AgentsLibraryPath .
```
El script transferirá el almacén actualizado a `/infocodes/var/storage/release-dashboard/agent_executive_messages.json` y actualizará automáticamente el catálogo de notificaciones.

#### Paso 5: Verificación en el Navegador
Recarga la web en producción:
* **[http://infocodes.si.orange.es:8081/dashboards/massive-incidents/](http://infocodes.si.orange.es:8081/dashboards/massive-incidents/)**

Verás que las incidencias que antes figuraban en estado `"pendiente"` ahora muestran el badge verde con el texto oficial completo y breve listo para Dirección.

---

## 🖥️ Consola Operativa: Consola de Emergencias IT Orange (Cockpit Incident Manager)

Para facilitar la supervisión del estado de las redacciones de agente y la gobernanza en tiempo real de situaciones de crisis según el procedimiento corporativo de **Orange España**, el sistema cuenta con la **Consola Operativa de Emergencias IT del Incident Manager** (*Cockpit IM*).

### Acceso a la Consola
* **Entorno de Desarrollo Local:** [http://localhost:8080/dashboards/incident-manager-monitor/](http://localhost:8080/dashboards/incident-manager-monitor/)
* **Entorno de Producción VPS:** [http://infocodes.si.orange.es:8081/dashboards/incident-manager-monitor/](http://infocodes.si.orange.es:8081/dashboards/incident-manager-monitor/)

> [!NOTE]
> **Aislamiento Estricto:** Esta herramienta es de uso exclusivo para el Incident Manager y el equipo de guardia operativa. **No aparece enlazada en el portal general público** (`/dashboards/portal/` o `/dashboards/index.html`) para mantener aislada la gestión de crisis IT. Su acceso se realiza mediante URL directa o marcadores de navegador.
> 
> 📖 Para consultar la guía de uso detallada durante los turnos de guardia, consulta el [Manual del Operador de la Consola Operativa](file:///c:/Users/jose.delafuente/proyectos/release-dashboard-application/docs/MANUAL-OPERADOR-CONSOLA-OPERATIVA.md).

### Capacidades de la Consola Operativa de Emergencias:
1. **Barra de KPIs de Emergencia en Tiempo Real:**
   * Contador de incidencias pendientes de redacción con alerta visual dinámica (rojo si $> 0$, verde si $= 0$).
   * Desglose de oficiales emitidos, total de activas y criticidad P1/SL1 y P2/SL2.
   * Contador de **Subescalaciones (Discrepancias de Triaje)** desglosando casos SL1 vs SL2 con métricas objetivas.
   * Contador de **Alertas de Escalado Telefónico (≥45m / +1h)** con resaltado visual.
   * Contador de **Workarounds Pendientes CSO** con aviso de bloqueo de desescalada.
2. **Detección Cuantitativa de Discrepancias (Regla de Oro N1):**
   * Despliega la tabla comparativa de Severidad Remedy Nominal vs Severidad ITIL Orange (SL1/SL2).
   * Identifica el Proceso Crítico afectado (ATC, Ventas, Facturación, Provisión, Red o Sistemas Core) y el **umbral numérico exacto superado** (ej. $>100$ llamadas en cola ATC, indisponibilidad POS $>50\%$ tiendas, corte de provisión $>500$ líneas).
3. **Cronometraje Anti-Drift y Alertas de Escalado Telefónico:**
   * Cronómetro en vivo de minutos transcurridos desde la apertura Remedy (`minutos_desde_apertura`), calculado sobre epoch UTC cada 10s con sobrecarga de CPU $<0.1\%$.
   * **Alerta 45 min (1er Escalado):** Banner ámbar que exige convocatoria obligatoria a resolutores N2/N3 vía telefónica/audio (Regla de Oro).
   * **Alerta +1h / 105 min (2º Escalado):** Banner rojo crítico que exige escalado telefónico a Dirección y Customer & Service Ops (IM-CSO).
4. **Gobernanza de Workarounds y Bloqueo Institucional de Desescaladas:**
   * Banner institucional con candado 🔒 (`.im-gov-lock-banner`).
   * Bloqueo estricto de desescaladas en la consola: una mitigación provisional **nunca** permite rebajar la severidad mientras el impacto en clientes siga activo y sin la autorización explícita de **IM-CSO**.
5. **Reporte Normalizado de Emergencia en 4 Bloques (1-Click Copy):**
   * Generador de reporte estructurado oficial con monospaced styling:
     * `[1] CLASIFICACIÓN DEL TICKET`: ID, Severidad ITIL, Proceso Crítico, Umbral de Emergencia, Sistemas e Impacto.
     * `[2] ESTADO DE COMUNICACIONES Y SLAS`: Tiempo transcurrido, estado de 1ª notificación (<20 min) y frecuencia.
     * `[3] PLAN DE ACCIÓN Y GOBERNANZA DE WORKAROUNDS`: Diagnóstico técnico, estatus de workaround y gobernanza CSO.
     * `[4] ESTADO DE ESCALADO TELEFÓNICO`: Fase temporal, canal telefónico obligatorio y matriz RACI.
   * Botón **"Copiar Reporte"** con retroalimentación instantánea al portapapeles y anuncio ARIA para lectores de pantalla.
6. **Alternancia de Modos de Consola:**
   * Botón **"Modo Emergencias" / "Modo Compacto"** para desplegar u ocultar los bloques operativos según la intensidad del turno de guardia.
7. **Protocolo de Emergencias IT & Matriz RACI (Drawer / Modal):**
   * Botón de cabecera **"Protocolo & Contactos"** que despliega el modal accesible con la matriz RACI corporativa:
     * **Incident Manager (IM):** Responsable (R) de triaje, cronometraje, convocatoria telefónica y reporte.
     * **Customer & Service Ops (IM-CSO):** Aprobador (A) exclusivo de mitigaciones (workarounds) y escalados a Dirección.
   * Enlaces directos a directorios de guardias y matrices de contacto: **GRIAL Orange** (`https://grial.orange.es`) y **Confluence Operaciones MasMóvil** (`https://confluence.masmovil.com`).
8. **Asistente de Ingesta Integrado con Validación Reactiva y Sugerencia IA:**
   * Botón **"✨ Sugerir Borrador IA"** (en la cabecera del editor) y **"✨ Sugerir"** (en la barra de ingesta rápida) para rellenar de forma inmediata un borrador normativo conforme a los límites de Orange ($\le 90$ palabras monopárrafo para Versión Completa y $\le 30$ palabras para Versión Breve).
   * Contadores en vivo de longitud de palabras con alerta visual en rojo ante excesos.
   * Botón **"Guardar en Almacén Oficial"** que persiste directamente vía API en `data/agent_executive_messages.json` y regenera el catálogo en vivo.
   * Botón de contingencia **"Copiar Comando CLI"** que genera la sintaxis exacta de `update_agent_message.py` lista para pegar en terminal si se opera sin conectividad API.
9. **Herramientas de Ejecución Rápida y Ciclo de Vida (4 Estados):**
   * Botón **"📋 Reclasif." / "Copiar Solicitud Reclasificación Remedy"** para generar la justificación formal ITIL al grupo resolutor N1.
   * Botón **"📞 War Room" / "Convocatoria War Room Teams"** para citar a canal de audio a los técnicos ante escalados $\ge 45\text{m}$.
   * Selector del **Ciclo de Vida de 4 Estados** (`Pendiente`, `Comunicada`, `En Seguimiento`, `Descartada`) con persistencia en `localStorage` y filtros reactivos `Solo Pendientes` vs `Todas las Activas`.

---

## ❓ Preguntas Frecuentes y Diagnóstico (FAQ)

### 1. ¿Por qué la subida web de un CSV en producción no genera los textos del agente automáticamente?
* **Diseño sin LLM en el servidor**: Por motivos de gobernanza, costes y prevención de alucinaciones, en el VPS de producción no corre ningún modelo de lenguaje desatendido.
* **Separación de responsabilidades**: La redacción ejecutiva formal para Dirección la genera el agente `incident-reporter` en el entorno local (con supervisión humana).
* **Comportamiento esperado**: Cuando el backend web de producción procesa un CSV, evalúa la severidad ITIL y busca los mensajes en el almacén persistente `/infocodes/var/storage/release-dashboard/agent_executive_messages.json`. Cualquier incidencia nueva que no esté en dicho almacén se marca automáticamente como `"estado": "pendiente"` con su prompt técnico listo para ser procesado.

### 2. ¿Por qué al ejecutar `deploy-production.ps1 -SkipPush` no veía los ficheros JSON actualizados en producción?
* **Seguridad de Git**: El script de despliegue verifica que el estado de Git esté limpio (`git status --porcelain`). Si tienes modificaciones locales no commiteadas o una confirmación interactiva esperando en terminal, el script aborta antes de empaquetar o conectar por SSH al VPS.
* **Ubicación en el servidor**: Los datos persistentes no residen dentro del árbol de código estático de la release, sino en el storage desacoplado:
  * Notificaciones activas: `/infocodes/var/storage/release-dashboard/output/high_priority_notifications.json`
  * Almacén de redacciones: `/infocodes/var/storage/release-dashboard/agent_executive_messages.json`
* **Sincronización en el script**: Asegúrate de que el script copie tanto `high_priority_notifications.json` como `agent_executive_messages.json` hacia `$STORAGE_BASE` antes de recrear el symlink `data/`.

---

## 🧰 Comandos Útiles y Rescate (CheatSheet)

| Acción | Comando |
| :--- | :--- |
| **Escanear pendientes** | `python .agents/skills/incident-executive-notifications/scripts/scan_pending_incidents.py` |
| **Pendientes en formato JSON** | `python .agents/skills/incident-executive-notifications/scripts/scan_pending_incidents.py --json` |
| **Ver contexto y prompt de un ticket** | `python .agents/skills/incident-executive-notifications/scripts/scan_pending_incidents.py --id <INC>` |
| **Guardar redacción manual** | `python converters/cli/update_agent_message.py --id <INC> --phase apertura --raw "<texto>"` |
| **Guardar desde archivo borrador** | `python converters/cli/update_agent_message.py --id <INC> --phase apertura --file "borrador.txt"` |
| **Reevaluar notificaciones** | `python converters/evaluate_incident_notifications.py` |
| **Ejecutar tests unitarios** | `python -m pytest converters/tests/unit/test_update_agent_message.py -v` |
| **Desplegar a producción** | `powershell -ExecutionPolicy Bypass -File scripts/deploy-production.ps1 -AgentsLibraryPath .` |

---

## 📁 Archivos Involucrados

* **Almacén acumulativo de mensajes oficiales:** [`data/agent_executive_messages.json`](file:///c:/Users/jose.delafuente/proyectos/release-dashboard-application/data/agent_executive_messages.json)
* **Catálogo de notificaciones para el frontend:** [`data/output/high_priority_notifications.json`](file:///c:/Users/jose.delafuente/proyectos/release-dashboard-application/data/output/high_priority_notifications.json)
* **Skill de redacción:** [`.agents/skills/incident-executive-notifications/SKILL.md`](file:///c:/Users/jose.delafuente/proyectos/release-dashboard-application/.agents/skills/incident-executive-notifications/SKILL.md)
* **Escáner auxiliar:** [`.agents/skills/incident-executive-notifications/scripts/scan_pending_incidents.py`](file:///c:/Users/jose.delafuente/proyectos/release-dashboard-application/.agents/skills/incident-executive-notifications/scripts/scan_pending_incidents.py)
* **CLI de actualización:** [`converters/cli/update_agent_message.py`](file:///c:/Users/jose.delafuente/proyectos/release-dashboard-application/converters/cli/update_agent_message.py)
* **Script de despliegue:** [`scripts/deploy-production.ps1`](file:///c:/Users/jose.delafuente/proyectos/release-dashboard-application/scripts/deploy-production.ps1)

