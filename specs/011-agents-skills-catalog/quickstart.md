# Quickstart: Catálogo y Dashboard de Agentes y Skills IA (011-agents-skills-catalog)

Esta guía explica cómo generar el catálogo de agentes, ejecutar las pruebas y visualizar el dashboard en el entorno local.

---

## 1. Requisitos Previos

- Python 3.10+
- Repositorio `biblioteca-agentes` ubicado en `C:\Users\jose.delafuente\Claude\Projects\biblioteca-agentes` (o ruta alternativa especificada en variable de entorno).

---

## 2. Generar el Fichero del Catálogo (`agents_catalog.json`)

Ejecuta el script conversor desde la raíz del proyecto `release-dashboard-application`:

```bash
# Ejecución estándar (utiliza la ruta canónica por defecto):
python converters/cli/build_agents_catalog.py

# O especificando una ruta explícita:
python converters/cli/build_agents_catalog.py --library-path "C:\Users\jose.delafuente\Claude\Projects\biblioteca-agentes"
```

Salida esperada:
```text
[INFO] Leyendo biblioteca desde C:\Users\jose.delafuente\Claude\Projects\biblioteca-agentes
[INFO] Procesados 5 agentes y 6 skills en 2 dominios
[INFO] Catálogo generado con éxito en data/output/agents_catalog.json
```

---

## 3. Ejecutar las Pruebas Unitarias

Para validar el extractor, la normalización de frontmatter y la integridad del schema:

```bash
pytest converters/tests/unit/test_build_agents_catalog.py -v
```

---

## 4. Iniciar el Servidor de Desarrollo Local

Inicia el servidor local:

```bash
python serve_app.py
```

Abre en tu navegador:
- **Catálogo de Agentes**: [http://localhost:8080/dashboards/agents-catalog/](http://localhost:8080/dashboards/agents-catalog/)
- **Portal Hub**: [http://localhost:8080/dashboards/portal/](http://localhost:8080/dashboards/portal/)

---

## 5. Verificación Funcional

1. **Catálogo y KPIs**:
   - Confirma que la cabecera muestra: **5 Agentes**, **2 Dominios**, **6 Skills**.
   - Revisa las tarjetas de `orange-brand-generator`, `incident-analyzer`, `incident-describer`, `incident-report-publisher`, `incident-reporter`.
2. **Búsqueda y Filtros**:
   - Escribe `postmortem` en el buscador; comprueba que solo quedan visibles `incident-analyzer` e `incident-reporter`.
   - Haz clic en el chip `Contenido y Marca`; verifica que solo aparece `orange-brand-generator`.
3. **Copia de Despliegue**:
   - Pulsa "Copiar comando" en una tarjeta y comprueba que se copia `.\deploy-agents.cmd "<TargetRepo>" -Agents "<name>"`.
4. **Ficha Completa / Skills**:
   - Pulsa "Ver Ficha Completa" para abrir el modal con el contenido Markdown íntegro.
   - Cambia a la pestaña "Skills" para ver el inventario con las 6 habilidades y qué agentes las emplean.

