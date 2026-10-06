# Feature Specification: Informe Ejecutivo de Incidencias Postmortem (010-incident-executive-report)

**Feature Branch**: `010-incident-executive-report`

**Created**: 2026-10-06

**Status**: Ready for Planning

**Input**: User description: "Quiero construir un informe ejecutivo de incidencias con un formato que te daré. Como fuente de datos te daré un enlace a confluence donde se detalla la informacion de postmortem de la incidenica. Actualment tenemos un dashboard de "Gestion de Problemas" donde existe una tabla de Postmortem candidatos a solicitar el informe bajo demanda."

**Reference Template**: `20260609 Incidencia IVR ExMM.pptx` (Presentación ejecutiva corporativa de 3 diapositivas: Resumen/Impacto/Causa/Solución/Puntos de Acción + Cronología de Hitos).

---

## Clarifications Resolved

### Q1: Formato de Salida del Informe Ejecutivo
- **Decisión**: **Opción A (PowerPoint `.pptx`)**.
- **Detalle**: El informe se generará como archivo descargable Microsoft PowerPoint (`.pptx`), replicando con fidelidad la estructura, diseño corporativo Orange y distribución de la plantilla de referencia `20260609 Incidencia IVR ExMM.pptx`.

### Q2: Método de Acceso e Ingesta de Confluence
- **Decisión**: **Opción B (Modal Interactivo con Sesión/URL)**.
- **Detalle**: Se dispondrá de un diálogo interactivo en el dashboard donde el usuario visualiza, confirma o introduce la URL de Confluence del postmortem (precargada automáticamente si la incidencia ya dispone de enlace registrado `wikiPage`). La extracción se apoya en la sesión de navegación del operador en Orange, informando con claridad si la página no es accesible o requiere autenticación.

### Q3: Punto de Integración en el Panel de "Gestión de Problemas"
- **Decisión**: **Opción A (Botón por Fila en la Tabla de Candidatos)**.
- **Detalle**: En la pestaña de *Postmortems* del dashboard de Gestión de Problemas (`IssuesTable.tsx`), se añade una acción dedicada por fila ("Generar Informe"). Si el informe ya fue generado previamente, el botón permite la "Descarga Directa" inmediata del `.pptx` y ofrece una opción secundaria para "Regenerar" si la página de Confluence ha cambiado.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Solicitud y Descarga del Informe Ejecutivo desde Gestión de Problemas (Priority: P1) 🎯 MVP

Como gestor de incidencias o responsable de operaciones de Orange, quiero solicitar la generación de un informe ejecutivo bajo demanda para una incidencia candidata a postmortem desde la tabla del dashboard de Gestión de Problemas, indicando o confirmando su enlace a Confluence, para descargar automáticamente una presentación ejecutiva estandarizada en PowerPoint (`.pptx`).

**Why this priority**: Es el flujo central de valor que ahorra horas de redacción y maquetación manual para los comités de dirección tras una incidencia crítica.

**Independent Test**: Acceder a la tabla de candidatos a postmortem en Gestión de Problemas, hacer clic en "Generar Informe Ejecutivo" sobre una incidencia, confirmar el enlace a Confluence del postmortem y descargar la presentación `.pptx` con los datos sintetizados y estructurados.

**Acceptance Scenarios**:

1. **Given** una incidencia candidata en la tabla de Gestión de Problemas con enlace a Confluence disponible (`wikiPage`), **When** el usuario hace clic en "Generar Informe", **Then** el sistema procesa el postmortem de Confluence y genera el informe ejecutivo en formato `.pptx` con cabecera corporativa, metadatos temporales, bloques de impacto, causa y solución, tabla de puntos de acción y tabla cronológica de hitos.
2. **Given** una incidencia candidata que aún no tiene enlace de Confluence registrado en el sistema, **When** el usuario pulsa solicitar informe, **Then** se despliega un diálogo interactivo donde puede pegar la URL de Confluence correspondiente para procesarla.

---

### User Story 2 - Ingesta Estructurada y Resiliente desde Confluence (Priority: P2)

Como gestor de problemas, quiero que el sistema extraiga de forma robusta las secciones y tablas clave de la página de postmortem de Confluence, mapeando la información en los bloques correspondientes de la presentación ejecutiva aunque la página contenga variaciones menores de maquetación.

**Why this priority**: Confluence es una fuente viva donde los operadores rellenan tablas y textos con pequeñas discrepancias de formato. El sistema debe ser tolerante y extraer fielmente: inicio, fin/duración, impacto, causa raíz, solución, puntos de acción (Pain Point, Descripción, Owner, Forecast) y cronología de eventos.

**Independent Test**: Probar con páginas de postmortem de Confluence que contengan tablas de cronología y acciones con distintas longitudes y verificar que el contenido se distribuye limpiamente entre las diapositivas de la presentación.

**Acceptance Scenarios**:

1. **Given** una página de Confluence con tabla cronológica que supera las 18-20 filas, **When** se genera el informe, **Then** el sistema pagina adecuadamente los eventos en diapositivas consecutivas (Diapositiva 2 y 3) manteniendo el encabezado y legibilidad.
2. **Given** una URL de Confluence inaccesible o no válida, **When** se solicita la generación, **Then** el sistema muestra un mensaje de advertencia descriptivo en menos de 3 segundos sin colapsar la interfaz.

---

### User Story 3 - Consulta Rápida y Reutilización de Informes Generados (Priority: P3)

