# Plan Estratégico de Usabilidad y Experiencia de Operador (UX/UI)
## Consola de Triaje y Orquestador de Emergencias IT · Orange Tech Operations

**Código de Documento:** DOC-UX-EMERGENCY-01  
**Versión:** 1.0.0  
**Fecha de Aprobación:** Noviembre 2026  
**Área Responsable:** Customer & Service Operations (CSO) · Dirección de Operaciones y TI  
**Audiencia:** Incident Managers (IM), Operadores del Centro de Control de Operaciones (CCO), Service Delivery Managers (SDM) e Ingenieros de Desarrollo Frontend  

---

## 1. Alcance y Justificación Operativa

La **Consola de Triaje y Orquestador de Emergencias IT Orange** es una herramienta de misión crítica diseñada para la toma de decisiones inmediata en situaciones de alta presión operativa. 

Durante una emergencia **SL1 / P1** (caída de pasarelas de pago, degradación masiva de red fija/móvil, caída de aprovisionamiento B2C/B2B), los operadores sufren **visión de túnel, saturación de estímulos y fatiga cognitiva**. Las mejores consolas de operaciones en tiempo real del sector (*Datadog Incident Management, AWS Incident Manager, Bloomberg Terminal, Grafana OnCall*) aplican principios de diseño defensivo, baja latencia interactiva y ergonomía sensorial.

### Objetivos del Plan:
1. **Reducir el Time-to-Acknowledge y Time-to-Triage a menos de 10 segundos.**
2. **Garantizar cero pérdida de datos** ante cierres accidentales de modal o recargas de página.
3. **Minimizar la fatiga visual** en salas de control 24/7 (NOC/CCO) mediante modos de contraste adecuados.
4. **Facilitar la navegación por teclado (*Keyboard-First*)** para operadores expertos sin dependencia del ratón.
5. **Acelerar el traspaso de turno (*Shift Handover*)**, automatizando la síntesis del estado de la guardia.

---

## 2. Diagnóstico UX/UI del Estado Actual

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                             ESTADO ACTUAL DE LA CONSOLA                          │
├────────────────────────────────────────┬─────────────────────────────────────────┤
│ Fortalezas Identificadas               │ Oportunidades de Mejora / Gaps UX       │
├────────────────────────────────────────┼─────────────────────────────────────────┤
│ • Identidad corporativa Orange sólida  │ • Fatiga lumínica nocturna (sin Dark    │
│ • Triaje algorítmico objetivo e ITIL   │   Mode en salas con luz atenuada).      │
│ • Relojes normativos visibles (45/105) │ • Dependencia de ratón para navegar     │
│ • Generador de plantillas 90/30 pal.   │   entre tarjetas y abrir modales.       │
│ • Footer con doctrina de crisis        │ • Riesgo de pérdida de borrador al      │
│                                        │   cerrar el modal del Orquestador.      │
│                                        │ • Modal a pantalla completa bloquea     │
│                                        │   la visión periférica del feed.        │
│                                        │ • Traspaso de turno manual y lento.     │
└────────────────────────────────────────┴─────────────────────────────────────────┘
```

---

## 3. Eje 1: Ergonomía Visual y Modos de Iluminación

### 1.1 Modo Turno de Noche (Dark / High-Contrast Mode)
* **Problema:** El fondo blanco cálido (`#F5F3F0`) produce deslumbramiento tras horas continuadas de supervisión en salas de guardia oscurecidas.
* **Solución Técnica:**
  - Selector conmutador en la cabecera: `☀️ Día / 🌙 Noche / ⚙️ Auto (según SO)`.
  - Atributo en el elemento raíz: `<html data-theme="dark">`.
  - Tokens específicos para modo oscuro:
    - Fondo de aplicación: `#0F0E0D` (grafito carbón cálido).
    - Superficies de tarjetas: `#1C1917` (antracita profundo).
    - Bordes: `#2E2A27` / `#3E3834`.
    - Textos principales: `#FAF8F5` / `#D6D0C5`.
    - Naranja Orange: `#FF7900` (con contraste ajustado para cumplir WCAG 2.1 AA > 4.5:1).
    - Badges de alerta: Rojo SL1 (`#EF4444`) sobre fondo translúcido (`rgba(239, 68, 68, 0.2)`).
  - Persistencia de la preferencia en `localStorage.getItem('theme_preference')`.

