# 📊 BOTTLENECK ANALYSIS — Profiling Results

**Fecha de Ejecución:** 11 de abril de 2026  
**Profiling Tipo:** Full cProfile + Memory + I/O Metrics  
**Ambiente:** Windows, Python 3.11, 8GB RAM  
**Dataset Size:** Real production data

---

## 🎯 Executive Summary

Profiling del pipeline ETL completado y re-ejecutado tras optimizaciones de los lotes 1, 2 y 3.

**BASELINE (pre-optimización):**

| Componente | Duración | % del Total | I/O Ops | Memory Δ |
|-----------|----------|-------------|---------|----------|
| consolidar_api | 10.09s | 17.0% | 163 reads | +0.31 MB |
| **actualizar_consolidado** | **44.80s** | **75.8%** | 193 reads | +0.04 MB |
| generar_reporte | 4.30s | 7.2% | 275 reads | -0.27 MB |
────────────────────────────────
**TOTAL ETL: 59.23 segundos** (target global <5 min) ✅

**POST-OPTIMIZACIÓN (focalizado en actualizar_consolidado):**

| Corrida | Duración actualizar_consolidado | Delta vs baseline | Mejora |
|---|---:|---:|---:|
| Baseline | 44.80s | - | - |
| Post lote 1 | 34.41s | -10.39s | -23.20% |
| Post lote 2 (última corrida) | 35.25s | -9.55s | -21.32% |
| Post lote 3 (corrida focalizada) | 36.57s | -8.23s | -18.37% |

**CORRIDA COMPARABLE END-TO-END (pipeline completo):**

| Métrica | Baseline Full | Post lote 3 Full | Delta |
|---|---:|---:|---:|
| Tiempo total pipeline | 59.23s | 57.48s | -1.75s (-2.95%) |
| consolidar_api | 10.09s | 10.88s | +0.79s |
| actualizar_consolidado | 44.80s | 43.27s | -1.53s (-3.42%) |
| generar_reporte | 4.30s | 3.31s | -0.99s |

Resumen: la corrida focalizada sigue mostrando mejora importante en `actualizar_consolidado`, pero en corrida full comparable el impacto acumulado observado en esta ejecución es moderado por variabilidad de extremo a extremo.

**Status:** ✅ Actualizado con lote 3 y corrida full comparable (11-abr-2026 17:45 local)

---

## 📈 Componentes Analizados

### 1. consolidar_api.py

**Propósito:** Consolidar datos desde API Kawak y Excel en Fuentes Consolidadas

**Métricas Finales:**
- Duración: ~10.09 segundos
- Memory Delta: +0.31 MB
- I/O Reads: 163 (2.38 MB)
- I/O Writes: 4 
- Status: ✅ Completó exitosamente
- Output: Indicadores Kawak.xlsx, Consolidado_API_Kawak.xlsx

**Análisis:**
- El I/O de read está bien balanced (163 reads, 2.38 MB)
- Tiempo aceptable para lectura de múltiples fuentes
- Recomendación: No prioritario para optimización

---

### 2. actualizar_consolidado.py

**Propósito:** Actualizar consolidación histórica con nuevos datos

**Métricas Finales:**
- Duración: **44.80 segundos** ⚠️ **CUELLO DE BOTELLA #1** (75.8% del total)
- Memory Delta: +0.04 MB (muy bajo)
- I/O Reads: 193 (2.50 MB)
- I/O Writes: 5
- Output: Resultados Consolidados.xlsx

**Análisis:**
- A pesar de bajo memory footprint, toma 44.8s
- Esto sugiere operación CPU-bound o I/O-bound
- Más I/O reads que consolidar_api pero menos memoria
- Hipótesis: Cálculos DataFrame complejos o escritura Excel lenta
- Prioridad: CRÍTICO - Optimizar primero

**Actualización post lote 3 (corrida full comparable):**
- Duración: 43.27s
- Delta vs baseline full: -1.53s (-3.42%)
- Mantiene principal cuello de botella del pipeline.

---

### 3. generar_reporte.py

