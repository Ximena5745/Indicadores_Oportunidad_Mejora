# Documento Técnico: Lógica de `actualizar_consolidado.py`

## 1. Resumen del Flujo

El script `actualizar_consolidado.py` es el **orquestador principal del ETL** que actualiza el archivo `Resultados Consolidados.xlsx`. Toda la lógica de negocio reside en módulos `scripts/etl/`.

---

## 2. Arquitectura del Pipeline

```
scripts/consolidar_api.py (PRE-REQUISITO)
    │
    ▼
[Fuentes API + Kawak] → cargar_fuente_consolidada()
    │
    ▼
actualizar_consolidado.py (ORQUESTADOR)
    │
    ├──► 1. Cargar fuente consolidada (df_api)
    ├──► 2. Cargar catálogo completo
    ├──► 3. Cargar metadatos y catálogos auxiliares
    ├──► 4. Cargar config_patrones
    ├──► 5. Abrir workbook de salida
    ├──► 6. Leer hojas existentes (signos)
    ├──► 7. Purga de filas inválidas
    ├──► 8. Construir escalas históricas
    ├──► 9. Preparar fuentes para builders
    ├──► 10. Construir nuevos registros (HISTÓRICO, SEMESTRAL, CIERRES)
    ├──► 11. Escribir nuevas filas
    ├──► 12. Reparar valores vacíos
    ├──► 13. Deduplicar y reescribir fórmulas
    ├──► 14. Actualizar Catálogo Indicadores
    └──► 15. Guardar
```

---

## 3. Módulos ETL y Responsabilidades

| Módulo | Responsabilidad |
|--------|----------------|
| `config.py` | Configuración centralizada (año cierre, IDs especiales, rutas) |
| `fuentes.py` | Carga de fuentes externas (API, Kawak, catálogos) |
| `catalogo.py` | Construcción del catálogo de indicadores |
| `builders.py` | Constructores de registros para Histórico, Semestral, Cierres |
| `extraccion.py` | Lógica de extracción de valores (Meta, Ejecución) |
| `signos.py` | Obtención de signos (+/-) por indicador |
| `formulas_excel.py` | Reescritura de fórmulas Excel y materialización |
| `escritura.py` | Escritura de filas al workbook |
| `purga.py` | Reparación de valores vacíos, deduplicación |
| `normalizacion.py` | Utilidades de normalización (IDs, fechas, llaves) |
| `periodos.py` | Utilidades de fechas y periodicidades |
| `cumplimiento.py` | Cálculo de cumplimiento |
| `desglose.py` | Desglose de series y variables |

---

## 4. Lógica de Negocio Clave

### 4.1 Concepto de "No Aplica"

**Definición:** Un indicador marca "No Aplica" cuando NO corresponde medirlo en un período específico (estacionalidad, fase del proyecto, etc.). **No es un error ni un dato faltante.**

**Detección:**
1. El campo `analisis` contiene "no aplica" → `es_na = True`
2. `resultado = NaN` Y sin datos en variables/series → `es_na = True`

**Escritura en consolidado:**
| Campo | Valor |
|-------|-------|
| Ejecución (K) | `None` (celda vacía) |
| Ejecución_Signo (O) | `"No Aplica"` |
| Cumplimiento (L) | `""` (fórmula) |
| Meta (J) | Se conserva si existe, `None` si no |

### 4.2 Construcción de Llaves (LLAVE)

La **LLAVE** es el identificador único de cada registro: `Id + Fecha`.

```
LLAVE = Id + "-" + AÑO + "-" + MES + "-" + DÍA
Ejemplo: "68-2024-06-30"
```

### 4.3 Flujo de Extracción de Valores

```
_extraer_registro(row, hist_escalas, ...)
    │
    ├──► Detectar tipo de indicador (VARIABLES, SERIES, DIRECTO, SIMBOLO)
    ├──► Extraer Meta y Ejecución según tipo
    ├──► Detectar si es "No Aplica"
    └──► Retornar (meta, ejec, fuente, es_na)
```

### 4.4 Tipos de Indicadores y Cálculo

| Tipo | Descripción | Cálculo |
|------|-------------|---------|
| `DIRECTO` | Valor directo del resultado | `resultado` |
| `VARIABLES` | Variable con símbolo | `_calc_ejec_series()` |
| `SERIES` | Serie con múltiples valores | `_calc_ejec_series()` + suma/promedio |
| `SUM` | Acumulado semestral | Suma de meses |
| `AVG` | Promedio semestral | Promedio de meses |

### 4.5 Cálculo de Cumplimiento (Fórmula Excel)

```excel
=IFERROR(
  IF(OR(J=0, K=""), "",
    IF(E="Positivo",
      MIN(MAX(K/J, 0), 1.3),   -- Cumplimiento positivo: min 0, max 1.3
      MIN(MAX(J/K, 0), 1.3)    -- Cumplimiento negativo: min 0, max 1.3
    )
  ),
"")
```

**Interpretación:**
- Si `Sentido = "Positivo"`: `Cumplimiento = Ejecución / Meta`
- Si `Sentido = "Negativo"`: `Cumplimiento = Meta / Ejecución`
- Tope: `1.3` (130%) para ambos casos
- Si Meta o Ejecución vacíos → `""`

### 4.6 Semaforización (Implícita)

| Rango | Nivel |
|-------|-------|
| < 70% | 🔴 Crítico |
| 70-80% | 🟡 Atención |
| 80-105% | 🟢 Normal |
| 105-120% | 🟡 Atención |
| > 120% | 🔴 Crítico |

---

