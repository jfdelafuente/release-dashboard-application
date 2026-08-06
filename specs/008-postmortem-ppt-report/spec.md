# Feature Specification: Informe PPT de Postmortem por Release

**Feature Branch**: `008-postmortem-ppt-report`

**Created**: 2026-08-04

**Status**: Draft

**Input**: User description: "crear un informe de postmortem para cada Release en formato ppt siguiendo el estilo del dashboard de postmortem. Debe incluir las gráficas que se muestra en release-kpis de forma general y los kpis que se muetran en el dashboard de postmortem para cada Release"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Generar el informe PPT de una release (Priority: P1)

Como responsable de operaciones, quiero generar un informe en formato PowerPoint (.pptx) para una release concreta, con el mismo estilo visual del dashboard de postmortem (colores, tipografía, tarjetas de KPI), para poder compartirlo con stakeholders que no tienen acceso o no van a entrar al dashboard web.

**Why this priority**: Es el valor central de la funcionalidad — sin esto no existe "informe de postmortem en PPT", solo el dashboard interactivo actual.

**Independent Test**: Con datos de postmortem ya cargados para una release concreta, se puede generar su informe y comprobar que el .pptx resultante se abre correctamente y contiene los KPIs de esa release.

**Acceptance Scenarios**:

1. **Given** existen datos de postmortem cargados para la release "2026R7", **When** el usuario solicita el informe PPT de esa release, **Then** se genera un fichero .pptx descargable que se abre sin errores en PowerPoint/LibreOffice/Google Slides.
2. **Given** el informe se ha generado para "2026R7", **When** se revisa su contenido, **Then** los KPIs mostrados (Total Incidencias, Total Pendientes, % Cerradas, Tiempo Medio de Resolución, % Resueltas PaP, Pendientes PaP, % Resueltas Mesa, Pendientes Mesa) coinciden con los valores que muestra el dashboard de postmortem para esa misma release en el momento de generar el informe.
3. **Given** dos releases distintas con datos cargados, **When** se genera el informe de cada una por separado, **Then** cada .pptx contiene únicamente los KPIs y datos de su propia release, sin mezclarse.

---

### User Story 2 - Incluir el contexto comparativo de release-kpis (Priority: P2)

Como responsable de operaciones, quiero que el informe incluya las gráficas generales del dashboard de KPIs de Release (comparativa de incidencias por release y de % de resolución PaP / 1ª semana entre releases), para que quien lea el informe entienda cómo se sitúa esta release frente a las anteriores, no solo sus cifras aisladas.

**Why this priority**: Aporta el contexto histórico que distingue a este informe de un simple volcado de KPIs; sin esto el informe pierde parte de su valor como "postmortem", pero el informe ya es útil sin esta sección (por eso es P2 y no P1).

**Independent Test**: Se genera el informe de una release con al menos otras dos releases ya cargadas en el sistema, y se comprueba que las diapositivas de contexto muestran datos de todas las releases disponibles (no solo la seleccionada), igual que se ven "de forma general" en el dashboard de KPIs de Release.

**Acceptance Scenarios**:

1. **Given** existen datos de KPIs de release para varias releases, **When** se genera el informe de una de ellas, **Then** el informe incluye la gráfica comparativa "Incidencias por release" con todas las releases disponibles, no solo la seleccionada.
2. **Given** el mismo escenario, **When** se revisa el informe, **Then** incluye también las gráficas comparativas de % de resolución PaP y % de resolución 1ª semana entre releases.

---

### User Story 3 - Generar informes para todas las releases de una vez (Priority: P3)

Como responsable de operaciones, quiero poder generar los informes de todas las releases con datos disponibles en una sola acción, para no tener que repetir el proceso release por release cuando necesito prepararlos todos (p. ej. para un cierre trimestral).

**Why this priority**: Es una mejora de comodidad sobre la User Story 1; el valor principal (poder generar el informe de una release) ya se cubre sin esto.

**Independent Test**: Con datos cargados para varias releases, se solicita la generación masiva y se comprueba que se obtiene un informe por cada release con datos disponibles, cada uno correcto de forma independiente.

**Acceptance Scenarios**:

1. **Given** hay 3 releases con datos de postmortem cargados, **When** el usuario solicita generar los informes de todas, **Then** se obtienen 3 ficheros .pptx, uno por release, cada uno con sus propios KPIs.

---

### Edge Cases