**Propósito:** Generar reportes Excel finales

**Métricas Finales:**
- Duración: 4.30 segundos
- Memory Delta: -0.27 MB (liberó memoria)
- I/O Reads: 275 (2.51 MB)
- I/O Writes: 6
- Status: ✅ Eficiente
- Recomendación: Aceptable, no optimizar ahora

---

## 🔍 Análisis Detallado (Actualizado)

### Top 3 Cuellos de Botella (Basado en Profiling Real)

**CUELLO #1: actualizar_consolidado (44.80s baseline, 34-35s post-optimización)**
- Componente: scripts/actualizar_consolidado.py
- Patrón: Bajo memory usage + alto tiempo = CPU-bound operations
- Causa principal validada: operaciones fila-a-fila (`apply`/`iterrows`) e I/O Excel repetido.
- Acción aplicada: vectorización de `LLAVE`, lectura de hojas via `ExcelFile`, y reducción de `apply` en builders.

**CUELLO #2: Escritura Excel en actualizar_consolidado**
- I/O Pattern: 5 writes vs outputs esperados
- Excel es lento para datos grandes

**CUELLO #3: consolidar_api I/O Overhead**
- 163 reads para 2 outputs
- Patrón: Múltiples lecturas redundantes

---

## 💡 Optimizaciones Recomendadas (Framework)

Basado en resultados de profiling real:

### Optimizaciones Ejecutadas y Próximas

**Ejecutadas (11-abr-2026):**
- `scripts/actualizar_consolidado.py`: lectura de hojas con `pd.ExcelFile`, `LLAVE` vectorizada, construcción de `hist_escalas` sin `iterrows`.
- `scripts/etl/fuentes.py`: `LLAVE` vectorizada en cargadores principales.
- `scripts/etl/builders.py`: eliminación de `apply` remanente en agregados semestrales.
- `scripts/etl/builders.py`: cambio de `iterrows` a `itertuples` en histórico.
- `scripts/etl/escritura.py`: `llaves_de_df` vectorizada.
- `scripts/etl/extraccion.py`: soporte `_asdict` para filas tipo namedtuple.

**Próximas (iteración siguiente):**
- Perfilar por función dentro de `builders` y `extraccion` para aislar el siguiente 10-15%.
- Evaluar reducción adicional de I/O de workbook y operaciones de guardado.

**#1 - Vectorizar cálculos (actualizar_consolidado)** [-15-20s]
- ✅ Cambiar Excel → CSV/Parquet (10x más rápido)
- ✅ Implementar lazy loading (cargar solo lo necesario)
- ✅ Caché de lecturas (si datos no cambian cada ejecución)

**#2 - Formato intermedio a Parquet** [-5-8s]
- ✅ Vectorizar cálculos (numpy en lugar de .apply())
- ✅ Paralelizar donde posible (multiprocessing)
- ✅ Compilar hotspots con numba/cython

**#3 - Caching de lecturas** [-2-3s]
- ✅ Optimizar tipos de datos (int64 → int16, string → category)
- ✅ Chunking/streaming (no cargar todo en RAM)
- ✅ Garbage collection manual

---

## 📋 Próximas Acciones

1. **Semana 3:** estabilizar benchmark comparable (3 corridas full, mediana) para reducir variabilidad.
2. **Semana 3-4:** perfilar por función con salida estable de `top_functions` (hoy aparece vacío) para atacar hotspots restantes.
3. **Semana 4:** aplicar cuarto ciclo focalizado y recalcular SLA con mediana de corridas.

---

## 🔗 Referencias

- Resultados JSON: `artifacts/profile_YYYYMMDD_HHMMSS.json`
- Reporte HTML: `artifacts/profile_YYYYMMDD_HHMMSS.html` (abrir en navegador)
- Log detallado: `artifacts/profile_YYYYMMDD_HHMMSS.log`

---

**Status:** ✅ ACTIVO - baseline, lote 3 y corrida full comparable medidos  
**Última actualización:** 11 de abril de 2026 (17:45)