## 5. Flujo de Datos Detallado

### 5.1 Carga de Fuentes

```
cargar_fuente_consolidada()
    │
    └──► Lee: data/raw/Fuentes Consolidadas/Consolidado_API_Kawak.xlsx
           (Generado por consolidar_api.py)
           │
           └──► Columnas normalizadas: ID→Id, nombre→Indicador, etc.
```

### 5.2 Lectura de Hojas Existentes

```
df_hist_ex    = pd.read_excel(OUTPUT_FILE, sheet_name="Consolidado Historico")
df_sem_ex     = pd.read_excel(OUTPUT_FILE, sheet_name="Consolidado Semestral")
df_cierres_ex = pd.read_excel(OUTPUT_FILE, sheet_name="Consolidado Cierres")
    │
    └──► Se usan para:
           - Obtener signos existentes (obtener_signos())
           - Construir escalas históricas (hist_escalas)
           - Conocer llaves ya existentes (llaves_de_df())
           - Evitar duplicados
```

### 5.3 Purga de Filas Inválidas

```
purgar_filas_invalidas(ws, nom, kawak_validos)
    │
    └──► Elimina filas cuyo Id no esté en kawak_validos
         (kawak_validos = conjunto de (Id, Año) válidos)
```

### 5.4 Construcción de Registros

**Histórico:**
```
construir_registros_historico(df_api, llaves_hist, hist_escalas, ...)
    │
    ├──► Filtra: registros nuevos (no en llaves_hist)
    ├──► Valida: (Id, Año) en kawak_validos
    ├──► Extrae: Meta, Ejecución, fuente, es_na
    └──► Retorna: (registros, skipped, conteo_na)
```

**Semestral:**
```
construir_registros_semestral(df_api, llaves_sem, hist_escalas, ...)
    │
    ├──► Indicadores estándar: usa último período del semestre (jun/dic)
    ├──► Indicadores AVG: promedia meses del semestre
    ├──► Indicadores SUM: suma meses del semestre
    └──► Retorna: (registros, skipped, conteo_na)
```

**Cierres:**
```
construir_registros_cierres(df_api, hist_escalas, ...)
    │
    ├──► Similar a semestral
    ├──► Cierres por año específico
    └──► Retorna: (registros, skipped, conteo_na)
```

### 5.5 Escritura y Reparación

```
escribir_filas(ws, regs_hist, signos, ids_metrica)
    │
    └──► Escribe nuevas filas al workbook

reparar_meta_vacia(ws, api_kawak_lookup, nom)
    │
    └──► Rellena Meta vacías desde api_kawak_lookup

reparar_multiserie(ws, api_kawak_lookup, tipo_calculo_map, nom)
    │
    └──► Repara indicadores multiserie

reparar_semestral_agregados(ws, df_api, extraccion_map, tipo_calculo_map, nom)
    │
    └──► Recalcula agregados (AVG/SUM) para semestral y cierres
```

### 5.6 Deduplicación y Fórmulas

```
deduplicar_sheet(ws, nom)
    │
    └──► Elimina filas duplicadas por LLAVE

_reescribir_formulas(ws)
    │
    └──► Reescribe fórmulas Excel (Año, Mes, Semestre, Cumplimiento, LLAVE)

_materializar_formula_año(ws)
    │
    └──► Convierte fórmulas de año a valores

_materializar_cumplimiento(ws)
    │
    └──► Calcula Cumplimiento desde Meta/Ejecución reales (no desde fórmulas)
         * USA openpyxl directamente, iterando celdas *
```

---

## 6. Áreas Críticas y Posibles Inconsistencias

### 6.1 Lectura con Fórmulas (Problema Detectado)

**Problema:** `pd.read_excel()` no evalúa fórmulas Excel. Las columnas `Cumplimiento`, `Año`, `Mes`, `Semestre` contienen fórmulas que no se calculan al leer.

**Impacto:** Los dashboards leen `data/output/Resultados Consolidados.xlsx` con pandas y obtienen celdas vacías o fórmulas en lugar de valores.

**Solución propuesta:**
1. Guardar con `data_only=True` al leer
2. O usar `openpyxl.load_workbook(data_only=True)`
3. O ejecutar macros de Excel para forzar cálculo

### 6.2 Normalización de Meta/Ejecución

**Problema potencial:** Los valores de Meta y Ejecución pueden venir como:
- Números (85.0)
- Strings ("85")
- NaN/None

**Verificar:** `nan2none()` y conversiones en `extraccion.py`

### 6.3hist_escalas - Metas desde Histórico

**Problema potencial:** Las metas se extraen del histórico existente (`df_hist_ex`) y se usan como fallback. Si el histórico tiene errores, estos se propagan.

### 6.4 API/Kawak Lookup

**Problema potencial:** `api_kawak_lookup` depende de `extraccion_map` que viene del catálogo. Si hay inconsistencias entre años, el lookup falla.

### 6.5 "No Aplica" - Detección

**Problema potencial:** La detección depende de:
1. Campo `analisis` conteniendo "no aplica"
2. `resultado = NaN` sin variables/series

**Verificar:** ¿Qué pasa si el texto es "N/A", "N/A.", "no aplica.", "NO APLICA"?

### 6.6 Deduplicación

**Problema potencial:** La deduplicación usa LLAVE (Id+Fecha). Si hay duplicados con fechas ligeramente diferentes, pueden pasar desapercibidos.

---

## 7. KPIs de Monitoreo

