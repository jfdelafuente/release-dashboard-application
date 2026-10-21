# Guía de Contribución - Release Dashboard Application

¡Gracias por contribuir a Release Dashboard Application! Esta guía establece los estándares de desarrollo, pruebas, seguridad y procedimientos de despliegue para colaborar eficazmente en el repositorio.

---

## 🧭 Principios de Desarrollo

1. **Simplicidad y Robustez**: Código legible, modular y enfocado a la fiabilidad operativa en entorno corporativo Orange.
2. **Identidad de Marca Estricta**: La marca corporativa es exclusivamente **Orange** (bajo ninguna circunstancia se debe emplear MASORANGE). La paleta visual estándar debe adherirse a los tokens definidos en [`dashboards/assets/tokens.css`](dashboards/assets/tokens.css).
3. **Calidad y Cobertura**: Todo cambio en el backend o motor de conversión debe incluir pruebas unitarias y de integración que mantengan la cobertura de código por encima del **80%**.
4. **Desacoplamiento de Datos**: Los datos de incidencias y archivos temporales (`data/`) nunca se suben al repositorio; en el servidor VPS residen desacoplados en `/infocodes/var/storage/`.

---

## 🛠️ Estándares de Código

### Python (Backend y Conversores)

- **Versión de referencia**: Python 3.10+ / 3.11.
- **Formateador**: `black` con longitud de línea de 120 caracteres.
- **Linter e imports**: `flake8` e `isort`.
- **Tipado estático**: Se recomienda el uso intensivo de *type hints* (`typing`).
- **Docstrings y comentarios**: Documentar todas las funciones y clases públicas siguiendo convenciones estándar (Sphinx o Google style).
- **Convenciones de nombres**:
  - Funciones y variables: `snake_case`
  - Clases: `PascalCase`
  - Constantes: `UPPER_CASE`

Ejemplo:
```python
from pathlib import Path
from typing import Tuple, Dict, Any

def convert_csv_to_json(input_path: Path, output_path: Path) -> Tuple[bool, Dict[str, Any]]:
    """
    Convierte un CSV de Remedy al esquema normalizado JSON del dashboard.

    Args:
        input_path: Ruta del fichero CSV de entrada.
        output_path: Ruta del fichero JSON resultante.

    Returns:
        Tupla con estado de éxito (bool) y diccionario con estadísticas/metadata.
    """
    # Lógica de conversión...
    return True, {"total": 100, "successful": 100}
```

### Frontend Web (Dashboards HTML/CSS/JS)

- **Arquitectura**: Vanilla ES6+ sin compiladores ni frameworks pesados (React, Vue o Angular no son necesarios en este repositorio; todo se ejecuta nativamente en el navegador).
- **Estilos**: Variables CSS nativas declaradas en [`dashboards/assets/tokens.css`](dashboards/assets/tokens.css).
- **Nomenclatura**: Nombres de clases en `kebab-case` (ej. `portal-hero-container`, `status-badge`).
- **Accesibilidad y Usabilidad**: Diseños adaptados a resoluciones móviles y de escritorio, atributos ARIA cuando proceda y contraste adecuado.
- **Consultas a APIs**: El servidor local [`serve_app.py`](serve_app.py) (puerto `8080`) actúa como proxy CORS para el servicio corporativo Epsilon IA (`/api/epsilon/resumenIA/{ID}`) y como pasarela para subida de ficheros (`/api/upload`).

---

## 🌿 Convenciones de Ramas y Git

### Nomenclatura de Ramas

```
feature/nombre-de-la-funcionalidad   # Nuevas capacidades
fix/descripcion-del-bug              # Corrección de errores
docs/tema-actualizado                # Mejoras de documentación
refactor/modulo-o-componente         # Refactorización de código sin cambio funcional
test/ampliacion-de-suite             # Añadir o actualizar pruebas
```

### Mensajes de Commit (Conventional Commits)

Utiliza el estándar de *Conventional Commits*:

```
tipo(ámbito opcional): descripción breve en presente

[cuerpo explicativo opcional]

[referencias a issues opcionales]
```

**Tipos habituales**:
- `feat`: Nueva funcionalidad.
- `fix`: Corrección de un fallo.
- `docs`: Modificaciones en documentación.
- `style`: Formato o estética de código sin cambio funcional.
- `refactor`: Mejora interna del código que no arregla un bug ni añade una feature.
- `test`: Incorporación o ajuste de pruebas automatizadas.
- `chore`: Mantenimiento de configuración, dependencias o infraestructura.