- ¿Qué pasa si se solicita el informe de una release que no tiene datos de postmortem cargados? El sistema debe informar claramente de que no hay datos, sin generar un informe vacío o con valores erróneos (p. ej. "0 de 0 incidencias").
- ¿Qué pasa si una release tiene datos de postmortem pero no aparece todavía en el dashboard de KPIs de Release (o viceversa)? El informe debe poder generarse igualmente con la parte de datos disponible, indicando qué sección no pudo completarse en vez de fallar por completo.
- ¿Qué pasa si el nombre de la release contiene caracteres no válidos para un nombre de fichero? El nombre del .pptx generado debe sanearse mantiniendo la release identificable.
- ¿Qué pasa si se pide regenerar el informe de una release para la que ya existe un informe previo? El nuevo informe sustituye o coexiste con el anterior de forma predecible (a definir, ver Assumptions).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE permitir generar un informe en formato .pptx para una release concreta identificada por su nombre, mediante una acción/botón accesible desde los dashboards web (p. ej. junto al nombre de la release en el dashboard de KPIs de Release, y/o en el propio dashboard de postmortem de esa release).
- **FR-002**: El informe DEBE mostrar los mismos 8 KPIs globales que muestra el dashboard de postmortem para esa release: Total Incidencias, Total Pendientes, % Cerradas (con detalle de cuántas de cuántas), Tiempo Medio de Resolución, % Resueltas PaP (con detalle), Total Pendientes PaP, % Resueltas Mesa (con detalle), Total Pendientes Mesa.
- ~~**FR-003**: El informe DEBE incluir también las 4 gráficas propias del dashboard de postmortem para esa release~~ — **eliminado tras la implementación**: el informe final se queda solo con los KPIs (FR-002) y el contexto general de release-kpis (FR-005/FR-006), sin las 4 gráficas propias de postmortem.
- **FR-004**: Los valores de KPI del informe DEBEN calcularse con la misma lógica que ya usa el dashboard de postmortem (mismas reglas de qué cuenta como "pendiente", "resuelta el día del PaP", etc.), para que informe y dashboard nunca muestren cifras distintas para los mismos datos.
- **FR-005**: El informe DEBE incluir la gráfica comparativa "Incidencias por release" del dashboard de KPIs de Release, mostrando el conjunto general de releases (no filtrada a una sola release).
- **FR-006**: El informe DEBE incluir las gráficas comparativas de % de resolución PaP y % de resolución en 1ª semana del dashboard de KPIs de Release, mostrando el conjunto general de releases.
- **FR-007**: El informe DEBE seguir el estilo visual del dashboard de postmortem (paleta de colores MASORANGE/Orange, tipografía, tarjetas de KPI) de forma reconocible, no una plantilla PPT genérica. Existe un informe manual de referencia ("PostMortem-PostProducción 2026R6 - v1.2.1.4.pptx") cuya diagramación (portada + slides de KPIs + slide de notas) inspira la estructura, pero su contenido exacto NO se replica en esta versión — ver Assumptions.
- **FR-008**: El nombre del fichero .pptx generado DEBE identificar inequívocamente la release a la que corresponde.
- **FR-009**: El sistema DEBE informar de forma clara cuando se solicita el informe de una release sin datos de postmortem cargados, sin generar un informe con cifras vacías o erróneas.
- **FR-010**: El sistema DEBE permitir generar el informe para cada release de forma independiente, sin que generar el de una release afecte a los datos o informes de otra.
- **FR-011**: El sistema DEBE permitir generar los informes de todas las releases con datos disponibles mediante una única acción (ver User Story 3).

### Key Entities *(include if feature involves data)*

- **Informe de Release**: Representa el documento .pptx generado para una release concreta. Se deriva de los datos de postmortem ya cargados para esa release y de los datos generales del dashboard de KPIs de Release; no introduce datos nuevos propios, es una vista/exportación de datos existentes en un momento dado.
- **Release**: Ya existente en el sistema (identificada por su nombre, p. ej. "2026R7"); el informe se genera "para" una release y usa sus KPIs de postmortem y su fila/posición en la comparativa general de KPIs de Release.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un usuario puede obtener el informe .pptx de una release con datos ya cargados en menos de 1 minuto desde que lo solicita.
- **SC-002**: El 100% de los KPIs numéricos que aparecen en el informe coinciden exactamente con los que muestra el dashboard de postmortem de esa release en el mismo momento.
- **SC-003**: El informe se puede abrir y visualizar correctamente en las herramientas de presentación habituales (Microsoft PowerPoint, LibreOffice Impress, Google Slides) sin errores de formato ni elementos superpuestos ilegibles.
- **SC-004**: Un usuario que conoce el dashboard de postmortem reconoce el informe como "del mismo sistema" por su estilo visual, sin necesidad de que se le explique.

## Assumptions

- El informe se genera a partir de los datos ya existentes en el sistema (JSON de postmortem por release y datos del dashboard de KPIs de Release) en el momento de la generación; no se recalculan datos históricos ni se re-sube ningún CSV como parte de esta funcionalidad.
- Cada informe corresponde a una única release; no se contempla en esta versión un informe consolidado con el detalle completo de varias releases a la vez (más allá de las gráficas comparativas generales de la User Story 2).
- El informe es un documento de solo lectura pensado para compartir/archivar; no se contempla edición colaborativa ni versionado dentro de la propia herramienta.
- **Fuera de alcance (decisión explícita)**: el informe NO incluye la taxonomía de causa raíz de resolución (RL-Servicio/Elemento Caído, RL-Error en Despliegue, RL-Error de Código, RL-Error Datos Configuración/Parámetros, Cancelado/No Aplica) que aparece en el informe manual de referencia, porque ese dato no existe en el esquema actual de datos de postmortem. Tampoco incluye una comparación numérica explícita contra la release anterior (p. ej. "91 incidencias, +20 respecto a la release previa"). Ambas quedarían para una feature futura aparte si se decide capturar esos datos.
- **Discrepancia detectada, no corregida aquí**: el informe manual de referencia usa un objetivo del 65% para "% resueltas en 1ª semana", mientras que el dashboard de KPIs de Release usa hoy un objetivo único del 75% para ambas gráficas de KPI (PaP y 1ª semana). Este informe PPT reutiliza tal cual las gráficas de `release-kpis` (con su objetivo del 75% actual); corregir esa discrepancia queda fuera del alcance de esta feature.
- Regenerar el informe de una release ya informada sobrescribe el fichero anterior de esa release (mismo criterio de "una versión activa" ya aplicado a `data/output/` para evitar acumulación de ficheros).
