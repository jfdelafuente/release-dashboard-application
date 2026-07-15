# Feature Specification: Dashboards por Release

**Feature Branch**: `007-per-release-dashboards`

**Created**: 2026-07-15

**Status**: Draft

**Input**: User description: "construye una aplicacion que me permita organizar las release en dashboard separados. Cada uno de esos dashboard debera tener el nombre que se le de a la Release y mostrará informacion que ahora se muestra en el dashboard/postmortem."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ver el dashboard de una release concreta (Priority: P1)

Como responsable de operaciones, quiero abrir un dashboard dedicado a una release concreta, identificado por su nombre, para revisar sus KPIs de postmortem, su evolución temporal y sus incidencias sin que se mezclen con las de otras releases.

**Why this priority**: Es el valor central de la funcionalidad — sin esto no hay "dashboards separados por release", solo el dashboard combinado actual.

**Independent Test**: Con datos de postmortem de al menos una release ya cargados, se puede abrir su dashboard dedicado y comprobar que todos los datos mostrados (KPIs, gráficas, tabla) pertenecen únicamente a esa release.

**Acceptance Scenarios**:

1. **Given** existen datos de postmortem cargados para la release "2026R4", **When** el usuario abre el dashboard de esa release, **Then** ve el nombre "2026R4" como identificador del dashboard y solo incidencias de esa release en KPIs, gráficas y tabla.
2. **Given** existen datos cargados para dos releases distintas ("2026R4" y "2026R6"), **When** el usuario abre el dashboard de "2026R6", **Then** no ve ninguna incidencia perteneciente a "2026R4".

---

### User Story 2 - Encontrar y navegar entre dashboards de distintas releases (Priority: P2)

Como responsable de operaciones, quiero acceder al dashboard de una release concreta haciendo clic en su nombre desde la tabla de releases que ya existe en el dashboard de KPIs de Release, sin necesidad de conocer de antemano su URL.

**Why this priority**: Sin un punto de acceso central, los dashboards por release solo son accesibles conociendo su enlace exacto, lo que limita mucho el valor de la funcionalidad para el día a día.

**Independent Test**: Con dos o más releases cargadas, se puede visitar `dashboards/release-kpis/`, localizar una release en la columna "RELEASE" de su tabla y, con un único clic, llegar al dashboard de postmortem de esa release.

**Acceptance Scenarios**:

1. **Given** hay 3 releases con datos de postmortem cargados y visibles en la tabla de `dashboards/release-kpis/`, **When** el usuario hace clic en el nombre de una de ellas en la columna "RELEASE", **Then** se abre el dashboard de postmortem de esa release concreta.
2. **Given** una release aparece en la tabla de `dashboards/release-kpis/` pero todavía no tiene datos de postmortem cargados, **When** el usuario hace clic en su nombre, **Then** ve un estado vacío claro (sin errores) indicando que esa release aún no tiene datos de postmortem.

---

### User Story 3 - Dar nombre a una release al cargar sus datos (Priority: P3)

Como responsable de operaciones, quiero asociar un nombre de release reconocible a los datos de postmortem que cargo, para que el dashboard resultante quede identificado con claridad de cara al futuro.

**Why this priority**: Es necesaria para que las historias 1 y 2 tengan un nombre de calidad que mostrar, pero el sistema puede funcionar con un nombre por defecto razonable mientras se decide el mecanismo exacto, por lo que tiene menor prioridad que poder ver y navegar los dashboards.

**Independent Test**: Se puede cargar un nuevo conjunto de datos de postmortem, indicar o comprobar el nombre de la release asociado, y verificar que ese nombre es el que aparece en su dashboard y en el listado central.

**Acceptance Scenarios**:

1. **Given** el usuario está cargando un nuevo CSV de postmortem, **When** completa el proceso de carga, **Then** el sistema asocia un nombre de release identificable a esos datos, sin que queden como "sin nombre".

---

### Edge Cases