**Ejemplos**:
```bash
feat(portal): incorporar buscador directo con resumen Epsilon IA
fix(converters): normalizar delimitadores con valores multilínea
docs(deployment): documentar procedimiento standalone runtime en VPS
test(report_generator): añadir pruebas unitarias para paginación de hitos
```

---

## 🧪 Pruebas y Aseguramiento de la Calidad

### Ejecución de Tests en Python

Todas las pruebas del motor de conversión y generador de informes residen en [`converters/tests/`](converters/tests/):

```bash
cd converters

# Ejecutar la suite completa (516+ tests)
pytest tests/ -v

# Ejecutar con reporte de cobertura (debe superar el 80%)
pytest tests/ -v --cov=src --cov-report=term-missing

# Ejecutar solo una categoría
pytest tests/unit/
pytest tests/integration/
pytest tests/e2e/

# Ejecutar un fichero específico
pytest tests/unit/report_generator/test_executive_report_builder.py -v
```

### Pruebas de Frontend (JavaScript)

```bash
# Validaciones unitarias de lógica JS (por ejemplo normalizador de códigos de Remedy)
node dashboards/tests/test_sanitize_incident_code.js
```

### Verificación de Estilo y Linters

```bash
cd converters
black --check src/ cli/ tests/
flake8 src/ cli/ tests/ --max-line-length=120
isort --check-only src/ cli/ tests/
```

---

## 🔐 Seguridad y Protección de Secretos

1. **Archivos `.env`**: Nunca deben commitearse credenciales ni archivos de variables de entorno. Utiliza [`config/.env.example`](config/.env.example) como plantilla.
2. **Hook de Pre-commit**: Es obligatorio activar el hook local para prevenir la inclusión accidental de claves o datos personales:
   ```bash
   cp config/pre-commit-hook.sh .git/hooks/pre-commit
   chmod +x .git/hooks/pre-commit
   ```
3. **Datos de Incidencias**: Los ficheros ubicados en `data/input/`, `data/output/` y `data/errors/` están ignorados por `.gitignore` y jamás deben formar parte de un commit.

---

## 🚀 Flujo de Integración y Despliegue

1. **Crear rama de trabajo**: `git checkout -b feature/mi-mejora` a partir de `production`.
2. **Desarrollar y probar en local**:
   - Levantar servidor local: `python serve_app.py` (accede en `http://localhost:8080/dashboards/portal/`).
   - Ejecutar la suite de tests en `converters/` para validar que pasan al 100%.
3. **Commit y Push**: Tras superar los linters y pruebas locales, sube la rama al repositorio remoto.
4. **Pull Request hacia `production`**:
   - Describe con claridad el problema resuelto y las pruebas efectuadas.
   - La rama `production` está sujeta a políticas de protección (ver [`docs/GITHUB-BRANCH-PROTECTION.md`](docs/GITHUB-BRANCH-PROTECTION.md)), requiriendo aprobación y CI verde.
5. **Despliegue a Producción (VPS `10.132.26.96:8081`)**:
   - El despliegue se efectúa mediante el script PowerShell [`scripts/deploy-production.ps1`](scripts/deploy-production.ps1) desde la máquina local autorizada:
     ```powershell
     .\scripts\deploy-production.ps1
     ```
   - El proceso empaqueta un *Standalone Runtime* (~2.3 MB) transferido vía SCP, rota copias de seguridad de forma automática y mantiene los datos persistentes desacoplados en `/infocodes/var/storage/`.

---

## 📚 Enlaces de Referencia

- [Inicio Rápido (Quickstart)](docs/QUICKSTART.md)
- [Guía de Desarrollo Local](docs/DEVELOPMENT.md)
- [Procedimientos de Despliegue](docs/DEPLOYMENT.md)
- [Protección de Ramas en GitHub](docs/GITHUB-BRANCH-PROTECTION.md)
- [Resolución de Incidencias (Troubleshooting)](docs/TROUBLESHOOTING.md)
- [Informe Ejecutivo Postmortem (PowerPoint)](docs/INFORME-EJECUTIVO-POSTMORTEM.md)

---

**Última actualización**: 2026-10-21
