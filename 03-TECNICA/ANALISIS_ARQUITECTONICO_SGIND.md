# 📋 ANÁLISIS ARQUITECTÓNICO INTEGRAL
## Sistema de Indicadores Poli (SGIND)

**Fecha de análisis:** 10 de abril de 2026  
**Scope:** Análisis de código base completo + mapeo funcional exhaustivo  
**Analista:** Software Architect + Senior Engineer + Especialista en Sistemas de Indicadores

> Nota de vigencia: este documento representa el diagnóstico previo al cierre técnico de Fase 1.
> El estado operativo actual ya incluye eliminación de wrappers, retiro de `pages_disabled/` y validación de regresión en verde.

---

## TABLA DE CONTENIDOS
1. [Entendimiento del Sistema](#entendimiento-del-sistema)
2. [Matriz Funcional Detallada](#matriz-funcional-detallada)
3. [Identificación de Problemas](#identificación-de-problemas)
4. [Resumen Ejecutivo](#resumen-ejecutivo)

---

# 1. ENTENDIMIENTO DEL SISTEMA

## 1.1 Propósito Real del Sistema

**Dashboard de desempeño institucional integrado** para Politécnico Grancolombiano que:

- **Centraliza** seguimiento de indicadores estratégicos, operativos y académicos
- **Monitorea** cumplimiento vs. metas con semaforización automática
- **Gestiona** oportunidades de mejora (OM) vinculadas a indicadores en riesgo
- **Consolida** datos de múltiples fuentes (Excel manual → PostgreSQL/SQLite)
- **Genera** reportes ejecutivos por proceso y objetivo estratégico

**No es:** Solo un tablero. Es un **sistema de gobernanza** que conecta métricas con planes de mejora.

---

## 1.2 Funcionalidades Implementadas

| Funcionalidad | Ubicación | Descripción |
|---|---|---|
| **Resumen General** | `streamlit_app/pages/resumen_general.py` | Tabla pivote con ~1000 indicadores; gráficos Plotly; drill-down por indicador |
| **CMI Estratégico** | `streamlit_app/pages/cmi_estrategico.py` | 4 perspectivas; tendencias históricas; filtro por objetivo |
| **Plan de Mejoramiento** | `streamlit_app/pages/plan_mejoramiento.py` | Vinculación OM ↔ indicadores; flujo de seguimiento |
| **Resumen por Procesos** | `streamlit_app/pages/resumen_por_proceso.py` | Desglose operativo; heatmap proceso × período |
| **Seguimiento de Reportes** | `streamlit_app/pages/seguimiento_reportes.py` | QA de cargas Excel; validación de errores |
| **PDI/Acreditación** | `streamlit_app/pages/pdi_acreditacion.py` | Tracking de PDI con estados |
| **Persistencia de OM** | `core/db_manager.py` | Dual SQLite/PostgreSQL; registro centralizado |

---

## 1.3 Flujos Principales

```
┌──────────────────────┐
│   Excel Source       │
│  (.xlsx files)       │
└──────────┬───────────┘
           ↓
    ┌─────────────────────────────┐
    │ services/data_loader.py     │
    │ - Normaliza cumplimiento    │
    │ - Mapea procesos padre      │
    │ - Caché st.cache_data       │
    └──────────┬──────────────────┘
               ↓
         ┌──────────────────────┐
         │ core/calculos.py     │
         │ - Categoriza         │
         │ - Calcula tendencias │
         │ - Aplica umbrales    │
         └──────────┬───────────┘
                    ↓
    ┌──────────────────────────────────────┐
    │    streamlit_app/pages/*.py          │
    │    - Resumen general                │
    │    - Estratégico (CMI)              │
    │    - Operativo (Procesos)           │
    │    - Mejoramiento (OM Plan)         │
    └──────────┬───────────────────────────┘
               ↓
         ┌───────────────────┐
         │ core/db_manager   │
         │ ← OM Registry     │
         │ SQLite/PostgreSQL │
         └───────────────────┘
```

---

## 1.4 Arquitectura Actual

**Patrón:** Monolítico modular con capas claramente separadas

```
app.py (entrypoint)
 └─ streamlit_app/main.py (router multi-página)
    │
    ├─ core/ (Lógica pura, testeable)
    │  ├─ config.py (umbrales, colores, rutas)
    │  ├─ calculos.py (normalización, categorización, tendencias)
    │  ├─ niveles.py (aliases para categorización)
    │  └─ db_manager.py (SQLite/PostgreSQL)
    │
    ├─ services/ (Caché Streamlit, orquestación)
    │  ├─ data_loader.py (carga Excel + mapeos)
    │  └─ ai_analysis.py (análisis con Claude)
    │
    ├─ streamlit_app/
    │  ├─ pages/ (UI principal, múltiples vistas)
    │  │  ├─ resumen_general.py
    │  │  ├─ cmi_estrategico.py
    │  │  ├─ plan_mejoramiento.py
    │  │  ├─ resumen_por_proceso.py
    │  │  ├─ seguimiento_reportes.py
    │  │  ├─ pdi_acreditacion.py
    │  │  └─ gestion_om.py (deshabilitada)
    │  │
    │  ├─ components/ (Componentes reutilizables)
    │  │  ├─ filters.py
    │  │  ├─ charts.py
    │  │  ├─ kpi.py
    │  │  ├─ topbar.py
    │  │  └─ banner.py
    │  │
    │  └─ services/ (Servicios internos)
    │     └─ strategic_indicators.py
    │
    ├─ components/ (LEGACY - compartido)
    │  └─ charts.py
    │
    ├─ scripts/ (ETL y procesamiento)
    │  ├─ consolidation/ (motor de reglas y auditoría)
    │  ├─ etl/ (pipelines de transformación)
    │  ├─ nivel3/ (funcionalidad operativa)
    │  └─ analytics/ (análisis especializado)
    │
    └─ pages_disabled/ (15+ archivos deprecated)
```

**Separación de responsabilidades:**
- ✅ Lógica pura (testeable sin Streamlit) en `core/`
- ✅ Caché Streamlit en `services/`
- ✅ UI + navegación en `streamlit_app/`

---

## 1.5 Modelo de Datos

### Entidades Clave

**Indicador**
```python
{
    'Id': str,                    # ej. '101'
    'Indicador': str,             # Nombre descriptivo
    'Proceso': str,               # DIRECCIÓN ESTRATÉGICA, DOCENCIA, etc.
    'Subproceso': str,            # Planeación Estratégica, Gestión Docente, etc.
    'Meta': float,                # 0.85, 1.0, etc. (decimal)
    'Cumplimiento%': float,       # 0-200+ (puede exceder 100%)
    'Periodicidad': str,          # Semestral, Anual, etc.
    'Clasificación': str,         # Estratégico, Operativo, Académico, etc.
}
```

**Cumplimiento (con categorización automática)**
```python
{
    'Fecha': str,                 # '2024-2S', '2025-1S'
    'Cumplimiento_norm': float,   # Normalizado a [0..n]
    'Categoría': str,             # Peligro | Alerta | Cumplimiento | Sobrecumplimiento
    'Tendencia': str,             # ↑ | ↓ | →
}
```

**Oportunidad de Mejora (OM)**
```sql
-- Persistida en SQLite/PostgreSQL
registros_om:
  id_indicador TEXT           -- Enlace a Indicador.Id
  numero_om TEXT              -- Código del plan de mejora
  tiene_om INTEGER            -- 0|1
  comentario TEXT             -- Notas
  periodo TEXT                -- 2024-2S, etc.
  anio INTEGER
  sede TEXT
  fecha_registro TEXT
  UNIQUE(id_indicador, periodo, anio, sede)
```

---

## 1.6 Reglas de Negocio Implementadas

### Umbrales de Categorización
Centralizados en `core/config.py` (línea 35):

```python
# Indicadores Generales
< 80%       → Peligro (🔴)
80–99.9%    → Alerta (🟡)
100–104.99% → Cumplimiento (🟢)
≥ 105%      → Sobrecumplimiento (🔵)

# Indicadores Plan Anual (IDs: 373, 390, 414-420, 469-471)
< 80%       → Peligro
80–94.9%    → Alerta
95–100%     → Cumplimiento
> 100%      → Sobrecumplimiento (raro, tope=100%)

# Indicadores con tope 100% (IDs: 208, 218)
≥ 100%      → Cap at 100% (son métricas negativas)
```

### Normalización de Cumplimiento
```python
# Si valor > 2, divide /100 (asume porcentaje)
# Si valor ≤ 2, mantiene como decimal
# Limpia símbolos: "85%", "85,5" → 0.85
```

### Mapeo Proceso → Subproceso
Hardcodeado en `services/data_loader.py` con 50+ entradas manuales:
```python
_MAPA_PROCESO_PADRE = {
    'gestion de proyectos' → 'DIRECCIÓN ESTRATÉGICA',
    'gestion docente' → 'DOCENCIA',
    'practicas' → 'EXTENSIÓN',
    ...
}
```

---

# 2. MATRIZ FUNCIONAL DETALLADA

## 2.1 Funcionalidades Activas ✅ (En Producción)

| Funcionalidad | Archivo Primario | Estado | Criticidad | Observaciones |
|---|---|---|---|---|
| **Carga de datos Excel** | `services/data_loader.py` | ✅ Completo | 🔴 ALTO | Caché st.cache_data; fuente oficial: *Resultados Consolidados.xlsx* |
| **Normalización de cumplimiento** | `core/calculos.py#L13` | ✅ Completo | 🔴 ALTO | Convierte % ↔ decimal; regla: si valor > 2 entonces /100 |
| **Categorización indicadores** | `core/calculos.py#L27` | ✅ Completo | 🔴 ALTO | Umbrales por tipo: General (80-100-105%), Plan Anual, Tope 100% |
| **Tabla pivote (Resumen General)** | `streamlit_app/pages/resumen_general.py` | ✅ Completo | 🔴 ALTO | Visualización principal; soporta ~1000+ indicadores |
| **Filtros de búsqueda** | `streamlit_app/components/filters.py` | ✅ Completo | 🔴 ALTO | ID, nombre, proceso, subproceso, nivel, período |
| **Gráficos históricos** | `components/charts.py#L1` | ✅ Completo | 🔴 ALTO | Línea con zonas, scatter 3D, heatmap interactivos |
| **CMI Estratégico** | `streamlit_app/pages/cmi_estrategico.py#L57` | ✅ Completo | 🔴 ALTO | 4 perspectivas; gráficos históricos |
| **Plan de Mejoramiento** | `streamlit_app/pages/plan_mejoramiento.py#L28` | ✅ Completo | 🔴 ALTO | Vinculación OM ↔ indicadores |
| **Resumen por Procesos** | `streamlit_app/pages/resumen_por_proceso.py` | ✅ Completo | 🔴 ALTO | Desglose por proceso; heatmap |
| **Seguimiento de Reportes** | `streamlit_app/pages/seguimiento_reportes.py` | ✅ Completo | 🟡 MEDIO | QA de cargas; validación de estructura |
| **PDI/Acreditación** | `streamlit_app/pages/pdi_acreditacion.py#L7` | ✅ Completo | 🟡 MEDIO | Tracking de PDI con estados |
| **Persistencia OM (BD)** | `core/db_manager.py` | ✅ Completo | 🔴 ALTO | Dual: Supabase (prod) ↔ SQLite (local) |
| **Exportación a Excel** | `components/charts.py#L189` | ✅ Completo | 🟡 MEDIO | Genera .xlsx con formato; auto-filtro |
| **Cálculo de tendencias** | `core/calculos.py#L73` | ✅ Completo | 🟡 MEDIO | Compara último vs penúltimo; ↑/↓/→ |
| **Recomendaciones contextuales** | `core/calculos.py#L98` | ✅ Completo | 🟡 MEDIO | Según categoría + tendencia (máx. 3) |

---

## 2.2 Funcionalidades Incompletas ⚠️

| Funcionalidad | Archivo | Estado | Criticidad | Bloques |
|---|---|---|---|---|
| **Análisis de texto con IA** | `services/ai_analysis.py` | ⚠️ Incompleto | 🟢 BAJO | **NUNCA IMPORTADO** — requiere ANTHROPIC_API_KEY; falta UI, tests, integración |
| **Motor de consolidación (Fase 2)** | `scripts/consolidation/` | ⚠️ En desarrollo | 🔴 ALTO | Reglas + auditoría OK, pero requiere validación con usuarios |
| **Nivel 3 (Operativo)** | `scripts/nivel3/` | ⚠️ Experimental | 🔴 ALTO | Sin documentación clara; Plan Fase 3 |
| **Alertas automáticas** | — | ⚠️ NO INICIADO | 🟡 MEDIO | Documentado pero sin code; requiere reglas configurables |
| **Predicciones/Proyecciones** | `pages_disabled/irip_predictivo.py` | ⚠️ Stub | 🟢 BAJO | Plan Fase 3; requiere modelos IA |
| **Detección de anomalías (DAD)** | `pages_disabled/dad_detector.py` | ⚠️ Stub | 🟢 BAJO | Plan Fase 3; requiere algoritmos ML |

---

## 2.3 Funcionalidades Deshabilitadas 🔴 (pages_disabled/)

| Archivo | Propósito | Razón | Riesgo | Crítica |
|---|---|---|---|---|
| **1_Resumen_General.py** | Tablero v1 | Reemplazado por versión v2 | BAJO | ❌ No |
| **2_Gestion_OM.py** | Gestión OM | **Refactoring INCOMPLETO** | **ALTO** | ⚠️ **SÍ** — a mitad |
| **2_Indicadores_en_Riesgo.py** | Vista Peligro/Alerta | Absorbida en resumen_general.py | BAJO | ❌ No |
| **3_Acciones_de_Mejora.py** | Plan de acciones | Integrado en plan_mejoramiento.py | MEDIO | ⚠️ Código útil |
| **3_Tablero_Estrategico_Operativo.py** | Dashboard híbrido | Dividido en CMI + procesos | BAJO | ❌ No |
| analitica_ia.py | Análisis IA | Plan Fase 3 | BAJO | ❌ No |
| auditorias.py | Trazabilidad | Reemplazado por audit.py v2 | BAJO | ❌ No |
| cmi_estrategico.py | CMI viejo | Completamente reemplazado | BAJO | ❌ No |
| coherencia_metas.py | Validación meta | Plan Fase 2 | BAJO | ❌ No |
| dad_detector.py | Anomalías | Plan Fase 3 | BAJO | ❌ No |
| inicio_estrategico.py | Dashboard inicial | Sustituido | BAJO | ❌ No |
| irip_predictivo.py | Predictivos | Plan Fase 3 | BAJO | ❌ No |
| pdi_acreditacion.py | PDI viejo | Reemplazado | BAJO | ❌ No |
| plan_mejoramiento.py | PM viejo | Reemplazado | BAJO | ❌ No |
| resumen_por_proceso.py | Procesos viejo | Reemplazado | BAJO | ❌ No |

---

# 3. IDENTIFICACIÓN DE PROBLEMAS

## 3.1 Duplicidades Críticas 🔴

| Problema | Ubicación | Causa | Impacto | Solución |
|---|---|---|---|---|
| **Mapa proceso → subproceso hardcodeado** | `services/data_loader.py#L30` (900+ líneas) | Evitar I/O dentro caché Streamlit | ALTO: cambios requieren redeploy | Mover a `data/mappings/procesos.yaml` + precarga startup |
| **Umbrales categorización duplicados** | `core/config.py#L35` + `core/niveles.py` | Compatibilidad legacy | ALTO: riesgo desincronización | Eliminar niveles.py; centralizar todo |
| **Funciones de formato dispersas** | `resumen_general.py#L100` (_is_null, _to_num, _limpiar, _fmt_num) | Cada página copia | ALTO: 5+ copias | Centralizar en `utils/formateo.py` |
| **Carga de datos (múltiples versiones)** | `resumen_general.py#L225` (múltiples funciones) + otras páginas | TTL inconsistente (300s vs 600s) | ALTO: datos desincronizados | Centralizar con decoradores uniformes |
| **Filtro de período** | Cada página (resumen_general, cmi_estrategico, plan_mejoramiento) | Sin patrón estándar | ALTO: inconsistencia UX | Crear componente FilterPeriodo reutilizable |

---

## 3.2 Flujos Fragmentados ⚠️

| Flujo | Ubicaciones | Problema | Riesgo |
|---|---|---|---|
| **Cálculo de categoría para OM** | `core/calculos.py`, `resumen_general.py#L126`, `core/niveles.py` | 3 implementaciones | ALTO: reglas divergen |
| **Registro OM (crear/editar)** | `gestion_om.py` (deshabilitada) + `pages_disabled/2_Gestion_OM.py` + `core/db_manager.py` | No hay interface única | ALTO: usuario confundido |
| **Validación de cumplimiento** | `services/data_loader.py`, `generar_reporte.py`, `scripts/ingesta_plantillas.py` | Dispersa en ETL | ALTO: inconsistencia QA |
| **Normalización de columnas Excel** | `services/data_loader.py#L20` + `resumen_general.py#L330` | Cascada | MEDIO: frágil |

---

## 3.3 Inconsistencias Técnicas 🔄

| Inconsistencia | Archivos | Impacto | Ejempl

o |
|---|---|---|---|
| **TTL de caché inconsistente** | `resumen_general.py#L224` (600s), `resumen_general.py#L278` (300s) | Datos desincronizados | Una cacha 10 min, otra 5 min |
| **Session state keys sin prefijo** | Cada página ("rc_clear_global", "om_filtro_proceso_tab") | Conflictos | Si coinciden → se pisan datos |
| **Importes cruzados entre capas** | `resumen_general.py` importa desde `components/`, `services/`, `core/`, `streamlit_app/` | Poco claro | Difícil refactorizar |
| **Naming columnas Excel → Python** | `services/data_loader.py#L20` (_RENAME dict) | Mapeos inconsistentes | "Ejecución" → "Ejecucion" (tildes) |
| **Componentes UI en dos places** | `components/charts.py` vs `streamlit_app/components/` | Confusión | ¿De cuál importan? |
| **Importación módulo "components/" sin path** | `resumen_general.py#L25` sin ruta absoluta | Asume cwd | Usar rutas absolutas |

---

# 4. RESUMEN EJECUTIVO

## 4.1 Estado General del Sistema

| Categoría | Cantidad | Status |
|---|---|---|
| ✅ Funcionales | 15+ | En producción, confiables |
| ⚠️ Incompletas | 7 | Necesitan completarse o integrarse |
| 🔴 Deshabilitadas | 15+ | En pages_disabled sin docs |
| 🔴 **DUPLICIDADES** | 6 | Alto impacto mantenimiento |
| ⚠️ **GESTION OM** | 1 | A mitad del refactoring |

---

## 4.2 Top 5 Riesgos Críticos

### 1. 🔴 Mapa de Procesos Hardcodeado (900+ líneas)
- **Ubicación:** `services/data_loader.py#L30`
- **Riesgo:** Cambios requieren editar codigo + redeploy
- **Impacto:** Mantenimiento difícil; escalabilidad limitada
- **Solución:** Mover a `data/mappings/procesos.yaml` con precarga en startup

### 2. 🔴 Gestión OM Fragmentada
- **Ubicación:** Entre `gestion_om.py` (nueva) y `pages_disabled/2_Gestion_OM.py` (vieja)
- **Riesgo:** Usuario no sabe dónde registrar OM; refactoring incompleto
- **Impacto:** Confusión; datos no consolidados
- **Solución:** Completar refactoring; unificar interface de OM

### 3. 🟡 Umbrales Duplicados
- **Ubicación:** `core/config.py#L35` + `core/niveles.py`
- **Riesgo:** Desincronización de reglas de negocio
- **Impacto:** Resultados inconsistentes
- **Solución:** Eliminar `core/niveles.py`; centralizar en `core/config.py`

### 4. 🟡 Funciones de Formato Dispersas
- **Ubicación:** 5+ copias en páginas (_is_null, _fmt_num, etc.)
- **Riesgo:** Bugs en múltiples places; mantenimiento pesado
- **Impacto:** Inconsistencia de formato
- **Solución:** Centralizar en `utils/formateo.py`

### 5. 🟡 TTL de Caché Inconsistente
- **Ubicación:** `resumen_general.py` (600s vs 300s)
- **Riesgo:** Datos desincronizados entre funciones
- **Impacto:** Reportes inconsistentes
- **Solución:** Estándar global: `CACHE_TTL` en `core/config.py`

---

## 4.3 Puntuación de Salud del Sistema

```
Arquitectura:    ████████░░ 80% — Buena modularidad, pero con deuda técnica
Funcionalidad:   ████████░░ 80% — Funciones core estables, pero incompletas
Mantenibilidad:  ██████░░░░ 60% — Duplicidad, fragmentación, inconsistencias
Testing:         ████░░░░░░ 40% — Lógica pura testeable, pero falta cobertura
Escalabilidad:   ██████░░░░ 60% — Limitada por hardcoding y caché manual
```

**Nota:** Sistema operativo pero con **deuda técnica moderada** que impede escalabilidad.

---

## 4.4 Próximos Pasos Recomendados

### Fase 0 (URGENTE — 2-3 semanas)
1. **Completar refactoring de Gestión OM** — Unificar entre nueva/vieja
2. **Eliminar `core/niveles.py`** — Consolidar en `core/config.py`
3. **Estandarizar session_state keys** — Convención `{page}_{feature}`
4. **Estandarizar CACHE_TTL** — 300s para datos, 600s para configuración

### Fase 1 (IMPORTANTE — 1 mes)
1. **Mover mapa de procesos a YAML** — Precarga en startup
2. **Centralizar funciones de formato** — `utils/formateo.py`
3. **Unificar carga de datos** — Decoradores uniformes en `services/`
4. **Crear componente FilterPeriodo** — Reutilizable en todas las páginas

### Fase 2 (BACKLOG — 2-3 meses)
1. **Completar validaciones ETL** — Consolidar en single pass
2. **Integrar análisis IA** — Activar `services/ai_analysis.py`
3. **Documentar pages_disabled** — Decidir recuperar o borrar
4. **Cobertura de tests** — Mínimo 60% para lógica core

---

## 4.5 Recomendaciones Arquitectónicas

### ✅ MANTENER
- Separación core/ → services/ → pages/ (unidireccional)
- Lógica pura en `core/` (sin Streamlit)
- Dual SQLite/PostgreSQL en `db_manager.py`
- Caché con ttl en `services/`

### 🔄 MEJORAR
- Consolidar hardcoding en archivos configuración
- Estandarizar pattern para caché (TTL, keys de session)
- Unificar imports (rutas absolutas, convención clara)
- Documentar flujos de datos end-to-end

### ❌ ELIMINAR
- `core/niveles.py` (duplica config.py)
- Funciones de formato en páginas (mover a utils/)
- Session state con keys genéricas (usar prefijos)
- Caché discontinua (TTL inconsistente)

---

## 4.6 Matriz de Decisiones

| Componente | Decision | Razón | Timeline |
|---|---|---|---|
| `gestion_om.py` | Completar refactoring | A mitad; crítico para usuarios | 2 semanas |
| `core/niveles.py` | Eliminar | Duplica `core/config.py` | 1 semana |
| `services/ai_analysis.py` | Activar | Existe pero nunca usado | 3 semanas |
| `pages_disabled/` | Documentar + archivar | 15+ archivos legacy | 2 semanas |
| Mapa procesos hardcodeado | Migrar a YAML | 900+ líneas; mantenibilidad | 3 semanas |

---

**FIN DEL DOCUMENTO**

Generado: 10 de abril de 2026  
Alcance: Análisis completo de arquitectura + mapeo funcional  
Revisor: Arquitecto Senior / Especialista en Indicadores
