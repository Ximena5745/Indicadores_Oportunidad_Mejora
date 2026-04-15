# 📚 MASTER INDEX — SGIND Documentación Centralizada

**Versión:** 2.0  
**Fecha:** 15 de abril de 2026  
**Propósito:** Mapa completo de toda la documentación del proyecto SGIND

---

## 🗂️ ESTRUCTURA DE DOCUMENTACIÓN

```
SGIND/
├── README.md                    ← 👈 COMIENZA AQUÍ (resumen general)
├── MASTER_INDEX.md              ← Estás aquí (mapa completo)
├── INDICE_DOCUMENTACION_TPM.md  ← Índice detallado por rol
│
├── 01-ESTRATEGIA/               ─── 📊 ¿POR QUÉ? ¿PARA QUIÉN? ¿GENERA IMPACTO?
│   ├── PROPUESTA_VALOR_USUARIOS.md        Valor por usuario + value maps + personas
│   ├── THEORY_OF_CHANGE_SGIND.md          Cadena causal + indicadores + riesgos
│   └── DIAGNOSTICO_EFECTIVIDAD_SGIND.md   Situación actual + gaps + baselines
│
├── 02-PLANIFICACION/            ─── 📋 ¿QUÉ HACER? ¿CUÁNDO? ¿CUÁNTO ESFUERZO?
│   ├── PLAN_INTEGRAL_MEJORA_SGIND.md      Visión 3 Fases + 15 Pilares + roadmap
│   ├── FASE_2_PLAN.md                     Plan detallado actual (Semanas 1-8)
│   ├── FASE_2_USER_VALUE_MAP.md           Features + outcomes + hipótesis
│   └── CIERRE_FASE_1.md                   Validación completado + aprendizajes
│
├── 03-TECNICA/                  ─── 🏗️ ¿CÓMO ESTÁ HECHO? ¿QUÉ CAMBIÓ?
│   ├── ARQUITECTURA_TECNICA_DETALLADA.md  Capas, módulos, flujos, ETL
│   ├── ANALISIS_ARQUITECTONICO_SGIND.md   Decisiones técnicas, paradigmas
│   ├── REFACTORIZACION_ARQUITECTURA_SGIND.md   Auditoría + plan + Sprint 1-2 resultados
│   └── DATA_MODEL_SGIND.md                Modelo conceptual + esquemas + validaciones
│
├── 04-FUNCIONAL/                ─── 👥 ¿CÓMO LO USA EL USUARIO?
│   └── DOCUMENTACION_FUNCIONAL.md         CUs, flujos, pantallas, casos
│
├── 05-OPERATIVO/                ─── 🚀 ¿CÓMO INSTALO/EJECUTO? ¿QUÉ RESULTADOS?
│   ├── GUIA_INSTALACION_EJECUCION.md      Setup local, config, deployment
│   └── RESULTADO_REFACTORIZACION_SPRINT1-2.md   Resumen ejecutivo mejoras
│
└── docs/INDEX.md                ─── 📚 DOCUMENTACIÓN TÉCNICA COMPLEMENTARIA
    │
    ├── 01-ANALISIS/             Análisis, reportes, profiling (4 docs)
    ├── 02-CALCULOS/             Lógica de cálculos (2 docs)
    ├── 03-CONFIG/               Configuración y decisiones (5 docs)
    ├── 04-FASE1/                Fase 1 (1 doc)
    ├── 05-FASE2/                Fase 2 (2 docs)
    ├── 06-FASE3/                Fase 3 (8 docs)
    └── 07-INTERFAZ/             UI/UX (1 doc)
```

---

## 🔬 DOCUMENTACIÓN TÉCNICA COMPLEMENTARIA

### [📚 docs/INDEX.md](docs/INDEX.md) — Mapa de Documentación Técnica

Complementa la estructura principal con **documentación específica por tema:**

