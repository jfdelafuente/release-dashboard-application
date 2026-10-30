[← Volver al Índice General](../README.md)

# 04. Módulo de Conversores y Normalización

Documentación técnica del paquete Python de conversión de datos masivos Remedy CSV a JSON estructurado y normalizado.

---

## 📚 Documentos de la Sección

| Documento | Audiencia | Propósito |
| :--- | :--- | :--- |
| **[estructura-tests.md](./estructura-tests.md)** | Desarrolladores | Organización híbrida de la suite de pruebas unitarias pytest (>590 tests), fixtures comunes y aislamiento de tests. |
| **[buenas-practicas-testing.md](./buenas-practicas-testing.md)** | Desarrolladores | Guía de mejores prácticas con pytest, mockeo de llamadas HTTP, parametrize y cobertura. |
| **[rendimiento.md](./rendimiento.md)** | Desarrolladores | Decisiones de optimización, benchmarks de lectura CSV por streaming, gestión de memoria y límites de CPU. |
| **[test-structure-diagram.txt](./test-structure-diagram.txt)** | Desarrolladores | Diagrama ASCII de la estructura de tests del conversor. |

---

## ⚙️ Capacidades Principales del Conversor

* **Detección Automática de Delimitadores**: Soporte para `,`, `;` y `\t`.
* **Detección Resiliente de Encoding**: Manejo automático de UTF-8, UTF-8 con BOM, Windows-1252 e ISO-8859-1.
* **Normalización Heurística de Fechas**: Formateo unificado a estándar ISO 8601 y strings amigables para Remedy.
* **Triaje ITIL Determinista**: Cálculo en lote de severidades de impacto/urgencia y enriquecimiento con Epsilon IA.

