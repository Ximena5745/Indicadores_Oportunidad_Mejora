# Documentación de Cálculos - `actualizar_consolidado.py`

## Resumen General

El script `actualizar_consolidado.py` es el motor de procesamiento de datos del Dashboard de Desempeño Institucional. Su función principal es consolidar datos provenientes de múltiples fuentes (API Kawak, archivos Excel, variables y series) en un único archivo de Excel estructurado con métricas de cumplimiento.

**Versión**: 7.0  
**Archivo fuente**: `scripts/actualizar_consolidado.py`  
**Archivo base**: `data/raw/Resultados_Consolidados_Fuente.xlsx`  
**Archivo salida**: `data/output/Resultados Consolidados.xlsx`

---

## 1. Fuentes de Datos

### 1.1 Fuentes Primarias

| Fuente | Archivo | Contenido | Propósito |
|--------|---------|-----------|-----------|
| **API Consolidada** | `Consolidado_API_Kawak.xlsx` | Datos históricos de indicadores con resultado, meta, variables, series y análisis | Fuente principal de datos operativos |
| **Catálogo Kawak** | `Indicadores Kawak.xlsx` | IDs de indicadores válidos por año | Validación de indicadores activos |
| **Archivo Base** | `Resultados_Consolidados_Fuente.xlsx` | Plantilla con hojas predefinidas y fórmulas Excel | Base para generar output |
| **LMI Reporte** | `lmi_reporte.xlsx` | Clasificación de indicadores (Tipo: Métrica) | Identificación de indicadores de métrica |

### 1.2 Estructura de Datos API

Cada registro de la API contiene:
- `ID`: Identificador del indicador
- `nombre`: Nombre descriptivo
- `proceso`: Proceso al que pertenece
- `frecuencia/periodicidad`: Mensual, Trimestral, Semestral, Anual, Bimestral
- `sentido`: Positivo (mayor es mejor) o Negativo (menor es mejor)
- `fecha`: Fecha del período
- `resultado`: Valor de ejecución desde API
- `meta`: Valor de meta desde API
- `variables`: JSON con variables desglosadas
- `series`: JSON con series de datos
- `analisis`: Texto de análisis del responsable

---

## 2. Lógica de Cálculo Principal

### 2.1 Flujo de Procesamiento

```
┌─────────────────────────────────────────────────────────────────┐
│  1. CARGA DE FUENTES                                            │
│     ├─ API Consolidada (DataFrame maestro)                     │
│     ├─ Kawak 2025 (datos adicionales año 2025)                 │
│     └─ Archivo Base (3 hojas: Histórico, Semestral, Cierres)   │
├─────────────────────────────────────────────────────────────────┤
│  2. DETECCIÓN DE NO APLICA (N/A)                                │
│     ├─ Análisis contiene "no aplica"                           │
│     └─ Resultado NaN + Sin datos útiles en variables/series    │
├─────────────────────────────────────────────────────────────────┤
│  3. EXTRACCIÓN META/EJECUCIÓN                                   │
│     ├─ Patrón LAST → Usar resultado API directo                │
│     ├─ Patrón VARIABLES → Extraer de variables por símbolo     │
│     ├─ Patrón SUM_SER → Sumar series                           │
│     └─ Heurística → Lógica automática según escala             │
├─────────────────────────────────────────────────────────────────┤
│  4. CÁLCULO DE CUMPLIMIENTO                                     │
│     ├─ Sentido Positivo: Ejecución / Meta                      │
│     ├─ Sentido Negativo: Meta / Ejecución                      │
│     └─ Aplicar tope (default: 130%)                            │
├─────────────────────────────────────────────────────────────────┤
│  5. GENERACIÓN DE OUTPUT                                        │
│     ├─ Escribir en 3 hojas según periodicidad                  │
│     ├─ Materializar fórmulas Excel                             │
│     └─ Deduplicar por LLAVE                                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Cálculo de Cumplimiento (`_calc_cumpl`)

### 3.1 Fórmula Matemática

```python
def _calc_cumpl(meta, ejec, sentido, tope=1.3):
    """
    Calcula (cumpl_capped, cumpl_real)
    
    Fórmulas:
    
    Sentido Positivo:
        cumplimiento = ejecución / meta
    
    Sentido Negativo:
        cumplimiento = meta / ejecución
    
    Aplicaciones:
        - cumpl_real = cumplimiento (valor exacto)
        - cumpl_capped = min(cumplimiento, tope) (limitado)
    """
