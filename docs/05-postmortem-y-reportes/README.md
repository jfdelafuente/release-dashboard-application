[← Volver al Índice General](../README.md)

# 05. Postmortem, Reportes Ejecutivos y Presentaciones PPTX

Guías para la generación y distribución de reportes ejecutivos PowerPoint (.pptx) para Dirección y comités de Post-Incident Review (PIR).

---

## 📚 Documentos de la Sección

| Documento | Audiencia | Propósito |
| :--- | :--- | :--- |
| **[informe-ejecutivo-postmortem.md](./informe-ejecutivo-postmortem.md)** | Incident Managers / Dirección | Generación del informe PowerPoint ejecutivo individual por incidencia (Single Source of Truth en backend CSO y storage `/infocodes/var/storage/executive_pptx/`). |
| **[informe-ppt-batch.md](./informe-ppt-batch.md)** | Responsables de Release | Generación masiva batch del informe PPT postmortem agrupado por ventana de despliegue (PAP/MESA) mediante `generate_postmortem_report.py`. |

---

## 📊 Integración con el Flujo PIR

Tras la estabilización o cierre de una incidencia SL1/P1 o SL2/P2, el proceso ITIL de Orange establece la elaboración de un informe postmortem sin culpa (*blameless*) respaldado por la skill `postmortem-pir-workflow`:
1. **Generación Automatizada:** Extracción de datos del catálogo y síntesis de Epsilon Resumen IA.
2. **Plantilla Corporativa:** Renderizado en formato PPTX oficial con líneas de tiempo verificadas y matriz de impacto.
3. **Plan CAPA:** Registro de acciones correctoras y preventivas derivadas a Problem Management.
