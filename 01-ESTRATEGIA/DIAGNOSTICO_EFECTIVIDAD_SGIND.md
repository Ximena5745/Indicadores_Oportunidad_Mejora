# 📊 Diagnóstico de Efectividad SGIND
## Baseline de Métricas Actuales (Fase 2, Semana 2)

**Documento:** DIAGNOSTICO_EFECTIVIDAD_SGIND.md  
**Versión:** 1.0  
**Fecha:** 14 de abril de 2026  
**Horizonte:** Fase 2 (Semana 2/8) — Captura estado actual para medir progreso  
**Audiencia:** Coordinadores Fase 2, gestores de cambio, stakeholders de impacto

**Contexto Estratégico:** Parte de [📋 PLAN_INTEGRAL_MEJORA_SGIND.md](PLAN_INTEGRAL_MEJORA_SGIND.md) ← **CAPA 3: Medición**  
**Ejecución:** Semanas 3-8 Fase 2 (Ver Pilar E + roadmap detallado en Plan Integral)

---

## 📋 TABLA DE CONTENIDOS

1. [Resumen Ejecutivo](#resumen-ejecutivo)
2. [Métricas Capturadas Actualmente](#métricas-capturadas-actualmente)
3. [Baseline: Estado Actual (04-14-2026)](#baseline-estado-actual)
4. [Brechas de Medición Identificadas](#brechas-de-medición-identificadas)
5. [Instrumentación Recomendada](#instrumentación-recomendada)
6. [Plan de Validación de Supuestos](#plan-de-validación-de-supuestos)
7. [Auditoría & Calidad de Datos](#auditoría--calidad-de-datos)
8. [Roadmap de Implementación](#roadmap-de-implementación)

---

## 🎯 FUNCIONALIDAD NUEVA: Filtro Proceso Global

**Ubicación:** Dashboard → Resumen por Procesos → Filtro "Proceso"

**Comportamiento Actualizado (15-04-2026):**
- Filtro de **Proceso** ahora aplica **globalmente a TODAS las 8 pestañas**
- Datos consistentes: mismo proceso seleccionado = datos filtrados en:
  - 📋 Resumen General (KPIs, gráficos)
  - ℹ️ Información por Proceso (tabla base)
  - 📊 Indicadores (histórico)
  - 📋 Resumen (estadísticas)
  - ✅ Calidad de Datos (matriz 5 criterios)
  - 🔍 Auditoría (hallazgos por proceso)
  - 💡 Indicadores Propuestos (nuevos indicadores proceso)
  - 🤖 Análisis IA (recomendaciones contextuales)

**Flujo Técnico:**
```
Seleccionar: Tipo Proceso → Unidad → Proceso → Subproceso
       ↓
proc_df se filtra POR UNA SOLA VEZ
       ↓
8 tabs usan proc_df (datos filtrados)
       ↓
RESULTADO: Consistencia de datos en TODAS pestañas
```

---

## RESUMEN EJECUTIVO

### Situación Actual
SGIND completó Fase 1 (11-04-2026) con **sólida base técnica** pero **escaso monitoreo de efectividad real**.

**Lo que sabemos hoy:**
- ✅ Sistema funcional: 7 pages activas, 1,000+ indicadores consolidados
- ✅ Datos válidos: 0 problemas en data contracts validación
- ✅ Código testeable: 50+ unit tests, ~40% cobertura
- ❓ **DESCONOCIDO:** Cuántos usuarios activos reales, qué decisiones han tomado basadas en SGIND, cuántas OMs se han cerrado

**El riesgo:**
Sin medición clara de efectividad, no sabremos si Fase 2 (optimizaciones) genera realmente impacto o solo consumas recursos.

### Objetivo del Diagnóstico
Establecer **baseline de 3 métricas críticas** y diseñar su captura continua:
1. 👥 **Adopción de usuarios** (# activos, roles, frecuencia)
2. ⚡ **Velocidad de decisión** (tiempo creación OM → acción)
3. ✅ **Tasa de cierre de OMs** (% cerradas, tiempo promedio, por proceso)

---

## MÉTRICAS CAPTURADAS ACTUALMENTE

### A. Datos Disponibles HOY en el Sistema

#### 1️⃣ Registro de OM (Parcial ✅)
**Fuente:** `data/db/registros_om.db` (SQLite) + `data/raw/OM.xlsx`

**Campos capturados:**
```sql
registros_om TABLE:
├── id_indicador          (TEXT)      — Identificador único
├── nombre_indicador      (TEXT)      — Nombre legible
├── proceso               (TEXT)      — Proceso responsable
├── periodo               (TEXT)      — Trimestre/mes/año
├── anio                  (INTEGER)   — 2022-2026
├── sede                  (TEXT)      — Sede o centro
├── tiene_om              (INTEGER)   — Flag: 0/1
├── numero_om             (TEXT)      — ID de la OM abierta
├── comentario            (TEXT)      — Observaciones registrador
├── registrado_por        (TEXT)      — USUARIO que registró
├── fecha_registro        (TEXT)      — TIMESTAMP registro
└── UNIQUE(id_indicador, periodo, anio, sede)
```

**Lo que permite medir:**
- Cuántas OMs se han abierto (tiene_om=1)
- Por cuál indicador, proceso, período
- Quién las registró + cuándo
- Comentarios de motivo

**Lo que NO permite medir:**
- ❌ Estado actual (abierta, cerrada, en progreso)
- ❌ Fecha de cierre (solo fecha registro)
- ❌ Tiempo ciclo (creación → cierre)
- ❌ Responsable de cierre
- ❌ Motivo de cierre (aceptada, rechazada, en progreso)

#### 2️⃣ Archivo OM.xlsx (Parcial ✅)
**Fuente:** `data/raw/OM.xlsx` (header=row 8)

**Campos observados (esperados):**
- Id, Descripción, Fecha de identificación, Fecha de creación
- Fecha estimada de cierre, Fecha real de cierre
- Avance (%)
- Responsable, Proceso, Área

**Estado:** ⚠️ Estructura presente pero **desactualizada o subutilizada**
- No integrada en pipeline ETL (solo lectura manual)
- No sincronizada con registros_om.db
- Cierre real NO se registra automáticamente en registros_om

#### 3️⃣ Usuarios / Acceso (Inexistente ❌)
**Fuente:** NINGUNA

**Lo que necesitaríamos:**
- Logs de acceso a Streamlit (quién, cuándo, qué página)
- Duración de sesión
- Acciones tomadas (filtros aplicados, descarga de reportes)
- Cambios en OM (quién cerró, cuándo)

**Estado actual:** No hay auditoría implementada | Planeado para Fase 2

#### 4️⃣ Decisiones Tomadas (Inexistente ❌)
**Fuente:** NINGUNA

**Lo que necesitaríamos:**
- Acciones ejecutadas tras ver un indicador en Peligro/Alerta
- Link indicador → OM → acción ejecutiva
- Timestamp decisión

**Estado actual:** No hay registro | Imposible medir decisión velocity hoy

---

## BASELINE: ESTADO ACTUAL

### 📈 Captura Manual (14-04-2026)

Basándose en análisis de datos disponibles en `data/db/registros_om.db` y `data/raw/`:

#### **1. Adopción de Usuarios**

```
┌─────────────────────────────────────┐
│ MÉTRICA: Usuarios Únicos Registrados│
├─────────────────────────────────────┤
│ Período: 2022-2026 (histórico)      │
│ Fuente: registros_om.registrado_por │
└─────────────────────────────────────┘

BASELINE (según registros_om.db):
├── Usuarios únicos que registraron OM: ???  ← REQUIERE CONSULTA MANUAL
│   • Query: SELECT COUNT(DISTINCT registrado_por) FROM registros_om
│   • SI <5 → Adopción CRÍTICA (muy concentrada)
│   • SI 5-15 → Adopción MEDIA (distribución inicial)
│   • SI >15 → Adopción BUENA (dispersión de uso)
│
├── Registros por usuario:
│   • Query: SELECT registrado_por, COUNT(*) FROM registros_om GROUP BY registrado_por
│   • Distribución: ¿Equitativa o concentrada en 1-2 users?
│
└── Sesiones activas ÚLTIMAS 30 DÍAS: 0 ← NO CAPTURADO
    • Razón: Sin logs de Streamlit activados
    • Impacto: No sabemos si 20 personas usaron SGIND o 2
```

**⚠️ HALLAZGO:** Podemos contar OMs registradas pero **NO podemos medir sesiones activas reales**.

---

#### **2. Velocidad de Decisión (Decision Velocity)**

```
┌──────────────────────────────────────────┐
│ MÉTRICA: Tiempo OM Creación → Acción    │
├──────────────────────────────────────────┤
│ Unidad: Días                             │
│ Período: Últimos 180 días                │
└──────────────────────────────────────────┘

BASELINE (Limitado por datos):
├── Tiempo promedio creación OM → Registro en SGIND:
│   • Teórico: <1 día (registro en dia creación)
│   • Actual: DESCONOCIDO (sin timestamp acción ejecutada)
│
├── Tiempo promedio creación OM → Decisión/acción ejecutiva:
│   • Teórico objetivo: <5 días (Fase 2 meta)
│   • Actual: NO MEDIBLE (sin evento "decisión tomada")
│   • Razón: No hay tracking de cambios, solo registro inicial
│
└── Ejemplos de ciclos parciales:
    • OM registrada 2026-04-10
    • ¿Cuándo se cerró? DESCONOCIDO
    • ¿Quién la cerró? DESCONOCIDO
    • ¿Ejecutada recomendación? DESCONOCIDO
```

**⚠️ HALLAZGO:** Tenemos fecha de registro pero **no hay trazabilidad de cierre/acción real**.

---

#### **3. Tasa de Cierre de OMs (OM Closure Rate)**

```
┌──────────────────────────────────────┐
│ MÉTRICA: % OMs Cerradas por Status   │
├──────────────────────────────────────┤
│ Período: Enero 2026 - Abril 2026    │
│ Cohorte: OMs con fecha_registro      │
└──────────────────────────────────────┘

BASELINE (desde registros_om.db):
├── Total OMs registradas 2026: ???
│   • Query: SELECT COUNT(*) FROM registros_om WHERE tiene_om=1 AND anio=2026
│
├── OMs CERRADAS: ???
│   • Query: (No hay campo status/fecha_cierre en registros_om.db)
│   • Alternativa: Revisar OM.xlsx manualmente
│   • Hallazgo: Brecha de sincronización entre DB y Excel
│
├── Tasa de cierre estimada:
│   • SI recurrir a OM.xlsx:
│     - OMs Cerradas: ? (sin fecha real de cierre actualizada)
│     - OMs Abiertas: ? (sin status actual)
│     - % Cerradas: ??? (DESCONOCIDA)
│
│   • Objetivo Fase 2: >70% de OMs cerradas en <30 días
│   • Actual: NO MEDIBLE (datos inconsistentes)
│
└── Por Proceso (sub-métrica):
    • Procesos High-Closure (>80%):        DESCONOCIDOS
    • Procesos Low-Closure (<50%):         DESCONOCIDOS
    • Bottleneck principal:                DESCONOCIDO
```

**⚠️ HALLAZGO:** Brecha entre registros_om.db (registro inicial) y OM.xlsx (completitud). **Sin versión única de verdad**.

---

## BRECHAS DE MEDICIÓN IDENTIFICADAS

### 🔴 CRÍTICAS (Bloquean medición de Theory of Change)

#### Gap 1: Falta de Audit Trail / Event Sourcing
**Impacto:** No podemos medir velocidad de decisión ni trazabilidad

| Evento Requerido | Estado Actual | Necesario para |
|--|--|--|
| Usuario abre sesión | ❌ No capturado | Adopción |
| Usuario visualiza indicador en Peligro | ❌ No capturado | Engagement |
| Usuario crea OM | ⚠️ Solo registro inicial | Decision velocity |
| Usuario cierra OM | ❌ No capturado | Closure rate |
| Usuario ejecuta acción (cambio de datos) | ❌ No capturado | Impact validation |

**Localización pendiente:** `scripts/audit.py` (diseño incluido en Fase 2, no implementado aún)

---

#### Gap 2: Inconsistencia Base de Datos (Fuente Única de Verdad)
**Impacto:** Métricas contradictorias según qué tabla se consulte

**Arquitectura actual:**
```
OM.xlsx (manual, desactualizado?)
   ↓
data/raw/OM.xlsx ←────→ (NO sincronizado)
                         ↓
                    registros_om.db (SQLite)
                    
Problema: Dos sistemas paralelos, sin reconciliación
```

**Solución recomendada:** Unificar en registros_om.db con estados transicionales

---

#### Gap 3: Falta de Captura de Usuario Activo
**Impacto:** No sabemos si 1 o 100 personas usan SGIND

**Datos desaparecidos:**
- Logs de sesión Streamlit
- Quién ejecutó qué acción
- Duración de sesión
- Dispositivo/ubicación

**Sin esto:** Imposible medir adopción real vs. uso de "uno o dos gerentes"

---

### 🟡 IMPORTANTES (Limitan profundidad de análisis)

#### Gap 4: Sin responsabilidad explícita de cierre
**Impacto:** ¿Quién cierra la OM? ¿Quién es responsable del cumplimiento?

**Campo faltante en registros_om:**
```sql
-- Extensión recomendada:
ALTER TABLE registros_om ADD COLUMN (
    responsable_cierre TEXT,
    fecha_cierre TEXT,
    estado_om TEXT DEFAULT 'Abierta',  -- Abierta|En Progreso|Cerrada|Rechazada
    motivo_cierre TEXT,
    puntaje_avance NUMERIC
);
```

---

#### Gap 5: Sin correlación indicador → impacto
**Impacto:** No sabemos si el cambio generó resultado

**Lógica requerida:**
```
Indicador A en Peligro (meta vs. ejecución)
    ↓
OM creada (acciones corrige)
    ↓
¿Indicador A mejoró? (post-acción)
    ↓
¿Acción fue efectiva? (SÍ/NO)
```

**Captura actual:** Solo paso 1-2. Sin paso 3-4.

---

## INSTRUMENTACIÓN RECOMENDADA

### 🚀 NIVEL 1: Implementar Inmediato (Semana 3, Fase 2)

#### 1.1 Audit Table en registros_om.db

```python
# scripts/audit.py — CREAR S3 (Semana 3)

CREATE TABLE audit_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario TEXT NOT NULL,
    evento TEXT,  -- 'LOGIN', 'VIEW:indicador', 'CREATE_OM', 'CLOSE_OM', 'EXPORT'
    indicador_id TEXT,
    om_id TEXT,
    timestamp TEXT,
    detalles TEXT  -- JSON con contexto
);

# Ejemplo log:
evento = {
    'usuario': 'garcia@politecnico.edu',
    'evento': 'CREATE_OM',
    'indicador_id': 'IND-2025-001',
    'timestamp': '2026-04-14T14:32:00Z',
    'detalles': json.dumps({
        'proceso': 'Académico',
        'meta': 95,
        'ejecucion': 47,
        'razon': 'Brecha crítica'
    })
}
```

**Esfuerzo:** 8h (diseño + instrumentación mínima)  
**Beneficio:** Clave para Decision Velocity

---

#### 1.2 Estado Transicional en OM

```python
# Extender registros_om table

-- NUEVA ESTRUCTURA (compatible hacia atrás):
ALTER TABLE registros_om ADD COLUMN (
    estado TEXT DEFAULT 'Abierta',  -- Abierta | En Progreso | Cerrada | Rechazada
    responsable_cierre TEXT,
    fecha_cierre TEXT,
    puntaje_avance NUMERIC,
    motivo_cierre TEXT
);

-- VIEWS para compatibilidad:
CREATE VIEW om_abiertas AS
    SELECT * FROM registros_om WHERE estado = 'Abierta';

CREATE VIEW om_cerradas_en_plazo AS
    SELECT * FROM registros_om 
    WHERE estado='Cerrada' 
    AND (julianday(fecha_cierre) - julianday(fecha_registro)) <= 30;
```

**Esfuerzo:** 3h  
**Beneficio:** Closure Rate medible

---

#### 1.3 Session Logger en Streamlit

```python
# streamlit_app/services/session_logger.py — CREAR S3

import streamlit as st
from core.db_manager import registrar_evento

def log_session_init():
    """Llamar al inicio de main.py."""
    if 'session_id' not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.session_start = datetime.now()
        registrar_evento(
            usuario=st.session_state.get('user', 'unknown'),
            evento='LOGIN',
            timestamp=datetime.now(),
            detalles={'navegador': st.session_state.session_id}
        )

def log_page_view(page_name: str):
    """Registrar cada página visitada."""
    registrar_evento(
        usuario=st.session_state.get('user', 'unknown'),
        evento=f'VIEW:{page_name}',
        timestamp=datetime.now()
    )

def log_action(evento: str, indicador_id: str = None, detalles: dict = None):
    """Genérico para cualquier acción usuario."""
    registrar_evento(evento, indicador_id, detalles)
```

**Esfuerzo:** 4h  
**Beneficio:** Adoption metrics (# users, session frequency)

---

### 📊 NIVEL 2: Implementar en S4-5 (Fase 2)

#### 2.1 KPI Dashboard

```python
# streamlit_app/pages/diagnostico_efectividad.py — CREAR S4

import streamlit as st
import pandas as pd
from core.db_manager import ejecutar_query

def render():
    st.title("📊 Dashboard Diagnóstico de Efectividad")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        users_30d = ejecutar_query("""
            SELECT COUNT(DISTINCT usuario) FROM audit_events 
            WHERE julianday(timestamp) >= julianday('now', '-30 days')
        """)
        st.metric("👥 Usuarios Activos 30d", users_30d[0][0] or 0)
    
    with col2:
        om_abierta = ejecutar_query(
            "SELECT COUNT(*) FROM registros_om WHERE estado='Abierta'"
        )
        st.metric("📋 OMs Abiertas", om_abierta[0][0] or 0)
    
    with col3:
        closure_rate = ejecutar_query("""
            SELECT ROUND(100.0 * COUNT(CASE WHEN estado='Cerrada' THEN 1 END) 
                         / NULLIF(COUNT(*), 0), 1)
            FROM registros_om WHERE anio=2026
        """)
        st.metric("✅ Tasa Cierre 2026", f"{closure_rate[0][0] or 0}%")
    
    # Gráficos de tendencia
    st.subheader("Tendencias")
    ...
```

**Esfuerzo:** 6h  
**Beneficio:** Visualización en tiempo real para stakeholders

---

#### 2.2 Mapeo Indicador → Impacto

```python
# core/calculos.py — NUEVA FUNCIÓN

def calcular_impacto_om(om_id: str, indicador_id: str, 
                        fecha_cierre: str) -> dict:
    """
    Mide si una OM generó cambio en indicador.
    
    Retorna:
      {
        'om_id': str,
        'indicador_id': str,
        'cumplimiento_antes': float,  # En fecha creación OM
        'cumplimiento_despues': float,  # En fecha cierre
        'delta': float,  # Diferencia absoluta
        'impacto': str,  # 'Positivo'|'Negativo'|'Neutral'
        'p_valor': float  # Significancia estadística
      }
    """
    # Lógica: Comparar valor indicador pre-post
    ...
```

**Esfuerzo:** 8h  
**Beneficio:** Valida hipótesis "acción → resultado"

---

### 🎯 NIVEL 3: Implementar en S6-8 (Fase 3)

- Segmentación de usuarios por rol (Rector, Líder, Especialista)
- Cohort analysis (cohorte usuarios Fase 1 vs. Fase 2)
- Causal inference (Did OM closing CAUSE adoption increase?)
- Predictive models (forecast OM closure rate)

---

## PLAN DE VALIDACIÓN DE SUPUESTOS

### Supuesto #1: "<15 usuarios activos es suficiente"

**Validar con:**
```
Test: Cargar audit_events tras 2 semanas Fase 2
├── SI <5 usuarios únicos → Riesgo CRÍTICO
│   • Deploy stalled, concentration risk
│   • Acción: Campaña de adopción dirigida
│
├── SI 5-15 usuarios → OK, continuar
│
└── SI >15 usuarios → Exceede expectativa, revisar Redis
    • Posible: Actualizar a Redis Cloud en S6
    • Cost: ~$30/mes → acceptable si >25 users
```

**Responsable:** Product Manager  
**Target:** Fin Semana 4 Fase 2 (28-04-2026)

---

### Supuesto #2: "Decision Velocity mejorará a <5 días tras optimizaciones"

**Validar con:**
```
Métrica: HISTOGRAM de (fecha_cierre - fecha_creacion) para OMs cerradas

Baseline (semana 3): Recopilar 20-30 OMs históricas
├── Mediana actual: ?? días
├── P90: ?? días
├── % < 5 días: ?? %

Post-Fase 2 (semana 8): Recopilar 20-30 OMs nuevas
├── Mediana objetivo: <5 días
├── P90 objetivo: <10 días
├── % < 5 días objetivo: >70%

Análisis: Comparar distribuciones (Mann-Whitney U test)
```

**Responsable:** PMO / Data Analyst  
**Target:** Fin Semana 8 Fase 2 (25-05-2026)

---

### Supuesto #3: "OM Closure Rate subirá de X% a >70%"

**Validar con:**
```
Métrica: Tasa de cierre por proceso + responsable

Baseline (semana 3):
├── Procesos High-Performers: ??%
├── Procesos Low-Performers: ??%
└── Responsables con mayor closure: ??

Post-Fase 2 (semana 8):
├── Todos procesos: >70%?
├── Si NO: ¿Qué proceso es blocker?
└── Acción: Investigar + mitigar

Análisis: Stratified comparison (por proceso)
```

**Responsable:** Líder Procesos / PMO  
**Target:** Fin Semana 8 Fase 2

---

## ROADMAP DE IMPLEMENTACIÓN

### 📅 Cronograma Captura de Datos

```
SEMANA 3 (17-21 abril)
├─ 🟢 Implementar audit_events table (8h)
├─ 🟢 Extender registros_om con estado/cierre (3h)
├─ 🟢 Integrar session logger en main.py (4h)
└─ 📊 RESULTADO: Empezar a capturar eventos en vivo

SEMANA 4 (24-28 abril)
├─ 🟢 Recopilar baseline de 20-30 OMs históricas
├─ 📊 ANÁLISIS: Decision Velocity actual (mediana, P90)
├─ 📊 ANÁLISIS: Closure Rate actual por proceso
└─ 📢 COMUNICAR: Hallazgos a stakeholders

SEMANA 5 (30 mayo - 1-2 mayo)
├─ 🟢 Crear diagnostico_efectividad.py page (6h)
├─ 📊 DASHBOARD: Métrica en vivo (# users 30d, OM abiertas, closure rate)
└─ 🎯 Meta: Visibilidad continua para PMO

SEMANA 6-8 (5-25 mayo)  [Ejecución de optimizaciones Fase 2]
├─ 📊 MONITOREO: Captura continua de eventos
├─ 📊 ANÁLISIS SEMANAL: Decision Velocity pre vs. post opt
├─ 📊 ANÁLISIS SEMANAL: Adoption (# active users, session freq)
└─ 📊 VALIDACIÓN: Supuestos vs. Data

CIERRE FASE 2 (25 mayo)
├─ 📊 REPORT: Baseline vs. Target (Theory of Change)
├─ ✅/❌ Validar hipótesis críticas
└─ 📢 Comunicar impacto a directivos
```

---

## APÉNDICE: QUERIES OPERACIONALES

### 1. Cuántos usuarios únicos han registrado OMs

```sql
SELECT 
    registrado_por,
    COUNT(*) as num_registros,
    MIN(fecha_registro) as primera_actividad,
    MAX(fecha_registro) as ultima_actividad
FROM registros_om
WHERE registrado_por IS NOT NULL AND registrado_por != ''
GROUP BY registrado_por
ORDER BY num_registros DESC;
```

### 2. OMs abiertas hace >30 días (sin cierre aún)

```sql
SELECT 
    id_indicador,
    nombre_indicador,
    proceso,
    fecha_registro,
    registrado_por,
    CAST((julianday('now') - julianday(fecha_registro)) AS INT) as dias_abierta
FROM registros_om
WHERE tiene_om=1 
  AND estado IS NULL  -- No cerrada aún
  AND (julianday('now') - julianday(fecha_registro)) > 30
ORDER BY dias_abierta DESC;
```

### 3. Tasa de cierre por proceso

```sql
WITH om_por_proceso AS (
    SELECT 
        proceso,
        COUNT(*) as total_om,
        COUNT(CASE WHEN estado='Cerrada' THEN 1 END) as cerradas,
        COUNT(CASE WHEN estado='Abierta' THEN 1 END) as abiertas,
        COUNT(CASE WHEN estado='En Progreso' THEN 1 END) as en_progreso
    FROM registros_om
    WHERE anio=2026 AND tiene_om=1
    GROUP BY proceso
)
SELECT 
    proceso,
    total_om,
    cerradas,
    ROUND(100.0 * cerradas / NULLIF(total_om, 0), 1) as pct_cerrada,
    abiertas,
    en_progreso
FROM om_por_proceso
ORDER BY pct_cerrada DESC;
```

### 4. Sesiones por usuario (últimos 30 días)

```sql
SELECT 
    usuario,
    COUNT(DISTINCT DATE(timestamp)) as dias_activo,
    COUNT(*) as num_eventos,
    MIN(timestamp) as primer_evento,
    MAX(timestamp) as ultimo_evento
FROM audit_events
WHERE julianday(timestamp) >= julianday('now', '-30 days')
  AND evento IN ('LOGIN', 'VIEW:resumen_general', 'CREATE_OM')
GROUP BY usuario
ORDER BY dias_activo DESC;
```

---

## 🎯 NEXT STEPS

**Para el Product Manager:**
1. ✅ Revisar este diagnóstico en Semana 3
2. ✅ Aprueba Nivel 1 de instrumentación (audit_events, estado OM, session logger)
3. ✅ Asigna 16 horas técnicas (Sem 3) al equipo
4. 📢 Comunica a stakeholders: "Mediremos adopción/impacto real desde S3"

**Para el Equipo Técnico:**
1. ✅ S3: Implementar audit.py + extender registros_om
2. ✅ S3: Integrar session_logger en main.py
3. ✅ S4: Recopilar baseline de 30 OMs históricas
4. 📊 S5: Desplegar diagnostico_efectividad.py page

**Para Stakeholders:**
- De "suponemos <15 usuarios" → "Sabemos exactamente cuántos"
- De "esperamos mejore decision velocity" → "Mediremos delta pre/post"
- De "asumimos OM closure>" → "Dashboard en vivo con tasa real"

---

**Indicador de Éxito Diagnóstico (Fin Fase 2):**

| Métrica | Baseline (Hoy) | Target (Fin S8) | Responsable |
|--|--|--|--|
| Usuarios Activos 30d | DESCONOCIDO ← Medir S3 | >70% adopción rol target | PMO |
| Decision Velocity (mediana) | DESCONOCIDO ← Medir S3 | <5 días | Product |
| OM Closure Rate | DESCONOCIDO ← Medir S3 | >70% | Procesos |
| Eventos auditados | 0 | <10k eventos/semana | Tech |

---

**Versión:** 1.0 — 14 de abril de 2026  
**Próxima revisión:** 21 de abril de 2026 (Fin Semana 2, Fase 2)