```

### 3.2 Casos Especiales

| Caso | Condición | Resultado |
|------|-----------|-----------|
| **Meta cero** | `meta == 0` | `(None, None)` - No calculable |
| **Ejecución cero (Negativo)** | `sentido == 'Negativo' and ejec == 0` | `(None, None)` - División por cero |
| **Valores nulos** | `meta is None or ejec is None` | `(None, None)` |
| **Tope excedido** | `cumplimiento > tope` | `cumpl_capped = tope` |
| **Negativos** | Cualquier valor < 0 | `max(valor, 0.0)` |

### 3.3 Umbrales de Categorización

```
Cumplimiento Capped → Categoría

0% - 79.9%      → 🔴 Peligro
80% - 99.9%     → 🟡 Alerta  
100% - 104.9%   → 🟢 Cumplimiento
≥ 105%          → 🔵 Sobrecumplimiento
```

**Nota**: Algunos indicadores Plan Anual (IDs: 373, 390, 414-418, 420, 469-471) cumplen desde 95% y topean en 100%.

---

## 4. Extracción de Datos (`determinar_meta_ejec`)

### 4.1 Patrones de Extracción

El sistema soporta 4 patrones configurables:

#### 4.1.1 LAST (Último valor)

```python
# Uso directo del resultado API
if resultado is not None:
    meta = campo meta API (si existe)
    ejec = resultado API
    fuente = 'api_directo'
```

**Cuándo usar**: Indicadores simples donde el resultado de la API ya es el valor final.

#### 4.1.2 VARIABLES (Desglose de variables)

```python
# Extraer de lista de variables por símbolo o keyword

# Opción A: Por símbolo configurado
simbolo_ejec = 'R'  # Configurado en Config_Patrones
simbolo_meta = 'M'  # Configurado en Config_Patrones
ejec = buscar_variable_por_simbolo(variables, simbolo_ejec)
meta = buscar_variable_por_simbolo(variables, simbolo_meta)

# Opción B: Por keywords (fallback)
keywords_meta = ['planeado', 'presupuestado', 'propuesto', ...]
keywords_ejec = ['real', 'ejecutado', 'recaudado', ...]
ejec = primera_variable_con_keyword_ejec
meta = primera_variable_con_keyword_meta

# Opción C: Por posición (último fallback)
if len(variables) >= 1: ejec = variables[0]
if len(variables) >= 2: meta = variables[1]
```

**Cuándo usar**: Indicadores con múltiples componentes donde el resultado API no es el valor a comparar contra la meta.

#### 4.1.3 SUM_SER (Suma de series)

```python
# Sumar todas las series disponibles
sum_meta = Σ(serie.meta for serie in series)
sum_ejec = Σ(serie.resultado for serie in series)

if sum_ejec > 0:
    meta = sum_meta
    ejec = sum_ejec
    fuente = 'series_sum'
```

**Cuándo usar**: Indicadores multiserie donde el cumplimiento se calcula sobre el agregado.

#### 4.1.4 AVG / SUM (Promedio/Suma)

```python
# En histórico mensual: usar resultado API directo
# En semestral/cierre: aplicar agregación posterior
resultado_num = pd.to_numeric(resultado, errors='coerce')
meta_num = pd.to_numeric(meta, errors='coerce')
```

### 4.2 Heurística Automática

Cuando no hay configuración explícita (`config_patrones`):

```python
# Detectar indicadores grandes con meta porcentaje
es_grande = (hist_meta_escala > 1000)  # Meta histórica mediana > 1000
api_es_porcentaje = (abs(meta_api) <= 200)  # Meta API es porcentaje

if es_grande and api_es_porcentaje:
    # Buscar en variables primero, luego en series
    if variables_disponibles:
        extraer_de_variables()
    elif series_disponibles:
        sumar_series()
    else:
        skip  # No hay datos suficientes
else:
    # Usar resultado API directo
    usar_api_directo()
```

---

## 5. Detección de No Aplica (N/A)

### 5.1 Criterios de N/A

Un registro se marca como **No Aplica** cuando:

```python
def is_na_record(row):
    """
    Criterio 1: Análisis explícito
    """
    if 'no aplica' in analisis.lower():
        return True
    
    """
    Criterio 2: Sin resultado + Sin datos útiles
    """
    if resultado is NaN and not tiene_datos_utiles(row):
        return True
    
    return False