### 1.2 Selector de Densidad Visual (Compacta vs. Detallada)
* **Problema:** En picos de degradación con más de 10 incidencias activas, el scroll vertical extenso dificulta la priorización global.
* **Solución Técnica:**
  - Botón selector en la barra de herramientas: `[ ≡ Vista Compacta ] [ ☲ Vista Detallada ]`.
  - **Vista Compacta (Tabular Ultra-Rápida):** Fila de 44px de altura por ticket. Muestra únicamente ID con link, Proceso Crítico, Severidad nominal vs ITIL, Aging y botón de apertura rápida.
  - **Vista Detallada (Tarjetas Actuales):** Muestra el desglose de reglas aplicadas, justificación de impacto y extracto de ticket.

---

## 4. Eje 2: Navegación de Alta Velocidad por Teclado (*Keyboard-First*)

Los operadores de emergencias trabajan de forma significativamente más ágil cuando pueden interactuar sin retirar las manos del teclado.

### 4.1 Tabla de Atajos Operativos
| Atajo | Contexto | Acción Operativa | Beneficio UX |
| :---: | :--- | :--- | :--- |
| `J` | Feed principal | Mover selección activa a la **siguiente incidencia** | Navegación secuencial rápida |
| `K` | Feed principal | Mover selección activa a la **incidencia anterior** | Navegación secuencial rápida |
| `Enter` u `O` | Incidencia activa | **Abrir Orquestador (Módulo 2)** del ticket enfocado | Apertura en < 1 segundo |
| `C` | Incidencia activa | **Copiar texto formal Remedy** al portapapeles | Reclasificación en 1 tecla |
| `M` | Global | Abrir **Centro de Comunicaciones & Matrices** (Módulo 3) | Consulta de guardias N2/N3 |
| `P` | Incidencia activa | Abrir **Generador de Plantillas Dinámicas** | Emisión de comunicado 20m |
| `/` | Global | **Enfocar el campo de búsqueda** de incidencias | Filtrado instantáneo |
| `1` - `4` | Global | Conmutar entre pestañas (`1`=Discrepancias, `2`=Críticas...) | Cambio de vista sin ratón |
| `Esc` | Modales | **Cerrar** el modal o diálogo activo | Despeje inmediato de pantalla |
| `?` | Global | Mostrar **Chuleta de Atajos de Teclado** en pantalla | Descubrimiento y aprendizaje |

### 4.2 Requisitos de Accesibilidad (A11y)
- Anillo de foco de alto contraste (`outline: 3px solid #FF7900; outline-offset: 2px;`) en el elemento seleccionado por teclado.
- Foco atrapado (*Focus Trap*) dentro de los modales abiertos para que el tabulador no escape al fondo inactivo.

---

## 5. Eje 3: Continuidad Operativa y UX Defensiva

### 5.1 Persistencia de Borradores en LocalStorage (Zero-Data-Loss)
* **Riesgo:** Si un operador redacta una anotación extensa en la bitácora o adapta una notificación ejecutiva y la ventana se recarga o se cierra involuntariamente, se produce pérdida de información crítica.
* **Solución Técnica:**
  - En cada pulsación de tecla (`input`), guardar el estado en `localStorage`:
    - Bitácora: `triage_draft_log_${incId}`
    - Versión Completa 90 pal.: `triage_draft_exec_${incId}`
    - Versión Breve SMS: `triage_draft_sms_${incId}`
  - Al abrir el modal, si existe borrador, restaurarlo automáticamente y mostrar un aviso sutil:
    `ℹ️ Borrador recuperado automáticamente · [Descartar borrador]`
  - Al confirmar la acción ("Añadir a Bitácora" o "Copiar y Registrar"), limpiar la clave de `localStorage`.

### 5.2 Confirmación Consciente para Acciones Destructivas
* **Orden de Rollback (Módulo 2):**
  - Para evitar clics accidentales, el botón *"Confirmar Ejecución de Rollback"* permanecerá bloqueado hasta que el operador marque dos casillas obligatorias:
    1. `[ ] Confirmo que el Rollback ha sido consensuado con el SDM del proveedor.`
    2. `[ ] Se ha verificado que la ventana PaP sigue abierta y el procedimiento es reversible.`
* **Deshacer Borrado en Bitácora (Undo Toast):**
  - Al eliminar una entrada de la bitácora, mostrar un toast de 6 segundos: *"Entrada eliminada · [Deshacer]"*.