| Indicador | Descripción |
|-----------|-------------|
| `total_registros_fuente` | Registros en df_api |
| `regs_hist` | Nuevos registros históricos |
| `regs_sem` | Nuevos registros semestrales |
| `regs_cierres` | Nuevos registros de cierres |
| `skip_h/s/c` | Registros omitidos por tipo |
| `na_h/s/c` | Registros "No Aplica" por tipo |
| `kawak_validos` | Indicadores válidos en Kawak |

---

## 8. Lógica de Extracción Detallada (`extraccion.py`)

### 8.1 Keywords para Extracción

**Keywords de Ejecución:**
```python
KW_EJEC = [
    "real", "ejecutado", "recaudado", "ahorrado", "consumo", "generado",
    "actual", "logrado", "obtenido", "reportado", "hoy",
]
```

**Keywords de Meta:**
```python
KW_META = [
    "planeado", "presupuestado", "propuesto", "programado", "objetivo",
    "esperado", "previsto", "estimado", "acumulado plan",
]
```

### 8.2 Tipos de Extracción

| Constante | Descripción |
|-----------|-------------|
| `_EXT_SER_SUM_VAR` | Sumar variables de series, luego aplicar fórmula |
| `_EXT_SER_AVG_RES` | Aplicar fórmula a cada serie, luego promediar resultados |
| `_EXT_SER_AVG_VAR` | Promediar variables de series, luego aplicar fórmula |
| `_EXT_SER_SUM_RES` | Aplicar fórmula a cada serie, luego sumar resultados |
| `_EXT_DESGLOSE_SERIES` | Desglose de series |

### 8.3 Algoritmo `determinar_meta_ejec`

```python
def determinar_meta_ejec(row_api, hist_meta_escala, patron_cfg):
    """
    Determina (meta, ejec, fuente, es_na) para un registro.
    
    Fuentes posibles:
    - 'api_directo': resultado directo de la API
    - 'variables': extraído de JSON de variables
    - 'variables_simbolo': extraído por símbolo específico
    - 'series_sum': suma de series
    - 'series_sum_fallback': fallback a series
    - 'na_record': registro No Aplica
    - 'skip': omitir registro
    - 'sin_resultado': sin datos para extraer
    """
    
    # PASO 1: Verificar si es No Aplica
    if is_na_record(row_api):
        meta_api = row_api.get("meta")
        meta_val = nan2none(pd.to_numeric(meta_api, errors="coerce"))
        return meta_val, None, "na_record", True
    
    # PASO 2: Extraer datos del row
    resultado   = row_api.get("resultado")
    meta_api    = row_api.get("meta")
    vars_list   = parse_json_safe(row_api.get("variables"))
    series_list = parse_json_safe(row_api.get("series"))
    
    # PASO 3: Aplicar patrón configurado si existe
    if patron_cfg:
        patron = patron_cfg.get("patron", "LAST")
        
        if patron == "VARIABLES":
            # Extraer por símbolo o keywords
            sim_e = patron_cfg.get("simbolo_ejec", "")
            sim_m = patron_cfg.get("simbolo_meta", "")
            _meta_num = nan2none(pd.to_numeric(meta_api, errors="coerce"))
            
            if sim_e and vars_list:
                ejec_v = extraer_por_simbolo(vars_list, sim_e)
                if ejec_v is not None:
                    meta_v = extraer_por_simbolo(vars_list, sim_m) if sim_m else _meta_num
                    return meta_v, ejec_v, "variables_simbolo", False
            
            if vars_list:
                meta_v, ejec_v = extraer_meta_ejec_variables(vars_list)
                if ejec_v is not None:
                    return meta_v or _meta_num, ejec_v, "variables", False
            
            if series_list:
                sum_m, sum_r = extraer_meta_ejec_series(series_list)
                if sum_r is not None:
                    return sum_m or _meta_num, sum_r, "series_sum", False
            
            return None, None, "skip", False
        
        elif patron == "SUM_SER":
            if series_list:
                sum_m, sum_r = extraer_meta_ejec_series(series_list)
                if sum_r is not None:
                    return sum_m, sum_r, "series_sum", False
            return None, None, "skip", False
        
        # LAST / AVG / SUM: usar resultado directo
        resultado_num = pd.to_numeric(resultado, errors="coerce")
        if resultado_num is not None and not np.isnan(resultado_num):
            meta_val = nan2none(pd.to_numeric(meta_api, errors="coerce"))
            return meta_val, resultado_num, "api_directo", False
        
        return None, None, "sin_resultado", False
    
    # PASO 4: Lógica heurística (sin patrón configurado)
    es_grande = (hist_meta_escala is not None and hist_meta_escala > 1000)
    api_es_porcentaje = (not _es_vacio(meta_api) and abs(float(meta_api)) <= 200)
    
    # Caso especial: Meta grande pero API es porcentaje
    if es_grande and api_es_porcentaje:
        if vars_list:
            meta_v, ejec_v = extraer_meta_ejec_variables(vars_list)
            if ejec_v is not None:
                return meta_v, ejec_v, "variables", False
        if series_list:
            sum_m, sum_r = extraer_meta_ejec_series(series_list)
            if sum_r is not None:
                return sum_m, sum_r, "series_sum", False
        return None, None, "skip", False
    
    # Caso normal: usar resultado directo
    resultado_num = pd.to_numeric(resultado, errors="coerce")
    if resultado_num is None or np.isnan(resultado_num):
        # Fallback a series si resultado está vacío
        if series_list:
            sum_m, sum_r = extraer_meta_ejec_series(series_list)
            if sum_r is not None:
                return sum_m, sum_r, "series_sum_fallback", False
        return None, None, "sin_resultado", False
    
    meta_val = nan2none(pd.to_numeric(meta_api, errors="coerce"))
    return meta_val, resultado_num, "api_directo", False
```

