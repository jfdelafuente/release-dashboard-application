# Contract: UI Search Component (Buscador de Incidencias)

**Feature**: `009-portal-incident-search` | **Date**: 2026-10-06

Este documento define el contrato de interfaz HTML, atributos de accesibilidad, eventos y métodos JavaScript del componente buscador en `dashboards/portal/index.html`.

---

## 1. Estructura HTML y Atributos Accesibles (ARIA)

```html
<section class="portal-search-hero" aria-label="Buscador rápido de incidencias">
    <div class="portal-search-hero-content">
        <div class="portal-search-badge">
            <span class="portal-search-badge-icon" aria-hidden="true">🤖</span>
            <span>Inteligencia Artificial Epsilon</span>
        </div>
        <h2 class="portal-search-title">Consulta de Incidencias y Resumen IA</h2>
        <p class="portal-search-subtitle">
            Accede al resumen ejecutivo, diagnóstico y causa raíz de cualquier incidencia técnica en tiempo real.
        </p>

        <form id="incident-search-form" class="portal-search-form" novalidate>
            <div class="portal-search-input-wrapper">
                <svg class="portal-search-icon" aria-hidden="true" viewBox="0 0 20 20" fill="currentColor">
                    <path fill-rule="evenodd" d="M9 3.5a5.5 5.5 0 100 11 5.5 5.5 0 000-11zM2 9a7 7 0 1112.452 4.391l3.328 3.329a.75.75 0 11-1.06 1.06l-3.329-3.328A7 7 0 012 9z" clip-rule="evenodd" />
                </svg>
                <input 
                    type="text" 
                    id="incident-search-input" 
                    class="portal-search-input" 
                    placeholder="Introduce código de incidencia (ej. INC000004141215 o 4141215)..." 
                    autocomplete="off" 
                    spellcheck="false"
                    aria-label="Código de incidencia a consultar"
                    aria-describedby="search-hint search-error"
                />
                <button type="submit" id="incident-search-btn" class="portal-search-btn">
                    <span>Consultar</span>
                    <svg aria-hidden="true" viewBox="0 0 20 20" fill="currentColor">
                        <path fill-rule="evenodd" d="M3 10a.75.75 0 01.75-.75h10.638L10.23 5.29a.75.75 0 111.04-1.08l5.5 5.25a.75.75 0 010 1.08l-5.5 5.25a.75.75 0 11-1.04-1.08l4.158-3.96H3.75A.75.75 0 013 10z" clip-rule="evenodd" />
                    </svg>
                </button>
            </div>
            <div class="portal-search-footer">
                <span id="search-hint" class="portal-search-hint">💡 Acepta códigos completos o solo números (se completará con ceros automáticamente).</span>
                <span id="search-error" class="portal-search-error" role="alert" aria-live="polite" style="display: none;"></span>
            </div>
        </form>
    </div>
</section>
```

---

## 2. Eventos y Lógica JavaScript

### Evento `submit` en `#incident-search-form`
- **Disparadores**: Clic en `#incident-search-btn` o pulsación de la tecla `Enter` dentro de `#incident-search-input`.
- **Acciones**:
  1. `e.preventDefault()`.
  2. Obtener `rawInput = input.value`.
  3. Ejecutar `sanitized = sanitizeIncidentCode(rawInput)`.
  4. Si `!sanitized`:
     - Mostrar mensaje en `#search-error`: `"Por favor, introduce un código de incidencia."`.
     - Añadir clase `is-invalid` al input.
     - Ejecutar `input.focus()`.
     - Retornar.
  5. Si es válido:
     - Ocultar `#search-error`.
     - Retirar clase `is-invalid`.
     - Invocar `window.ResumenIAModal.open(sanitized)`.

### Evento `input` en `#incident-search-input`
- Si el input tenía la clase `is-invalid`, retirarla y ocultar el mensaje de error para una experiencia limpia mientras el usuario escribe.
