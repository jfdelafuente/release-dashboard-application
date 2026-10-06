# Phase 0 Research: Buscador de Incidencias con Resumen IA en Portal Principal

**Feature**: `009-portal-incident-search` | **Date**: 2026-10-06

Este documento consolida las decisiones arquitectónicas y técnicas para la implementación del buscador de incidencias en el portal principal (`dashboards/portal/index.html`).

---

## 1. Ubicación y Estructura en el Layout del Portal

### Contexto
El portal principal de fiabilidad (`dashboards/portal/index.html`) organiza sus contenidos en:
1. Barra corporativa superior (`#mo-topbar-root`)
2. Cabecera principal (`.portal-header`) con el título y la hora de última sincronización
3. Contenedor principal (`<main id="main-content" class="container">`) que aloja:
   - Fila 1: Plataformas Operativas y Seguimiento (3 tarjetas)
   - Fila 2: Releases y Entregas (2 tarjetas)
   - Fila 3: Detalle de Sincronización

### Decisión
Insertar un contenedor hero de búsqueda (`<section class="portal-search-hero" aria-label="Buscador de incidencias">`) al inicio de `<main>`, justo antes del separador `.row-divider` de la Fila 1.

### Razón
- **Máxima visibilidad**: Es lo primero que ve el usuario tras el título, permitiendo una acción rápida sin scroll.
- **Jerarquía limpia**: No sobrecarga la cabecera blanca de la página (que mantiene su propósito de identidad y metadatos).
- **Diseño responsive**: Un bloque hero fluye de forma natural en rejilla de 1 columna en móviles y tablets, expandiéndose con elegancia en pantallas de escritorio.

### Alternativas Evaluadas
- *Integrar el input dentro de `.portal-header` junto a la fecha*: Descartada por reducir drásticamente el espacio disponible para títulos en pantallas medianas y restar prominencia visual a la función de búsqueda.
- *Barra fija flotante (sticky header)*: Descartada por resultar innecesariamente intrusiva al navegar las tarjetas de plataformas operativas inferiores.

---

## 2. Reutilización del Componente Modal de Resumen IA

### Contexto
Los dashboards de Incidencias Masivas y Postmortem ya disponen de una implementación probada y estable para la síntesis de incidencias vía inteligencia artificial:
- **`dashboards/assets/resumen-ia.css`**: Estilos del modal, chips de sistemas afectados, bloques de colores por severidad/estado, cronología de hitos y botón interactivo de refresco.
- **`dashboards/assets/resumen-ia.js`**: Lógica de cliente, llamada a la API (`/api/epsilon/resumenIA/<codigo>`), singleton `window.ResumenIAModal`, deduplicación de peticiones concurrentes (`inFlightRequests`) y caché en cliente con TTL de 15 minutos en `sessionStorage`.

### Decisión
Enlazar directamente estos dos recursos compartidos en `dashboards/portal/index.html`:
```html
<link rel="stylesheet" href="/dashboards/assets/resumen-ia.css">
...
<script src="/dashboards/assets/resumen-ia.js" defer></script>
```
E invocar la apertura del modal con:
```javascript
window.ResumenIAModal.open(codigoSanitizado);
```

### Razón
- **Cero duplicación de código**: Se reutilizan al 100% las 500+ líneas de lógica y presentación ya validadas.
- **Protección de doble capa automática**: El portal se beneficia de inmediato de la caché de sesión del navegador y de la caché compartida de Nginx (`proxy_cache my_cache`), evitando saturar el backend de Epsilon.
- **Mantenimiento centralizado**: Cualquier mejora visual o en el parser de la API se propaga instantáneamente a todas las páginas de la aplicación.

---

## 3. Lógica de Saneamiento y Normalización del Código

### Contexto
Los operadores obtienen códigos de incidencia de distintas fuentes (correos, Remedy, alertas de mensajería). Es frecuente que contengan espacios circundantes, letras minúsculas (`inc...`), o que se introduzcan solo los dígitos significativos (`4141215`).

El estándar de códigos de incidencia de Remedy en Orange sigue la convención:
`INC` seguido de 12 dígitos (ej. `INC000004141215`).

### Decisión
Implementar una función de normalización pura:
```javascript
function sanitizeIncidentCode(input) {
    if (!input || typeof input !== 'string') return '';
    let code = input.trim().toUpperCase();
    
    // Si contiene solo dígitos (ej. "4141215"), añadir prefijo INC y ceros hasta 12 dígitos
    if (/^\d+$/.test(code)) {
        return 'INC' + code.padStart(12, '0');
    }
    
    // Si empieza por INC seguido de menos de 12 dígitos (ej. "INC4141215"), rellenar ceros
    const incMatch = code.match(/^INC(\d+)$/);
    if (incMatch) {
        const digits = incMatch[1];
        if (digits.length < 12) {
            return 'INC' + digits.padStart(12, '0');
        }
    }
    
    return code;
}
```

### Razón
- Es 100% tolerante con entradas abreviadas habituales.
- No altera códigos de otro tipo de entidades si la API los soportara en el futuro.
- Previene peticiones erróneas a la API por simples descuidos de tecleo.

---

## 4. Accesibilidad (a11y) y Validación Visual

### Contexto
La Constitución del proyecto exige accesibilidad por teclado y feedback comprensible sin exponer códigos de error crudos.

### Decisión
1. **Accesibilidad por teclado**:
   - El formulario utiliza un `<form id="incident-search-form">` con `<input type="text">` y `<button type="submit">`.
   - La pulsación de la tecla `Enter` envía el formulario de manera nativa.
   - Si el modal se abre, el modal atrapa el foco y permite cerrarse con la tecla `Escape`, devolviendo el foco al input del buscador.
2. **Validación de campo vacío**:
   - `e.preventDefault()` previene recargas de página.
   - Si el valor saneado está vacío, se añade la clase `.is-invalid` al input y se muestra un mensaje `<span>` con `role="alert"` y `aria-live="polite"`.
   - El cursor se posiciona en el input (`input.focus()`).
   - Al escuchar el evento `input`, se retira la clase de error automáticamente.

---

## Conclusión
La solución es limpia, modular, de muy bajo riesgo y de alto impacto operativo. No requiere dependencias externas nuevas ni cambios en el backend.