- ¿Qué ocurre si dos releases distintas terminan con el mismo nombre o un nombre muy parecido?
- ¿Qué ocurre si se abre el dashboard de una release que no existe o fue eliminada?
- ¿Qué ocurre si una release no tiene ninguna incidencia registrada (CSV vacío o sin filas válidas)?
- ¿Qué ocurre si el nombre de release introducido al subir el CSV no coincide con ninguna de las releases de la tabla de `dashboards/release-kpis/` (por ejemplo, por una errata)?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE permitir abrir un dashboard dedicado a una única release, mostrando exclusivamente los datos de postmortem de esa release.
- **FR-002**: Cada dashboard de release DEBE mostrar el nombre de la release como identificador principal (título/cabecera).
- **FR-003**: Cada dashboard de release DEBE mostrar la misma información que hoy ofrece el dashboard de Postmortem/Release: KPIs (total, % cerradas, % resueltas PaP, % resueltas Mesa), gráfica temporal de entradas/resoluciones/backlog, distribución por sistema y por estado, y tabla de incidencias filtrable y ordenable.
- **FR-004**: El sistema DEBE convertir el nombre de cada release en la columna "RELEASE" de la tabla de `dashboards/release-kpis/` en un enlace que abra el dashboard de postmortem de esa release, reutilizando ese dashboard existente como punto de acceso central (no se crea un listado nuevo ni un selector adicional).
- **FR-005**: El sistema DEBE pedir al usuario el nombre de la release como parte del proceso de carga de un CSV de postmortem (no se deriva automáticamente del nombre de archivo). Ese nombre DEBE coincidir con el nombre de release ya usado en `dashboards/release-kpis/` (columna "RELEASE") para que el enlace de la Historia 2 encuentre el dashboard correcto.
- **FR-006**: El sistema DEBE sustituir el dashboard de Postmortem/Release combinado (todas las releases juntas) por los dashboards individuales por release; deja de existir una vista única que las mezcle todas.
- **FR-007**: El sistema DEBE permitir cargar nuevos datos de postmortem para una release, igual que hoy permite cargar un CSV de postmortem, asociando esos datos a un nombre de release.
- **FR-008**: El sistema DEBE soportar un número creciente de releases a lo largo del tiempo, según se van cargando nuevos datos de postmortem.
- **FR-009**: El sistema DEBE impedir que los datos de una release aparezcan en el dashboard de otra release distinta.
- **FR-010**: El sistema DEBE mostrar un estado vacío claro (sin errores) cuando todavía no se ha cargado ninguna release, y también cuando se hace clic en una release de la tabla de `dashboards/release-kpis/` que todavía no tiene datos de postmortem asociados.
- **FR-011**: El sistema DEBE avisar al usuario si el nombre de release introducido al subir un CSV no coincide con ninguna de las releases conocidas en `dashboards/release-kpis/`, para evitar dashboards huérfanos que no se puedan alcanzar desde ningún enlace.

### Key Entities *(include if feature involves data)*

- **Release**: agrupación de datos de postmortem identificada por un nombre. Tiene asociado un conjunto de incidencias de postmortem y unos KPIs calculados sobre ellas, y un dashboard propio.
- **Incidencia de Postmortem** *(entidad ya existente)*: pertenece exactamente a una Release; conserva los mismos atributos que usa hoy el dashboard de Postmortem/Release (estado, urgencia, impacto, despliegue PAP/MESA, fechas, sistema asignado).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un usuario puede abrir el dashboard de cualquier release existente y confirmar visualmente que el 100% de los datos mostrados pertenecen a esa release, con un único clic desde la tabla de `dashboards/release-kpis/`.
- **SC-002**: Un usuario puede localizar y abrir el dashboard de una release concreta de entre las más de 40 releases ya listadas en `dashboards/release-kpis/` sin necesidad de conocer su URL de antemano.
- **SC-003**: El dashboard de una release recién cargada está disponible y navegable desde la tabla de `dashboards/release-kpis/` sin pasos manuales adicionales una vez completada la carga del CSV (más allá de indicar el nombre de la release al subirlo).
- **SC-004**: El 100% de los KPIs, gráficas y funcionalidad de tabla disponibles hoy en el dashboard de Postmortem/Release siguen disponibles en cada dashboard por release, sin pérdida de funcionalidad.

## Assumptions

- Cada carga de CSV de postmortem corresponde a una única release (no hace falta dividir un mismo archivo cargado en varias releases distintas).
- El desglose por Despliegue (PAP/MESA) que ya existe dentro de los datos de postmortem se mantiene como una dimensión dentro del dashboard de cada release, no como una release distinta.
- Se reutiliza la tubería de conversión y almacenamiento de datos ya existente (`data/output/*-postmortem.json`); el cambio es principalmente en cómo se organizan y presentan esos datos por release, no en cómo se generan.
- No cambia el modelo de acceso/autenticación: mismo acceso abierto de hoy (red interna/VPN), sin login por release.
- El número de releases a listar en el punto de acceso central no tiene un límite superior definido de antemano; se espera un crecimiento moderado a lo largo del tiempo (del orden de decenas, no miles).