### 5.3 Modo Split-View / Drawer Lateral para el Orquestador
* **Problema:** El modal actual (`.orch-modal-dialog`) tapa el 100% del fondo, impidiendo que el Incident Manager supervise si aparece una nueva incidencia crítica mientras está en War Room.
* **Solución Técnica:**
  - Añadir botón de alternancia en la cabecera del modal: `[ ◨ Fijar en Panel Lateral ]`.
  - En modo drawer, la pantalla se divide al 50%:
    - **Izquierda (50%):** Feed de incidencias y KPIs en vivo actualizándose automáticamente.
    - **Derecha (50%):** Orquestador con cronómetros, War Room y bitácora interactiva en seguimiento continuo.

---

## 6. Eje 4: Ergonomía Sensorial y Alertas Perceptivas

### 6.1 Alertas Sonoras No Estridentes (Audio Earcons Opcionales)
* **Justificación:** En salas de crisis, los operadores suelen tener múltiples monitores y teléfonos. Una alerta auditiva sutil evita la pérdida de ventanas críticas.
* **Especificación Acústica:**
  - Conmutador en cabecera: `[ 🔊 Audio Activado / 🔇 Silenciado ]` (silenciado por defecto para respetar accesibilidad).
  - **Tono A (Ingreso de nueva SL1 con discrepancia):** Doble pulso de frecuencia media (880 Hz / 1046 Hz), volumen moderado (≤ 45 dB).
  - **Tono B (Alarma de 45 min / 105 min):** Pulso grave de advertencia repetido 2 veces con intervalo de 5 segundos.
  - Generación nativa con la API Web Audio (`AudioContext`), sin requerir carga de archivos MP3 externos.

### 6.2 Indicador Dinámico en Título de Pestaña (*Favicon & Title Notification*)
* Si el operador cambia de pestaña del navegador, el título debe reflejar la urgencia:
  - Sin alertas: `Consola de Triaje · Orange Tech Ops`
  - Con SL1 activa: `(🚨 1 SL1) INC000004171670 · Consola Orange`
  - Cronómetro a punto de expirar (< 5 min para los 45m): `(⏱️ 41m / 45m) ¡Escalado Inminente! · Consola Orange`
  - Favicon dinámico: Punto rojo parpadeante cuando haya alarmas críticas activas.

---

## 7. Eje 5: Eficiencia en el Traspaso de Turno (*Shift Handover*)

### 7.1 Generador de Informe de Traspaso en 1 Clic
* **Problema:** Al finalizar una guardia, el operador invierte entre 20 y 30 minutos recopilando el estado de los tickets para el relevo.
* **Solución Técnica:**
  - Botón en cabecera o footer: `[ 📋 Traspaso de Guardia ]`.
  - Genera automáticamente en el portapapeles una plantilla formal estructurada:

```markdown
# 📋 INFORME DE TRASPASO DE GUARDIA · INCIDENT MANAGEMENT ORANGE
**Fecha/Hora:** 01/11/2026 07:00 | **Turno:** Noche ➔ Mañana | **Operador Saliente:** IM-CSO

## 1. Incidencias SL1 / P1 Activas (01)
* **INC000004171670:** Fallo de Aprovisionamiento Fibra B2C / GDU
  - **Estado Relojes:** 45m [Vencido - Escalado a N2 Sopra] | 105m [En curso - 62m restantes]
  - **War Room:** Activa en Teams (Cuórum 3/3 completado)
  - **Cambios PaP:** CHG000000889120 revisado (En observación, rollback pendiente de validación)
  - **Último hito bitácora:** "Se reinicia pool de pods de aprovisionamiento en cluster OCI"

## 2. Discrepancias Pendientes de Reclasificación (02)
* INC000004189001: Clasificado P3 en Remedy ➔ Propuesta SL2/P2 por fallo Middleware Transversal.
* INC000004192230: Clasificado P2 en Remedy ➔ Propuesta SL1/P1 por caída de pasarela Redsýs.

## 3. Workarounds en Seguimiento con IM-CSO
* INC000004165500: Reinicio de gateway realizado; pendiente monitorizar métricas 30m para desescalar.
```

### 7.2 Fijación de Incidencia Prioritaria (Pinning / Star)
* Capacidad de marcar cualquier ticket con un icono de chincheta o estrella (📌 / ⭐).
* El ticket fijado se mantiene anclado permanentemente en la primera posición del feed, con un borde destacado anaranjado, sin importar los filtros de proceso que se apliquen.

---

## 8. Métricas de Usabilidad y Medición del Rendimiento

