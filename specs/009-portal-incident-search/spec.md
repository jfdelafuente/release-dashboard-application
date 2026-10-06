# Feature Specification: Buscador de Incidencias con Resumen IA en Portal Principal

**Feature Branch**: `009-portal-incident-search`

**Created**: 2026-10-06

**Status**: Draft

**Input**: User description: "Quiero que incluyas en la parte superior de panel del portal principal un buscador de incidencias. En un campo de texto incluirás la incidencias que quieres consultar y botón de consulta. Para ello harás que se hizo para implementar pantalla flotante de resumen IA para incidencias masivas y postmortem"

## Clarifications

### Session 2026-10-06
- Q: ¿Cuál es la denominación corporativa y de marca aplicable al diseño e identidad visual? → A: La compañía se denomina Orange (anteriormente referida como MASORANGE).
- Q: ¿Cuál es la disposición y ubicación exacta del buscador en el portal? → A: Bloque destacado (hero banner / tarjeta) situado en la parte superior del contenido principal, entre la cabecera y la primera fila de plataformas operativas.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Consulta Directa de Incidencia desde el Portal Principal (Priority: P1)

Como operador o responsable de operaciones en el portal principal, quiero disponer de una barra de búsqueda en la parte superior del portal donde introducir el identificador de una incidencia y pulsar un botón de consulta, para acceder de inmediato al resumen ejecutivo generado por inteligencia artificial sin tener que navegar previamente a los paneles de Incidencias Masivas o Postmortem.

**Why this priority**: Es el núcleo de la funcionalidad solicitada. Aporta valor inmediato permitiendo una consulta rápida "ad-hoc" de cualquier incidencia desde la puerta de entrada de la plataforma.

**Independent Test**: Puede probarse de forma independiente accediendo al portal principal, introduciendo un código de incidencia válido (ej. `INC000004141215`), pulsando el botón de consulta y verificando que se despliega la pantalla flotante con el resumen ejecutivo de la IA, el estado de la incidencia, impacto, causa y enlace a la ficha completa en Remedy.

**Acceptance Scenarios**:

1. **Given** que el usuario está en la página del portal principal, **When** introduce un identificador válido de incidencia en la caja de búsqueda y pulsa el botón de consulta (o pulsa la tecla `Enter`), **Then** se abre la pantalla flotante de Resumen IA mostrando el análisis sintetizado correspondiente a dicha incidencia.
2. **Given** que la pantalla flotante de Resumen IA se ha abierto tras la búsqueda, **When** el usuario pulsa el botón de cerrar o la tecla `Escape`, **Then** la pantalla flotante se cierra y el usuario vuelve a ver el portal principal exactamente en el estado en que lo dejó, con el foco listo para una nueva consulta.

---

### User Story 2 - Normalización y Tolerancia en el Formato de Entrada (Priority: P2)

Como usuario que a menudo copia y pega códigos de incidencia desde correos, mensajes de chat o registros externos, quiero que el buscador acepte identificadores con espacios accidentales, en minúsculas o solo numéricos, para no tener que editar manualmente el texto antes de consultar.

**Why this priority**: Evita errores frustrantes de usuario por diferencias tipográficas menores y agiliza las operaciones en momentos de resolución crítica.

**Independent Test**: Puede probarse introduciendo variantes como `  inc000004141215  ` o `4141215` y comprobando que el sistema las interpreta y busca con éxito.

**Acceptance Scenarios**:

1. **Given** que el usuario introduce un código con espacios en blanco al inicio o al final, **When** ejecuta la consulta, **Then** el sistema elimina los espacios automáticamente y realiza la consulta con el identificador limpio.
2. **Given** que el usuario introduce el código en minúsculas (`inc000004141215`), **When** ejecuta la consulta, **Then** el sistema normaliza el texto a mayúsculas y procesa la búsqueda correctamente.
3. **Given** que el usuario introduce únicamente los dígitos numéricos de la incidencia (ej. `4141215`), **When** ejecuta la consulta, **Then** el sistema completa el prefijo estándar de incidencia antes de realizar la petición.

---

### User Story 3 - Validación de Entrada y Respuesta ante Errores (Priority: P3)

Como usuario del portal, quiero recibir una indicación clara y accesible si intento consultar con el campo de texto vacío o si la incidencia no existe, para saber qué corregir sin que la interfaz quede bloqueada.

**Why this priority**: Asegura una experiencia de usuario consistente, robusta y accesible sin fallos silenciosos.

**Independent Test**: Puede probarse pulsando el botón de consulta con el campo vacío o con un identificador inexistente, verificando que se muestra feedback visual informativo.

**Acceptance Scenarios**:

1. **Given** que el campo de búsqueda está vacío, **When** el usuario pulsa el botón de consulta o pulsa `Enter`, **Then** el sistema no dispara la petición de red, resalta visualmente el campo de texto y sitúa el cursor de nuevo en él con un mensaje de aviso.
2. **Given** que se introduce un código de incidencia que no existe o el servicio de síntesis no está disponible, **When** se ejecuta la consulta, **Then** la pantalla flotante muestra un mensaje explicativo informando del problema y ofreciendo la opción de reintentar o abrir la incidencia directamente en la herramienta de origen (Remedy).