```

### 5.2 Datos Útiles (`_tiene_datos_utiles`)

```python
def _tiene_datos_utiles(row):
    # Verificar variables con valores no-NaN
    if variables:
        for var in variables:
            if var.valor is not None and not NaN:
                return True
    
    # Verificar series con resultado/meta no-NaN
    if series:
        for serie in series:
            if serie.resultado is not None and not NaN:
                return True
            if serie.meta is not None and not NaN:
                return True
    
    return False
```

### 5.3 Tratamiento de N/A

| Campo | Valor | Descripción |
|-------|-------|-------------|
| `Ejecucion` | `None` | Celda vacía en Excel |
| `Ejecucion_Signo` | `'No Aplica'` | Texto literal |
| `Cumplimiento` | `''` | Vacío (fórmula Excel) |
| `Cumplimiento Real` | `''` | Vacío (fórmula Excel) |
| `Meta` | Valor API (si existe) | Conservar meta si está disponible |

---

## 6. Procesamiento de JSON (Variables y Series)

### 6.1 Parseo Seguro

```python
def parse_json_safe(val):
    """
    Convierte string JSON a objeto Python de forma segura.
    
    Entradas posibles:
        - "[{'valor': 100, 'nombre': 'Real'}]"
        - "[{'meta': 100, 'resultado': 95}]"
        - None / NaN / ''
    
    Salida:
        - Lista de diccionarios o None
    """
    if pd.isna(val) or val == '' or val is None:
        return None
    
    try:
        return ast.literal_eval(str(val))  # Seguro vs eval()
    except:
        return None
```

### 6.2 Extracción de Variables

```python
def extraer_meta_ejec_variables(vars_list):
    """
    Estrategia de extracción por prioridad:
    
    1. Buscar por keywords en nombre
       - Meta: ['planeado', 'presupuestado', 'propuesto', ...]
       - Ejec: ['real', 'ejecutado', 'recaudado', ...]
    
    2. Si no se encuentra meta y hay ≥2 variables:
       - meta = variables[1]  # Segunda posición
    
    3. Si no se encuentra ejec y hay ≥1 variable:
       - ejec = variables[0]  # Primera posición
    
    Retorna: (meta_val, ejec_val)
    """
```

### 6.3 Extracción por Símbolo

```python
def extraer_por_simbolo(vars_list, simbolo):
    """
    Busca variable específica por símbolo exacto (case-insensitive).
    
    Ejemplo:
        variables = [
            {'simbolo': 'R', 'valor': 95},
            {'simbolo': 'M', 'valor': 100}
        ]
        extraer_por_simbolo(variables, 'R') → 95.0
    """
```

---

## 7. Agregaciones Semestrales y Cierres

### 7.1 Tipos de Cálculo por Periodicidad

| Periodicidad | Períodos | Fechas de Cierre |
|--------------|----------|-------------------|
| **Mensual** | 12 (ene-dic) | Último día de cada mes |
| **Trimestral** | 4 (mar, jun, sep, dic) | 31/03, 30/06, 30/09, 31/12 |
| **Semestral** | 2 (jun, dic) | 30/06, 31/12 |
| **Bimestral** | 6 (feb, abr, jun, ago, oct, dic) | Último día cada 2 meses |
| **Anual** | 1 (dic) | 31/12 |

### 7.2 Cálculo de Agregados

#### Cierre (TipoCalculo = 'Cierre')
```python
# Último período del año con datos
if diciembre_existe:
    usar_diciembre()
else:
    usar_ultimo_periodo_disponible()