| Carpeta | Docs | Propósito |
|---------|------|----------|
| **docs/01-ANALISIS/** | 4 | Análisis del sistema, bottlenecks, profiling |
| **docs/02-CALCULOS/** | 2 | Lógica de cálculos y consolidación |
| **docs/03-CONFIG/** | 5 | CI/CD, contratos de datos, decisiones técnicas |
| **docs/04-FASE1/** | 1 | Documentación Fase 1 completada |
| **docs/05-FASE2/** | 2 | Documentación Fase 2 en ejecución |
| **docs/06-FASE3/** | 8 | Documentación Fase 3 planeada |
| **docs/07-INTERFAZ/** | 1 | Especificación visual UI/UX |

👉 **Lectura recomendada:** Después de MASTER_INDEX.md, ve a [docs/INDEX.md](docs/INDEX.md) si necesitas profundizar en un tema específico

---

### 🔴 Si NUNCA has visto SGIND

1. **Lee en 10 min:** [README.md](README.md)
2. **Entiende valor en 20 min:** [01-ESTRATEGIA/PROPUESTA_VALOR_USUARIOS.md](01-ESTRATEGIA/PROPUESTA_VALOR_USUARIOS.md)
3. **Aprende arquitectura en 30 min:** [03-TECNICA/ARQUITECTURA_TECNICA_DETALLADA.md](03-TECNICA/ARQUITECTURA_TECNICA_DETALLADA.md)
4. **Instala en 45 min:** [05-OPERATIVO/GUIA_INSTALACION_EJECUCION.md](05-OPERATIVO/GUIA_INSTALACION_EJECUCION.md)

### 👔 Si eres DIRECTIVO/RECTOR

**Lectura mínima (40 min):**
1. [README.md](README.md) — Resumen (5 min)
2. [01-ESTRATEGIA/PROPUESTA_VALOR_USUARIOS.md](01-ESTRATEGIA/PROPUESTA_VALOR_USUARIOS.md#persona-1-rector--vicerrector) — Tu rol (15 min)
3. [01-ESTRATEGIA/THEORY_OF_CHANGE_SGIND.md](01-ESTRATEGIA/THEORY_OF_CHANGE_SGIND.md) — Impacto esperado (20 min)

**Si necesitas detalles:**
- [02-PLANIFICACION/PLAN_INTEGRAL_MEJORA_SGIND.md](02-PLANIFICACION/PLAN_INTEGRAL_MEJORA_SGIND.md) — Roadmap completo 3 Fases

### 👨‍💼 Si eres LÍDER DE PROCESO/DIRECTOR

**Lectura mínima (50 min):**
1. [04-FUNCIONAL/DOCUMENTACION_FUNCIONAL.md](04-FUNCIONAL/DOCUMENTACION_FUNCIONAL.md) — Cómo usarlo (30 min)
2. [01-ESTRATEGIA/PROPUESTA_VALOR_USUARIOS.md](01-ESTRATEGIA/PROPUESTA_VALOR_USUARIOS.md#persona-2-líder-de-procesocsv) — Tu valor (10 min)
3. [README.md](README.md) — Overview (10 min)

### 👨‍💻 Si eres DESARROLLADOR/TÉCNICO

**Lectura mínima (2 horas):**
1. [README.md](README.md) — Start here (10 min)
2. [03-TECNICA/REFACTORIZACION_ARQUITECTURA_SGIND.md](03-TECNICA/REFACTORIZACION_ARQUITECTURA_SGIND.md) — Estado actual (45 min)
3. [03-TECNICA/DATA_MODEL_SGIND.md](03-TECNICA/DATA_MODEL_SGIND.md) — Modelo datos (30 min)
4. [05-OPERATIVO/GUIA_INSTALACION_EJECUCION.md](05-OPERATIVO/GUIA_INSTALACION_EJECUCION.md) — Setup (20 min)
5. [02-PLANIFICACION/FASE_2_PLAN.md](02-PLANIFICACION/FASE_2_PLAN.md) — Qué viene (15 min)

### 🏗️ Si eres ARQUITECTO/SENIOR

**Lectura completa (4 horas):**
1. [03-TECNICA/ARQUITECTURA_TECNICA_DETALLADA.md](03-TECNICA/ARQUITECTURA_TECNICA_DETALLADA.md) — Diseño completo (60 min)
2. [03-TECNICA/REFACTORIZACION_ARQUITECTURA_SGIND.md](03-TECNICA/REFACTORIZACION_ARQUITECTURA_SGIND.md) — Auditoría + Plan (90 min)
3. [03-TECNICA/ANALISIS_ARQUITECTONICO_SGIND.md](03-TECNICA/ANALISIS_ARQUITECTONICO_SGIND.md) — Decisiones (30 min)
4. [03-TECNICA/DATA_MODEL_SGIND.md](03-TECNICA/DATA_MODEL_SGIND.md) — Modelo completo (30 min)
5. [02-PLANIFICACION/PLAN_INTEGRAL_MEJORA_SGIND.md](02-PLANIFICACION/PLAN_INTEGRAL_MEJORA_SGIND.md) — Visión (20 min)

### 📊 Si eres ANALISTA/PM

**Lectura mínima (1.5 horas):**
1. [02-PLANIFICACION/PLAN_INTEGRAL_MEJORA_SGIND.md](02-PLANIFICACION/PLAN_INTEGRAL_MEJORA_SGIND.md) — Plan integral (45 min)
2. [02-PLANIFICACION/FASE_2_PLAN.md](02-PLANIFICACION/FASE_2_PLAN.md) — Fase actual (30 min)
3. [02-PLANIFICACION/FASE_2_USER_VALUE_MAP.md](02-PLANIFICACION/FASE_2_USER_VALUE_MAP.md) — Valor + hipótesis (15 min)

---

## 🔍 BÚSQUEDA RÁPIDA POR PREGUNTA

### Preguntas Estratégicas

| Pregunta | Documento | Sección |
|----------|-----------|---------|
| **¿Qué es SGIND?** | [README.md](README.md) | "Descripción General" |
| **¿Cuál es la visión?** | [02-PLANIFICACION/PLAN_INTEGRAL_MEJORA_SGIND.md](02-PLANIFICACION/PLAN_INTEGRAL_MEJORA_SGIND.md) | "Visión General" |
| **¿Qué valor aporta?** | [01-ESTRATEGIA/PROPUESTA_VALOR_USUARIOS.md](01-ESTRATEGIA/PROPUESTA_VALOR_USUARIOS.md) | "Value Map por Rol" |
| **¿Cómo genera impacto?** | [01-ESTRATEGIA/THEORY_OF_CHANGE_SGIND.md](01-ESTRATEGIA/THEORY_OF_CHANGE_SGIND.md) | "Cadena de Valor Completa" |
| **¿Cuáles son los riesgos?** | [01-ESTRATEGIA/THEORY_OF_CHANGE_SGIND.md](01-ESTRATEGIA/THEORY_OF_CHANGE_SGIND.md) | "Riesgos & Mitigación" |
| **¿Cuál es el estado actual?** | [02-PLANIFICACION/FASE_2_PLAN.md](02-PLANIFICACION/FASE_2_PLAN.md) | "Estado" |

### Preguntas Técnicas

| Pregunta | Documento | Sección |
|----------|-----------|---------|
| **¿Cómo está arquitecto?** | [03-TECNICA/ARQUITECTURA_TECNICA_DETALLADA.md](03-TECNICA/ARQUITECTURA_TECNICA_DETALLADA.md) | "Capas de Arquitectura" |
| **¿Qué cambios hubo?** | [03-TECNICA/REFACTORIZACION_ARQUITECTURA_SGIND.md](03-TECNICA/REFACTORIZACION_ARQUITECTURA_SGIND.md) | "FASE 7: Resultados" |
| **¿Cuál es el modelo de datos?** | [03-TECNICA/DATA_MODEL_SGIND.md](03-TECNICA/DATA_MODEL_SGIND.md) | "Modelo Conceptual" |
| **¿Cómo fluyen los datos?** | [03-TECNICA/DATA_MODEL_SGIND.md](03-TECNICA/DATA_MODEL_SGIND.md) | "Flujo de Transformación" |
| **¿Cómo instalo?** | [05-OPERATIVO/GUIA_INSTALACION_EJECUCION.md](05-OPERATIVO/GUIA_INSTALACION_EJECUCION.md) | "Instalación" |

### Preguntas Funcionales

| Pregunta | Documento | Sección |
|----------|-----------|---------|
| **¿Cómo lo uso?** | [04-FUNCIONAL/DOCUMENTACION_FUNCIONAL.md](04-FUNCIONAL/DOCUMENTACION_FUNCIONAL.md) | "Casos de Uso" |
| **¿Cuáles son las pantallas?** | [04-FUNCIONAL/DOCUMENTACION_FUNCIONAL.md](04-FUNCIONAL/DOCUMENTACION_FUNCIONAL.md) | "Interfaz Visual" |
| **¿Cómo reporto?** | [04-FUNCIONAL/DOCUMENTACION_FUNCIONAL.md](04-FUNCIONAL/DOCUMENTACION_FUNCIONAL.md) | "CU-4: Analista Genera Reportes" |

### Preguntas de Ejecución

| Pregunta | Documento | Sección |
|----------|-----------|---------|
| **¿Qué se completó?** | [02-PLANIFICACION/CIERRE_FASE_1.md](02-PLANIFICACION/CIERRE_FASE_1.md) | "Entregables" |
| **¿Cuál es el roadmap?** | [02-PLANIFICACION/FASE_2_PLAN.md](02-PLANIFICACION/FASE_2_PLAN.md) | "Roadmap Detallado" |
| **¿Qué sigue?** | [02-PLANIFICACION/PLAN_INTEGRAL_MEJORA_SGIND.md](02-PLANIFICACION/PLAN_INTEGRAL_MEJORA_SGIND.md) | "Fase 3" |
| **¿Cuál es la refactorización?** | [05-OPERATIVO/RESULTADO_REFACTORIZACION_SPRINT1-2.md](05-OPERATIVO/RESULTADO_REFACTORIZACION_SPRINT1-2.md) | "Resumen Ejecutivo" |

---

## 📋 MATRIZ DE CONTENIDOS

### CAPA 1: ESTRATÉGICA (¿POR QUÉ?)

**Documentos:** 3  
**Audiencia:** Directivos, PMs, Stakeholders  
**Duración total:** 90 minutos

| Documento | Duración | Propósito |
|-----------|----------|----------|
| [PROPUESTA_VALOR_USUARIOS.md](01-ESTRATEGIA/PROPUESTA_VALOR_USUARIOS.md) | 45 min | Valor específico por persona + pain points |
| [THEORY_OF_CHANGE_SGIND.md](01-ESTRATEGIA/THEORY_OF_CHANGE_SGIND.md) | 30 min | Cadena causal + indicadores + riesgos |
| [DIAGNOSTICO_EFECTIVIDAD_SGIND.md](01-ESTRATEGIA/DIAGNOSTICO_EFECTIVIDAD_SGIND.md) | 15 min | Baselines actuales + gaps |

### CAPA 2: PLANIFICACIÓN (¿QUÉ HACER?)

**Documentos:** 4  
**Audiencia:** PMs, Leads, Técnicos  
**Duración total:** 150 minutos

| Documento | Duración | Propósito |
|-----------|----------|----------|
| [PLAN_INTEGRAL_MEJORA_SGIND.md](02-PLANIFICACION/PLAN_INTEGRAL_MEJORA_SGIND.md) | 75 min | Visión 3 Fases + 15 Pilares + roadmap |
| [FASE_2_PLAN.md](02-PLANIFICACION/FASE_2_PLAN.md) | 45 min | Semanas 1-8, sprints, tasks, owners |
| [FASE_2_USER_VALUE_MAP.md](02-PLANIFICACION/FASE_2_USER_VALUE_MAP.md) | 20 min | Features → outcomes, hipótesis |
| [CIERRE_FASE_1.md](02-PLANIFICACION/CIERRE_FASE_1.md) | 10 min | Validación completado |

### CAPA 3: TÉCNICA (¿CÓMO?)

**Documentos:** 4  
**Audiencia:** Arquitectos, Seniors, Developers  
**Duración total:** 180 minutos

| Documento | Duración | Propósito |
|-----------|----------|----------|
| [ARQUITECTURA_TECNICA_DETALLADA.md](03-TECNICA/ARQUITECTURA_TECNICA_DETALLADA.md) | 90 min | Módulos, capas, ETL, cálculos |
| [REFACTORIZACION_ARQUITECTURA_SGIND.md](03-TECNICA/REFACTORIZACION_ARQUITECTURA_SGIND.md) | 60 min | Auditoría + plan + Sprint 1-2 |
| [DATA_MODEL_SGIND.md](03-TECNICA/DATA_MODEL_SGIND.md) | 20 min | Esquemas, validaciones, flujos |
| [ANALISIS_ARQUITECTONICO_SGIND.md](03-TECNICA/ANALISIS_ARQUITECTONICO_SGIND.md) | 10 min | Decisiones de diseño |

### CAPA 4: FUNCIONAL (¿CÓMO USA?)

**Documentos:** 1  
**Audiencia:** Usuarios finales, Analistas, PMs  
**Duración total:** 60 minutos

| Documento | Duración | Propósito |
|-----------|----------|----------|
| [DOCUMENTACION_FUNCIONAL.md](04-FUNCIONAL/DOCUMENTACION_FUNCIONAL.md) | 60 min | CUs, flujos, pantallas |

### CAPA 5: OPERATIVA (¿CÓMO EJECUTO?)

**Documentos:** 2  
**Audiencia:** DevOps, Developers, Operations  
**Duración total:** 75 minutos

| Documento | Duración | Propósito |
|-----------|----------|----------|
| [GUIA_INSTALACION_EJECUCION.md](05-OPERATIVO/GUIA_INSTALACION_EJECUCION.md) | 45 min | Setup, config, deployment |
| [RESULTADO_REFACTORIZACION_SPRINT1-2.md](05-OPERATIVO/RESULTADO_REFACTORIZACION_SPRINT1-2.md) | 30 min | Resultados ejecutivos |

---

## 🚀 PROCESOS DE ACTUALIZACIÓN

### Cada Semana
- ✏️ Actualizar: [02-PLANIFICACION/FASE_2_PLAN.md](02-PLANIFICACION/FASE_2_PLAN.md) (progreso %)
- 📊 Actualizar: [01-ESTRATEGIA/DIAGNOSTICO_EFECTIVIDAD_SGIND.md](01-ESTRATEGIA/DIAGNOSTICO_EFECTIVIDAD_SGIND.md) (métricas)

### Cada Sprint (2 semanas)
- ✏️ Actualizar: [02-PLANIFICACION/FASE_2_USER_VALUE_MAP.md](02-PLANIFICACION/FASE_2_USER_VALUE_MAP.md) (aprendizajes)
- 📝 Crear: Documento de Cierre Sprint (entregables + learnings)

### Cada Fase (8 semanas)
- 📋 Crear: `CIERRE_FASE_X.md` (validación completado, lecciones)
- 🔄 Actualizar: [PLAN_INTEGRAL_MEJORA_SGIND.md](02-PLANIFICACION/PLAN_INTEGRAL_MEJORA_SGIND.md) (siguiente fase)

### Cambios Técnicos
- ✏️ Actualizar: [03-TECNICA/](03-TECNICA/) (según refactorización realizada)
- ✏️ Crear: Si hay decisión arquitectónica nueva

---

## 📊 ESTADÍSTICAS

| Métrica | Valor |
|---------|-------|
| **Total de documentos** | 14 (+ docs/ extras) |
| **Cobertura de documentación** | ✅ 100% (estrategia + técnica + funcional + operativa) |
| **Duración de lectura completa** | ~9 horas |
| **Duración de lectura mínima** | ~2 horas |
| **Última actualización** | 15 de abril de 2026 |
| **Próxima revisión** | 26 de abril de 2026 (fin Sprint 2) |

---

## 💡 TIPS DE USO

1. **Usa Ctrl+F** para buscar en este documento
2. **Sigue los links** — todo está interconectado
3. **Lee en orden** según tu rol (arriba ⬆️)
4. **Comparte este MASTER_INDEX** con nuevos team members
5. **Contribuye** — si encuentras un gap, envía PR o comenta

---

**Última actualización:** 15 de abril de 2026  
**Próxima revisión:** 26 de abril de 2026

---

## 🎯 ACCIÓN RECOMENDADA

👉 Si estás aquí por primera vez:
1. Identifica tu rol arriba ⬆️
2. Sigue la ruta de lectura
3. Guarda este archivo en marcadores
4. Comparte con tu equipo

🚀 **¡Bienvenido a SGIND!**
