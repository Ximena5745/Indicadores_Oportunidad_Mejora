# Arquitectura Técnica Detallada - SGIND

**Documento:** ARQUITECTURA_TECNICA_DETALLADA.md  
**Versión:** 2.0  
**Última actualización:** 11 de abril de 2026  
**Audiencia:** Arquitectos, desarrolladores senior, DevOps

---

## Tabla de Contenidos

1. [Visión General](#visión-general)
2. [Capas de Arquitectura](#capas-de-arquitectura)
3. [Módulos Core](#módulos-core)
4. [Pipeline ETL Detallado](#pipeline-etl-detallado)
5. [Capa de Datos](#capa-de-datos)
6. [Capa de Presentación](#capa-de-presentación)
7. [Estrategia de Caché](#estrategia-de-caché)
8. [Flujos de Datos](#flujos-de-datos)
9. [Problemas Identificados](#problemas-identificados)
10. [Hoja de Ruta Técnica](#hoja-de-ruta-técnica)

---

## Visión General

### Paradigma Arquitectónico: Post-Procesamiento

SGIND implementa un **paradigma de consolidación → reportería → reglas → monitoreo**:

```
FUENTE 1     FUENTE 2     FUENTE 3
   |             |            |
   └─────────────┴────────────┘
             ↓
    [CONSOLIDACIÓN ETL]
         ↓ ↓ ↓ 
    (Paso 1, 2, 3)
             ↓
    [ARTEFACTOS INTERMEDIOS]
    Excel con fórmulas y validaciones
             ↓
    [CAPA DE NEGOCIO]
    Reglas, umbrales, categorización
             ↓
    [REPORTERÍA]
    Dashboards, KPIs, alertas
             ↓
    [MONITOREO]
    Indicadores en paneles, seguimiento OM
```

**No** es un pipeline real-time. Es un **batch diario/semanal** que:
1. Consolida datos históricos
2. Aplica reglas de negocio
3. Genera reportería estática
4. Expone en dashboard interactivo

### Principios de Diseño

- **Separación de capas:** Core (lógica) ≠ Services (datos) ≠ UI (presentación)
- **Testeabilidad:** Lógica en `core/` sin dependencias Streamlit
- **Configurabilidad:** Umbrales en `core/config.py` (no hardcodeados)
- **Redundancia controlada:** Optimización vs. mantenibilidad
- **Persistencia dual:** SQLite (dev) + PostgreSQL (prod)

---

## Capas de Arquitectura

### 1. Capa de Integración (Fuentes)

**Responsabilidad:** Extraer datos de múltiples orígenes

**Componentes:**

| Componente | Tipo | Ubicación | Entrada | Salida | Frecuencia |
|-----------|------|-----------|---------|--------|-----------|
| API Kawak | Sistema web | Kawak.cloud | GET /api/indicators?year=2026 | JSON | Diaria |
| Excel Histórico | Archivo | `data/raw/Kawak/Catalogo_2026.xlsx` | Hojas: Indicadores, Procesos | 1000+ registros | Manual |
| LMI Reporte | Archivo | `data/raw/lmi_reporte.xlsx` | Hoja: LMI | Tracking | Mensual |
| API Interna | Base datos | PostgreSQL (prod) | Query OMs | 50-200 registros | Real-time |

**Configuración:** `config/settings.toml` (año cierre, rangos, URLs)

---

### 2. Capa de Consolidación (ETL)

**Responsabilidad:** Normalizar, validar, enriquecer datos

#### 2.1 Paso 1: `consolidar_api.py` (45-60 seg)

**Objetivo:** Fusionar Kawak + API en histórico único

**Flujo:**

```python
1. Limpiar directorio previo
   ├─ Eliminar Indicadores_Kawak.xlsx
   └─ Eliminar Consolidado_API_Kawak.xlsx

2. Cargar catálogos anuales
   ├─ data/raw/Kawak/Catalogo_2025.xlsx (estructura año anterior)
   ├─ data/raw/Kawak/Catalogo_2026.xlsx (años actuales)
   └─ Extrae: ID, Nombre, Proceso, Meta, Unidad, Fórmula

3. Normalizar IDs
   ├─ Eliminar espacios / caracteres especiales
   ├─ Aplicar mapeos especiales (IDS_PLAN_ANUAL, IDS_TOPE_100)
   └─ Crear llave única (id-periodo-año-sede)

4. Codificar HTML entities (→ Kawak retorna &quot;, &amp;)
   ├─ &quot; → "
   ├─ &amp; → &
   └─ &nbsp; → " "

5. Concatenar históricos
   ├─ Indicadores 2022.xlsx + 2023.xlsx + ... + 2026.xlsx
   └─ Preservar metadatos (Fecha, Fuente, Usuario)

6. Archivo de salida
   ├─ Indicadores_Kawak.xlsx (maestro de IDs activos)
   └─ Consolidado_API_Kawak.xlsx (histórico completo)
```

**Configuración:**

```toml
[ETL]
año_inicio = 2022
año_actual = 2026
ruta_kawak = "data/raw/Kawak"
ruta_api = "data/raw/API"
ruta_salida = "data/raw/Fuentes Consolidadas"
```

**Manejo de errores:**

```python
try:
    df = pd.read_excel(archivo)
except FileNotFoundError:
    logger.warning(f"Archivo no encontrado: {archivo}")
    df = pd.DataFrame()  # DataFrame vacío, continuar
except ValueError as e:
    logger.error(f"Error lectura Excel: {e}")
    raise  # Parar ejecución
```

---

#### 2.2 Paso 2: `actualizar_consolidado.py` (2-5 min) — MOTOR PRINCIPAL

**Objetivo:** Aplicar reglas de negocio y generar reportería

**Arquitectura modular:**

```
actualizar_consolidado.py (orquestador principal)
│
├── scripts/etl/config.py
│   └─ Cargar settings.toml (año_cierre, validaciones)
│
├── scripts/etl/fuentes.py
│   ├─ cargar_fuente_consolidada() → DataFrame histórico
│   └─ cargar_kawak_validos() → IDs activos con metadatos
│
├── scripts/etl/catalogo.py
│   ├─ cargar_catalogo_completo() → CMI + LMI + mapeos
│   └─ enrichment_indicadores() → Agrega proceso, subproceso, área
│
├── scripts/etl/builders.py
│   ├─ construir_registros_historico() → Hoja "Consolidado Histórico"
│   ├─ construir_registros_semestral() → Hoja "Consolidado Semestral" (agg)
│   └─ construir_cierres() → Hoja "Consolidado Cierres" (cierre anual)
│
├── scripts/etl/formulas_excel.py
│   └─ _reescribir_formulas() → Materializar Excel formulas en valores
│
├── scripts/etl/workbook_io.py
│   ├─ workbook_local_copy() → Copiar seguro en Excel
│   └─ workbook_write_safe() → Escribir sin corrupción
│
├── scripts/etl/normalizacion.py
│   ├─ normalizar_cumplimiento() → % → decimal
│   ├─ detectar_na() → Análisis contiene "no aplica"
│   └─ deduplicar() → LLAVE única por registro
│
└── scripts/etl/validacion.py
    ├─ validar_metas() → Meta > 0
    ├─ validar_ejecuciones() → Ejecución ≥ 0
    └─ validar_fechas() → Formato YYYY-MM-DD
```

**Lógica de Cálculo (Principal):**

```python
# Para cada indicador en Consolidado_API_Kawak:
for id_indicador, registros in df.groupby('id'):
    
    # 1. NORMALIZACIÓN
    registros['cumplimiento'] = registros.apply(
        lambda r: normalizar_cumplimiento(r['cumplimiento'])
    )
    
    # 2. DETECCIÓN N/A
    if 'no aplica' in registros['analisis'].lower():
        registros['categoria'] = 'Sin Dato'
        continue
    
    # 3. CATEGORIZACIÓN (con especiales)
    registros['categoria'] = registros.apply(
        lambda r: categorizar_cumplimiento(
            cumplimiento=r['cumplimiento'],
            id_indicador=id_indicador,
            config=config  # umbrales
        ),
        axis=1
    )
    
    # 4. TENDENCIA (último vs penúltimo período)
    registros_ordenados = registros.sort_values('fecha')
    if len(registros_ordenados) >= 2:
        tendencia = calcular_tendencia(
            registros_ordenados[-1]['cumplimiento'],
            registros_ordenados[-2]['cumplimiento']
        )
        registros['tendencia'] = tendencia
    
    # 5. RECOMENDACIONES
    registros['recomendacion'] = registros.apply(
        lambda r: generar_recomendaciones(
            categoria=r['categoria'],
            cumplimiento_series=registros['cumplimiento'].values
        ),
        axis=1
    )
```

**Especiales de Negocio:**

```python
# core/config.py

# Umbral bajo para Plan Anual
IDS_PLAN_ANUAL = frozenset([373, 390, 414, 415, 416, 417, 418, 419, 420, 469, 470, 471])
UMBRAL_PLAN_ANUAL = 0.95  # En lugar de 1.00

# Tope en 100% (no permite sobrecumpl)
IDS_TOPE_100 = frozenset([208, 218])

# Umbrales estándar
UMBRAL_PELIGRO = 0.80              # 0 a 79%
UMBRAL_ALERTA = 1.00               # 80 a 99%
UMBRAL_SOBRECUMPLIMIENTO = 1.05    # 105+%

# Colores semáforo
COLORES_SEMAFORO = {
    'Peligro': '#D32F2F',               # Rojo
    'Alerta': '#FBAF17',                # Naranja
    'Cumplimiento': '#43A047',          # Verde
    'Sobrecumplimiento': '#1A3A5C',     # Azul oscuro
    'Sin Dato': '#CCCCCC'               # Gris
}
```

**Deduplicación:**

```python
# Manejo de múltiples registros para misma fecha
df_indicador = df[df['id'] == id_indicador].sort_values('fecha', ascending=False)

# Llave única: (id, periodo, año, sede)
llave = (df_indicador['id_indicador'], 
         df_indicador['periodo'], 
         df_indicador['anio'], 
         df_indicador['sede'])

# Prioridad si duplicados:
# 1. Si existe "Revisar" = 1 → Usar ese
# 2. Si no → Usar más reciente (por fecha de carga)

df_dedup = df_indicador.drop_duplicates(subset=llave, keep='first')
```

**Output:**

```
Resultados Consolidados.xlsx:
├─ Hoja: "Consolidado Histórico" (10,000+ registros)
│  Columnas: id, nombre, proceso, periodo, año, cumplimiento, 
│            categoría, tendencia, recomendación, fecha_carga
│
├─ Hoja: "Consolidado Semestral" (2,000+ registros agregados)
│  Grupo: (id, año, semestre)
│  Agregación: 
│    - cumplimiento → PROMEDIO
│    - categoría → MODA (más frecuente)
│    - tendencia → Último período
│
└─ Hoja: "Consolidado Cierres" (500+ registros)
   Grupo: (id, año)
   Cierre anual (último registro del año)
```

---

#### 2.3 Paso 3: `generar_reporte.py` (30-60 seg)

**Objetivo:** Generar tracking de qué fue reportado vs pendiente

**Entrada:**

1. `lmi_reporte.xlsx` (estructura de indicadores LMI)
2. `Consolidado_API_Kawak.xlsx` (Paso 1, para detectar "Reportado")

**Lógica:**

```python
# Cargar LMI estructura
df_lmi = pd.read_excel('data/raw/lmi_reporte.xlsx')

# Cargar API histórico
df_api = pd.read_excel('data/raw/Fuentes Consolidadas/Consolidado_API_Kawak.xlsx')

# Para cada indicador LMI en período actual:
for idx, row in df_lmi.iterrows():
    id_indicador = row['id_indicador']
    periodo = row['periodo_actual']  # Ej: 2026-03
    
    # ¿Este indicador fue reportado en este período?
    if existe_registro_en_periodo(df_api, id_indicador, periodo):
        estado = "Reportado"
    else:
        estado = "Pendiente"
    
    # Casos especiales: "No aplica"
    if es_no_aplica(row['analisis']):
        estado = "No Aplica"
    
    df_reporte.loc[idx, 'estado'] = estado

# Salida: Matriz ID × mes con estados
# Ejemplo:
#   ID    | Ene 26 | Feb 26 | Mar 26
#   ----  | ------ | ------ | ------
#   150   | Report | Report | Pend
#   151   | Report | N/A    | N/A
#   152   | Pend   | Report | Report
```

**Output:**

```
Seguimiento_Reporte.xlsx:
├─ Hoja: "Tracking Mensual" (Matriz)
│  Índices: Indicador ID
│  Columnas: Enero, Febrero, ..., Diciembre
│  Valores: "Reportado" / "Pendiente" / "No Aplica"
│
├─ Hoja: "Seguimiento" (Copia LMI enriquecida)
│  Copia del LMI + columna "Estado Reporte" (Reportado/Pend/N/A)
│
├─ Hoja: "Resumen" (Estadísticas)
│  Estadísticas por periodicidad:
│    - Total indicadores: 1000
│    - Reportados: 950
│    - Pendientes: 40
│    - No aplica: 10
│
└─ Hojas por periodicidad (dinámicas)
   Renombradas con fechas: "2026-Q1", "2026-Semestre 1", etc.
```

---

## Módulos Core

### `core/calculos.py` (200 líneas) — Lógica Pura

**Responsabilidad:** Cálculos de indicadores (sin Streamlit, sin BD)

**Funciones principales:**

```python
def normalizar_cumplimiento(valor: float) -> float:
    """
    Convierte escala de % a decimal si valor > 2.
    
    Ejemplo:
        95 → 0.95 (si valor ≤ 2 ya es decimal)
        1.05 → 1.05 (no para, ya decimal)
        150 → 1.50 (conversión % → decimal)
    """
    if valor > 2:
        valor = valor / 100
    return max(0, valor)  # Evitar negativos


def categorizar_cumplimiento(
    cumplimiento: float, 
    id_indicador: int,
    config: dict = None
) -> str:
    """
    Mapea cumplimiento a categoría con reglas especiales.
    
    Lógica:
        - IDS_PLAN_ANUAL: Umbral bajo (0.95 en lugar de 1.00)
        - IDS_TOPE_100: Capped a 1.00 máximo
        - Estándares: 0.80/1.00/1.05
    
    Retorna: "Peligro" | "Alerta" | "Cumplimiento" | "Sobrecumplimiento" | "Sin Dato"
    """
    if pd.isna(cumplimiento):
        return "Sin Dato"
    
    # Special case: Plan Anual
    if id_indicador in IDS_PLAN_ANUAL:
        if cumplimiento < 0.95:
            return "Peligro"
        elif cumplimiento < 1.00:
            return "Alerta"
        else:
            return "Cumplimiento"  # Tope 100%, no sobrecumple
    
    # Special case: Indicadores con tope
    if id_indicador in IDS_TOPE_100:
        cumplimiento = min(cumplimiento, 1.00)
    
    # Estándar
    if cumplimiento < UMBRAL_PELIGRO:
        return "Peligro"
    elif cumplimiento < UMBRAL_ALERTA:
        return "Alerta"
    elif cumplimiento < UMBRAL_SOBRECUMPLIMIENTO:
        return "Cumplimiento"
    else:
        return "Sobrecumplimiento"


def calcular_tendencia(df_indicador: pd.DataFrame, periodos: int = 2) -> str:
    """
    Compara últimos periodos para detectar mejora/empeoramiento.
    
    Retorna: "↑" (mejora) | "↓" (empeora) | "→" (estable)
    
    Umbral estabilidad: ±2% cambio
    """
    if len(df_indicador) < periodos:
        return "→"  # Datos insuficientes
    
    df_ord = df_indicador.sort_values('fecha')
    ultimo = df_ord.iloc[-1]['cumplimiento']
    penultimo = df_ord.iloc[-2]['cumplimiento']
    
    cambio = (ultimo - penultimo) / penultimo if penultimo != 0 else 0
    
    if cambio > 0.02:
        return "↑"
    elif cambio < -0.02:
        return "↓"
    else:
        return "→"


def calcular_meses_en_peligro(df_indicador: pd.DataFrame) -> int:
    """
    Cuenta períodos consecutivos en estado "Peligro".
    
    Usa para: Alertas urgentes (ej: 3+ meses en peligro)
    """
    df_ord = df_indicador.sort_values('fecha')
    contador = 0
    
    for _, row in df_ord.iloc[::-1].iterrows():
        if row['categoria'] == 'Peligro':
            contador += 1
        else:
            break
    
    return contador


def generar_recomendaciones(categoria: str, cum_series: list) -> str:
    """
    Genera recomendación contextual según categoría y tendencia.
    
    Ejemplos:
        "Peligro" + ↓ → "Deterioro crítico. Ejecutar plan de acción inmediato."
        "Cumplimiento" + ↑ → "En buen camino. Mantener iniciativas actuales."
        "Alerta" + → → "A punto de incumplir. Intensificar esfuerzos."
    
    Retorna: String (150 caracteres máximo)
    """
    recomendaciones = {
        'Peligro': "🔴 Crítico: Ejecutar plan de acción emergente.",
        'Alerta': "🟡 Riesgo: Intensificar esfuerzos para cumplimiento.",
        'Cumplimiento': "🟢 Mantener: Continuar iniciativas actuales.",
        'Sobrecumplimiento': "🔵 Excelente: Documentar éxito y replicar.",
        'Sin Dato': "⚪ Pendiente: Aguardar dato actual."
    }
    
    return recomendaciones.get(categoria, "Sin recomendación")


def calcular_kpis(df_ultimo: pd.DataFrame) -> dict:
    """
    Calcula KPIs agregados desde último registro por indicador.
    
    Retorna:
        {
            'total_indicadores': 1000,
            'en_peligro': 50,
            'en_alerta': 150,
            'cumplidos': 700,
            'sobrecumplidos': 100,
            'tasa_cumplimiento': 0.80,
            'indicadores_sin_dato': 0
        }
    """
    total = len(df_ultimo)
    peligro = (df_ultimo['categoria'] == 'Peligro').sum()
    alerta = (df_ultimo['categoria'] == 'Alerta').sum()
    cumplimiento = (df_ultimo['categoria'] == 'Cumplimiento').sum()
    sobrecumpl = (df_ultimo['categoria'] == 'Sobrecumplimiento').sum()
    sin_dato = (df_ultimo['categoria'] == 'Sin Dato').sum()
    
    tasa = (cumplimiento + sobrecumpl) / (total - sin_dato) if (total - sin_dato) > 0 else 0
    
    return {
        'total_indicadores': total,
        'en_peligro': peligro,
        'en_alerta': alerta,
        'cumplidos': cumplimiento,
        'sobrecumplidos': sobrecumpl,
        'tasa_cumplimiento': round(tasa, 4),
        'indicadores_sin_dato': sin_dato
    }
```

**Tests:**

```python
# tests/test_calculos.py
def test_normalizar_cumplimiento():
    assert normalizar_cumplimiento(95) == 0.95
    assert normalizar_cumplimiento(1.05) == 1.05
    assert normalizar_cumplimiento(0) == 0

def test_categorizar_plan_anual():
    assert categorizar_cumplimiento(0.94, id_indicador=373) == "Peligro"
    assert categorizar_cumplimiento(0.95, id_indicador=373) != "Peligro"
    # Plan Anual: umbral bajo

def test_calcular_tendencia():
    df = pd.DataFrame({
        'fecha': ['2026-01-01', '2026-02-01'],
        'cumplimiento': [0.80, 0.85]
    })
    assert calcular_tendencia(df) == "↑"

# 50+ casos más...
```

---

### `core/config.py` (150 líneas) — Single Source of Truth

**Responsabilidad:** Constantes y configuración centralizada

```python
# UMBRALES DE CUMPLIMIENTO
UMBRAL_PELIGRO = 0.80              # 0-79%    → Rojo
UMBRAL_ALERTA = 1.00               # 80-99%   → Naranja
UMBRAL_SOBRECUMPLIMIENTO = 1.05    # 105%+    → Azul

# INDICADORES CON REGLAS ESPECIALES
IDS_PLAN_ANUAL = frozenset([
    373, 390, 414, 415, 416, 417, 418, 419, 420, 469, 470, 471
])
# Estas IDs cumplen desde 95% (no 100%)

IDS_TOPE_100 = frozenset([208, 218])
# Estos indicadores máximo llegan a 100% (no permiten sobrecumpl)

# COLORES SEMÁFORO
COLORES_SEMAFORO = {
    'Peligro': '#D32F2F',                # RGB: 211, 47, 47 - Rojo
    'Alerta': '#FBAF17',                 # RGB: 251, 175, 23 - Naranja
    'Cumplimiento': '#43A047',           # RGB: 67, 160, 71 - Verde
    'Sobrecumplimiento': '#1A3A5C',      # RGB: 26, 58, 92 - Azul oscuro
    'Sin Dato': '#CCCCCC'                # RGB: 204, 204, 204 - Gris
}

# CACHÉ
CACHE_TTL = 300  # segundos - Estandarizado para todas las páginas

# COLUMNAS DE TABLA
COLS_TABLA_RESUMEN = [
    'id_indicador',
    'nombre_indicador',
    'proceso',
    'periodo',
    'cumplimiento',
    'categoria',
    'tendencia',
    'recomendacion'
]

COLS_TABLA_RIESGO = [
    'id_indicador',
    'nombre',
    'categoria',
    'meses_en_peligro',
    'accion_recomendada'
]

COLS_TABLA_OM = [
    'numero_om',
    'id_indicador',
    'descripcion',
    'estado',
    'fecha_cierre_planeada',
    'responsable'
]

# MAPEOS ESPECIALES (CANDIDATOS PARA YAML)
# Proceso padre para cada subprocess
MAPA_PROCESO_PADRE = {
    "Dirección Estratégica": "DIRECCIONAMIENTO ESTRATÉGICO",
    "Gestión de Proyectos": "DIRECCIONAMIENTO ESTRATÉGICO",
    # ... 50+ más (EXTRAER A YAML EN FASE 2)
}
```

**Uso en código:**

```python
from core.config import (
    UMBRAL_PELIGRO, 
    COLORES_SEMAFORO, 
    IDS_PLAN_ANUAL,
    CACHE_TTL
)

# En lugar de hardcodear valores
if cumplimiento < UMBRAL_PELIGRO:
    color = COLORES_SEMAFORO['Peligro']
```

---

### `core/db_manager.py` (100 líneas) — Persistencia Dual

**Responsabilidad:** Abstraer BD (SQLite desarrollo | PostgreSQL producción)

```python
import sqlalchemy as sa
import os

class DBManager:
    """Gestor de persistencia con soporte dual (SQLite/PostgreSQL)."""
    
    def __init__(self):
        # Preferencia PostgreSQL (prod) → fallback SQLite (dev)
        self.db_url = os.environ.get(
            'DATABASE_URL',
            'sqlite:///data/db/registros_om.db'
        )
        self.engine = sa.create_engine(self.db_url)
        self._init_tables()
    
    def _init_tables(self):
        """Crear tablas si no existen."""
        Base.metadata.create_all(self.engine)
    
    def crear_om(self, numero_om: int, id_indicador: int, 
                 descripcion: str, estado: str = "abierta"):
        """
        Registrar nueva Oportunidad de Mejora.
        
        LLAVE ÚNICA: (id_indicador, periodo, año, sede)
        """
        with sa.orm.Session(self.engine) as session:
            om = RegistroOM(
                numero_om=numero_om,
                id_indicador=id_indicador,
                descripcion=descripcion,
                estado=estado,
                periodo=self._obtener_periodo_actual(),
                anio=datetime.now().year,
                sede='MATRIZ'
            )
            
            # Upsert: Si existe por LLAVE, actualizar; si no, insertar
            stmt = sa.insert(RegistroOM).values(
                numero_om=numero_om,
                id_indicador=id_indicador,
                periodo=om.periodo,
                anio=om.anio,
                sede=om.sede,
                descripcion=descripcion,
                estado=estado
            ).on_conflict_do_update(
                index_elements=['id_indicador', 'periodo', 'anio', 'sede'],
                set_=dict(descripcion=descripcion, estado=estado)
            )
            
            session.execute(stmt)
            session.commit()
    
    def obtener_om(self, id_indicador: int) -> list:
        """Recuperar todas las OMs para indicador."""
        with sa.orm.Session(self.engine) as session:
            return session.query(RegistroOM).filter(
                RegistroOM.id_indicador == id_indicador
            ).all()

# Modelo SQLAlchemy
class RegistroOM(Base):
    __tablename__ = 'registros_om'
    
    id = sa.Column(sa.Integer, primary_key=True)
    numero_om = sa.Column(sa.String(20), nullable=False)
    id_indicador = sa.Column(sa.Integer, nullable=False)
    descripcion = sa.Column(sa.String(500))
    estado = sa.Column(sa.String(20), default='abierta')
    fecha_creacion = sa.Column(sa.DateTime, default=datetime.now)
    fecha_cierre = sa.Column(sa.DateTime)
    periodo = sa.Column(sa.String(10))
    anio = sa.Column(sa.Integer)
    sede = sa.Column(sa.String(50))
    
    __table_args__ = (
        sa.UniqueConstraint(
            'id_indicador', 'periodo', 'anio', 'sede',
            name='uq_om_key'
        ),
    )

# Instancia global
db = DBManager()
```

**Ventajas de patrón dual:**

| Escenario | BD Usada | Ventaja |
|-----------|----------|---------|
| Desarrollo local | SQLite (archivo) | Sin dependencias externas, más rápido |
| Testing | SQLite (en memoria) | Aislamiento total, rápido |
| Producción (Render) | PostgreSQL | Concurrencia, backups, escalabilidad |
| Transición | Ambas | Migración sin downtime |

---

### `core/niveles.py` (80 líneas) — [DEPRECADO]

**Problema:** Duplica constantes de `config.py`

```python
# ❌ INCORRECTO (Hoy)
from core.niveles import UMBRAL_PELIGRO  # Reimporta desde config.py

# ✅ CORRECTO (Post-refactor)
from core.config import UMBRAL_PELIGRO
```

**Plan:** Eliminar en Fase 2 cleanup (ver LIMPIEZA_REPOSITORIO_SGIND.md)

---

## Pipeline ETL Detallado

### Diagrama de Flujo Completo

```
INICIO
  ↓
[Paso 1: consolidar_api.py — 45-60 seg]
  ├─ Entrada: data/raw/Kawak/*.xlsx + data/raw/API/*.xlsx
  ├─ Proceso:
  │  1. Limpiar directorio previo
  │  2. Cargar catálogos años 2022-2026
  │  3. Normalizar IDs (espacios, caracteres)
  │  4. Codificar HTML entities
  │  5. Concatenar históricos
  └─ Salida:
     ├─ Indicadores_Kawak.xlsx (maestro)
     └─ Consolidado_API_Kawak.xlsx (histórico)
  ↓
[Paso 2: actualizar_consolidado.py — 2-5 min]
  ├─ Entrada: Consolidado_API_Kawak.xlsx + config/settings.toml + catálogos
  ├─ Proceso:
  │  1. Cargar datos fuente consolidada
  │  2. Enriquecer con metadatos (Proceso, CMI, LMI)
  │  3. Detectar N/A (análisis contiene texto)
  │  4. Normalizar cumplimiento (% → decimal)
  │  5. Validar metas > 0 y ejecuciones ≥ 0
  │  6. Deduplicar por LLAVE única (id-período-año-sede)
  │  7. Categorizar (Peligro/Alerta/Cumpl/Sobre)
  │  8. Calcular tendencias (mejora/empeora)
  │  9. Generar recomendaciones
  │ 10. Construir 3 hojas (Histórico, Semestral, Cierres)
  │ 11. Materializar fórmulas Excel
  └─ Salida: Resultados Consolidados.xlsx (10,000+ registros)
  ↓
[Paso 3: generar_reporte.py — 30-60 seg]
  ├─ Entrada: lmi_reporte.xlsx + Consolidado_API_Kawak.xlsx
  ├─ Proceso:
  │  1. Cargar estructura LMI
  │  2. Para cada indicador LMI, detectar:
  │     - ¿Fue reportado en período actual? → "Reportado"
  │     - ¿Está marcado como N/A? → "No Aplica"
  │     - De lo contrario → "Pendiente"
  │  3. Construir matriz ID × mes
  │  4. Generar estadísticas (50 reportados / 40 pendientes / 10 N/A)
  │  5. Crear hojas por periodicidad (mensuales, semestrales)
  └─ Salida: Seguimiento_Reporte.xlsx (4 hojas)
  ↓
[Validación de Salida]
  ├─ ✓ Verificar archivo existe
  ├─ ✓ Verificar hojas esperadas
  └─ ✓ Verificar > 0 registros
  ↓
[Generación QA Report]
  ├─ Crear artifacts/pipeline_run_YYYYMMDD_HHMMSS.json
  ├─ Incluir: Duraciones, registros procesados, errores (si los hay)
  └─ Crear artifacts/pipeline_run_YYYYMMDD_HHMMSS.log
  ↓
FIN ✓
```

### Matriz de Dependencias

```
┌─────────────────────────────────────────────────────────┐
│                    run_pipeline.py                       │
│              (Orquestador principal)                     │
└─────┬──────────────────────────────────────────────┬────┘
      │                                              │
      ├─ [Ejecutar] consolidar_api.py ────┐        │
      │                                    │        │
      │  Entrada: Kawak/*.xlsx, API/*.xlsx│        │
      │  Salida:  Consolidado_API_Kawak   │        │
      │                                    │        │
      ├────────────────────────────────────┴─┐     │
      │                                       ↓     │
      ├─ [Ejecutar] actualizar_consolidado.py│     │
      │              + scripts/etl/*          │     │
      │                                       │     │
      │  Entrada: Consolidado_API_Kawak +    │     │
      │           catálogos + config          │     │
      │  Salida:  Resultados Consolidados    │     │
      │                                       │     │
      ├───────────────────────────────────────┼─┐   │
      │                                       │ ↓   │
      ├─ [Ejecutar] generar_reporte.py      │     │
      │                                       │     │
      │  Entrada: lmi_reporte.xlsx +         │     │
      │           Consolidado_API_Kawak      │     │
      │  Salida:  Seguimiento_Reporte        │     │
      │                                       │     │
      └───────────────────────────────────────┼─────┘
                                              ↓
                                  [VALIDACIÓN + QA]
                                        ↓
                                  [ARTEFACTOS OK]
```

---

## Capa de Datos

### Ubicaciones Físicas

| Artefacto | Ubicación | Tamaño | Generado | Frecuencia |
|-----------|-----------|--------|----------|-----------|
| Indicadores_Kawak.xlsx | `data/raw/Fuentes Consolidadas/` | 50 KB | Paso 1 | Diaria |
| Consolidado_API_Kawak.xlsx | `data/raw/Fuentes Consolidadas/` | 5-10 MB | Paso 1 | Diaria |
| Resultados Consolidados.xlsx | `data/output/` | 15-20 MB | Paso 2 | Diaria |
| Seguimiento_Reporte.xlsx | `data/output/` | 2-5 MB | Paso 3 | Diaria |
| registros_om.db | `data/db/` | <1 MB | BD | Continuamente |
| pipeline_run_*.json | `artifacts/` | <100 KB | Orquestador | Cada ejecución |
| lmi_reporte.xlsx | `data/raw/` | 200 KB | Manual | Mensual |

### Esquema Lógico de Datos

```
CONSOLIDADO_HISTORICO (10,000+ registros)
├─ id_indicador (clave foránea hacia Indicadores_Kawak)
├─ nombre_indicador (string, ej: "Tasa de aprobación")
├─ proceso (string, ej: "DOCENCIA")
├─ subproceso (string, ej: "Pregrado")
├─ area (string, ej: "VICERRECTORÍA ACADÉMICA")
├─ periodo (string, ej: "2026-03", formato YYYY-MM)
├─ anio (integer, ej: 2026)
├─ fecha_corte (date, ej: 2026-03-31)
├─ ejecucion (float, ej: 85.5)
├─ meta (float, ej: 90.0)
├─ cumplimiento (float, ej: 0.95, NORMALIZADO)
├─ categoria (enum: Peligro|Alerta|Cumplimiento|Sobrecumplimiento|Sin Dato)
├─ tendencia (enum: ↑|↓|→)
├─ analisis (string, ej: "Aumento de aprobados en X% por...")
├─ recomendacion (string, ej: "Mantener iniciativas...")
├─ fuente (enum: Kawak|API|Manual)
├─ usuario_carga (string, ej: "sistema@poli.edu.co")
├─ fecha_carga (datetime, timestamp de ingesta)
└─ revisar (boolean, flag para validación manual)

CONSOLIDADO_SEMESTRAL (2,000+ registros, agregado)
├─ id_indicador
├─ periodo_semestral (string, ej: "2026-S1")
├─ cumplimiento_promedio (float, AVG de ese semestre)
├─ categoria_moda (enum, categoría más frecuente en sem)
├─ meses_en_peligro (integer, count)
└─ tendencia_semestral (enum: ↑|↓|→)

CONSOLIDADO_CIERRES (500+ registros, cierre anual)
├─ id_indicador
├─ anio
├─ cumplimiento_anual (float, cierre final del año)
├─ categoria_anual (enum)
├─ variacion_anual (float, (cierre_actual - cierre_anterior) / cierre_anterior)
└─ indicadores_bajo_meta (count, cuántos meses estuvo bajo meta)

REGISTROS_OM (50-500 registros)
├─ id (PK)
├─ numero_om (ej: "OM-2026-001")
├─ id_indicador (FK)
├─ descripcion (text, max 500 chars)
├─ estado (enum: abierta|en_ejecucion|cerrada|retrasada)
├─ fecha_creacion (datetime)
├─ fecha_cierre_planeada (date)
├─ fecha_cierre_real (date)
├─ responsable (string, ej: "Juan Pérez")
├─ periodo (string, ej: "2026-Q1")
├─ anio (integer)
├─ sede (string, ej: "MATRIZ")
└─ UNIQUE CONSTRAINT: (id_indicador, periodo, anio, sede)

LMI_REPORTE (1,700+ registros, NO modificado por nosotros)
├─ id_indicador
├─ nombre
├─ periodicidad (enum: Mensual|Semestral|Anual)
├─ periodo_LMI (string, ej: "03/2026")
└─ analisis (text, notas cuáles son N/A)
```

---

## Capa de Presentación

### Streamlit Architecture

```
streamlit_app/
├── main.py (Punto de entrada)
│   └─ st.set_page_config(layout="wide", page_title="SGIND")
│   └─ Ruta páginas: streamlit_app/pages/*.py
│
├── pages/
│   ├── resumen_general.py (1900 líneas)
│   │   ├─ Tabs: Consolidado | Histórico | Cierres
│   │   ├─ Filtros dinámicos (Año, Mes, Proceso, Subprocess, ID, Categoría)
│   │   ├─ KPIs: Total, Peligro, Alerta, Cumplimiento, Sobrecumpl
│   │   ├─ Tablas interactivas (Plotly DataTable con sorting/filtering)
│   │   ├─ Gráficos (Tendencias, scatter, heatmaps Semaforo)
│   │   ├─ Drill-down: Click fila → Modal con detalles indicador
│   │   └─ Exportación: Excel styling con formatos/colores
│   │
│   ├── cmi_estrategico.py (250 líneas)
│   │   ├─ Perspectivas: Financiera | Procesos | Aprendizaje | Cliente
│   │   ├─ Filtros: Línea estratégica, Año
│   │   ├─ Visualización trendlines
│   │   └─ Target vs actuales
│   │
│   ├── plan_mejoramiento.py (150 líneas)
│   │   ├─ Tabla OMs: Estado, Responsable, Plazo
│   │   ├─ Botón: "+ Nueva OM" → Modal de creación
│   │   ├─ Update estado: Abierta → En ejecución → Cerrada
│   │   └─ Vínculo: OM ← Indicador en incumplimiento
│   │
│   ├── resumen_por_proceso.py
│   │   ├─ Seleccionar Proceso → Subprocesos
│   │   ├─ Heatmap (Subproceso × Período) con semáforo
│   │   ├─ Tabla detalle: Indicadores en cada subproceso
│   │   └─ Drill-down a indicador
│   │
│   ├── gestion_om.py
│   │   ├─ Página activa para creación/seguimiento OM
│   │   └─ Integrada con `core/db_manager.py`
│   │
│   ├── seguimiento_reportes.py
│   │   ├─ Página activa de tracking mensual
│   │   └─ Lee `data/output/Seguimiento_Reporte.xlsx`
│
├── components/
│   ├── charts.py
│   │   ├─ plot_tendencia_lineal(df, id) → Plotly figure
│   │   ├─ plot_matriz_semaforo(df) → Heatmap coloreado
│   │   ├─ plot_scatter_riesgo(df) → Scatter categorías
│   │   └─ plot_distribucion_estados(df) → Donut chart
│   │
│   └── filters.py
│       ├─ select_anio() → Dropdown años [2022..2026]
│       ├─ select_mes() → Dropdown / Slider periodos
│       ├─ select_proceso() → Multiselect procesos
│       └─ select_categoria() → Checkboxes [Peligro, Alerta, ...]
│
├── services/
│   ├── strategic_indicators.py
│   │   ├─ obtener_perspectiva(perspectiva: str) → df
│   │   └─ calcular_kpis_cmi() → KPIs por perspectiva
│   │
│   └── __init__.py
│
├── styles/
│   ├── custom.css
│   │   └─ Colores semáforo, fuentes, espaciado
│   │
│   └── theme.json
│       └─ Configuración Streamlit theme colors
│
└── assets/
    ├── logo_poli.png
    ├── icono_peligro.svg
    ├── icono_alerta.svg
    ├── ...
    └── favicon.ico
```

### Flujo de Estado (Session State)

```python
# https://docs.streamlit.io/library/api-reference/session-state

# Estado global compartido entre páginas
st.session_state:
    ├─ "selected_anio" = 2026 (Año seleccionado)
    ├─ "selected_mes" = "03" (Mes seleccionado)
    ├─ "selected_proceso" = ["DOCENCIA", "INVESTIGACION"] (Procesos)
    ├─ "filtro_categoria" = ["Peligro", "Alerta"] (Categorías a mostrar)
    ├─ "om_modal_visible" = False (Mostrar/ocultar modal OM)
    ├─ "om_id_seleccionado" = None (ID indicador para OM)
    ├─ "drilldown_id_indicador" = None (Indicador en drill-down)
    ├─ "page_view_mode" = "tabla" (Tabla vs gráfico)
    │
    └─ [PROBLEMA]: Keys NO namespaced
        ├─ ❌ "rc_clear_global" (origen: resumen_general.py)
        ├─ ❌ "cmi_pdi_objetivo" (origen: cmi_estrategico.py)
        ├─ ⚠️ Colisiones potenciales entre páginas
        └─ ✅ SOLUCIÓN: Implementar key_generator(page, feature) (Fase 2)
```

---

## Estrategia de Caché

### Problema Vigente

```python
# ❌ INCONSISTENCIA ACTUAL

# Página 1: resumen_general.py
@st.cache_data(ttl=600)  # 10 minutos
def cargar_consolidados():
    return pd.read_excel('Resultados Consolidados.xlsx')

# Página 2: cmi_estrategico.py
@st.cache_data(ttl=300)  # 5 minutos
def cargar_consolidados():
    return pd.read_excel('Resultados Consolidados.xlsx')

# Usuario ve datos desincronizados hasta 5-10 minutos después del pipeline
```

### Solución Propuesta (Fase 1)

```python
# ✅ ESTANDARIZAR EN config.py

from core.config import CACHE_TTL  # 300 segundos

@st.cache_data(ttl=CACHE_TTL)
def cargar_consolidados():
    """Cargar desde caché centralizado."""
    return pd.read_excel('Resultados Consolidados.xlsx')

# Aplicar a TODAS las funciones con @st.cache_data
```

### Capas de Caché

```
┌─ CAPA 1: Caché Python (en memoria)
│  ├─ TTL: 5 minutos (CACHE_TTL = 300s)
│  ├─ Aplicado a: Todas funciones de lectura Excel
│  └─ Invalidación: Manual con st.cache_data.clear() + restart
│
├─ CAPA 2: Archivos Excel (disco)
│  ├─ Ubicación: data/output/
│  ├─ Generados: Cada ejecución pipeline
│  └─ Vigencia: "Actual" una vez ejecutado
│
├─ CAPA 3: Base de datos (OM registry)
│  ├─ SQLite: Caché indefinida (dev)
│  ├─ PostgreSQL: Caché indefinida (prod)
│  └─ [NO cacheable en Streamlit]
│
└─ CAPA 4: API Kawak (remoto)
   ├─ N/A para Fase 1 (procesa offline)
   ├─ Será usado en Fase 3 para real-time
   └─ TTL en Kawak: Diaria

JERARQUÍA DE FETCH:
┌─ ¿Existe en CAPA 1 (Streamlit cache)? → Usar
├─ ¿Cache expiró (>300s)? → ...
├─ ¿Existe en CAPA 2 (Archivos)? → Cargar +guardar cache
└─ ¿Pipeline aún no ejecutado? → Mostrar vacío o última ejecución
```

---

## Flujos de Datos

### Flujo 1: Ejecución del Pipeline (Batch Diario)

```
INICIO (Programado: 06:00 UTC)
  ↓
[cron o scheduler llama: python scripts/run_pipeline.py]
  ↓
PASO 1: consolidar_api.py
  ├─ Lee: data/raw/Kawak/*.xlsx (2022-2026)
  ├─ Lee: data/raw/API/*.xlsx (histórico)
  ├─ Limpia IDs (espacios, caracteres)
  ├─ Escribe: Consolidado_API_Kawak.xlsx
  └─ Duración: 45-60 seg
  ↓
PASO 2: actualizar_consolidado.py
  ├─ Lee: Consolidado_API_Kawak.xlsx (del Paso 1)
  ├─ Lee: config/settings.toml (umbrales, año cierre)
  ├─ Lee: catálogos (CMI, LMI, procesos)
  ├─ Transforma:
  │   ├─ Normaliza cumplimiento (% → decimal)
  │   ├─ Categoriza (Peligro/Alerta/Cumpl/Sobre)
  │   ├─ Calcula tendencias
  │   ├─ Genera recomendaciones
  │   └─ Deduplica por LLAVE
  ├─ Valida:
  │   ├─ Meta > 0
  │   ├─ Ejecución ≥ 0
  │   └─ Detecta N/A
  ├─ Escribe: Resultados Consolidados.xlsx
  │   ├─ Hoja "Consolidado Histórico"
  │   ├─ Hoja "Consolidado Semestral"
  │   └─ Hoja "Consolidado Cierres"
  └─ Duración: 2-5 min
  ↓
PASO 3: generar_reporte.py
  ├─ Lee: lmi_reporte.xlsx
  ├─ Lee: Consolidado_API_Kawak.xlsx (Paso 1)
  ├─ Mapea: Reportado / Pendiente / N/A
  ├─ Construye: Matriz ID × mes
  ├─ Escribe: Seguimiento_Reporte.xlsx
  │   ├─ Hoja "Tracking Mensual"
  │   ├─ Hoja "Seguimiento"
  │   ├─ Hoja "Resumen"
  │   └─ Hojas por periodo
  └─ Duración: 30-60 seg
  ↓
[run_pipeline.py] Validación
  ├─ ✓ Archivos existen
  ├─ ✓ Hojas esperadas presentes
  ├─ ✓ > 0 registros en cada
  └─ Genera: artifacts/pipeline_run_*.json + .log
  ↓
FIN ✓
NOTA: Próximo dashboard refresh:
  └─ En próximo st.cache_data expiry (300s)
  │  o manual st.cache_data.clear() + rerun
```

### Flujo 2: Carga del Dashboard (Usuario abre página)

```
Usuario abre streamlit_app/main.py
  ↓
st.set_page_config() + st.sidebar.radio() selecciona página
  ↓
[Usuario navega a: "📊 Resumen General"]
  ↓
Página: resumen_general.py ejecuta
  ├─ @st.cache_data(ttl=300)
  │   └─ cargar_consolidados()
  │       ├─ ¿Está en Streamlit cache? (Sí, menos de 5 min) → Usar
  │       ├─ (No, expiró o primera vez) → Leer Excel
  │       │   └─ pd.read_excel('data/output/Resultados Consolidados.xlsx')
  │       └─ Guardar en cache 5 minutos
  │
  ├─ Mostrar KPIs en top
  │   ├─ st.metric("Total indicadores", 1000)
  │   ├─ st.metric("En peligro", 50)
  │   ├─ st.metric("En alerta", 150)
  │   ├─ st.metric("Cumplimiento", 700)
  │   └─ st.metric("Sobrecumplimiento", 100)
  │
  ├─ TAB 1: Mostrar tabla Consolidado
  │   ├─ Aplicar filtros dinámicos (Año, Mes, Proceso, Categoria)
  │   ├─ Renderizar tabla con colores semáforo
  │   └─ [INTERACTIVE] Click en fila → open modal drill-down
  │
  ├─ TAB 2: Histórico con gráficos
  │   ├─ plot_tendencia_lineal() → Línea de cumplimiento en tiempo
  │   ├─ plot_scatter_riesgo() → Scatter % vs meta
  │   └─ plot_matriz_semaforo() → Heatmap período × estado
  │
  └─ TAB 3: Cierres anuales
      └─ Tabla año × cumplimiento anual
  ↓
FIN: Página renderizada

NOTA: Si usuario espera >5 min sin refresh:
  ├─ Cache expira (TTL=300s)
  ├─ Próximo tab click → releer Excel (transparente)
  └─ Mostrar datos más recientes
```

### Flujo 3: Creación de una Oportunidad de Mejora

```
Usuario en "✅ Plan Mejoramiento" hace click "+Nueva OM"
  ↓
Modal abre con inputs:
  ├─ ID Indicador (dropdown autocomplete)
  ├─ Descripción (textarea)
  ├─ Plazo (date picker)
  ├─ Responsable (text input)
  └─ Botón: "Crear OM"
  ↓
Usuario completa y hace click "Crear OM"
  ↓
plan_mejoramiento.py código ejecuta:
  ├─ Validar inputs (ID no vacío, descripción ≥ 10 caracteres)
  ├─ Generar número_om = f"OM-{año}-{contador}" (ej: "OM-2026-047")
  ├─ Llamar: db.crear_om(numero_om, id_indicador, descripción)
  │   └─ Esto ejecuta Upsert en BD:
  │       ├─ INSERT si no existe OM para (id, período, año, sede)
  │       └─ UPDATE si ya existe (reemplazar descripción)
  │
  ├─ st.success("OM creada") ✓
  └─ st.cache_data.clear()  # Invalida caché de tabla OM
     └─ Próximo render muestra OM nueva
  ↓
FIN: Tabla actualizada

PERSISTENCIA:
  ├─ DEV: registros_om.db (SQLite local)
  ├─ PROD: PostgreSQL en Render.com
  └─ Backup: Ambas fuentes en Supabase
```

---

## Problemas Identificados

### 1. ⚠️ Inconsistencia de Caché (Prioridad: ALTO)

**Problema:**
```
Hoy:
  - resumen_general.py: TTL=600s
  - cmi_estrategico.py: TTL=300s
  - Resultado: Datos desincronizados 5-10 min post-pipeline
```

**Impacto:** Usuarios ven datos contradictorios (resumen dice 50 en peligro, detalle dice 30)

**Solución (Fase 1, Semana 1):**
```python
# core/config.py
CACHE_TTL = 300  # Estándar global

# Todas las páginas
@st.cache_data(ttl=CACHE_TTL)
def cargar_consolidados():
    ...
```

**Esfuerzo:** 2-4 horas (encontrar/reemplazar todos @st.cache_data)

---

### 2. 🔴 Duplicación de Código (Prioridad: MEDIO)

**Problema:**
```python
# resumen_general.py (1900 líneas)
def _is_null(valor):
    return pd.isna(valor) or valor == ""

# plan_mejoramiento.py
def _is_null(valor):
    return pd.isna(valor) or valor == ""

# cmi_estrategico.py
def _is_null(valor):
    return pd.isna(valor) or valor == ""

# ... 2-3 páginas más
```

**Impacto:** Mantenimiento difícil (bug en una função = buscar/fijar en 5 archivos)

**Solución (Fase 1 o 2):**
```
$ mkdir -p streamlit_app/utils/
$ cat > streamlit_app/utils/formatting.py << 'EOF'
def is_null(valor):
    """Verificar si valor es nulo o vacío."""
    return pd.isna(valor) or valor == ""

def to_num(valor, default=0):
    """Convertir a número o retornar default."""
    try:
        return float(valor)
    except:
        return default

# ... más funciones
EOF

# Luego en cada página:
from streamlit_app.utils.formatting import is_null, to_num
```

**Funciones duplicadas (6 total):**
- `_is_null()`
- `_to_num()`
- `_nivel()` (categoría → color)
- `_limpiar()` (normalizar strings)
- `_id_limpio()` (extraer ID de texto)
- `_fmt_num()` (formatear número)
- `_fmt_valor()` (formatear valor con unidad)

**Esfuerzo:** 4-6 horas

---

### 3. 🔴 Mappings Hardcoded (Prioridad: BAJO)

**Problema:**
```python
# services/data_loader.py (900 líneas!)
_MAPA_PROCESO_PADRE = {
    "Dirección Estratégica": "DIRECCIONAMIENTO ESTRATÉGICO",
    "Gestión de Proyectos": "DIRECCIONAMIENTO ESTRATÉGICO",
    "Auditoría Interna": "DIRECCIONAMIENTO ESTRATÉGICO",
    # ... 50+ entradas más
    "Admisiones": "PROCESOS MISIONALES",
    "Pregrado": "PROCESOS MISIONALES",
    # ...
}
```

**Impacto:**
- No-devs no pueden actualizar mapeos
- Difícil mantener (buscar en 900 líneas)
- Cambios requieren merge+deploy

**Solución (Fase 2-3):**
```yaml
# config/mappings.yaml
procesos:
  "Dirección Estratégica": "DIRECCIONAMIENTO ESTRATÉGICO"
  "Gestión de Proyectos": "DIRECCIONAMIENTO ESTRATÉGICO"
  "Auditoría Interna": "DIRECCIONAMIENTO ESTRATÉGICO"
  # ... 50+ más
```

```python
# Cargar con caché
@st.cache_data
def cargar_mapeos():
    import yaml
    with open('config/mappings.yaml') as f:
        return yaml.safe_load(f)
```

**Esfuerzo:** 6-8 horas

---

### 4. ✅ Wrappers Eliminados (Actualización)

**Estado actual:**
```python
# `gestion_om.py` y `seguimiento_reportes.py` contienen lógica activa.
# `_page_wrapper.py` fue retirado del repositorio.
# `pages_disabled/` fue eliminado.
```

**Impacto del cierre:**
- 2 páginas críticas quedaron operativas sin delegación
- eliminación de dependencia a código deprecated
- reducción de deuda técnica y rutas muertas

**Resultado aplicado (Fase 1):**
- `gestion_om.py` activo y cubierto por pruebas
- `seguimiento_reportes.py` activo y cubierto por pruebas
- limpieza de `pages_disabled/` y archivos puente

**Validación:** suite completa en verde (100 tests)

---

### 5. 🟡 Pipeline Secuencial (Prioridad: BAJO)

**Problema:**
```
Paso 1: consolidar_api.py (45-60 seg) ✓ Independiente
Paso 2: actualizar_consolidado.py (120-300 seg) ← Requiere Paso 1
Paso 3: generar_reporte.py (30-60 seg) ✓ Independiente de Paso 2

HITO ACTUAL: Paso 1 → Paso 2 → Paso 3 (SERIAL)
OPTIMIZACIÓN: Ejecutar Paso 1 & Paso 3 EN PARALELO mientras Paso 2 corre
```

**Impacto:** 
```
Hoy: 1min (P1) + 3min (P2) + 1min (P3) = 5 minutos total
Optimizado: max(1min, 1min) + 3min = 4 minutos total
Mejora: 20% menos tiempo
```

**Solución (Fase 2):**
```python
# scripts/run_pipeline.py
import concurrent.futures

def run_pipeline_optimized():
    # Paso 1 & 3 en paralelo
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        p1_future = executor.submit(consolidar_api.main)
        
        # Esperar Paso 1 para iniciar Paso 2
        p1_result = p1_future.result()
        
        # Paso 3 en paralelo con Paso 2
        p2_future = executor.submit(actualizar_consolidado.main)
        p3_future = executor.submit(generar_reporte.main)
        
        p2_result = p2_future.result()
        p3_result = p3_future.result()
    
    return aggregate_results([p1_result, p2_result, p3_result])
```

**Esfuerzo:** 3-4 horas

---

### 6. 🟡 Falta de Session State Namespacing (Prioridad: BAJO)

**Problema:**
```python
# Hoy
st.session_state['rc_clear_global'] = False  # ← Sin namespacing
st.session_state['cmi_pdi_objetivo'] = "FINANCIERO"

# Riesgo: Colisión si dos páginas usan mismo nombre
# ¿Cuál es el origen de 'rc_clear_global'? 
# → Gripa en resumen_general.py
```

**Solución (Fase 1):**
```python
# core/session_keys.py
def get_key(page: str, feature: str) -> str:
    """Generar namespace único para session state."""
    return f"{page.upper()}_{feature.lower()}"

# Uso:
RG_CLEAR_GLOBAL = get_key("resumen_general", "clear_global")
CMI_PDI_OBJETIVO = get_key("cmi_estrategico", "pdi_objetivo")

# En código:
st.session_state[RG_CLEAR_GLOBAL] = False
```

**Esfuerzo:** 2-3 horas

---

## Hoja de Ruta Técnica

### Fase 1: Estabilidad (Semanas 1-4)

| ID | Tarea | Prioridad | Esfuerzo | Bloqueos |
|----|-------|-----------|----------|----------|
| 1.1 | Estandarizar caché (TTL=300s) | 🔴 ALTO | 4h | Ninguno |
| 1.2 | Extraer funciones duplicadas a utils/ | 🟠 MEDIO | 5h | Ninguno |
| 1.3 | Refactorizar gestion_om.py | 🟠 MEDIO | 8h | Ninguno |
| 1.4 | Refactorizar seguimiento_reportes.py | 🟠 MEDIO | 8h | Ninguno |
| 1.5 | Implementar session key namespacing | 🟡 BAJO | 3h | Ninguno |
| 1.6 | Agregar tests para nuevas utilidades | 🟡 BAJO | 4h | 1.2 |
| **TOTAL FASE 1** | | | **32h** | |

### Fase 2: Optimización (Semanas 5-8)

| ID | Tarea | Prioridad | Esfuerzo | Bloqueos |
|----|-------|-----------|----------|----------|
| 2.1 | Paralelizar pipeline (Paso 1 & 3) | 🟡 BAJO | 4h | Ninguno |
| 2.2 | Eliminar deprecated/ (cleanup) | 🟡 BAJO | 3h | 1.3, 1.4 |
| 2.3 | Implementar CI/CD (GitHub Actions) | 🟡 BAJO | 6h | Ninguno |
| 2.4 | Agregar Tests de integración | 🟡 BAJO | 5h | Ninguno |
| **TOTAL FASE 2** | | | **18h** | |

### Fase 3: Expansión (Semanas 9-12)

| ID | Tarea | Prioridad | Esfuerzo | Bloqueos |
|----|-------|-----------|----------|----------|
| 3.1 | Extraer mapeos a YAML config | 🟡 BAJO | 7h | Ninguno |
| 3.2 | Implementar motor de reglas v2 | 🟡 BAJO | 16h | Ninguno |
| 3.3 | API REST (exposición de datos) | 🟡 BAJO | 12h | Ninguno |
| 3.4 | Dashboards PowerApps embed | 🟡 BAJO | 10h | Ninguno |
| 3.5 | Anomaly detection (modelos) | 🟡 BAJO | 15h | Ninguno |
| **TOTAL FASE 3** | | | **60h** | |

**TOTAL ROADMAP:** ~110 horas de desarrollo

---

**Fecha:** 11 de abril de 2026  
**Revisión siguiente:** 15 de mayo de 2026  
**Contacto:** Equipo de BI Institucional
