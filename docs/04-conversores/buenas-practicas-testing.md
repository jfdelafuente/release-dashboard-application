# Buenas Prácticas de Testing

Este documento establece las directrices obligatorias para el desarrollo, refactorización y mantenimiento de pruebas automatizadas en el módulo `converters`.

---

## Principios Fundamentales de Diseño de Tests

### 1. Uso Obligatorio de `tmp_path` para Ficheros de Salida

Al probar conversores que generan ficheros JSON o informes PowerPoint, los ficheros de salida **nunca** deben escribirse en rutas del repositorio ni en `tests/test_data/`.

#### ❌ Anti-patrón (Efectos secundarios y contaminación del repositorio):
```python
def test_converter():
    converter = PostmortemConverter()
    # MAL: Escribe dentro de tests/test_data/, dejando ficheros residuales
    converter.convert_file(
        "tests/test_data/input.csv",
        "tests/test_data/output.json"  # Contamina el sistema de ficheros
    )
    with open("tests/test_data/output.json") as f:
        data = json.load(f)
    # El archivo permanece en disco tras finalizar el test
```

#### ✅ Patrón Correcto (Aislamiento completo con `tmp_path`):
```python
def test_converter(tmp_path):
    converter = PostmortemConverter()
    # BIEN: Utiliza un directorio temporal aislado gestionado por pytest
    output_file = tmp_path / "output.json"
    error_file = tmp_path / "errors.json"
    
    converter.convert_file(
        "tests/test_data/input.csv",
        str(output_file),
        str(error_file)
    )
    
    with open(output_file) as f:
        data = json.load(f)
    # Pytest elimina automáticamente los ficheros tras la ejecución
```

---

### 2. Comparativa: `tests/test_data/` vs `tmp_path`

| Aspecto | Escritura en `tests/test_data/` | Uso de fixture `tmp_path` |
| :--- | :--- | :--- |
| **Limpieza** | Manual, propensa a olvidos | Totalmente automática |
| **Efectos Secundarios** | Ficheros residuales en el repositorio | Ninguno, entorno 100% aislado |
| **Paralelismo** | Difícil (conflictos de concurrencia) | Totalmente soportado (`pytest -n auto`) |
| **Historial Git** | Sucio (marcas de tiempo cambian los hashes) | Limpio (sin artefactos rastreados) |
| **Rendimiento** | Lento (I/O persistente en disco del repo) | Rápido (aislado en directorio temporal) |

---

### 3. Contenido Permitido en `tests/test_data/`

#### ✅ Qué DEBE estar en `tests/test_data/`:
* Ficheros CSV de entrada inmutables para fixtures (`valid-100.csv`, `invalid-mixed.csv`, `normalization-edge-cases.csv`).
* Ficheros de referencia o comparación fija (*golden master files*).
* Ficheros mock para pruebas de encoding o delimitador.

#### ❌ Qué NUNCA debe estar en `tests/test_data/`:
* Ficheros JSON de salida generados durante la prueba.
* Ficheros de log o informes temporales.
* Presentaciones PowerPoint (`.pptx`) generadas dinámicamente.

---

### 4. Guía para Escribir Nuevos Tests

1. Inyectar siempre el parámetro `tmp_path` en las funciones o métodos de test que involucren I/O.
2. Definir las rutas de salida esperadas utilizando el operador de división de rutas de `pathlib.Path`:
   ```python
   output_json = tmp_path / "resultado.json"
   error_json = tmp_path / "resultado_errors.json"
   ```
3. Convertir a `str` si el método del conversor requiere tipos de cadena: `str(output_json)`.
4. Realizar las aserciones sobre el fichero generado en la ruta temporal.

---

## Ejecución del Suite de Pruebas

Para garantizar que las rutas relativas a fixtures (`tests/test_data/valid-100.csv`) se resuelvan correctamente, los tests deben ejecutarse siempre desde el directorio `converters/`:

```bash
# 1. Situarse en la carpeta converters
cd converters

# 2. Ejecutar la suite completa
pytest tests/ -v

# 3. Ejecutar pruebas en paralelo (aprovechando el aislamiento tmp_path)
pytest tests/ -n auto

# 4. Generar reporte de cobertura de código
pytest tests/ --cov=src --cov-report=term-missing
```

---

## Verificación de Integridad

Todas las pruebas del módulo siguen estrictamente estas directrices de aislamiento, permitiendo una ejecución paralela segura y garantizando que el árbol de trabajo de Git permanezca limpio tras cualquier tanda de pruebas.