```

#### Promedio (TipoCalculo = 'Promedio')
```python
# Promedio de Ejecución y Meta de todos los meses
ejec_promedio = mean([mes.ejec for mes in meses_del_año])
meta_promedio = mean([mes.meta for mes in meses_del_año])
```

#### Acumulado (TipoCalculo = 'Acumulado')
```python
# Suma de Ejecución y Meta de todos los meses
ejec_suma = sum([mes.ejec for mes in meses_del_año])
meta_suma = sum([mes.meta for mes in meses_del_año])
```

---

## 8. Materialización de Fórmulas Excel

### 8.1 Recálculo de Cumplimiento (`_materializar_cumplimiento`)

**Problema**: Las fórmulas Excel contienen referencias de celda (ej: `J1372`, `K1372`) que se desplazan al insertar/borrar filas, causando cálculos incorrectos.

**Solución**: Recalcular todas las filas en Python usando valores reales.

```python
def _materializar_cumplimiento(ws):
    """
    Para cada fila en la hoja:
        1. Leer Meta, Ejecucion, Sentido de celdas
        2. Si son fórmulas (empiezan con '='), ignorar
        3. Calcular cumplimiento con _calc_cumpl()
        4. Escribir resultado con formato 0.00%
    """
    for row in ws.iter_rows(min_row=2):
        meta = row[col_meta].value
        ejec = row[col_ejec].value
        sentido = row[col_sentido].value or 'Positivo'
        
        cumpl_capped, cumpl_real = _calc_cumpl(meta, ejec, sentido)
        
        row[col_cumpl].value = cumpl_capped
        row[col_cumpl].number_format = '0.00%'
        
        if col_cumpl_real:
            row[col_cumpl_real].value = cumpl_real
            row[col_cumpl_real].number_format = '0.00%'
```

### 8.2 Materialización de Fechas

```python
def _materializar_formula_año(ws):
    """
    Reemplaza fórmulas de Año, Mes, Semestre, LLAVE por valores calculados.
    
    Formulas reemplazadas:
        - Año: =YEAR(Fecha) → 2024
        - Mes: =TEXT(Fecha, "MMMM") → "Marzo"
        - Semestre: =Año & "-" & IF(MES<=6, 1, 2) → "2024-1"
        - LLAVE: =Id & "-" & Año & "-" & Mes & "-" & Dia → "123-2024-03-31"
    """
```

---

## 9. Deduplicación y Limpieza

### 9.1 Generación de LLAVE

```python
def make_llave(id_val, fecha):
    """
    Genera clave única para identificar registros duplicados.
    
    Formato: "{id}-{año}-{mes:02d}-{día:02d}"
    Ejemplo: "123-2024-03-31"
    
    Normalizaciones:
        - ID "123.0" → "123"
        - Fecha convertida a datetime
    """
```

### 9.2 Deduplicación

```python
def deduplicar_sheet(ws, sheet_name):
    """
    Elimina filas duplicadas manteniendo la primera ocurrencia.
    
    Criterio de duplicación: Columna LLAVE idéntica
    
    Proceso:
        1. Leer todas las filas
        2. Trackear LLAVEs vistas
        3. Si LLAVE ya vista → eliminar fila
        4. Si LLAVE nueva → mantener, registrar
    """
```

### 9.3 Limpieza de Cierres

```python
def limpiar_cierres_existentes(ws):
    """
    Deja solo el registro más reciente por (Id, Año).
    
    Útil para: Mantener solo el cierre anual actualizado.
    
    Criterio: Fecha más reciente dentro del año.
    """
```

---

## 10. Configuración de Patrones (`Config_Patrones`)

### 10.1 Estructura de Configuración

La hoja `Config_Patrones` en el Excel de salida permite configurar extracción por indicador:

| Columna | Descripción | Ejemplo |
|---------|-------------|---------|
| `Id` | Identificador del indicador | "123" |
| `Patron_Ejecucion` | Patrón a usar | "VARIABLES", "LAST", "SUM_SER" |
| `Simbolo_Ejec` | Símbolo para ejecución | "R", "EJEC", "REAL" |
| `Simbolo_Meta` | Símbolo para meta | "M", "META", "OBJ" |

### 10.2 Reglas de Configuración

```python
# Si un indicador NO está en Config_Patrones:
#   → Usar heurística automática

# Si indicador está en Config_Patrones:
#   → Usar patrón configurado
#   → Usar símbolos configurados (si aplica)
```

---

## 11. Flujo Completo del Proceso

### 11.1 Secuencia de Ejecución (método `main`)

```
Paso 1: Carga de Fuentes
   ├─ Cargar API Consolidada
   ├─ Cargar Kawak 2025 (si existe)
   └─ Cargar archivo base (3 hojas)

Paso 2: Carga de Metadatos
   ├─ IDs válidos Kawak
   ├─ Metadatos de indicadores
   ├─ Config_Patrones
   └─ IDs tipo Métrica

