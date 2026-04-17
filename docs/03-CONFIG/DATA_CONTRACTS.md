# 📋 DATA CONTRACTS — Garantía de Calidad de Datos

**Fecha:** 11 de abril de 2026  
**Status:** ✅ Contratos alineados al esquema real y gate estricto activo

---

## 🎯 Qué son Data Contracts?

Un **Data Contract** es una especificación formal de "qué es un dato válido":

- **Esquema:** Columnas, tipos de datos, formatos esperados
- **Reglas:** Restricciones (min/max, valores permitidos, nulos, etc.)
- **Metadata:** Descripción, fuente, frecuencia de actualización

Permiten:
- ✅ Rechazar datos malos (early warning)
- ✅ Documentar estructura esperada (onboarding)
- ✅ Automatizar validación (CI/CD gates)
- ✅ Detectar derivas (data quality monitoring)

---

## 📂 Archivos Implementados

### 1. `config/data_contracts.yaml` — Definición de Contrato

Define contratos para **4 fuentes principais**:

| Fuente | Archivo | Actualizado por |
|--------|---------|-----------------|
| **Consolidado** | `data/output/Resultados Consolidados.xlsx` | `actualizar_consolidado.py` |
| **Kawak Data** | `data/raw/Fuentes Consolidadas/Consolidado_API_Kawak.xlsx` | `consolidar_api.py` |
| **Kawak Meta** | `data/raw/Fuentes Consolidadas/Indicadores Kawak.xlsx` | `consolidar_api.py` |
| **CMI** | `data/raw/Indicadores por CMI.xlsx` | Manual |

**Estructura de cada contrato:**

```yaml
fuente_nombre:
  archivo: "ruta/archivo"
  tipo: "excel | csv | api | database"
  hojas:
    nombre_hoja:
      columnas:
        nombre_col:
          tipo: "string | integer | float | datetime | categorical"
          requerida: true | false
          min/max: límites numéricos
          valores_permitidos: [lista]
          patron: regex
```

### 2. `services/data_validation.py` — Validador

Implementa validaciones:

```python
from services.data_validation import validate_dataset

# Validar un DataFrame
report = validate_dataset(df, source_name="resultados_consolidados")

# Revisar issues
if not report.is_valid:
    report.print_issues()  # Imprime problemas encontrados
    
# Export to JSON
import json
json_report = report.to_dict()
```

**Validaciones ejecutadas:**

| Validación | Qué chequea | Nivel |
|-----------|-----------|-------|
| Required Columns | ¿Existen todas las columnas requeridas? | Error |
| Type Mismatch | ¿Tipos de datos correctos? | Warning |
| Categorical Values | ¿Valores en set permitido? | Warning |
| Null Constraints | ¿Nulls donde no deben estar? | Error |
| Numeric Ranges | ¿Min/max respetados? | Warning |

---

## 🚀 Cómo Usar

### Opción 1: Validar Archivo Nuevo

```bash
# Validar una fuente configurada manualmente
python services/data_validation.py "data/output/Resultados Consolidados.xlsx" resultados_consolidados

# Validar todas las fuentes configuradas
python services/data_validation.py --all
```

**Output:**
```
📋 DataValidation Report — resultados_consolidados
   Shape: (500, 15)
   Issues: 2 errors, 5 warnings

   ❌ Null in Required Column [Anio] — Column 'Anio' has 3 null values but is required (3 rows)
   ⚠️ Value Below Minimum [Meta] — Column 'Meta' has 12 values < 0.0 (12 rows)
   ...
```

### Opción 2: Gate estricto en Pipeline y CI

El gate quedó activo en dos puntos:

- `pytest tests/test_data_contracts.py` falla si cualquier fuente viola su contrato.
- `python scripts/run_pipeline.py --no-exec` retorna código distinto de cero si los contratos no cumplen.

Integración programática:

En `services/data_loader.py`, validar después de cargar:

```python
from services.data_validation import validate_dataset

def cargar_dataset():
    df = pd.read_excel("data/output/Resultados Consolidados.xlsx")
    
    # Validar
    report = validate_dataset(df, "resultados_consolidados")
    
    if report.error_count > 0:
        logger.error(f"Data contract violation: {report.error_count} errors")
        for issue in report.issues:
            if issue.level == "error":
                logger.error(f"  {issue}")
    
    return df
```

### Opción 3: Crear Custom Validator

Extender `services/data_validation.py` para reglas personalizadas:

