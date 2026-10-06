# Quickstart: Buscador de Incidencias con Resumen IA en Portal Principal

**Feature**: `009-portal-incident-search` | **Date**: 2026-10-06

Guía para verificar y probar localmente el buscador de incidencias en el portal principal.

---

## 1. Arrancar el Servidor Local

Ejecuta el servidor de desarrollo local (que incluye el endpoint proxy `/api/epsilon/resumenIA/<codigo>` con caché simulada y bypass SSL):

```powershell
python serve_app.py
```

El servidor quedará escuchando en `http://localhost:8000`.

---

## 2. Abrir el Portal Principal

Abre tu navegador en:
`http://localhost:8000/dashboards/portal/`

---

## 3. Pruebas de Funcionamiento

### Prueba A: Búsqueda con Código Completo
1. En el buscador situado en la parte superior, escribe: `INC000004141215`.
2. Pulsa el botón **"Consultar"** o presiona la tecla `Enter`.
3. **Resultado esperado**:
   - Se abre el modal flotante de Resumen IA.
   - Aparece el spinner de carga brevemente y se presentan el estado, título, sistemas y los bloques temáticos.
   - Se incluye el enlace "Abrir en Remedy" y el botón de refresco.
4. Cierra el modal pulsando la tecla `Escape` o la `X`.

### Prueba B: Normalización Automática (Solo Números o Espacios)
1. Escribe en el buscador: `  4141215  ` (con espacios antes y después).
2. Presiona `Enter`.
3. **Resultado esperado**:
   - El código se normaliza a `INC000004141215`.
   - Se abre el modal de Resumen IA de forma idéntica a la Prueba A.
   - Al haber sido consultado hace menos de 15 minutos, la respuesta es inmediata (0 ms) con la insignia `⚡ En caché`.

### Prueba C: Validación de Campo Vacío
1. Borra todo el texto del campo de búsqueda.
2. Pulsa el botón **"Consultar"** o presiona `Enter`.
3. **Resultado esperado**:
   - No se dispara ninguna petición de red ni se abre el modal.
   - El campo se resalta con borde de advertencia y se muestra el mensaje de que debe introducirse un código.
   - El cursor permanece activo dentro del campo para seguir escribiendo.
   - Al escribir cualquier carácter, la advertencia desaparece inmediatamente.