Paso 3: Preparación
   ├─ Enriquecer datos con metadatos
   ├─ Expandir variables, series, análisis
   └─ Calcular escalas históricas

Paso 4: Procesamiento Histórico
   ├─ Para cada registro API:
   │   ├─ ¿Es N/A? → Marcar y continuar
   │   ├─ Determinar extractor
   │   ├─ Extraer meta/ejec
   │   ├─ Calcular cumplimiento
   │   └─ Agregar a registros históricos
   └─ Escribir en hoja Consolidado Historico

Paso 5: Procesamiento Semestral
   ├─ Agregar mensuales por semestre
   ├─ Aplicar Promedio/Acumulado según TipoCalculo
   └─ Escribir en hoja Consolidado Semestral

Paso 6: Procesamiento Cierres
   ├─ Agregar por año
   ├─ Seleccionar último período
   └─ Escribir en hoja Consolidado Cierres

Paso 7: Post-procesamiento
   ├─ Materializar fórmulas
   ├─ Deduplicar por LLAVE
   ├─ Limpiar cierres (1 por Id+Año)
   └─ Reescribir fórmulas con referencias correctas

Paso 8: Generación de Hojas Adicionales
   ├─ Desglose Variables
   ├─ Desglose Series
   ├─ Desglose Análisis
   ├─ Catálogo Indicadores
   ├─ Base Normalizada
   └─ Config_Patrones (si no existe)

Paso 9: Guardado
   └─ Guardar workbook con todas las hojas
```

### 11.2 Métricas de Salida

Al finalizar, el script reporta:

```
RESUMEN FINAL:
  Histórico:  +{n} filas  ({na} N/A)
  Semestral:  +{n} filas  ({na} N/A)
  Cierres:    +{n} filas  ({na} N/A)
  Total 'No Aplica' marcados: {total_na}
  Hojas nuevas: Desglose Variables, Desglose Series, ...
```

---

## 12. Notas Técnicas Importantes

### 12.1 Manejo de Errores

| Error | Estrategia |
|-------|------------|
| **Archivo no encontrado** | Mensaje `[ERROR]` + fallback vacío |
| **Columna no encontrada** | Búsqueda por nombre similar (case-insensitive) |
| **Parseo JSON fallido** | Retornar None, continuar con siguiente registro |
| **Conversión numérica fallida** | `pd.to_numeric(errors='coerce')` → NaN |
| **División por cero** | Retornar (None, None) |

### 12.2 Optimizaciones

1. **Caché**: No implementado explícitamente, pero DataFrames se mantienen en memoria
2. **Vectorización**: Algunas operaciones usan pandas nativo
3. **Procesamiento por lotes**: No implementado (oportunidad de mejora)
4. **Paralelización**: No implementado (oportunidad de mejora)

### 12.3 Dependencias Críticas

```python
import pandas as pd      # Manipulación de datos
import numpy as np      # Cálculos numéricos
import openpyxl         # Lectura/escritura Excel
import ast              # Parseo seguro de JSON
import calendar         # Cálculo de días en mes
```

---

## 13. Glosario

| Término | Definición |
|---------|------------|
| **Meta** | Valor objetivo o planificado del indicador |
| **Ejecución** | Valor real alcanzado |
| **Cumplimiento** | Porcentaje de ejecución vs meta |
| **Sentido** | Dirección del indicador (Positivo: más es mejor; Negativo: menos es mejor) |
| **Variables** | Componentes individuales que desglosan un indicador |
| **Series** | Múltiples valores temporales del mismo indicador |
| **N/A** | No Aplica - período donde el indicador no se mide |
| **LLAVE** | Identificador único compuesto: Id-Fecha |
| **Cierre** | Registro anual consolidado (31 de diciembre) |
| **Config_Patrones** | Configuración por indicador del método de extracción |
| **TipoCalculo** | Método de agregación (Cierre, Promedio, Acumulado) |

---

## 14. Referencias

- **Archivo original**: `scripts/actualizar_consolidado.py` (3,140 líneas)
- **Versión modular**: `scripts/consolidation/` (nueva arquitectura)
- **Tests**: `tests/consolidation/test_utils.py`

---

*Documento generado: Marzo 2026*  
*Para consultas técnicas, referirse al equipo de Data Science*
