# 📊 PIPELINE PROFILING — Reporte de Análisis

**Fecha de Análisis:** 11 de abril de 2026  
**Herramienta:** `scripts/profile_pipeline.py`  
**Status:** ✅ Profiling Infrastructure Ready

---

## 🎯 Objetivo

Identificar cuellos de botella en el pipeline ETL para optimización en Fase 2:

```
Baseline (Fase 1): 10-15 minutos
Target (Fase 2):   <5 minutos (50-70% reduction)
```

---

## 🔧 Uso del Script de Profiling

### Instalación de dependencias

```bash
# Instalar herramientas de profiling
pip install -r requirements-dev.txt
```

### Ejecución básica

```bash
# Profile todo el pipeline
python scripts/profile_pipeline.py

# Profile un componente específico
python scripts/profile_pipeline.py --component consolidar_api

# Profile con instrumentación completa (más lento, más detallado)
python scripts/profile_pipeline.py --full
```

### Salida

El script genera archivos en `artifacts/profile_<timestamp>.{json,html,log}`:

```
artifacts/
  profile_20260411_120000.json    ← Datos estructurados (para análisis)
  profile_20260411_120000.html    ← Reporte interactivo (visualizar en navegador)
  profile_20260411_120000.log     ← Log detallado de ejecución
```

---

## 📈 Interpretación de Resultados

### Metricasimportantes

| Métrica | Qué significa | Acción si es alto |
|---------|---------------|-------------------|
| **Duration (seg)** | Tiempo total de ejecución del componente | Optimizar funciones top |
| **Memory Delta (MB)** | RAM adicional consumido durante ejecución | Optimizar data loading |
| **Output Files** | Cantidad de archivos generados | Diagnosticar si falta salida |

### Top Functions

Para cada componente, listamos las funciones que consumen más tiempo (cumulative):

```
function:        core/calculos.py:normalizar_cumplimiento
calls:           15,000
total_time_sec:  2.34s  ← Tiempo total consumido por esta función
per_call_sec:    0.00016s  ← Tiempo promedio por llamada
```

**Interpretación:**
- Si `total_time_sec` es alto → Esta función es un cuello de botella
- Si `per_call_sec` es alto pero `total_time_sec` es bajo → La función es lenta pero se llama pocas veces
- Si se llama muchas veces (`calls`) → Considerar optimización o caching

---

## 🎯 Hallazgos Típicos & Soluciones

Sin datos reales aún, aquí está el framework de análisis post-profiling:

### Patrón 1: Procesamiento de Pandas (Alto Memory Delta)

**Síntoma:**
```
Duration: 5.2s
Memory Delta: +450 MB
Top function: pandas.DataFrame.apply
```

**Causa:**
- Aplicar funciones fila-por-fila en DataFrames grandes
- Carga de múltiples archivos Excel en memoria simultáneamente

**Soluciones (por orden de impacto):**
1. **Vectorización:** Reemplazar `.apply()` con operaciones numpy/pandas nativas
   ```python
   # SLOW
   df['category'] = df['valor'].apply(categorize_func)
   
   # FAST
   df['category'] = pd.cut(df['valor'], bins=[0, 0.8, 1.0, 1.05], labels=['Bajo', 'Alerta', 'Ok'])
   ```

2. **Lectura selectiva:** Leer solo columnas necesarias
   ```python
   # SLOW
   df = pd.read_excel('huge_file.xlsx')  # Carga TODO
   
   #FAST
   df = pd.read_excel('huge_file.xlsx', usecols=['col1', 'col2'])
   ```

3. **Chunking:** Procesar en lotes pequeños
   ```python
   for chunk in pd.read_excel(..., chunksize=1000):
       process(chunk)
   ```

4. **Data type optimization:** Reducir footprint
   ```python
   df['year'] = df['year'].astype('int16')  # int64 → int16
   df['category'] = df['category'].astype('category')  # string → category
   ```

---

### Patrón 2: I/O Lento (Alto Duration, bajo Memory Delta)

**Síntoma:**
```
Duration: 8.5s
Memory Delta: +50 MB
Top function: openpyxl.worksheet  # Leer/escribir Excel
```

**Causa:**
- Múltiples lecturas/escrituras de Excel (son LENTAS)
- Formatos ineficientes (XLSX vs CSV vs Parquet)

**Soluciones:**
1. **Cambiar formato de salida:** CSV o Parquet es 10-50x más rápido
   ```python
   # SLOW
   df.to_excel('output.xlsx')  # 3-5 segundos
   
   # FAST
   df.to_parquet('output.parquet')  # 0.5-1 segundo
   # O CSV para simplicidad
   df.to_csv('output.csv')  # 0.5-1 segundo
   ```