### 8.4 Cálculo de Series

```python
def _calc_ejec_series(series_raw, extraccion):
    """Calcula Ejecución desde JSON de series según tipo de Extraccion."""
    lst = parse_json_safe(series_raw)
    if not lst:
        return None
    
    def _ok(v):
        return v is not None and not (isinstance(v, float) and np.isnan(v))
    
    if extraccion == _EXT_SER_SUM_VAR:
        # Sumar TODAS las variables de TODAS las series
        total = sum(
            v.get("valor", 0) 
            for s in lst 
            for v in s.get("variables", []) 
            if _ok(v.get("valor"))
        )
        return total if any(_ok(v.get("valor")) for s in lst for v in s.get("variables", [])) else None
    
    elif extraccion == _EXT_SER_AVG_VAR:
        # Promedio de sumas por serie
        sumas = []
        for s in lst:
            vals = [v.get("valor") for v in s.get("variables", []) if _ok(v.get("valor"))]
            if vals:
                sumas.append(sum(vals))
        return sum(sumas) / len(sumas) if sumas else None
    
    elif extraccion == _EXT_SER_AVG_RES:
        # Promedio de resultados
        vals = [x.get("resultado") for x in lst if _ok(x.get("resultado"))]
        return sum(vals) / len(vals) if vals else None
    
    elif extraccion == _EXT_SER_SUM_RES:
        # Suma de resultados
        vals = [x.get("resultado") for x in lst if _ok(x.get("resultado"))]
        return sum(vals) if vals else None
    
    return None
```

---

## 9. Lógica de Builders Detallada (`builders.py`)

### 9.1 Construcción Histórico

```python
def construir_registros_historico(df_fuente, llaves_existentes, hist_escalas, ...):
    """
    Genera registros nuevos para Consolidado Histórico.
    
    Args:
        df_fuente: DataFrame con datos de API/Kawak
        llaves_existentes: Set de LLAVEs ya existentes (para evitar duplicados)
        hist_escalas: Dict de escalas históricas por Id
        ...otros parámetros de configuración...
    
    Returns:
        (registros, skipped, conteo_na)
    """
    registros = []
    skipped = 0
    conteo_na = 0
    
    # Filtrar solo registros nuevos (no en llaves_existentes)
    df = df_fuente[~df_fuente["LLAVE"].isin(llaves_existentes)].dropna(subset=["LLAVE"])
    
    for _, row in df.iterrows():
        # Validar contra kawak_validos
        if kawak_validos is not None:
            id_s = _id_str(row.get("Id") or row.get("ID", ""))
            fecha_raw = row.get("fecha")
            try:
                año = pd.to_datetime(fecha_raw).year
            except:
                año = None
            if año is not None and (id_s, año) not in kawak_validos:
                skipped += 1
                continue
        
        # Extraer valores
        meta, ejec, fuente, es_na = _extraer_registro(
            row, hist_escalas,
            config_patrones=config_patrones,
            extraccion_map=extraccion_map,
            api_kawak_lookup=api_kawak_lookup,
            variables_campo_map=variables_campo_map,
            tipo_indicador_map=tipo_indicador_map,
        )
        
        # Omitir si fuente indica skip
        if fuente in ("skip", "sin_resultado"):
            skipped += 1
            continue
        
        # Validar No Aplica según periodicidad
        if es_na:
            try:
                fecha_ts = pd.to_datetime(row["fecha"])
            except:
                fecha_ts = None
            periodicidad = str(row.get("Periodicidad", ""))
            if periodicidad and fecha_ts is not None:
                if not _fecha_es_periodo_valido(fecha_ts, periodicidad):
                    skipped += 1
                    continue
            conteo_na += 1
        
        # Construir registro
        registros.append({
            "Id": row["Id"],
            "Indicador": limpiar_html(str(row.get("Indicador", ""))),
            "Proceso": row.get("Proceso", ""),
            "Periodicidad": row.get("Periodicidad", ""),
            "Sentido": row.get("Sentido", ""),
            "fecha": row["fecha"],
            "Meta": meta,
            "Ejecucion": ejec,
            "LLAVE": row["LLAVE"],
            "es_na": es_na,
        })
    
    return registros, skipped, conteo_na
```

### 9.2 Construcción Semestral