Como operador o miembro del comité, quiero consultar si una incidencia candidata ya cuenta con un informe ejecutivo generado previamente para descargarlo de inmediato sin recalcular, o solicitar una regeneración forzada si el postmortem en Confluence fue actualizado con nuevas acciones.

**Why this priority**: Reduce los tiempos de espera a 0 ms para informes ya elaborados y evita saturar la red interna con peticiones redundantes.

**Independent Test**: Solicitar el informe de una incidencia, verificar que en la tabla de Gestión de Problemas queda marcado como "Informe Disponible" con la fecha de generación, descargarlo de inmediato y validar que existe un botón de "Regenerar" para forzar la actualización.

**Acceptance Scenarios**:

1. **Given** una incidencia con informe ya generado, **When** el usuario hace clic en "Descargar Informe", **Then** la descarga comienza de inmediato utilizando la versión archivada.
2. **Given** un informe existente cuyo postmortem ha recibido actualizaciones en Confluence, **When** el usuario pulsa "Regenerar Informe", **Then** el sistema vuelve a consultar Confluence y sobrescribe la versión archivada con los nuevos datos.

---

## Edge Cases

- **Postmortem en Confluence muy extenso**: Si la cronología tiene más de 40 eventos, el informe debe paginar ordenadamente en diapositivas adicionales sin solapar textos ni deformar tablas.
- **Acciones sin Owner o Forecast**: Si la tabla de acciones de Confluence no tiene asignado responsable o fecha estimada, debe mostrarse como pendiente (`—`) sin fallar la generación.
- **Páginas restringidas o privadas en Confluence**: El diálogo interactivo debe informar con claridad de la falta de permisos de acceso o sesión activa.
- **Caracteres especiales y codificación**: Símbolos matemáticos, flechas ($\rightarrow$, $\leftrightarrow$) y acentos deben renderizarse sin fallos de codificación en el documento final `.pptx`.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE ofrecer un botón de acción interactivo ("Generar Informe") por fila en la tabla de candidatos a postmortem del dashboard de Gestión de Problemas.
- **FR-002**: El sistema DEBE admitir como fuente de datos una URL de Confluence, precargándola si existe en la incidencia (`wikiPage.url`) o permitiendo introducirla en un diálogo interactivo.
- **FR-003**: El sistema DEBE extraer del postmortem de Confluence: identificador de la incidencia / TT, título, fecha/hora de inicio, duración, descripción del impacto, causa raíz técnica, solución aplicada, tabla de puntos de acción relevantes y tabla cronológica de eventos.
- **FR-004**: El sistema DEBE generar una presentación ejecutiva descargable en formato PowerPoint (`.pptx`) respetando la plantilla corporativa Orange y la distribución establecida en la plantilla de referencia (`20260609 Incidencia IVR ExMM.pptx`):
  - *Diapositiva 1*: Resumen ejecutivo, impacto, causa, solución y tabla de puntos de acción relevantes (Pain Point, Description, Owner, Forecast).
  - *Diapositivas 2 y 3 (o siguientes)*: Cronología detallada de hitos y eventos con tabla formateada (Hora | Evento).
- **FR-005**: El sistema DEBE permitir la descarga directa del archivo `.pptx` generado en el navegador del usuario.
- **FR-006**: El sistema DEBE almacenar los informes generados para permitir su descarga inmediata posterior.
- **FR-007**: El sistema DEBE incluir opción de regeneración forzada para incidencias cuyo postmortem haya sido modificado con posterioridad.
- **FR-008**: El sistema DEBE ofrecer retroalimentación de estado accesible durante el tiempo de generación y reportar errores claros si la URL de Confluence no es accesible.

---

### Key Entities *(include if feature involves data)*

- **Incidencia Candidata a Postmortem**: Código Remedy/TT, descripción breve, fecha de apertura/resolución, criticidad, URL de Confluence (`wikiPage`) y estado del informe ejecutivo.
- **Postmortem en Confluence**: URL, metadatos temporales, síntesis de impacto, causa raíz, solución técnica, listado estructurado de puntos de acción (Pain Point, Description, Owner, Forecast) y registro cronológico de eventos (Hora, Hito/Acción).
- **Informe Ejecutivo de Incidencia**: Archivo de presentación (`.pptx`), metadatos de generación (fecha, incidencia asociada, usuario/origen) y ruta de descarga.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: La generación del informe ejecutivo a partir del enlace de Confluence se completa en menos de 15 segundos.
- **SC-002**: La presentación generada conserva el 100% de la fidelidad visual, tipografía y estructura corporativa de la plantilla de referencia `20260609 Incidencia IVR ExMM.pptx`.
- **SC-003**: Se eliminan por completo las tareas manuales de transcripción y maquetación en PowerPoint para el equipo de gestión de problemas.
- **SC-004**: La descarga de un informe previamente generado se inicia en menos de 1 segundo (respuesta inmediata en caché/almacenamiento).

---

## Assumptions

- La plantilla de referencia para el informe ejecutivo es el archivo `20260609 Incidencia IVR ExMM.pptx` presente en la raíz del repositorio.
- Las páginas de postmortem en Confluence siguen una estructura reconocible con secciones de impacto, causa, solución, puntos de acción y cronología.
- El panel de Gestión de Problemas (`gestion-problemas-dashboard`) se comunica con el servicio de generación para solicitar y recibir el archivo `.pptx`.
