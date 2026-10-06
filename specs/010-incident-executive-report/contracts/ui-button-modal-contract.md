# UI Contract: Botón y Modal de Informe Ejecutivo en Gestión de Problemas

**Feature**: `010-incident-executive-report`

---

## 1. Botón de Acción en la Tabla de Candidatos a Postmortem (`IssuesTable.tsx`)

### 1.1 Estados del Botón por Fila

| Estado de la Fila | Renderizado Visual | Acción al Hacer Clic |
|---|---|---|
| **Informe No Generado** | Botón con borde naranja (`#FF7900`), fondo blanco, texto `"📄 Generar PPT"` | Abre el modal de generación con la URL de Confluence precargada (`issue.wikiPage.url`). |
| **Generando Informe** | Botón inactivo con spinner de carga y texto `"⏳ Generando..."` | Bloqueado para evitar dobles peticiones. |
| **Informe Disponible** | Botón sólido naranja (`#FF7900`), texto blanco `"⬇️ Descargar PPT"` + icono lateral `"🔄"` (Regenerar) | Clic principal: Descarga directa inmediata del `.pptx` sin esperas.<br>Clic en `"🔄"`: Abre el modal para confirmar regeneración desde Confluence. |

---

## 2. Componente Modal de Generación (`ExecutiveReportModal.tsx`)

### 2.1 Elementos del Modal

1. **Cabecera**:
   - Título: `"Informe Ejecutivo de Postmortem"`
   - Subtítulo: Código de incidencia (`issue.incidentRef` o `issue.key`) y descripción breve.
2. **Campo URL de Confluence**:
   - Input de texto precargado con `issue.wikiPage.url` (si existe) o vacío para introducirlo manualmente.
   - Botón de enlace externo para abrir la página en nueva pestaña y validar sesión.
3. **Pestaña opcional / Acordeón "Pegar contenido manualmente"**:
   - Para casos donde el entorno de red impida acceso directo por fetch/proxy.
4. **Área de Estado / Feedback**:
   - Barra de progreso indeterminada durante el procesamiento (<15s).
   - Notificación de éxito con enlace de descarga directa.
   - Mensaje de error accesible (`role="alert"`) si la URL no es válida o la página no responde.
5. **Botones de Pie de Diálogo**:
   - Botón secundario: `"Cancelar"` (cierra el modal).
   - Botón primario: `"Generar y Descargar PPT"` (color `#FF7900`, activa el flujo).

---

## 3. Accesibilidad y Ergonomía (WCAG 2.1 AA)

- Soporte total para teclado: tecla `Escape` cierra el modal, tecla `Enter` envía el formulario.
- Atributos `aria-modal="true"`, `role="dialog"` y foco automático en el botón de confirmación o campo de entrada.
- Anuncio dinámico para lectores de pantalla mediante `aria-live="polite"` al completarse la generación o producirse un error.