```python
def construir_registros_semestral(df_fuente, llaves_existentes, hist_escalas, ...):
    """
    Genera registros para Consolidado Semestral.
    
    TipoCalculo:
      - Promedio  → promedio de meses del semestre
      - Acumulado → suma de meses del semestre
      - Cierre    → último período de cierre (jun/dic)
    """
    # Clasificar indicadores por patrón
    ids_avg = set()  # Promedio
    ids_sum = set()  # Acumulado
    
    if config_patrones:
        for ids, cfg in config_patrones.items():
            if cfg["patron"] == "AVG":
                ids_avg.add(ids)
            elif cfg["patron"] == "SUM":
                ids_sum.add(ids)
    
    if tipo_calculo_map:
        for ids, tc in tipo_calculo_map.items():
            tc_n = tc.lower().strip()
            if tc_n == "promedio":
                ids_avg.add(ids)
            elif tc_n == "acumulado":
                ids_sum.add(ids)
    
    # Preparar datos
    df_base = df_fuente.copy()
    df_base["_ids"] = df_base["Id"].apply(_id_str)
    df_base["_sem"] = df_base["fecha"].apply(
        lambda d: f"{d.year}-{'1' if d.month <= 6 else '2'}"
    )
    
    ids_agg = ids_avg | ids_sum
    partes = []
    
    # ── Indicadores Cierre/estándar ──────────────────────────────
    df_std = df_base[~df_base["_ids"].isin(ids_agg)].copy()
    df_std = df_std[df_std["fecha"].dt.month.isin([6, 12])]
    df_std = df_std[
        df_std["fecha"] == df_std["fecha"].apply(
            lambda d: pd.Timestamp(d.year, d.month, ultimo_dia_mes(d.year, d.month))
        )
    ]
    partes.append(df_std)
    
    # ── Indicadores Promedio/Acumulado ───────────────────────────
    registros_agg = []
    if ids_agg:
        df_agg_src = df_base[df_base["_ids"].isin(ids_agg)].copy()
        
        # Calcular valores corregidos
        df_agg_src["_ejec_corr"] = df_agg_src.apply(
            lambda r: _ejec_corrected_from_row(r, extraccion_map, api_kawak_lookup), axis=1
        )
        df_agg_src["_meta_corr"] = df_agg_src.apply(
            lambda r: _meta_corrected_from_row(r, extraccion_map, api_kawak_lookup), axis=1
        )
        
        # Agrupar por (Id, semestre)
        for (id_val, sem_label), grupo in df_agg_src.groupby(["Id", "_sem"]):
            ids = _id_str(id_val)
            patron = "AVG" if ids in ids_avg else "SUM"
            
            # Calcular agregados
            ejecs = pd.to_numeric(grupo["_ejec_corr"], errors="coerce").dropna()
            metas = pd.to_numeric(grupo["_meta_corr"], errors="coerce").dropna()
            
            if len(ejecs) == 0:
                continue
            
            ejec_agg = ejecs.mean() if patron == "AVG" else ejecs.sum()
            meta_agg = (
                (metas.mean() if patron == "AVG" else metas.sum())
                if len(metas) > 0 else None
            )
            
            # Fecha de cierre del semestre
            year, sem = int(sem_label.split("-")[0]), int(sem_label.split("-")[1])
            end_month = 6 if sem == 1 else 12
            end_fecha = pd.Timestamp(year, end_month, ultimo_dia_mes(year, end_month))
            llave = make_llave(id_val, end_fecha)
            
            # Validaciones
            if llave in llaves_existentes:
                continue
            if kawak_validos is not None and (ids, year) not in kawak_validos:
                continue
            
            # Crear registro agregado
            last = grupo.sort_values("fecha").iloc[-1]
            registros_agg.append({
                "Id": id_val,
                "Indicador": limpiar_html(str(last.get("Indicador", ""))),
                "Proceso": last.get("Proceso", ""),
                "Periodicidad": last.get("Periodicidad", ""),
                "Sentido": last.get("Sentido", ""),
                "fecha": end_fecha,
                "Meta": nan2none(pd.to_numeric(meta_agg, errors="coerce")) if meta_agg else None,
                "Ejecucion": nan2none(pd.to_numeric(ejec_agg, errors="coerce")),
                "LLAVE": llave,
                "es_na": False,
            })
    
    # Combinar resultados
    df_sem = pd.concat(partes, ignore_index=True) if partes else pd.DataFrame()
    
    # Procesar estándar con builder de histórico
    regs_std, skip_std, na_std = construir_registros_historico(
        df_sem, llaves_existentes, hist_escalas, ...
    )
    
    return regs_std + registros_agg, skip_std, na_std
```

### 9.3 Construcción Cierres

```python
def construir_registros_cierres(df_fuente, hist_escalas, ...):
    """
    Genera registros para Consolidado Cierres.
    
    Similar a semestral pero para todo el año.
    """
    df = df_fuente.copy()
    df["año"] = df["fecha"].dt.year
    df["mes"] = df["fecha"].dt.month
    
    registros = []
    skipped = 0
    conteo_na = 0
    
    # Identificar indicadores por tipo de cálculo
    ids_avg = {ids for ids, tc in (tipo_calculo_map or {}).items() if tc.lower() == "promedio"}
    ids_sum = {ids for ids, tc in (tipo_calculo_map or {}).items() if tc.lower() == "acumulado"}
    
    for (id_val, año), grupo in df.groupby(["Id", "año"]):
        id_s = _id_str(id_val)
        
        # Validar contra kawak_validos
        if kawak_validos is not None and (id_s, int(año)) not in kawak_validos:
            skipped += len(grupo)
            continue
        
        # Determinar patrón
        patron = (
            "AVG" if id_s in ids_avg else
            "SUM" if id_s in ids_sum else
            "LAST"
        )
        
        if patron in ("AVG", "SUM"):
            # Calcular agregados del año
            grupo = grupo.sort_values("fecha")
            ejecs = []
            for _, r in grupo.iterrows():
                ev = _ejec_corrected_from_row(r, extraccion_map, api_kawak_lookup)
                if ev is not None:
                    try:
                        ejecs.append(float(ev))
                    except:
                        pass
            
            if not ejecs:
                skipped += 1
                continue
            
            ejec_agg = sum(ejecs) / len(ejecs) if patron == "AVG" else sum(ejecs)
            
            # Calcular meta agregada
            metas_corr = []
            for _, r in grupo.iterrows():
                mv = _meta_corrected_from_row(r, extraccion_map, api_kawak_lookup)
                if mv is not None:
                    try:
                        metas_corr.append(float(mv))
                    except:
                        pass
            
            meta_agg = (
                (sum(metas_corr) / len(metas_corr) if patron == "AVG" else sum(metas_corr))
                if metas_corr else None
            )
            
            # Fecha de cierre (diciembre o último mes)
            dic_rows = grupo[grupo["mes"] == 12]
            fecha_cierre = (
                dic_rows.iloc[-1]["fecha"] if len(dic_rows) > 0
                else grupo.iloc[-1]["fecha"]
            )
            
            last = grupo.iloc[-1]
            registros.append({
                "Id": id_val,
                "Indicador": limpiar_html(str(last.get("Indicador", ""))),
                "Proceso": last.get("Proceso", ""),
                "Periodicidad": last.get("Periodicidad", ""),
                "Sentido": last.get("Sentido", ""),
                "fecha": fecha_cierre,
                "Meta": meta_agg,
                "Ejecucion": ejec_agg,
                "LLAVE": make_llave(id_val, fecha_cierre),
                "es_na": False,
            })
```