```python
def validate_cumplimiento_logic(df: pd.DataFrame, contract):
    """Validación custom: cumplimiento = ejecución / meta"""
    issues = []
    
    if 'Cumplimiento' in df.columns and 'Ejecucion' in df.columns and 'Meta' in df.columns:
        # Calcular esperado
        df['Cumplimiento_Expected'] = df['Ejecucion'] / df['Meta']
        
        # Comparar
        mismatches = df[
            abs(df['Cumplimiento'] - df['Cumplimiento_Expected']) > 0.01
        ]
        
        if len(mismatches) > 0:
            issues.append(ValidationIssue(
                level="warning",
                rule="Cumplimiento Calculation Mismatch",
                row_count=len(mismatches),
                description="Cumplimiento != Ejecucion / Meta",
            ))
    
    return issues
```

---

## 📊 Contratos Definidos

### `resultados_consolidados` (Fuente Oficial)

**Hojas:**
1. `Consolidado Semestral` — Datos principales (consumo general)
   - Columnas: Anio, Semestre, Id, Indicador, Proceso, Meta, Ejecución, Cumplimiento, etc.
   - Reglas: Sin nulos en campos críticos, cumplimiento coherente

2. `Consolidado Historico` — Soporte para análisis longitudinal y Gestión OM
  - Columnas: estructura equivalente por período histórico
  - Reglas: coherencia temporal por Id, Año, Mes y Periodo

3. `Catalogo Indicadores` — Metadatos
   - Columnas: Id, Indicador, Tipo, Periodicidad, Clasificación
  - Reglas: Todos los Ids deben existir en Consolidado Semestral

### `kawak_consolidado`

**Estructura:**
- Columns: Ano, Fecha, Id, Valor, Meta
- Reglas: Datos sin duplicados (Ano + Id + Fecha), fechas válidas

### `kawak_catalogo`

**Estructura:**
- Columns: Ano, Id, Indicador, Proceso, Sentido (requerido)
- Reglas: Sin duplicados, Sentido en ["Ascendente", "Descendente"]

### `indicadores_cmi`

**Estructura:**
- Columns: Id, Subproceso, Linea
- Reglas: IDs deben existir en catálogo Kawak

---

## 🔄 Roadmap

### ✅ Fase 1 (Completado 11-abr-2026)
- Define contracts en YAML
- Implementa validador básico (5 reglas)
- Documentación

### 🟡 Fase 2 (Próximas 4 semanas)

**Semana 3-4:**
- [ ] Integrar validaciones en `data_loader.py`
- [ ] Setup logging + alertas de violaciones
- [ ] Crear página Streamlit para monitoreo

**Semana 5-6:**
- [ ] Evaluar Great Expectations (framework profesional)
- [ ] Migrate si necesario
- [ ] Setup CI/CD gates (bloquear PRs si contract violated)

### 🔮 Fase 3+ (Futuro)
- Great Expectations full integration
- Automated data profiling (detectar cambios en distribuciones)
- SLA dashboards (% de datos valid vs violators)
- Causal analysis (si X viola contract, qué impacta)

---

## ⚙️ Cómo Agregar Nuevos Contracts

**Paso 1:** Editar `config/data_contracts.yaml`

```yaml
nueva_fuente:
  archivo: "ruta/archivo"
  tipo: "excel"
  descripcion: "..."
  hojas:
    Sheet1:
      columnas:
        col_name:
          tipo: "string"
          requerida: true
```

**Paso 2:** La validación funciona automáticamente

```python
report = validate_dataset(df, "nueva_fuente")
```

---

## 🎯 Beneficios para Fase 2

| Beneficio | Impacto |
|-----------|--------|
| **Early detection** | Detectar data issues antes que afecten análisis (-30% debugging time) |
| **Automated testing** | Data quality checks en CI/CD (-20% manual validation) |
| **Documentation** | Fuentes documentadas automáticamente (+onboarding) |
| **Auditability** | Rastrear dónde/cuándo data violated contract (+compliance) |

---

## 📝 Próximas Tareas

- [x] Ejecutar validación sobre datasets actuales
- [x] Documentar hallazgos en [docs/DATA_CONTRACTS_VALIDATION_REPORT.md](docs/DATA_CONTRACTS_VALIDATION_REPORT.md)
- [ ] Ajustar contratos según esquema real de resultados_consolidados y kawak_catalogo
- [ ] Crear página Streamlit para visualizar health
- [ ] Integrar con CI/CD cuando los contratos queden alineados con el dato real

## Resultado Actual

Tras alinear los contratos con el esquema real y corregir la validación por hoja:

- resultados_consolidados: 0 issues
- kawak_consolidado: 0 issues
- kawak_catalogo: 0 issues
- indicadores_cmi: 0 issues

El detalle histórico de la primera pasada y del ajuste posterior quedó en [docs/DATA_CONTRACTS_VALIDATION_REPORT.md](docs/DATA_CONTRACTS_VALIDATION_REPORT.md).

---

**Documento Generado:** 11 de abril de 2026  
**Versión:** 1.0 — MVP  
**Mantenedor:** Data Engineering Team

Para preguntas: Ver `config/data_contracts.yaml` section "documentacion"
