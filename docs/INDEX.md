# 📚 INDEX — Documentación Técnica Complementaria SGIND

**Carpeta:** `docs/`  
**Versión:** 1.0  
**Fecha:** 15 de abril de 2026  
**Propósito:** Documentación adicional organizada por tema (análisis, cálculos, configuración, fases)

---

## 🗂️ ESTRUCTURA DE DOCUMENTACIÓN TÉCNICA

```
docs/
├── 📊 INDEX.md                  ← Estás aquí (mapa de docs/)
│
├── 01-ANALISIS/                 ─── Análisis, reportes, profiling
│   ├── analisis_sistema_indicadores.md      Análisis del sistema completo
│   ├── BOTTLENECK_ANALYSIS.md              Identificación de cuellos de botella
│   ├── DATA_CONTRACTS_VALIDATION_REPORT.md  Reporte de validación de contratos
│   └── PIPELINE_PROFILING.md               Benchmarking y profiling del ETL
│
├── 02-CALCULOS/                 ─── Lógica y cálculos específicos
│   ├── calculos_actualizar_consolidado.md   Fórmulas y cálculos en actualizar_consolidado.py
│   └── logica_actualizar_consolidado.md     Flujo lógico del proceso de consolidación
│
├── 03-CONFIG/                   ─── Configuración y decisiones técnicas
│   ├── CI_CD_SETUP.md                     GitHub Actions, pipelines, automation
│   ├── DATA_CONTRACTS.md                  Definición de contratos de datos
│   ├── DECISION_NO_REDIS.md               Decisión arquitectónica: sin Redis Cloud
│   ├── REDIS_CACHING_PLAN.md              Plan alternativo de caché local
│   └── power_apps_embed.md                Integración con Power Apps
│
├── 04-FASE1/                    ─── Documentación de Fase 1 (Completada)
│   └── documentacion_fase1.md              Detalles de ejecución Fase 1
│
├── 05-FASE2/                    ─── Documentación de Fase 2 (En ejecución)
│   ├── documentacion_fase2.md              Detalles de ejecución Fase 2
│   └── catalogo_plantillas.md              Catálogo de plantillas de referencia
│
├── 06-FASE3/                    ─── Documentación de Fase 3 (Planeada)
│   ├── fase3_deployment.md                 Plan de deployment Phase 3
│   ├── fase3_guia_uso.md                  Guía de usuario para Fase 3
│   ├── fase3_kickoff.md                   Kick-off meeting Fase 3
│   ├── fase3_kpis.md                      KPIs y métricas Fase 3
│   ├── fase3_operativo_spec.md            Spec operativa Fase 3
│   ├── fase3_prioritizacion.md            Priorización de features Fase 3
│   ├── fase3_wireframes.md                Wireframes UI Fase 3
│   └── fase3_wireframes_detailed.md       Wireframes detallados Fase 3
│
└── 07-INTERFAZ/                 ─── Documentación de interfaz de usuario
    └── Interfaz Visual.md                  Especificación visual completa

---

## 🎯 ¿POR DÓNDE EMPEZAR?

### Si quieres entender el sistema actual

**Lectura mínima (30 min):**
1. [01-ANALISIS/analisis_sistema_indicadores.md](01-ANALISIS/analisis_sistema_indicadores.md) (15 min)
   - Visión completa del sistema
   - Flujos principales
   - Componentes interconectados

2. [01-ANALISIS/BOTTLENECK_ANALYSIS.md](01-ANALISIS/BOTTLENECK_ANALYSIS.md) (15 min)
   - Dónde está el problema
   - Por qué es un problema
   - Impacto actual

### Si necesitas optimizar ETL

**Lectura técnica (45 min):**
1. [02-CALCULOS/logica_actualizar_consolidado.md](02-CALCULOS/logica_actualizar_consolidado.md) (20 min)
   - Flujo lógico paso-a-paso
   - Decisiones en cada etapa
   - Validaciones aplicadas

2. [02-CALCULOS/calculos_actualizar_consolidado.md](02-CALCULOS/calculos_actualizar_consolidado.md) (15 min)
   - Fórmulas exactas
   - Casos especiales
   - Excepciones

3. [01-ANALISIS/PIPELINE_PROFILING.md](01-ANALISIS/PIPELINE_PROFILING.md) (10 min)
   - Dónde se gasta el tiempo
   - Oportunidades de mejora

### Si configuras CI/CD o despliegue

**Lectura operativa (20 min):**
1. [03-CONFIG/CI_CD_SETUP.md](03-CONFIG/CI_CD_SETUP.md) — Setup GitHub Actions
2. [03-CONFIG/DECISION_NO_REDIS.md](03-CONFIG/DECISION_NO_REDIS.md) — Por qué sin Redis
3. [03-CONFIG/REDIS_CACHING_PLAN.md](03-CONFIG/REDIS_CACHING_PLAN.md) — Plan alternativo

### Si trabajas en Fase 3 (Analytics/Predicción)

**Lectura de planeación (45 min):**
1. [06-FASE3/fase3_kickoff.md](06-FASE3/fase3_kickoff.md) — Overview
2. [06-FASE3/fase3_kpis.md](06-FASE3/fase3_kpis.md) — Métricas
3. [06-FASE3/fase3_operativo_spec.md](06-FASE3/fase3_operativo_spec.md) — Spec técnica

### Si diseñas interfaz

**Lectura de diseño (30 min):**
1. [07-INTERFAZ/Interfaz Visual.md](07-INTERFAZ/Interfaz Visual.md) — Especificación visual
2. [06-FASE3/fase3_wireframes.md](06-FASE3/fase3_wireframes.md) — Wireframes Fase 3
3. [06-FASE3/fase3_wireframes_detailed.md](06-FASE3/fase3_wireframes_detailed.md) — Detalle

---

## 📊 MATRIZ DE CONTENIDOS

### Categoría: ANALISIS (4 documentos)

| Documento | Duración | Propósito |
|-----------|----------|----------|
| [analisis_sistema_indicadores.md](01-ANALISIS/analisis_sistema_indicadores.md) | 15 min | Visión del sistema completo + flujos |
| [BOTTLENECK_ANALYSIS.md](01-ANALISIS/BOTTLENECK_ANALYSIS.md) | 20 min | Cuellos de botella identificados |
| [DATA_CONTRACTS_VALIDATION_REPORT.md](01-ANALISIS/DATA_CONTRACTS_VALIDATION_REPORT.md) | 10 min | Validación de contratos de datos |
| [PIPELINE_PROFILING.md](01-ANALISIS/PIPELINE_PROFILING.md) | 15 min | Performance profiling detallado |

### Categoría: CALCULOS (2 documentos)

| Documento | Duración | Propósito |
|-----------|----------|----------|
| [logica_actualizar_consolidado.md](02-CALCULOS/logica_actualizar_consolidado.md) | 20 min | Flujo lógico ETL |
| [calculos_actualizar_consolidado.md](02-CALCULOS/calculos_actualizar_consolidado.md) | 15 min | Fórmulas exactas |

### Categoría: CONFIG (5 documentos)

| Documento | Duración | Propósito |
|-----------|----------|----------|
| [CI_CD_SETUP.md](03-CONFIG/CI_CD_SETUP.md) | 15 min | GitHub Actions setup |
| [DATA_CONTRACTS.md](03-CONFIG/DATA_CONTRACTS.md) | 10 min | Definición contratos datos |
| [DECISION_NO_REDIS.md](03-CONFIG/DECISION_NO_REDIS.md) | 5 min | Decisión arquitectónica |
| [REDIS_CACHING_PLAN.md](03-CONFIG/REDIS_CACHING_PLAN.md) | 15 min | Plan caché alternativo |
| [power_apps_embed.md](03-CONFIG/power_apps_embed.md) | 10 min | Integración Power Apps |

### Categoría: FASE1 (1 documento)

| Documento | Duración | Propósito |
|-----------|----------|----------|
| [documentacion_fase1.md](04-FASE1/documentacion_fase1.md) | 30 min | Detalles ejecución |

### Categoría: FASE2 (2 documentos)

| Documento | Duración | Propósito |
|-----------|----------|----------|
| [documentacion_fase2.md](05-FASE2/documentacion_fase2.md) | 30 min | Detalles ejecución |
| [catalogo_plantillas.md](05-FASE2/catalogo_plantillas.md) | 15 min | Referencias |

### Categoría: FASE3 (8 documentos)

| Documento | Duración | Propósito |
|-----------|----------|----------|
| [fase3_kickoff.md](06-FASE3/fase3_kickoff.md) | 20 min | Overview Fase 3 |
| [fase3_deployment.md](06-FASE3/fase3_deployment.md) | 15 min | Plan deployment |
| [fase3_operativo_spec.md](06-FASE3/fase3_operativo_spec.md) | 20 min | Spec técnica |
| [fase3_guia_uso.md](06-FASE3/fase3_guia_uso.md) | 20 min | Guía usuario |
| [fase3_kpis.md](06-FASE3/fase3_kpis.md) | 15 min | Métricas |
| [fase3_prioritizacion.md](06-FASE3/fase3_prioritizacion.md) | 15 min | Priorización |
| [fase3_wireframes.md](06-FASE3/fase3_wireframes.md) | 10 min | Wireframes |
| [fase3_wireframes_detailed.md](06-FASE3/fase3_wireframes_detailed.md) | 15 min | Wireframes detallado |

### Categoría: INTERFAZ (1 documento)

| Documento | Duración | Propósito |
|-----------|----------|----------|
| [Interfaz Visual.md](07-INTERFAZ/Interfaz Visual.md) | 20 min | Spec visual UI |

---

## 🔍 BÚSQUEDA RÁPIDA POR PREGUNTA

### ANALISIS (¿Cómo funciona?)

| Pregunta | Documento | Sección |
|----------|-----------|---------|
| **¿Cómo funciona el sistema?** | [analisis_sistema_indicadores.md](01-ANALISIS/analisis_sistema_indicadores.md) | Todo |
| **¿Dónde está el cuello de botella?** | [BOTTLENECK_ANALYSIS.md](01-ANALISIS/BOTTLENECK_ANALYSIS.md) | "Hot paths" |
| **¿Cómo validamos datos?** | [DATA_CONTRACTS_VALIDATION_REPORT.md](01-ANALISIS/DATA_CONTRACTS_VALIDATION_REPORT.md) | "Tests" |
| **¿Cuál es la performance?** | [PIPELINE_PROFILING.md](01-ANALISIS/PIPELINE_PROFILING.md) | "Benchmarks" |

### CALCULOS (¿Cómo se calcula?)

| Pregunta | Documento | Sección |
|----------|-----------|---------|
| **¿Cuál es el flujo ETL?** | [logica_actualizar_consolidado.md](02-CALCULOS/logica_actualizar_consolidado.md) | "Pasos" |
| **¿Cuáles son las fórmulas?** | [calculos_actualizar_consolidado.md](02-CALCULOS/calculos_actualizar_consolidado.md) | Todo |
| **¿Cómo se normaliza?** | [calculos_actualizar_consolidado.md](02-CALCULOS/calculos_actualizar_consolidado.md) | "Normalización" |

### CONFIG (¿Cómo se configura?)

| Pregunta | Documento | Sección |
|----------|-----------|---------|
| **¿Cómo configuro CI/CD?** | [CI_CD_SETUP.md](03-CONFIG/CI_CD_SETUP.md) | "Instalación" |
| **¿Qué son los contratos de datos?** | [DATA_CONTRACTS.md](03-CONFIG/DATA_CONTRACTS.md) | "Definición" |
| **¿Por qué sin Redis?** | [DECISION_NO_REDIS.md](03-CONFIG/DECISION_NO_REDIS.md) | Todo |
| **¿Cuál es el plan de caché?** | [REDIS_CACHING_PLAN.md](03-CONFIG/REDIS_CACHING_PLAN.md) | "Opciones" |

### FASES (¿Qué viene?)

| Pregunta | Documento | Sección |
|----------|-----------|---------|
| **¿Qué pasó en Fase 1?** | [04-FASE1/documentacion_fase1.md](04-FASE1/documentacion_fase1.md) | Todo |
| **¿Qué hace Fase 2?** | [05-FASE2/documentacion_fase2.md](05-FASE2/documentacion_fase2.md) | "Objetivos" |
| **¿Cuál es el plan Fase 3?** | [06-FASE3/fase3_kickoff.md](06-FASE3/fase3_kickoff.md) | Todo |
| **¿Cuáles son los wireframes?** | [06-FASE3/fase3_wireframes.md](06-FASE3/fase3_wireframes.md) | Todo |

---

## 📈 ESTADÍSTICAS

| Métrica | Valor |
|---------|-------|
| **Total de documentos en docs/** | 23 |
| **Carpetas temáticas** | 7 |
| **Duración de lectura completa** | ~4.5 horas |
| **Duración mínima (overview)** | ~30 minutos |
| **Última actualización** | 15 de abril de 2026 |

---

## 🔗 CONEXIÓN CON DOCUMENTACIÓN PRINCIPAL

**Esta carpeta `docs/` es COMPLEMENTARIA a:**

- [MASTER_INDEX.md](../MASTER_INDEX.md) — Mapa general de TODA la documentación
- [02-PLANIFICACION/FASE_2_PLAN.md](../02-PLANIFICACION/FASE_2_PLAN.md) — Plan actual
- [03-TECNICA/ARQUITECTURA_TECNICA_DETALLADA.md](../03-TECNICA/ARQUITECTURA_TECNICA_DETALLADA.md) — Arquitectura general

**Para una lectura integral:**
1. Comienza en [MASTER_INDEX.md](../MASTER_INDEX.md) (orientación general)
2. Lee [03-TECNICA/ARQUITECTURA_TECNICA_DETALLADA.md](../03-TECNICA/ARQUITECTURA_TECNICA_DETALLADA.md) (visión técnica)
3. Profundiza en [docs/INDEX.md](https://docs/INDEX.md) (este archivo — detalles)

---

## 💾 PROCESOS DE ACTUALIZACIÓN

### Cuando hay cambio en análisis
- Actualizar: [01-ANALISIS/](01-ANALISIS/)
- Referencia desde: [MASTER_INDEX.md](../MASTER_INDEX.md)

### Cuando hay cambio en cálculos
- Actualizar: [02-CALCULOS/](02-CALCULOS/)
- Validar: Contra tests en `tests/test_calculos.py`

### Cuando hay cambio de decisión técnica
- Actualizar: [03-CONFIG/](03-CONFIG/)
- Referencia desde: [02-PLANIFICACION/FASE_2_PLAN.md](../02-PLANIFICACION/FASE_2_PLAN.md)

### Cuando se completa una fase
- Crear: Documento de cierre en carpeta correspondiente
- Actualizar: [MASTER_INDEX.md](../MASTER_INDEX.md)

---

**Última actualización:** 15 de abril de 2026  
**Próxima revisión:** 26 de abril de 2026 (fin Sprint 2)

---

## 🎯 ACCIÓN RECOMENDADA

👉 **Para nuevos team members entienden documentación técnica:**
1. Comienza en [MASTER_INDEX.md](../MASTER_INDEX.md)
2. Luego lee [docs/INDEX.md](https://docs/INDEX.md) (aquí)
3. Profundiza en lo que necesites según tu rol
4. Usa **Ctrl+F** para buscar en este INDEX

🚀 **¡Bienvenido a la documentación técnica de SGIND!**