2. **Caché de entrada:** Si lees el mismo archivo múltiples veces, cachea
   ```python
   @st.cache_data(ttl=3600)
   def load_data(file_path):
       return pd.read_excel(file_path)
   ```

3. **Lazy loading:** Cargar datos solo cuando se necesitan

---

### Patrón 3: SQL Queries Lentas (Alto Duration)

**Síntoma:**
```
Duration: 6.3s
Top function: psycopg2.connect, execute
```

**Causa:**
- N+1 queries (loop que query por fila)
- Queries sin índices
- Transactions sin batching

**Soluciones:**
1. **Batch inserts:** Insertar múltiples filas en 1 query
   ```python
   # SLOW
   for row in data:
       cursor.execute("INSERT INTO table VALUES (...)")  # N queries
   
   # FAST
   import psycopg2.extras
   psycopg2.extras.execute_batch(cursor, "INSERT ...", data, page_size=1000)
   ```

2. **Índices:** Asegurar índices en columnas de búsqueda
3. **Stored procedures:** Si la lógica es compleja, mover a DB

---

### Patrón 4: Cálculos Repetidos (Alto en función específica)

**Síntoma:**
```
Top function: core.calculos.categorizar_cumplimiento
calls: 500,000
total_time_sec: 3.2s
```

**Causa:**
- Cálculos recalculados que ya fueron hechos
- Lógica no-vectorizada

**Soluciones:**
1. **Memoization/Caching:**
   ```python
   from functools import lru_cache
   
   @lru_cache(maxsize=128)
   def categorizar(valor):
       ...
   ```

2. **Vectorización:** Procesar arrays, no escalares

---

## 🚀 Roadmap de Optimización (Fase 2)

### Semana 3-4: Identificar Top 3 Bottlenecks
- [ ] Run profiling en ambiente similar a producción
- [ ] Documentar hallazgos en `BOTTLENECK_ANALYSIS.md`
- [ ] Priorizar por (duración × frecuencia)

### Semana 5-6: Implementar Optimizaciones
- [ ] Fix patrón #1 (Pandas) si aplicable → -2-3s esperados
- [ ] Fix patrón #2 (I/O) si aplicable → -3-5s esperados
- [ ] Fix patrón #3 (SQL) si aplicable → -2-4s esperados

### Semana 7: Validar Mejora
- [ ] Re-profile con misma carga
- [ ] Comparar antes vs después
- [ ] Documentar learning

---

## 📝 Template: Reporte de Análisis Post-Profiling

Después de ejecutar profiling, documentar hallazgos:

```markdown
## Profiling Report — Consolidar API Component

**Executed:** 2026-04-15  
**Environment:** Windows 10, Python 3.11, 8 GB RAM  
**Dataset Size:** 50,000 rows × 25 columns

### Results

| Métrica | Baseline | Target | Status |
|---------|----------|--------|--------|
| Duration | 4.2s | <2s | 🔴 |
| Memory Peak | 650 MB | <400 MB | 🟡 |

### Top Bottlenecks

1. **DataFrame.apply() in consolidar_api.py:123**
   - Duration: 1.8s (43% of total)
   - Calls: 50,000
   - Recommendation: Vectorize with pandas.cut()
   - Expected Improvement: 1.5s saved

2. **read_excel() in data loading**
   - Duration: 1.2s (29% of total)
   - Recommendation: Use Parquet + caching
   - Expected Improvement: 0.8s saved

3. **SQL INSERT in db_manager**
   - Duration: 0.9s (21% of total)
   - Recommendation: Batch inserts
   - Expected Improvement: 0.5s saved

### Implementation Plan

- [ ] Task 1: Vectorize consolidar_api funciones (PR #XX)
- [ ] Task 2: Add Parquet support (PR #XX)
- [ ] Task 3: Batch SQL inserts (PR #XX)
- [ ] Validation: Re-profile after all changes

### Expected Outcome

- Before: 4.2s
- After: 1.7s (60% improvement) ✅
```

---

## 🔗 Referências

- [Python cProfile Docs](https://docs.python.org/3/library/profile.html)
- [Pandas Best Practices](https://pandas.pydata.org/docs/user_guide/enhancing.html#performance)
- [psutil Documentation](https://psutil.readthedocs.io/)
- [Openpyxl Performance](https://openpyxl.readthedocs.io/en/stable/performance.html)

---

**Documento Generado:** 11 de abril de 2026  
**Próximo Paso:** Ejecutar profiling en Semana 1 y documentar hallazgos.