---

### Edge Cases

- **Campo con solo espacios en blanco**: El sistema debe tratar cadenas de espacios en blanco como un campo vacío, evitando consultas innecesarias.
- **Códigos con caracteres especiales no válidos**: El sistema debe sanear la entrada y avisar al usuario si el formato no se asemeja a una incidencia válida.
- **Pulsación múltiple o rápida del botón de consulta**: El sistema debe ignorar envíos duplicados mientras una consulta esté en proceso de carga o reutilizar la solicitud en curso.
- **Interrupción o lentitud de red**: El sistema debe mostrar el indicador de carga durante la espera y, en caso de superar el tiempo límite, presentar una opción de reintento.
- **Navegación por teclado y lectores de pantalla**: El buscador y el modal resultante deben poder utilizarse completamente mediante teclado (Tab, Enter, Escape) y anunciar su estado a tecnologías de asistencia.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El portal principal MUST incluir un bloque destacado (hero banner / tarjeta) de búsqueda de incidencias situado en el contenedor principal (`<main>`), ubicado estratégicamente entre la cabecera del portal y la primera fila de plataformas operativas ("Plataformas Operativas y Seguimiento").
- **FR-002**: El buscador MUST contar con un campo de texto con texto de sugerencia (placeholder) descriptivo y un botón de acción con icono y texto claro para consultar.
- **FR-003**: El buscador MUST permitir activar la consulta tanto al hacer clic en el botón de consulta como al pulsar la tecla `Enter` desde el campo de texto.
- **FR-004**: El sistema MUST sanear automáticamente la entrada del usuario eliminando espacios superfluos y normalizando a mayúsculas.
- **FR-005**: Si el usuario introduce solo el número de incidencia, el sistema MUST auto-completar el formato estándar antes de iniciar la consulta.
- **FR-006**: Al validar el identificador de incidencia, el sistema MUST desplegar la pantalla flotante interactiva de Resumen IA con el detalle ejecutivo del caso (título, estado, impacto, solución, bloqueos, cronología de hitos y enlace directo a Remedy).
- **FR-007**: El sistema MUST reutilizar el mecanismo existente de pantalla flotante de resumen IA implementado para los paneles de Incidencias Masivas y Postmortem, beneficiándose de su diseño, accesibilidad y sistema de caché.
- **FR-008**: Si el campo de búsqueda se encuentra vacío en el momento de la consulta, el sistema MUST evitar el envío, mantener al usuario en el portal y proporcionar una indicación visual de foco y obligatoriedad.
- **FR-009**: La interfaz del buscador MUST integrarse armónicamente con la identidad visual corporativa de Orange (anteriormente referida como MASORANGE), respetando los colores oficiales (`#FF7900`), tipografía y espaciados del portal.
- **FR-010**: El buscador MUST ser completamente adaptable a diferentes tamaños de pantalla (escritorio, tablet y móvil).

### Key Entities

- **Búsqueda de Incidencia**: Representa la acción de consulta realizada por el usuario, caracterizada por el identificador ingresado, su valor normalizado y el momento en que se solicita.
- **Resumen Ejecutivo de Incidencia (Epsilon IA)**: Información sintetizada por el motor de inteligencia artificial asociada a la incidencia consultada, que incluye código, título, estado de resolución, severidad, sistemas afectados, problema raíz, impacto en el negocio, acciones de mitigación, bloqueos pendientes y cronología técnica de eventos.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Los usuarios pueden consultar y visualizar el resumen IA de cualquier incidencia en menos de 2 segundos desde el portal principal en condiciones normales de red.
- **SC-002**: El 100% de las consultas activadas mediante la tecla `Enter` producen el mismo resultado que las ejecutadas mediante clic en el botón de consulta.
- **SC-003**: El 100% de los códigos ingresados con espacios circundantes o en minúsculas son normalizados automáticamente sin requerir intervención del usuario.
- **SC-004**: El 100% de los intentos de consulta con campo vacío son interceptados localmente en 0 ms sin generar tráfico de red ni recargar la página.
- **SC-005**: El componente de búsqueda cumple con los estándares de accesibilidad para navegación íntegra por teclado y contraste de color.

## Assumptions

- El portal principal comparte el mismo entorno web y tiene conectividad con el servicio proxy de síntesis de incidencias existente (`/api/epsilon/`).
- La pantalla flotante de Resumen IA (`resumen-ia.js` y `resumen-ia.css`) se reutilizará directamente sin alterar el comportamiento ya existente en los paneles de Incidencias Masivas y Postmortem.
- El formato estándar habitual de las incidencias es `INC` seguido de dígitos numéricos (ej. `INC000004141215`), aunque la API de consulta admite cualquier código de caso válido en el sistema.
- Las consultas repetidas para una misma incidencia se beneficiarán automáticamente de la caché de doble capa (cliente y servidor) ya activa en la plataforma.