---

## 10. Lógica de Purga y Reparación (`purga.py`)

### 10.1 Purga de Filas Inválidas

```python
def purgar_filas_invalidas(ws, nombre, kawak_validos):
    """
    Elimina filas donde:
      - La fecha es futura (año > AÑO_CIERRE_ACTUAL)
      - El campo Año contiene texto inválido
      - El par (Id, año) no existe en el catálogo Kawak
    """
    cm = _build_col_map(ws)
    idx_id = cm.get("Id", 1) - 1
    idx_fecha = cm.get("Fecha", 6) - 1
    idx_anio = cm.get("Anio", 7) - 1
    
    filas_a_borrar = []
    n_kawak = 0
    
    for row in ws.iter_rows(min_row=2, values_only=False):
        if row[0].value is None:
            continue
        
        # Validar fecha
        fecha_raw = row[idx_fecha].value if len(row) > idx_fecha else None
        año_fila = None
        
        try:
            fecha = pd.to_datetime(fecha_raw)
            año_fila = fecha.year
            if fecha.year > AÑO_CIERRE_ACTUAL:
                filas_a_borrar.append(row[0].row)
                continue
        except:
            pass
        
        # Validar campo Año
        anio_val = row[idx_anio].value if len(row) > idx_anio else None
        if anio_val is not None:
            if isinstance(anio_val, str) and anio_val.startswith("="):
                pass  # Es fórmula, ignorar
            else:
                try:
                    año_fila = int(float(anio_val))
                except:
                    filas_a_borrar.append(row[0].row)
                    continue
        
        # Validar contra kawak_validos
        if kawak_validos is not None and año_fila is not None:
            id_val = row[idx_id].value if len(row) > idx_id else None
            id_s = _id_str(id_val) if id_val else None
            if id_s and (id_s, año_fila) not in kawak_validos:
                filas_a_borrar.append(row[0].row)
                n_kawak += 1
    
    # Borrar en orden inverso para no desplazar índices
    for r_idx in sorted(set(filas_a_borrar), reverse=True):
        ws.delete_rows(r_idx)
    
    return len(set(filas_a_borrar))
```

### 10.2 Limpiar Cierres Existentes

```python
def limpiar_cierres_existentes(ws):
    """
    Para años <= AÑO_CIERRE_ACTUAL: conserva solo el registro de diciembre.
    Para años > AÑO_CIERRE_ACTUAL: conserva todos.
    """
    filas = []
    for row in ws.iter_rows(min_row=2, values_only=False):
        if row[0].value is None:
            continue
        
        fecha_raw = row[5].value
        try:
            fecha = pd.to_datetime(fecha_raw)
        except:
            fecha = None
        
        filas.append({
            "row_idx": row[0].row,
            "Id": row[0].value,
            "fecha": fecha,
            "mes": fecha.month if fecha else None,
            "año": fecha.year if fecha else None,
        })
    
    if not filas:
        return 0
    
    # Agrupar por (Id, año)
    grupos = defaultdict(list)
    for f in filas:
        if f["año"] is None:
            continue
        grupos[(str(f["Id"]), f["año"])].append(f)
    
    # Decidir cuáles conservar
    filas_a_conservar = set()
    for (id_val, año), grupo in grupos.items():
        if año > AÑO_CIERRE_ACTUAL:
            # Año futuro: conservar todos
            for f in grupo:
                filas_a_conservar.add(f["row_idx"])
        else:
            # Año actual o pasado: conservar solo diciembre
            dic = [f for f in grupo if f["mes"] == 12]
            keep = sorted(dic if dic else grupo, key=lambda f: f["fecha"])[-1]
            filas_a_conservar.add(keep["row_idx"])
    
    # Agregar filas sin año
    for f in filas:
        if f["año"] is None:
            filas_a_conservar.add(f["row_idx"])
    
    # Borrar el resto
    filas_a_borrar = sorted(
        [f["row_idx"] for f in filas if f["row_idx"] not in filas_a_conservar],
        reverse=True,
    )
    
    for r_idx in filas_a_borrar:
        ws.delete_rows(r_idx)
    
    return len(filas_a_borrar)
```

### 10.3 Deduplicación

