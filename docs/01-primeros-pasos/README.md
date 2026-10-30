[← Volver al Índice General](../README.md)

# 01. Primeros Pasos y Desarrollo Local

Guías esenciales para nuevos desarrolladores y colaboradores del proyecto Release Dashboard Application.

---

## 📚 Documentos de la Sección

| Documento | Audiencia | Propósito |
| :--- | :--- | :--- |
| **[quickstart.md](./quickstart.md)** | Desarrolladores | Puesta en marcha en 5 minutos, entorno virtual, arranque de `serve_app.py` en el puerto `8080` y comandos esenciales. |
| **[desarrollo.md](./desarrollo.md)** | Desarrolladores | Manual integral de desarrollo, configuración de Python 3.10+/3.11/3.12, suite de pruebas pytest (>590 tests), linters y formateadores. |
| **[troubleshooting.md](./troubleshooting.md)** | Soporte y Desarrollo | Diagnóstico paso a paso y resolución de incidencias en entorno local, conversores CLI, dashboards y servidor VPS. |

---

## 🚀 Flujo Recomendado de Inicio

1. Ejecuta el setup de **[quickstart.md](./quickstart.md)** para clonar, activar tu venv e instalar dependencias.
2. Inicia el servidor de desarrollo local con `python serve_app.py`.
3. Consulta **[desarrollo.md](./desarrollo.md)** para ejecutar la suite de pruebas unitarias (`pytest converters/tests/unit/`).
4. Si encuentras algún bloqueo en puertos o permisos en Windows, consulta **[troubleshooting.md](./troubleshooting.md)**.
