# 📊 Modelo de Datos SGIND
## Fuentes, Esquemas, Cálculos y Validaciones

**Documento:** DATA_MODEL_SGIND.md  
**Versión:** 1.0  
**Fecha:** 14 de abril de 2026  
**Audiencia:** Desarrolladores, Analistas, Arquitectos de datos

---

## TABLA DE CONTENIDOS

1. [Visión General](#visión-general)
2. [Modelo Conceptual](#modelo-conceptual)
3. [Fuentes de Datos](#fuentes-de-datos)
4. [Esquemas por Tabla](#esquemas-por-tabla)
5. [Flujo de Transformación (ETL)](#flujo-de-transformación-etl)
6. [Cálculos y Lógica](#cálculos-y-lógica)
7. [Diccionario de Campos](#diccionario-de-campos)
8. [Data Contracts & Validación](#data-contracts--validación)

---

## VISIÓN GENERAL

### Objetivo del Modelo

SGIND consolida **1,000+ indicadores institucionales** desde múltiples fuentes, aplica reglas de negocio, calcula cumplimiento y entrega reportería centralizada.

```
ENTRADA (Múltiples fuentes)
    ↓
CONSOLIDACIÓN (ETL 3 pasos, 3-5 min)
    ↓
CÁLCULOS (Cumplimiento, tendencias, categorización)
    ↓
VALIDACIÓN (Data contracts, integridad)
    ↓
SALIDA (Dashboard + Reportes)
```

### Volumen de Datos

| Métrica | Valor |
|---------|-------|
| Indicadores activos | 1,000+ |
| Períodos históricos | 60+ (2022-2026, monthly) |
| Registros en consolidado | 60,000+ |
| Frecuencia actualización | Diaria (06:00 UTC) |
| Tempo de procesamiento | 45-50 segundos |

---

## MODELO CONCEPTUAL

### Entidades Principales

```
┌──────────────────────────────────────────────────────────┐
│                    INDICADOR                             │
│  ┌─ ID (PK)                                             │
│  ├─ Nombre                                              │
│  ├─ Descripción                                         │
│  ├─ Sentido (Ascendente/Descendente)                   │
│  ├─ Clasificación                                       │
│  ├─ Periodicidad (Mensual/Trimestral/Semestral/Anual) │
│  ├─ Unidad                                              │
│  ├─ Fórmula                                             │
│  └─ Estado (Activo/Inactivo)                           │
└──────────────────────────────────────────────────────────┘
              ↓ MUCHOS A MUCHOS ↓
┌──────────────────────────────────────────────────────────┐
│              INDICADOR_RESULTADO                         │
│  ┌─ ID_Indicador (FK)                                  │
│  ├─ Fecha                                              │
│  ├─ Año                                                │
│  ├─ Período (Mes/Semestre/Trimestre)                 │
│  ├─ Meta                                               │
│  ├─ Ejecución                                          │
│  ├─ Cumplimiento (calculado)                          │
│  ├─ Categoría (Peligro/Alerta/Cumpl/Sobre)          │
│  ├─ Tendencia (↑/→/↓)                                |
│  ├─ Fuente (API/Kawak/Manual)                         │
│  └─ Timestamp_Carga                                    │
└──────────────────────────────────────────────────────────┘
              ↓ 1 A MUCHOS ↓
┌──────────────────────────────────────────────────────────┐
│         OPORTUNIDAD_DE_MEJORA (OM)                       │
│  ┌─ ID_OM (PK)                                         │
│  ├─ ID_Indicador (FK)                                 │
│  ├─ Fecha_Creación                                    │
│  ├─ Descripción                                       │
│  ├─ Responsable                                       │
│  ├─ Plazo_Cierre                                      │
│  ├─ Estado (Abierta/En_Ejecución/Cerrada)           │
│  ├─ Resultado_Verificado (Bool)                      │
│  └─ Fecha_Cierre                                      │
└──────────────────────────────────────────────────────────┘
        ↓              ↓              ↓
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│   PROCESO        │ │   SUBPROCESO     │ │      ÁREA        │
│ ┌─ ID (PK)      │ │ ┌─ ID (PK)       │ │ ┌─ Código       │
│ ├─ Nombre       │ │ ├─ Nombre        │ │ ├─ Nombre       │
│ ├─ Descripción  │ │ ├─ Proceso (FK)  │ │ ├─ Area_Padre   │
│ └─ Tipo         │ │ └─ Descripción   │ │ └─ Responsable │
└──────────────────┘ └──────────────────┘ └──────────────────┘
```

### Relaciones Clave

| Relación | Conecta | Cardinalidad |
|----------|---------|--------------|
| Indicador → Proceso | Clasificación | 1:M |
| Indicador → Subproceso | Clasificación | 1:M |
| Indicador → Resultado | Histórico diario | 1:M |
| Resultado → OM | Triggers automático | 1:M |
| OM → Auditoría | Compliance | M:1 |

---

## FUENTES DE DATOS

### 1. Fuentes Primarias (Entrada del Sistema)

#### 1.1 API Kawak (Fuente Principal)

```yaml
Nombre: API Kawak
URL: https://kawak.cloud/api/v1/indicators
Tipo: REST API
Autenticación: Token API
Frecuencia: Diaria (06:00 UTC)
Volumen: ~1,000 indicadores × 12 períodos = 12,000 registros/año

Estructura Respuesta:
  - id: string (Identificador indicador)
  - nombre: string (Nombre descriptivo)
  - proceso: string (Clasificación)
  - meta: float (META del período)
  - resultado: float (EJECUCIÓN del período)
  - fecha: datetime (ISO 8601)
  - variables: JSON array (Desglose componentes)
  - series: JSON array (Series temporales)
  - analisis: string (Análisis cualitativo)

Archivos Salida:
  - data/raw/Kawak/Catalogo_2025.xlsx (Metadatos año)
  - data/raw/Kawak/Catalogo_2026.xlsx (Metadatos año)
  - data/raw/API/Resultados_2025.xlsx (Histórico año)
  - data/raw/API/Resultados_2026.xlsx (Histórico año)
```

#### 1.2 Excel Histórico (Datos Consolidados)

```yaml
Nombre: Consolidado API Kawak
Ubicación: data/raw/Fuentes Consolidadas/Consolidado_API_Kawak.xlsx
Tipo: Excel XLSX (Multi-sheet)
Actualizado por: consolidar_api.py
Frecuencia: Diaria

Hojas Principales:
  1. Indicadores Kawak (Maestro de IDs)
     - ID, Nombre, Proceso, Subproceso, Meta, Unidad, Fórmula
     
  2. Histórico Completo (Data Lake)
     - ID, Nombre, Proceso, Período, Año, Meta, Ejecución, Fuente, Fecha_Carga
     - ~60,000 registros (1000 indicadores × 60 períodos)
```

#### 1.3 LMI Reporte (Tracking de Reportería)

```yaml
Nombre: LMI Reporte
Ubicación: data/raw/lmi_reporte.xlsx
Tipo: Excel XLSX
Frecuencia: Mensual
Propósito: Tracking de qué indicadores fueron reportados vs pendientes

Hojas:
  - Tracking Mensual: Matriz ID × Mes (Reportado/Pendiente/N-A)
  - Estructura: 25 columnas, ~1000 filas

Columnas Clave:
  - ID: Identificador indicador
  - Indicador: Nombre
  - Ene, Feb, Mar... Dic: Estado de reporte por mes
  - Valores: "Reportado" | "Pendiente" | "N/A" | ""
```

#### 1.4 Mapeo de Procesos & Estructura (YAML Config)

```yaml
Ubicación: config/mapeos_procesos.yaml
Tipo: YAML configuración
Propósito: Hierarquía de procesos, subprocesos, áreas

Estructura:
  procesos:
    - nombre: "DOCENCIA"
      id_proceso: "P01"
      subprocesos:
        - nombre: "Formación Pregrado"
          id_subproceso: "SP01-01"
        - nombre: "Formación Postgrado"
          id_subproceso: "SP01-02"
    - nombre: "INVESTIGACIÓN"
      id_proceso: "P02"
      subprocesos: []
  
  áreas:
    - codigo: "AC"
      nombre: "Área de Calidad"
      procesos_responsables: ["P01", "P03"]
```

### 2. Fuentes Intermedias (Generadas por ETL)

#### 2.1 Archivo Base (Plantilla)

```yaml
Ubicación: data/raw/Resultados_Consolidados_Fuente.xlsx
Tipo: Excel con fórmulas (template)
Propósito: Base para generar outputs, contiene fórmulas Excel pre-configuradas

Hojas Predefinidas:
  1. Consolidado Histórico
     - Columnas: ID, Indicador, Proceso, Período, Cumplimiento, Categoría, Tendencia
     - Fórmulas: Cumplimiento = Ejecución / Meta (por sentido)
  
  2. Consolidado Semestral
     - Agregación: Prometio por semestre
     - Columnas: ID, Indicador, Proceso, Semestre, Meta, Ejecución, Cumplimiento
  
  3. Cierres Anuales
     - Agregación: Cierre anual (último periodo)
     - Columnas: ID, Indicador, Clasificación, Año, Meta, Ejecución, Cumplimiento
  
  4. Catálogo de Indicadores
     - Metadatos: ID, Nombre, Tipo, Clasificación, Proceso, Subproceso, Periodicidad
  
  5. Lógica & Variables
     - Reglas de cálculo por indicador (qué patrón usar)
     - Variables configuradas (símbolo_meta, símbolo_ejec)
```

### 3. Fuentes Auxiliares

#### 3.1 Estructura Organizacional

```yaml
Ubicación: data/raw/Subproceso-Proceso-Area.xlsx
Hojas: 
  - Hoja1: Mapa de procesos completo (Área → Proceso → Subproceso)
  - Rectoria: Estructura de rectoría
  - Facultades: Información de facultades

Columnas Clave:
  - Vicerrectoría, Área, Proceso, Subproceso, Responsable
```

#### 3.2 Fichas Técnicas

```yaml
Ubicación: data/raw/Ficha_Tecnica.xlsx
Propósito: Documentación de cada indicador (63 columnas)
Columnas: ID, Nombre, Unidad, Fórmula, Meta Esperada, Responsable, Periodicidad, etc.
```

#### 3.3 Indicadores por CMI

```yaml
Ubicación: data/raw/Indicadores por CMI.xlsx
Propósito: Indicadores alineados a Cuadro de Mando Integral
Estructura: 
  - Línea Estratégica, Objetivo, Indicador, Meta
  - Perspectivas: Financiera, Cliente, Procesos Internos, Aprendizaje
```

---

## ESQUEMAS POR TABLA

### TABLA 1: Indicadores (Máster)

```sql
CREATE TABLE indicadores (
  id VARCHAR(10) PRIMARY KEY,
  nombre VARCHAR(255) NOT NULL,
  descripcion TEXT,
  tipo VARCHAR(50),  -- "CUMPLIMIENTO" | "PROCESO" | "ACREDITACION"
  clasificacion VARCHAR(100),
  proceso VARCHAR(100) NOT NULL,
  subproceso VARCHAR(100),
  periodicidad VARCHAR(20),  -- "MENSUAL" | "TRIMESTRAL" | "SEMESTRAL" | "ANUAL"
  sentido VARCHAR(20) NOT NULL,  -- "ASCENDENTE" | "DESCENDENTE"
  unidad VARCHAR(50),  -- "%", "Horas", "Cantidad", etc.
  formula TEXT,
  meta_esperada FLOAT,
  responsable VARCHAR(255),
  estado VARCHAR(20) DEFAULT 'ACTIVO',  -- "ACTIVO" | "INACTIVO"
  fecha_creacion DATETIME DEFAULT CURRENT_TIMESTAMP,
  fecha_modificacion DATETIME DEFAULT CURRENT_TIMESTAMP,
  activo BOOLEAN DEFAULT TRUE
);

-- Índices
CREATE INDEX idx_indicadores_proceso ON indicadores(proceso);
CREATE INDEX idx_indicadores_clasificacion ON indicadores(clasificacion);
CREATE INDEX idx_indicadores_estado ON indicadores(estado);
```

### TABLA 2: Resultados / Ejecución

```sql
CREATE TABLE resultados_indicadores (
  id_resultado INT AUTO_INCREMENT PRIMARY KEY,
  id_indicador VARCHAR(10) NOT NULL,
  fecha DATE NOT NULL,
  ano INT NOT NULL,
  periodo VARCHAR(20),  -- "01", "02", "SEMESTRE_1", "Q1", etc.
  meta FLOAT,
  ejecucion FLOAT,
  cumplimiento FLOAT GENERATED ALWAYS AS (
    CASE 
      WHEN sentido = 'ASCENDENTE' THEN ejecucion / meta
      WHEN sentido = 'DESCENDENTE' THEN meta / ejecucion
      ELSE NULL
    END
  ),
  cumplimiento_real FLOAT,  -- Sin tope
  cumplimiento_capped FLOAT,  -- Con tope (130%)
  categoria VARCHAR(20),  -- "PELIGRO" | "ALERTA" | "CUMPLIMIENTO" | "SOBRECUMPLIMIENTO"
  tendencia VARCHAR(5),  -- "↑" | "→" | "↓"
  estado_reporte VARCHAR(20),  -- "REPORTADO" | "PENDIENTE" | "N/A"
  fuente VARCHAR(50),  -- "API_KAWAK" | "EXCEL_MANUAL" | "CALCULO"
  variables JSON,  -- Desglose de variables {"R": 100, "M": 80}
  series JSON,  -- Array de series temporales
  analisis TEXT,  -- Análisis cualitativo
  timestamp_carga DATETIME DEFAULT CURRENT_TIMESTAMP,
  validado BOOLEAN DEFAULT FALSE,
  
  FOREIGN KEY (id_indicador) REFERENCES indicadores(id),
  CONSTRAINT unique_resultado UNIQUE (id_indicador, fecha, ano, periodo)
);

-- Índices
CREATE INDEX idx_resultados_indicador ON resultados_indicadores(id_indicador);
CREATE INDEX idx_resultados_fecha ON resultados_indicadores(fecha);
CREATE INDEX idx_resultados_ano_periodo ON resultados_indicadores(ano, periodo);
CREATE INDEX idx_resultados_categoria ON resultados_indicadores(categoria);
```

### TABLA 3: Oportunidades de Mejora (OM)

```sql
CREATE TABLE oportunidades_mejora (
  id_om INT AUTO_INCREMENT PRIMARY KEY,
  numero_om VARCHAR(20) UNIQUE,  -- "OM-2026-001"
  id_indicador VARCHAR(10) NOT NULL,
  fecha_creacion DATETIME DEFAULT CURRENT_TIMESTAMP,
  descripcion TEXT NOT NULL,
  causa_raiz TEXT,
  responsable VARCHAR(255) NOT NULL,
  plazo_cierre DATE NOT NULL,
  estado VARCHAR(20) DEFAULT 'ABIERTA',  -- "ABIERTA" | "EN_EJECUCION" | "CERRADA" | "RETRASADA"
  fecha_cierre DATE,
  resultado_verificado BOOLEAN,
  evidencias TEXT,  -- Link o descripción de evidencias
  crear_por VARCHAR(255),
  cierre_por VARCHAR(255),
  notas_internales TEXT,
  
  FOREIGN KEY (id_indicador) REFERENCES indicadores(id)
);

-- Índices
CREATE INDEX idx_om_indicador ON oportunidades_mejora(id_indicador);
CREATE INDEX idx_om_estado ON oportunidades_mejora(estado);
CREATE INDEX idx_om_responsable ON oportunidades_mejora(responsable);
CREATE INDEX idx_om_fecha_cierre ON oportunidades_mejora(plazo_cierre);
```

### TABLA 4: Auditoría (Audit Trail)

```sql
CREATE TABLE audit_log (
  id_audit INT AUTO_INCREMENT PRIMARY KEY,
  tabla_afectada VARCHAR(50),
  id_registro VARCHAR(50),
  accion VARCHAR(20),  -- "INSERT" | "UPDATE" | "DELETE"
  usuario VARCHAR(255),
  timestamp_cambio DATETIME DEFAULT CURRENT_TIMESTAMP,
  dato_anterior JSON,
  dato_nuevo JSON,
  razon_cambio TEXT
);

-- Índices
CREATE INDEX idx_audit_tabla ON audit_log(tabla_afectada);
CREATE INDEX idx_audit_timestamp ON audit_log(timestamp_cambio);
```

---

## FLUJO DE TRANSFORMACIÓN (ETL)

### Paso 1: Consolidación API (45-60 seg)

```
ENTRADA:
  • API Kawak → 1,000 indicadores × 12 períodos
  • Excel catálogos (2022-2026)
  
PROCESO:
  1. Limpieza de IDs
     - Eliminar espacios: "ID 150" → "ID150"
     - Eliminar caracteres especiales: "ID-150" → "ID150"
     
  2. Normalización de valores
     - Codificar HTML: "&quot;" → '"'
     - Fechas: formato consistente YYYY-MM-DD
     
  3. Deduplicación
     - Llave única: (ID, período, año, sede)
     - Resolver conflicto: usar registro más reciente por timestamp
     
  4. Concatenación
     - Unir 5 años de datos (2022-2026)
     - Preservar metadatos (fuente, fecha carga, usuario)

SALIDA:
  ✓ Indicadores_Kawak.xlsx (maestro activos)
  ✓ Consolidado_API_Kawak.xlsx (histórico completo)
```

### Paso 2: Actualización del Consolidado (2-5 min) ⚡ BOTTLENECK

```
ENTRADA:
  • Consolidado_API_Kawak.xlsx (histórico)
  • Resultados_Consolidados_Fuente.xlsx (archivo base con fórmulas)
  • Config mapeos procesos (YAML)

PROCESO:

1️⃣ DETECCIÓN N/A
   IF análisis contiene "no aplica":
     categoría = "No Aplica"
     cumplimiento = NULL
   ELIF sin resultado + sin variables útiles:
     categoría = "No Aplica"

2️⃣ EXTRACCIÓN META/EJECUCIÓN
   Patrón LAST (directo):
     meta = meta_api
     ejec = resultado_api
   
   Patrón VARIABLES (desglose):
     ejec = buscar_variable(símbolo='R')
     meta = buscar_variable(símbolo='M')
   
   Patrón SUM_SERIES (agregación):
     ejec = SUM(serie.resultado for serie en series)
     meta = SUM(serie.meta for serie en series)
   
   Heurística (automático):
     IF indicador_grande AND meta_es_porcentaje:
       extraer_de_variables()
     ELSE:
       usar_api_directo()

3️⃣ CÁLCULO CUMPLIMIENTO
   IF sentido == "ASCENDENTE":
     cumpl = ejecución / meta
   ELIF sentido == "DESCENDENTE":
     cumpl = meta / ejecución
   
   cumpl_capped = MIN(cumpl, tope=1.3)
   
4️⃣ TENDENCIA
   tendencia = COMPARAR(período_actual vs período_anterior)
   IF mejora > 2%: tendencia = ↑
   IF empeora > 2%: tendencia = ↓
   ELSE: tendencia = →

5️⃣ CATEGORIZACIÓN
   IF cumplimiento < 0.80: categoría = "Peligro" 🔴
   ELIF cumplimiento < 1.00: categoría = "Alerta" 🟡
   ELIF cumplimiento <= 1.04: categoría = "Cumplimiento" 🟢
   ELSE: categoría = "Sobrecumplimiento" 🔵

SALIDA:
  ✓ 3 hojas Excel:
    1. Consolidado Histórico (10,000+ registros)
    2. Consolidado Semestral (2,000+ registros agregados)
    3. Consolidado Cierres (500+ registros anuales)
```

### Paso 3: Generación de Reporte (30-60 seg)

```
ENTRADA:
  • Resultados_Consolidados.xlsx (consolidado actualizado)
  • lmi_reporte.xlsx (estructura LMI)

PROCESO:
  Para cada indicador en LMI:
    IF existe en Consolidado para período actual:
      estado = "Reportado" ✅
    ELSE:
      estado = "Pendiente" ⏳
    
    IF análisis = "no aplica":
      estado = "No Aplica" ⚪

SALIDA:
  ✓ Seguimiento_Reporte.xlsx:
    1. Tracking Mensual (matriz ID × mes)
    2. Seguimiento (copia LMI enriquecida)
    3. Resumen (estadísticas: reportados, pendientes, N/A)
```

---

## CÁLCULOS Y LÓGICA

### 1. Cumplimiento (Fórmula Principal)

```python
def calcular_cumplimiento(meta, ejecucion, sentido, tope=1.30):
    """
    Calcula cumplimiento de indicador.
    
    Args:
        meta (float): Valor meta
        ejecucion (float): Valor ejecutado
        sentido (str): "ASCENDENTE" o "DESCENDENTE"
        tope (float): Límite máximo (default 130%)
    
    Returns:
        tuple: (cumplimiento_real, cumplimiento_capped)
    """
    
    # Validación
    if meta is None or ejecucion is None:
        return (None, None)
    if meta == 0:
        return (None, None)
    if sentido == 'DESCENDENTE' and ejecucion == 0:
        return (None, None)  # División por cero
    
    # Cálculo
    if sentido == 'ASCENDENTE':
        cumpl = ejecucion / meta
    else:  # DESCENDENTE
        cumpl = meta / ejecucion
    
    # Aplicar negativos
    cumpl_real = max(cumpl, 0.0)
    cumpl_capped = min(cumpl_real, tope)
    
    return (cumpl_real, cumpl_capped)

# Ejemplos
# Ascendente: Meta 100, Ejecución 80
  cumpl = 80 / 100 = 0.80 (80%)  🟡 Alerta

# Descendente: Meta 10 (menos errores mejor), Ejecución 5
  cumpl = 10 / 5 = 2.0 (200%)  🔵 Sobrecumplimiento

# Sobrecumplimiento con tope: Meta 100, Ejecución 150
  cumpl_real = 150 / 100 = 1.50
  cumpl_capped = MIN(1.50, 1.30) = 1.30  🔵 (limitado a 130%)
```

### 2. Tendencia (Comparación Período)

```python
def calcular_tendencia(cumpl_actual, cumpl_anterior, umbral=0.02):
    """
    Calcula tendencia comparando cumplimiento.
    
    umbral=0.02 → require 2% de diferencia para cambiar
    """
    
    if cumpl_anterior is None or cumpl_actual is None:
        return None
    
    delta = cumpl_actual - cumpl_anterior
    delta_pct = abs(delta / cumpl_anterior) if cumpl_anterior != 0 else 0
    
    if delta_pct < umbral:
        return "→"  # Estable
    elif delta > 0:
        return "↑"  # Mejorada
    else:
        return "↓"  # Empeorada
    
    # Ejemplos
    # Anterior: 79%, Actual: 82% (delta +3%) → ↑ Mejorada
    # Anterior: 95%, Actual: 94% (delta -1%) → → Estable (< 2%)
    # Anterior: 50%, Actual: 45% (delta -5%) → ↓ Empeorada
```

### 3. Categorización

```python
def categorizar(cumplimiento_capped):
    """
    Categoriza cumplimiento en 4 niveles + N/A.
    """
    
    if cumplimiento_capped is None:
        return "Sin Dato"
    
    if cumplimiento_capped < 0.80:
        return "Peligro"  # 🔴
    elif cumplimiento_capped < 1.00:
        return "Alerta"  # 🟡
    elif cumplimiento_capped <= 1.04:
        return "Cumplimiento"  # 🟢
    else:
        return "Sobrecumplimiento"  # 🔵
    
    # EXCEPCIONES (Plan Anual)
    # IDs: 373, 390, 414-418, 420, 469-471
    # Umbrales: <95% = Peligro, 95-99% = Alerta, >=100% = Cumpl (sin sobre)
```

### 4. Extracción de Meta/Ejecución desde Variables

```python
def extraer_de_variables(variables, simbolo_meta='M', simbolo_ejec='R'):
    """
    Extrae meta y ejecución desde desglose de variables.
    
    Estructura variables:
    [
      {'simbolo': 'R', 'nombre': 'Real', 'valor': 85},
      {'simbolo': 'M', 'nombre': 'Meta', 'valor': 100},
      {'simbolo': 'P', 'nombre': 'Presupuesto', 'valor': 95}
    ]
    """
    
    meta = None
    ejec = None
    
    for var in variables:
        if var.get('simbolo') == simbolo_ejec:
            ejec = var.get('valor')
        if var.get('simbolo') == simbolo_meta:
            meta = var.get('valor')
    
    # Fallback por keywords si no existe símbolo
    if ejec is None:
        for var in variables:
            if any(k in var.get('nombre', '').lower() for k in ['real', 'ejecutado', 'ejecución']):
                ejec = var.get('valor')
                break
    
    if meta is None:
        for var in variables:
            if any(k in var.get('nombre', '').lower() for k in ['meta', 'planeado', 'presupuesto']):
                meta = var.get('valor')
                break
    
    return meta, ejec
```

### 5. Agregación Semestral

```python
def agregar_semestral(df_historico):
    """
    Agrega registros mensuales a semestral.
    """
    
    df_semestral = df_historico.groupby(
        ['id_indicador', 'ano', 'semestre']
    ).agg({
        'meta': 'mean',  # Promedio de metas
        'ejecucion': 'sum',  # Suma de ejecuciones
        'cumplimiento': 'mean',  # Promedio de cumplimientos
    }).reset_index()
    
    # Recalcular cumplimiento
    df_semestral['cumplimiento'] = (
        df_semestral['ejecucion'] / df_semestral['meta']
    )
    
    return df_semestral
```

---

## DICCIONARIO DE CAMPOS

### Tabla: resultados_indicadores

| Campo | Tipo | Descripción | Restricciones |
|-------|------|-----------|--------------|
| id_resultado | INT | Identificador único de registro | PK, auto-increment |
| id_indicador | VARCHAR(10) | Referencia a indicador maestro | FK, NOTNULL |
| fecha | DATE | Fecha del período reportado | NOTNULL, YYYY-MM-DD |
| ano | INT | Año del período | NOTNULL, ≥2022, ≤2030 |
| periodo | VARCHAR(20) | Identificador período | "01" (enero), "S1" (semestre 1), etc. |
| meta | FLOAT | Valor meta del período | ≥0, puede ser NULL si N/A |
| ejecucion | FLOAT | Valor ejecutado del período | ≥0, puede ser NULL si N/A |
| cumplimiento | FLOAT | ejecucion / meta (ascendente) | 0-∞, calculated |
| cumplimiento_capped | FLOAT | cumplimiento limitado a 130% | 0-1.30, calculated |
| categoria | VARCHAR(20) | Semáforo de riesgo | "PELIGRO" \| "ALERTA" \| "CUMPLIMIENTO" \| "SOBRECUMPLIMIENTO" |
| tendencia | VARCHAR(5) | Cambio vs período anterior | "↑" \| "→" \| "↓" \| NULL |
| estado_reporte | VARCHAR(20) | Fue reportado o pendiente | "REPORTADO" \| "PENDIENTE" \| "N/A" |
| fuente | VARCHAR(50) | Origen del dato | "API_KAWAK" \| "EXCEL_MANUAL" \| "CALCULO" |
| variables | JSON | Desglose de componentes | {"R": 85, "M": 100}, nullable |
| series | JSON | Series temporales asociadas | Array of objects, nullable |
| analisis | TEXT | Comentarios del responsable | Libre, nullable |
| timestamp_carga | DATETIME | Cuándo se cargó en SGIND | auto = NOW() |
| validado | BOOLEAN | Pasó validación de data contracts | 0 \| 1, default 0 |

---

## DATA CONTRACTS & VALIDACIÓN

### Data Contracts Implementados

#### ✅ Contract: `resultados_consolidados`

```yaml
fuente_nombre: "Resultados Consolidados"
archivo: "data/output/Resultados Consolidados.xlsx"
tipo: "EXCEL"

hojas:
  "Consolidado Semestral":
    columnas:
      Anio:
        tipo: "INTEGER"
        requerida: true
        min: 2022
        max: 2030
      
      Semestre:
        tipo: "STRING"
        requerida: true
        valores_permitidos: ["S1", "S2"]
      
      Id:
        tipo: "STRING"
        requerida: true
        patron: "^[A-Z0-9]{1,10}$"
      
      Indicador:
        tipo: "STRING"
        requerida: true
      
      Meta:
        tipo: "FLOAT"
        requerida: false
        min: 0.0
      
      Ejecucion:
        tipo: "FLOAT"
        requerida: false
        min: 0.0
      
      Cumplimiento:
        tipo: "FLOAT"
        requerida: false
        min: 0.0
        max: 2.0  # Permitir sobrecumplimientos
      
      Categoria:
        tipo: "CATEGORICAL"
        requerida: true
        valores_permitidos: 
          - "PELIGRO"
          - "ALERTA"
          - "CUMPLIMIENTO"
          - "SOBRECUMPLIMIENTO"
          - "Sin Dato"

  "Catalogo Indicadores":
    columnas:
      Id:
        tipo: "STRING"
        requerida: true
      
      Indicador:
        tipo: "STRING"
        requerida: true
      
      Periodicidad:
        tipo: "CATEGORICAL"
        valores_permitidos:
          - "MENSUAL"
          - "TRIMESTRAL"
          - "SEMESTRAL"
          - "ANUAL"
```

#### ✅ Contract: `kawak_consolidado`

```yaml
fuente_nombre: "Kawak Consolidado"
archivo: "data/raw/Fuentes Consolidadas/Consolidado_API_Kawak.xlsx"
tipo: "EXCEL"

hojas:
  "Sheet1":
    columnas:
      ID:
        tipo: "STRING"
        requerida: true
        unique: true  # No duplicados
      
      fecha:
        tipo: "DATETIME"
        requerida: true
        formato: "YYYY-MM-DD"
      
      resultado:
        tipo: "FLOAT"
        requerida: false
      
      meta:
        tipo: "FLOAT"
        requerida: false
      
      analisis:
        tipo: "STRING"
        requerida: false
```

### Validaciones Automáticas

```python
# services/data_validation.py

class ValidationReport:
    def __init__(self):
        self.issues = []
        self.error_count = 0
        self.warning_count = 0
    
    def add_issue(self, level, rule, description, row_count):
        """level: 'error' | 'warning'"""
        self.issues.append({
            'level': level,
            'rule': rule,
            'description': description,
            'row_count': row_count
        })
        if level == 'error':
            self.error_count += 1
        else:
            self.warning_count += 1

# Validaciones ejecutadas en CI/CD
✓ Required columns exist
✓ Data types match schema
✓ Categorical values in allowed set
✓ No nulls in required columns
✓ Numeric ranges (min/max) respected
✓ Unique constraints
✓ Referential integrity (FK checks)
✓ Cumplimiento = Ejecucion / Meta (lógica)
✓ Categoría matches cumplimiento thresholds
```

### Monitoreo de Data Quality

```
Métrica de Quality Score por fuente:

Quality Score = (1 - (errors + 0.5*warnings) / total_checks) * 100

Targets:
  🟢 Verde: ≥95% (< 5 issues críticas)
  🟡 Amarillo: 85-95% (5-15 issues)
  🔴 Rojo: <85% (> 15 issues, requiere investigación)

Reporte: Generado después de cada ETL
```

---

## REFERENCIAS CRUZADAS

| Concepto | Documentación | Script |
|----------|---|---------|
| Flujo completo | [ARQUITECTURA_TECNICA_DETALLADA.md](ARQUITECTURA_TECNICA_DETALLADA.md) | `scripts/actualizar_consolidado.py` |
| Extracción datos | [DOCUMENTACION_FUNCIONAL.md](DOCUMENTACION_FUNCIONAL.md) § Proceso 1 | `scripts/consolidar_api.py` |
| Cálculos detallados | `docs/calculos_actualizar_consolidado.md` | `core/calculos.py` |
| Validaciones | [DATA_CONTRACTS.md](docs/DATA_CONTRACTS.md) | `services/data_validation.py` |
| Reglas negocio | [TEORIA_OF_CHANGE_SGIND.md](THEORY_OF_CHANGE_SGIND.md) | `core/config.py` |

---

**Versión:** 1.0 | **Última actualización:** 14 de abril de 2026 | **Mantenedor:** Equipo SGIND