```python
def deduplicar_sheet(ws, nombre):
    """
    Elimina filas con LLAVE duplicada (mismo Id+Fecha),
    conservando la que tenga ejecución más completa.
    """
    cm = _build_col_map(ws)
    idx_fecha = cm.get("Fecha", 6) - 1
    idx_ejec = cm.get("Ejecucion", 11) - 1
    
    filas = []
    for row in ws.iter_rows(min_row=2, values_only=False):
        if row[0].value is None:
            continue
        
        try:
            llave = make_llave(row[0].value, row[idx_fecha].value)
        except:
            llave = None
        
        ejec_val = row[idx_ejec].value if len(row) > idx_ejec else None
        
        filas.append({"row_idx": row[0].row, "llave": llave, "ejec": ejec_val})
    
    # Agrupar por llave
    grupos = defaultdict(list)
    for f in filas:
        grupos[f["llave"]].append(f)
    
    # Elegir la mejor de cada grupo
    filas_a_borrar = []
    for llave, grupo in grupos.items():
        if llave is None or len(grupo) <= 1:
            continue
        
        # Score: 2 si ejec != 0, 1 si ejec != vacío, 0 si vacío
        def _score(f):
            if f["ejec"] is None:
                return 0
            try:
                return 2 if float(f["ejec"]) != 0.0 else 1
            except:
                return 1 if str(f["ejec"]).strip() not in ("", "nan", "None") else 0
        
        mejor = max(grupo, key=_score)
        filas_a_borrar.extend(
            f["row_idx"] for f in grupo if f["row_idx"] != mejor["row_idx"]
        )
    
    # Borrar
    for r_idx in sorted(filas_a_borrar, reverse=True):
        ws.delete_rows(r_idx)
    
    return len(filas_a_borrar)
```

---

## 11. Lógica de Escritura (`escritura.py`)

### 11.1 Escritura de Filas

```python
def escribir_filas(ws, filas, signos, start_row=None, ids_metrica=None):
    """
    Escribe filas nuevas en la hoja usando el mapa de columnas real.
    """
    cm = _build_col_map(ws)
    
    def _set(r, campo, value, fmt=None):
        col = cm.get(campo)
        if col is None:
            return
        ws.cell(r, col).value = value
        if fmt and value is not None:
            ws.cell(r, col).number_format = fmt
    
    if start_row is None:
        start_row = get_last_data_row(ws) + 1
    
    r = start_row
    for fila in filas:
        id_str_val = str(fila.get("Id", ""))
        sg = signos.get(id_str_val, {
            "meta_signo": "%",
            "ejec_signo": "%",
            "dec_meta": 0,
            "dec_ejec": 0,
        })
        
        # Preparar fecha
        fecha_raw = fila.get("fecha")
        fecha_dt = pd.to_datetime(fecha_raw) if fecha_raw else None
        fecha_val = fecha_dt.to_pydatetime().date() if fecha_dt else None
        
        # Extraer valores
        meta = nan2none(fila.get("Meta"))
        ejec = nan2none(fila.get("Ejecucion"))
        es_na = fila.get("es_na", False)
        sentido = str(fila.get("Sentido", "Positivo"))
        es_metrica = ids_metrica is not None and id_str_val in ids_metrica
        
        # Manejar No Aplica
        if es_na:
            ejec = None
        ejec_signo = "No Aplica" if es_na else sg["ejec_signo"]
        
        # Tipo de registro
        if es_metrica:
            tipo_registro = "Metrica"
        elif es_na:
            tipo_registro = "No Aplica"
        else:
            tipo_registro = ""
        
        # Escribir campos básicos
        _set(r, "Id", fila.get("Id"))
        _set(r, "Indicador", fila.get("Indicador", ""))
        _set(r, "Proceso", fila.get("Proceso", ""))
        _set(r, "Periodicidad", fila.get("Periodicidad", ""))
        _set(r, "Sentido", sentido)
        _set(r, "Fecha", fecha_val, "YYYY-MM-DD")
        
        # Escribir fórmulas
        _set(r, "Anio", f"=YEAR(F{r})")
        _set(r, "Mes", f'=PROPER(TEXT(F{r},"mmmm"))')
        _set(r, "Semestre", f'=IF(OR(H{r}="Enero",...),G{r}&"-1",G{r}&"-2")')
        
        # Escribir Meta y Ejecución
        _set(r, "Meta", meta)
        _set(r, "Ejecucion", ejec)
        
        # Escribir Cumplimiento (con fórmula o vacío)
        if es_metrica:
            _set(r, "Cumplimiento", None)
            _set(r, "CumplReal", None)
        else:
            # Determinar tope según tipo de indicador
            _id_fila = _id_str(fila.get("Id"))
            _tope = 1.0 if _id_fila in IDS_PLAN_ANUAL or _id_fila in IDS_TOPE_100 else 1.3
            
            # Fórmula de cumplimiento
            formula_cumpl = (
                f'=IFERROR(IF(OR(J{r}=0,K{r}=""),"",'
                f'IF(E{r}="Positivo",MIN(MAX(K{r}/J{r},0),{_tope}),'
                f'MIN(MAX(J{r}/K{r},0),{_tope}))),"")'
            )
            _set(r, "Cumplimiento", formula_cumpl, "0.00%")
            
            # Fórmula de cumplimiento real (sin tope)
            formula_real = (
                f'=IFERROR(IF(OR(J{r}=0,K{r}=""),"",'
                f'IF(E{r}="Positivo",MAX(K{r}/J{r},0),'
                f'MAX(J{r}/K{r},0))),"")'
            )
            _set(r, "CumplReal", formula_real, "0.00%")
        
        # Escribir signos y otros campos
        _set(r, "MetaS", sg["meta_signo"])
        _set(r, "EjecS", ejec_signo)
        _set(r, "DecMeta", sg.get("dec_meta", 0))
        _set(r, "DecEjec", sg.get("dec_ejec", 0))
        _set(r, "LLAVE", f'=A{r}&"-"&YEAR(F{r})&"-"&TEXT(MONTH(F{r}),"00")&"-"&TEXT(DAY(F{r}),"00")')
        _set(r, "TipoRegistro", tipo_registro)
        
        r += 1
    
    return r - 1
```