Para validar cuantitativamente la eficacia de este plan tras su despliegue, se auditarán cuatro métricas clave:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              MÉTRICAS DE RENDIMIENTO OPERATIVO                         │
├──────────────────────────┬───────────────────┬───────────────────┬─────────────────────┤
│ Indicador (KPI)          │ Situación Base    │ Objetivo Post-Plan│ Método de Medición  │
├──────────────────────────┼───────────────────┼───────────────────┼─────────────────────┤
│ Tiempo de Reclasificación│ ~45 segundos      │ < 10 segundos     │ Telemetría interna  │
│ Remedy (Time-to-Triage)  │ (3 clics y copia) │ (Atajo 'C' / 'O') │ en eventos DOM      │
├──────────────────────────┼───────────────────┼───────────────────┼─────────────────────┤
│ Tiempo de Convocatoria   │ ~3 minutos        │ < 45 segundos     │ Bitácora auditable  │
│ War Room y Comms 20m     │                   │                   │ del ticket          │
├──────────────────────────┼───────────────────┼───────────────────┼─────────────────────┤
│ Pérdida de Borradores    │ Casos puntuales   │ 0 pérdidas        │ Logs locales        │
│ por Cierre Involuntario  │ reportados        │ (100% guardado)   │ LocalStorage        │
├──────────────────────────┼───────────────────┼───────────────────┼─────────────────────┤
│ Escala de Usabilidad del │ ~72 / 100         │ > 88 / 100        │ Cuestionario SUS    │
│ Sistema (SUS)            │ (Aceptable)       │ (Excelente / A+)  │ a 10 operadores IM  │
└──────────────────────────┴───────────────────┴───────────────────┴─────────────────────┘
```

---

## 9. Backlog de Ejecución Priorizado (Matriz Esfuerzo vs. Impacto)

Este backlog está diseñado en forma de lista de verificación (*Checklist*) para ir abordando las propuestas de manera modular e incremental:

### 🚀 Sprint 1: Quick-Wins de Inmediato Impacto (Bajo Esfuerzo / Alto Retorno)
- [ ] **US-01:** Implementar motor de atajos de teclado básicos (`J`/`K` para feed, `C` para copiar Remedy, `/` para buscador, `Esc` para modales).
- [ ] **US-02:** Diseñar e integrar el modal de chuleta de atajos de teclado al pulsar la tecla `?`.
- [ ] **US-03:** Implementar auto-guardado en `localStorage` para el formulario de bitácora y los editores de plantillas ejecutivas.
- [ ] **US-04:** Añadir botón de generación y copiado de "Informe de Traspaso de Guardia" en la cabecera/footer.
- [ ] **US-05:** Añadir notificación dinámica en el título de la pestaña (`document.title`) ante alertas críticas de tiempo.

### 🎨 Sprint 2: Ergonomía Visual y Modos de Iluminación (Medio Esfuerzo / Alto Retorno)
- [ ] **US-06:** Crear tokens CSS y lógica del **Modo Turno de Noche (Dark Mode)** con selector manual y detección automática de sistema.
- [ ] **US-07:** Implementar selector de densidad: **Vista Compacta (Tabular)** vs **Vista Detallada (Tarjetas)**.
- [ ] **US-08:** Añadir sistema de alertas acústicas opcionales (*Audio Earcons*) con Web Audio API para nuevas SL1 y alertas de 45m/105m.
- [ ] **US-09:** Añadir funcionalidad de "Fijar Ticket Prioritario" (Pin/Star) en la cabecera del feed.

### 🛡️ Sprint 3: Arquitectura Avanzada y UX Defensiva (Mayor Complejidad)
- [ ] **US-10:** Implementar modo **Split-View / Drawer lateral** para el Orquestador Operativo, permitiendo supervisión dual sin ocluir el feed.
- [ ] **US-11:** Añadir confirmación reforzada de 2 pasos para la orden de Rollback en el monitor PaP.
- [ ] **US-12:** Implementar toast con opción de "Deshacer" (Undo Toast de 6 segundos) tras eliminar anotaciones de la bitácora.
- [ ] **US-13:** Realizar auditoría de accesibilidad completa (WCAG 2.1 AA) con navegación 100% por lector de pantalla y tabulación ciega.

---

*Documento técnico elaborado y aprobado para la hoja de ruta evolutiva de la Consola de Emergencias IT Orange.*  
*Customer & Service Operations (CSO) · MasOrange Tech Operations.*