---

## 12. Flujo Completo de Datos

```
ENTRADA: data/raw/Fuentes Consolidadas/Consolidado_API_Kawak.xlsx
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│  actualizar_consolidado.py (ORQUESTADOR)                    │
├─────────────────────────────────────────────────────────────┤
│  1. Cargar df_api (fuente consolidada)                     │
│     - Lee Excel de fuente                                  │
│     - Normaliza columnas (ID→Id, nombre→Indicador)        │
│     - Crea columna LLAVE                                   │
│                                                              │
│  2-4. Cargar catálogos y configuración                     │
│     - extraccion_map: tipo de extracción por indicador    │
│     - tipo_calculo_map: Promedio/Acumulado/Cierre         │
│     - config_patrones: patrones especiales (AVG/SUM)      │
│     - kawak_validos: indicadores válidos por año          │
│                                                              │
│  5-6. Abrir workbook y leer existente                     │
│     - Abre Resultados Consolidados.xlsx                   │
│     - Lee hojas existentes para signos y escalas          │
│     - Calcula llaves existentes (para evitar duplicados)  │
│                                                              │
│  7. PURGA                                                  │
│     - Elimina filas con año futuro                        │
│     - Elimina filas no válidas en Kawak                   │
│     - Limpia cierres existentes                           │
│                                                              │
│  8. Construir hist_escalas                                 │
│     - Extrae escalas del histórico existente              │
│                                                              │
│  9. Preparar df_api                                        │
│     - Normaliza fechas                                     │
│     - Crea LLAVEs                                          │
│                                                              │
│  10. BUILDERS                                              │
│     ├─ construir_registros_historico()                    │
│     │   └─ Para cada registro nuevo:                      │
│     │       ├─ Validar contra kawak_validos               │
│     │       ├─ _extraer_registro() → (meta, ejec, fuente, es_na)│
│     │       └─ Agregar a lista de registros             │
│     │                                                      │
│     ├─ construir_registros_semestral()                    │
│     │   └─ Para indicadores AVG/SUM:                      │
│     │       ├─ Agrupar por semestre                     │
│     │       ├─ Calcular promedio o suma                 │
│     │       └─ Crear registro agregado                  │
│     │                                                      │
│     └─ construir_registros_cierres()                      │
│         └─ Similar a semestral pero anual               │
│                                                              │
│  11. ESCRIBIR                                              │
│     └─ escribir_filas() → Escribe en workbook abierto    │
│         ├─ Escribe campos básicos                        │
│         ├─ Escribe fórmulas (Año, Mes, Semestre)        │
│         ├─ Escribe Meta y Ejecución                      │
│         └─ Escribe fórmulas de Cumplimiento            │
│                                                              │
│  12. REPARAR                                               │
│     ├─ reparar_meta_vacia() → Rellena metas vacías      │
│     ├─ reparar_multiserie() → Repara multiserie        │
│     └─ reparar_semestral_agregados() → Recalcula AVG/SUM │
│                                                              │
│  13. DEDUPLICAR Y MATERIALIZAR                             │
│     ├─ deduplicar_sheet() → Elimina duplicados          │
│     ├─ _reescribir_formulas() → Reescribe fórmulas     │
│     ├─ _materializar_formula_año() → Convierte a valores│
│     └─ _materializar_cumplimiento() → Calcula valores   │
│                                                              │
│  14. CATÁLOGO                                              │
│     └─ Actualiza hoja Catalogo Indicadores              │
│                                                              │
│  15. GUARDAR                                               │
│     ├─ Crea backup (.bak.xlsx)                          │
│     └─ Guarda Resultados Consolidados.xlsx              │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
SALIDA: data/output/Resultados Consolidados.xlsx
```

---

## 13. Validaciones Recomendadas

### 13.1 Post-Ejecución

| Validación | Cómo verificar |
|------------|----------------|
| Conteo de registros | Comparar fuente vs. output |
| Nulos | `df.isnull().sum()` no debe ser > 20% |
| Rangos | Cumplimiento entre 0 y 1.3 |
| Duplicados | Sin LLAVEs duplicadas |
| Backup | Comparar .bak.xlsx vs. nuevo |

### 13.2 Casos Edge a Verificar

1. **Indicadores sin meta**: ¿Se rellenan correctamente?
2. **Indicadores "No Aplica"**: ¿Se marcan correctamente?
3. **Indicadores AVG/SUM**: ¿Se agregan correctamente?
4. **Fechas de cierre**: ¿Son últimos días del mes?
5. **Fórmulas materializadas**: ¿Tienen valores calculados?

---

## 14. Problemas Conocidos y Soluciones

### 14.1 Fórmulas No Evaluadas

**Problema:** `pd.read_excel()` no evalúa fórmulas Excel.

**Solución:** Usar `_materializar_cumplimiento()` después de escribir.

### 14.2 Metas Vacías

**Problema:** Algunos indicadores no tienen meta definida.

**Solución:** `reparar_meta_vacia()` usa api_kawak_lookup como fallback.

### 14.3 Inconsistencia de Años

**Problema:** Datos de años futuros en el histórico.

**Solución:** `purgar_filas_invalidas()` elimina años > AÑO_CIERRE_ACTUAL.

### 14.4 Duplicados

**Problema:** Mismo indicador con misma fecha de diferentes fuentes.

**Solución:** `deduplicar_sheet()` conserva el de mejor ejecución.
