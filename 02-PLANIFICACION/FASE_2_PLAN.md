# 📅 PLAN FASE 2 — SGIND
## Optimización, Automatización y Escalado

**Documento Maestro:** [📋 PLAN_INTEGRAL_MEJORA_SGIND.md](PLAN_INTEGRAL_MEJORA_SGIND.md) ← Ver para visión completa (3 Fases + 15 Pilares)

**Fecha de Inicio:** 12 de abril de 2026  
**Duración Estimada:** 8 semanas (12 abril - 6 junio 2026)  
**Esfuerzo:** 232 horas (6 personas × 4 semanas)  
**Infraestructura:** NO Redis Cloud (sin presupuesto de inversión)  
**Estado:** � SEMANA 2/8 — REFACTORIZACIÓN SPRINT 1-2 COMPLETADA ✅ | Limpieza dead code (8,034 líneas), descomposición cargar_dataset(), servicios desacoplados, imports estandarizadas, tests 105/105 pasando

---
## 📊 RESUMEN DE AVANCE GENERAL

| Semana | Periodo | Estado | Avance | Logros Clave |
|--------|---------|--------|--------|-------------|
| **1-2** | 12-25 abril | 🟢 **COMPLETADA** | **100%** | ✅ Refactorización Sprint 1-2, 8,034L código muerto eliminadas, arquitectura limpia |
| **3-4** | 26 abril - 9 mayo | 🟡 Próxima | 0% | ⏳ ETL optimization, validation automation, forecasting POC |
| **5-6** | 10-23 mayo | ⏳ Planeada | 0% | ⏳ Cache tuning, risk models, runbooks, drift detection |
| **7-8** | 24 mayo - 6 junio | ⏳ Planeada | 0% | ⏳ Causal analysis, docs finales, production readiness |

### Avance por Pilar

| Pilar | Nombre | Avance | Estado |
|-------|--------|--------|--------|
| **A** | Performance & Optimization | 10% | 🟡 Pendiente (inicia S3-4) |
| **B** | CI/CD & Quality | 15% | 🟡 GitHub Actions UP, testing base en place; Sprint automation pendiente |
| **C** | Data Validation & Contracts | 5% | 🟡 Definiciones listas; implementación pendiente (S3-4) |
| **D** | Analytics & Predictions | 0% | ⏳ Planificado para S5+ |
| **E** | Documentation & Knowledge | 60% | 🟢 Significativo avance: arquitectura documentada, índices, organización |

**Esfuerzo consumido:** ~28 horas de 232 (12%)  
**Velocidad:** 14 horas/semana (on track con ~28h esperadas en Semana 1-2)

---
## TABLA DE CONTENIDOS

1. [Dependencias de Fase 1](#1-dependencias-de-fase-1)
2. [Objetivos Fase 2](#2-objetivos-fase-2)
3. [Pilares Principales](#3-pilares-principales)
4. [Roadmap Detallado](#4-roadmap-detallado)
5. [Riesgos y Mitigación](#5-riesgos-y-mitigación)
6. [Métricas de Éxito](#6-métricas-de-éxito)

---

## 1. DEPENDENCIAS DE FASE 1

### Estado Previo Requerido: ✅ VALIDADO

**Fase 1 completó exitosamente:**

| Entregable | Estado | Validación |
|-----------|--------|-----------|
| Eliminación de deuda técnica | ✅ | 0 archivos duplicados |
| Centralización de constantes | ✅ | CACHE_TTL = 300s global |
| Consolidación de lógica | ✅ | simple_categoria() en core/calculos.py |
| Extracción YAML (mapeos) | ✅ | 14 procesos, 47 subprocesos |
| Testing base | ✅ | 50+ tests unitarios |
| Documentación sincronizada | ✅ | CIERRE_FASE_1.md completado |

**Bloqueos removidos:**
- ✅ No hay imports circulares
- ✅ No hay hardcoding crítico
- ✅ Codebase está sintácticamente limpio
- ✅ Documentación alineada con código

**➜ FASE 2 PUEDE COMENZAR INMEDIATAMENTE**

---

## 2. OBJETIVOS FASE 2

### Objetivo General
Transformar SGIND de plataforma funcional a **escalable, automatizable y predecible** con énfasis en:
- 🚀 Rendimiento (3x más rápido)
- 🔄 Automatización (CI/CD EOL)
- 📊 Análisis avanzado (predictivo + causal)
- 🔒 Robustez (data validation + contracts)

### Objetivos Específicos

| # | Objetivo | KPI | Owner |
|---|----------|-----|-------|
| 1 | Pipeline 10-15 min → 5 min | Ejecución <5 min | Backend |
| 2 | CI/CD automático 100% | 0 merges sin tests passing | DevOps |
| 3 | Data contracts implementados | 100% de fuentes validadas | Analytics |
| 4 | Predicción de riesgo (+30 días) | MAPE <15% | ML Eng |
| 5 | API REST productiva | 99.5% uptime | Backend |

---

## 3. PILARES PRINCIPALES

### 3.1 PILAR A: Consolidación & Performance

**Objetivo:** Reducir tiempo ETL a 5 min (desde 10-15 min)

**Areas de Trabajo:**

#### A1. Optimización de Pipeline ETL
- **Tarea:** Identificar cuellos de botella (profiling)
- **Esfuerzo:** 8h
- **Entregable:** Report con top 3 bottlenecks + soluciones
- **Owner:** Backend
- **Dependencias:** Ninguna

#### A2. Implementar Lazy Loading en Data Loader
- **Tarea:** Cargar solo lo necesario al inicio; cargar el resto async
- **Esfuerzo:** 12h
- **Entregable:** data_loader.py con async/await + paging
- **Owner:** Backend
- **Dependencias:** A1

#### A3. Caché optimization (Local Only - NO REDIS)
- **Tarea:** DECISIÓN: NO a Redis Cloud (sin presupuesto)
  - Optimize local cache (@st.cache_data TTL strategy)
  - Implement cache warming on startup
  - Monitor cache hit rates
- **Esfuerzo:** 8h (reducido, sin infra nuevas)
- **Entregable:** Optimized caching strategy en data_loader.py
- **Owner:** Backend
- **Dependencias:** A1, A2
- **Nota:** Re-evaluar Redis si load real lo requiere

#### A4. Compresión de exports (Excel)
- **Tarea:** Usar compression algo + streaming write para Excel grandes
- **Esfuerzo:** 6h
- **Entregable:** generar_reporte.py con exports <2s para 5000+ registros
- **Owner:** Backend
- **Dependencias:** None

**Subtotal Pilar A:** 32h (reducido de 40h)

### 3.2 PILAR B: Automatización (CI/CD & Quality Gates)

**Objetivo:** Zero manual steps from commit to deploy (staging)

**Areas de Trabajo:**

#### B1. GitHub Actions Setup
- **Tarea:** Crear workflows para test → lint → build → stage
- **Esfuerzo:** 12h
- **Entregable:** `.github/workflows/test.yml`, `lint.yml`, `deploy-staging.yml`
- **Owner:** DevOps
- **Dependencias:** Ninguna; Hacer en paralelo con A1-A4

#### B2. Pre-commit Hooks
- **Tarea:** Lint + format automático antes de commit
- **Esfuerzo:** 4h
- **Entregable:** `.pre-commit-config.yml` + setup docs
- **Owner:** DevOps
- **Dependencias:** B1

#### B3. Test Coverage Gates
- **Tarea:** Bloquear merge si coverage <80%
- **Esfuerzo:** 6h
- **Entregable:** codecov.io integration + badge en README
- **Owner:** QA
- **Dependencias:** B1

#### B4. Automated Changelog Generation
- **Tarea:** Semantic commit → auto changelog + version bump
- **Esfuerzo:** 4h
- **Entregable:** `CHANGELOG.md` auto-generated
- **Owner:** DevOps
- **Dependencias:** B1

#### B5. Staging Environment
- **Tarea:** Render.com auto-deploy para PR (preview deploys)
- **Esfuerzo:** 8h
- **Entregable:** Preview URL en each PR
- **Owner:** DevOps
- **Dependencias:** B1, A1-A4 complete

**Subtotal Pilar B:** 36h

### 3.3 PILAR C: Data Contracts & Validation

**Objetivo:** 100% de fuentes con validación automática; 0 inconsistencias sin alertas

**Areas de Trabajo:**

#### C1. Data Contracts (Great Expectations)
- **Tarea:** Definir contracts para cada source (API Kawak, Excel, LMI)
- **Esfuerzo:** 8h
- **Entregable:** `config/data_contracts.yaml` + expectations por source
- **Owner:** Analytics / Data Eng
- **Dependencias:** Ninguna

#### C2. Validación Automática en Ingest
- **Tarea:** Ejecutar contracts al cargar datos; log + alert si fail
- **Esfuerzo:** 10h
- **Entregable:** `services/validation.py` + integration en consolidar_api.py
- **Owner:** Backend
- **Dependencias:** C1

#### C3. Data Quality Dashboard
- **Tarea:** Crear página Streamlit mostrando validation stats
- **Esfuerzo:** 8h
- **Entregable:** `streamlit_app/pages/calidad_datos.py`
- **Owner:** Frontend
- **Dependencias:** C2

#### C4. Drift Detection (ML)
- **Tarea:** Detectar when data distributions shift; alert si drift >threshold
- **Esfuerzo:** 10h
- **Entregable:** `services/drift_detector.py` usando scipy/sklearn
- **Owner:** ML Eng
- **Dependencias:** C1, C2

**Subtotal Pilar C:** 36h

### 3.4 PILAR D: Análisis Avanzado (Predictivo + Causal)

**Objetivo:** Capabilities para forecasting (+30d) y causal analysis (¿qué causa cambios?)

**Areas de Trabajo:**

#### D1. Time Series Forecasting
- **Tarea:** Implementar ARIMA/Prophet para indicadores históricos
- **Esfuerzo:** 20h
- **Entregable:** `services/forecasting.py` + Streamlit page
- **Owner:** ML Eng
- **Dependencias:** Ninguna

#### D2. Risk Prediction (Supervised ML)
- **Tarea:** Entrenar modelo XGBoost para predecir riesgo de caída indicador
- **Esfuerzo:** 16h
- **Entregable:** Model pkl + inference API + Streamlit page
- **Owner:** ML Eng
- **Dependencias:** D1 (datos históricos)

#### D3. Causal Graph (Bayesian Network)
- **Tarea:** Mapear relaciones causales entre indicadores / procesos
- **Esfuerzo:** 16h
- **Entregable:** Graph visualization + inference engine
- **Owner:** Analytics / ML Eng
- **Dependencias:** D1, D2

#### D4. Scenario Simulation
- **Tarea:** "What if" analysis: cambiar un indicador, ver impacto en otros
- **Esfuerzo:** 12h
- **Entregable:** Simulador interactivo en Streamlit
- **Owner:** Analytics
- **Dependencias:** D3

**Subtotal Pilar D:** 64h

### 3.5 PILAR E: Documentación & Knowledge Transfer

**Objetivo:** 100% operationally ready; nuevo developer puede onboard en <1 día

**Areas de Trabajo:**

#### E0. Architecture Book — Base (REFACTORIZACIÓN EJECUTADA)
- **Tarea:** Auditoría técnica completa + eliminación deuda técnica + refactorización
- **Esfuerzo:** 14h (realizado Semana 2)
- **Entregable:** ✅ `REFACTORIZACION_ARQUITECTURA_SGIND.md` (7 fases + resultados ejecución)
- **Owner:** Tech Lead (Completado)
- **Logros:**
  - ✅ Auditoría 135 archivos Python
  - ✅ Identificación 8 problemas críticos
  - ✅ Sprint 1-2 ejecutados: 8,034 líneas dead code eliminadas
  - ✅ Arquitectura limpia lista para siguiente fase
  - ✅ 105 tests pasando, importes verificadas

#### E1. Architecture Book (Detallado) — Continuación
- **Tarea:** Diagramas + explicaciones de cada componente (C4 model)
- **Esfuerzo:** 12h
- **Entregable:** `docs/ARQUITECTURA_FASE_2.md` + diagrams (basado en REFACTORIZACION_ARQUITECTURA_SGIND.md)
- **Owner:** Tech Lead
- **Dependencias:** E0 (refactorización blueprint) ✅ + Pilares A-D en progress

#### E2. Runbooks
- **Tarea:** Operativos: como escalar, rollback, responder a alertas, etc.
- **Esfuerzo:** 8h
- **Entregable:** `docs/RUNBOOKS/` con 5+ scenarios
- **Owner:** DevOps + Operations
- **Dependencias:** B1-B5 complete

#### E3. API Documentation (OpenAPI)
- **Tarea:** Generar Swagger spec de APIs creadas en Fase 2
- **Esfuerzo:** 6h
- **Entregable:** `docs/api-spec.yaml` + Swagger UI
- **Owner:** Backend
- **Dependencias:** Backend APIs ready

#### E4. Training & Onboarding
- **Tarea:** Grabar videos, crear quick-start, setup local env guide
- **Esfuerzo:** 10h
- **Entregable:** `docs/ONBOARDING.md` + videos
- **Owner:** Tech Lead + Demo team
- **Dependencias:** All pillars

**Subtotal Pilar E:** 36h (base E0 ✅) + 36h (E1-4 in progress)

---

## 4. ROADMAP DETALLADO

### Semana 1-2 (12-25 abril) — 🟢 COMPLETADA

**Sprint Goal:** Setup CI/CD, identificar bottlenecks, definir y ejecutar contracts + **Refactorización arquitectónica**

| Task | Owner | Days | Deliverable |
|------|-------|------|-------------|
| GitHub Actions setup | DevOps | 3 | `.github/workflows/*` ✅ |
| Pipeline profiling | Backend | 3 | Bottleneck analysis report ✅ |
| Data contracts definition + validation real | Analytics | 3 | `config/data_contracts.yaml` + validation report ✅ |
| Redis integration plan | DevOps | 2 | Decision tomada: NO Redis Cloud ✅ |
| **[NUEVO] Arquitectura Audit + Dead Code Cleanup** | **Tech Lead** | **6** | **REFACTORIZACION_ARQUITECTURA_SGIND.md + Sprint 1-2 executed** ✅ |
| **[NUEVO] Refactorización Servicios (cargar_dataset, ai_analysis)** | **Backend** | **6** | **services/ desacoplado, 5 funciones privadas, tests 105/105** ✅ |
| **[NUEVO] Centralización Constantes + Imports Estandarizadas** | **Backend** | **2** | **core/config.py constants, imports uniformes, strategic_indicators.py moved** ✅ |

**Gate:** 🟢 Bottlenecks identificados, contratos ejecutados, **refactorización completada — 8,034 líneas dead code eliminadas, arquitectura limpia lista para pipeline unification**

**Logros Semana 2 (Refactorización):**
- ✅ Eliminadas 4 versiones duplicadas de resumen_general (2,062 + 1,985 + 247 + 312 L)
- ✅ Eliminados 4 stubs deprecated en utils/ (calculos, data_loader, db_manager, charts)
- ✅ Descompuesto `cargar_dataset()` de 1 god function → 5 funciones privadas
- ✅ Desacoplado `ai_analysis.py` de st.session_state (service puro)
- ✅ Centralización de constantes ESTADO_* y SENTIDO_* en core/config.py
- ✅ Movido `strategic_indicators.py` a capa Services (importable correctamente)
- ✅ Estandarización de imports en todas las páginas (0 variaciones)
- ✅ Tests: 105/105 pasando, conftest.py con collect_ignore_glob creado
- ✅ Documentación: REFACTORIZACION_ARQUITECTURA_SGIND.md FASE 7 resultados ejecución

**Impacto en Sprints 3+:**
- 🚀 Arquitectura limpia desbloqueará Sprint 3 (pipeline unificado scripts/etl + consolidation/)
- 🚀 Funciones modularizadas permiten optimizaciones enfocadas en cargar_dataset()
- 🚀 Tests centralizados + imports standardizadas reducen fricción en cambios futuros

---

### Semana 3-4 (26 abril - 9 mayo) — 🟡 PRÓXIMA (Pendiente inicio)

**Sprint Goal:** Optimize ETL, implement validation, start API (desbloqueado por refactorización Sprint 1-2)

**Status:** 🟡 Planificado | Avance esperado: 0% (inicia 26 de abril)

| Task | Owner | Days | Deliverable | Avance |
|------|-------|------|-------------|--------|
| ETL hot-path optimization (lote 1-2) | Backend | 3 | actualizar_consolidado/fuentes/builders optimizados | 0% |
| Validation auto in ingest | Backend | 3 | services/validation.py | 0% |
| Quality dashboard page | Frontend | 3 | Streamlit page | 0% |
| Forecasting POC | ML Eng | 4 | Prophet model trained | 0% |

**Gate:** Planificado ⏳ `actualizar_consolidado` con mejora >20% vs baseline, validation working, forecast accuracy >80%

---

### Semana 5-6 (10-23 mayo) — ⏳ PLANEADA (Pendiente)

**Sprint Goal:** Deploy optimization, advance ML, create runbooks

**Status:** ⏳ Futuro | Avance esperado: 0% (inicia 10 de mayo)

| Task | Owner | Days | Deliverable | Avance |
|------|-------|------|-------------|--------|
| Local cache tuning + observabilidad | DevOps/Backend | 3 | hit-rate y estrategia TTL documentadas | 0% |
| Risk prediction model | ML Eng | 4 | XGBoost model ready | 0% |
| Runbooks drafted | Operations | 3 | 5+ key scenarios | 0% |
| Drift detector | ML Eng | 2 | Deployed to staging | 0% |

**Gate:** Planificado ⏳ Pipeline estable y optimizado (sin Redis), risk model >85% accuracy, staging stable

---

### Semana 7-8 (24 mayo - 6 junio) — ⏳ PLANEADA (Pendiente)

**Sprint Goal:** Causal analysis, final docs, production readiness

**Status:** ⏳ Futuro | Avance esperado: 0% (inicia 24 de mayo)

| Task | Owner | Days | Deliverable | Avance |
|------|-------|------|-------------|--------|
| Causal graph | Analytics | 3 | Graph visualization + inference | 0% |
| Scenario simulator | Analytics | 3 | Interactive "what if" tool | 0% |
| Architecture book | Tech Lead | 3 | `ARQUITECTURA_FASE_2.md` | 0% |
| Onboarding docs | Tech Lead | 2 | `ONBOARDING.md` + videos | 0% |
| Production readiness review | ALL | 2 | Sign-off checklist | 0% |

**Gate:** Planificado ⏳ All features tested, docs complete, SLA defined (99.5%)

---

## 5. RIESGOS Y MITIGACIÓN

### Risk Register

| # | Risk | Prob | Impact | Mitigation | Owner |
|---|------|------|--------|-----------|-------|
| R1 | Streamlit bottleneck (async limits) | Media | Alto | Evaluar FastAPI layer en Fase 3 | Backend |
| R2 | Redis failover en prod | Baja | Alto | Implement circuit breaker + fallback | DevOps |
| R3 | Data drift no detectado | Media | Medio | Runbook + manual checks semanales | Analytics |
| R4 | ML model overfitting | Media | Medio | Cross-validation + test OOF | ML Eng |
| R5 | Scope creep (nuevas features) | Alta | Alto | Strict feature freeze; backlog a Fase 3 | PM |

### Mitigación por Pilar

| Pilar | Riesgo | Acción |
|-------|--------|--------|
| A | Perf no mejora después de optimizar | Perfilar cada cambio; rollback rápido si regresa |
| B | Tests se ponen lentos (CI timeout) | Separate fast tests; nightly para full suite |
| C | Falsos positivos en validation | Calibrate thresholds con data reales; manual review |
| D | Modelos no generalizan | Collect más datos historia; cross-validation estricta |
| E | Documentación obsoleta en 1 mes | Asignar owner por doc; review async in code reviews |

---

## 6. MÉTRICAS DE ÉXITO

### Performance (Pilar A)

| Métrica | Baseline (Fase 1) | Target (Fase 2) | SLA |
|---------|-------------------|-----------------|-----|
| Tiempo ETL | 10-15 min | <5 min | 99% execution <5min |
| Memory usage | 2GB | <1.5GB | Peak <2GB |
| API response P95 | TBD | <1s | 95th percentile |

### Quality (Pilar B/C)

| Métrica | Baseline | Target | SLA |
|---------|----------|--------|-----|
| Test coverage | 40% | >80% | >80% maintained |
| Linting score | — | A+ | 0 high-priority issues |
| Data contract pass rate | — | >99% | Auto-alert if <99% |
| Validation false positives | — | <1% | Manual review <1 per week |

### Analytics (Pilar D)

| Métrica | Baseline | Target | SLA |
|---------|----------|--------|-----|
| Forecast MAPE | — | <15% | Accuracy tracked daily |
| Risk model accuracy | — | >85% | F1 >0.85 |
| Causal graph coverage | 0% | >80% | All major relationships |
| Scenario execution | — | <5s | Interactive responsiveness |

### Operations (Pilar E)

| Métrica | Baseline | Target | SLA |
|---------|----------|--------|-----|
| Time to onboard dev | 3+ días | <4 horas | New dev productive same day |
| MTTR (Mean Time To Repair) | >2 horas | <15 min | Runbook execution |
| Deployment frequency | Manual | Daily | 0 deployment failures |
| Documentation staleness | ~30% outdated | <5% | Weekly review |

---

## 7. DECISIONES COMPLETADAS & PENDIENTES

### ✅ Decisiones Completadas (11 de abril)

| Decision | Option Selected | Implication | Owner |
|----------|-----------------|-------------|-------|
| **Cache Strategy** | ❌ NO Redis Cloud | Maintain local cache, monitor scalability | Tech Lead |

### 🤔 Architecture Decisions (Pendientes)

| Decision | Options | Implication | Owner | Target Date |
|----------|---------|-------------|-------|-------------|
| Streamlit → FastAPI migration | Yes / No / Fase 3 | Affect API design, deployment | Backend Arch | 30-abr |
| ML framework (scikit-learn vs PyTorch) | sklearn / torch / h2o | Model complexity, training | ML Eng | 15-abr |
| Database choice (PostgreSQL vs BigQuery) | PG / BQ / Hybrid | Cost, latency, analytics | Data Eng | 25-abr |

### ⚙️ Implementation Decisions

| Decision | Options | Implication | Owner | Target Date |
|----------|---------|-------------|-------|-------------|
| Prediction frequency (Daily vs Real-time) | Daily / Hourly / Real-time | Infra complexity | ML Eng / DevOps | 22-abr |
| Causal inference method (Bayesian Net vs Causal Forests) | Bayesian / CF / Hybrid | Accuracy vs explainability | Analytics | 28-abr |
| Contract validation (Great Expectations vs Custom) | GE / Custom / Hybrid | Maintainability | Data Eng | 20-abr |

---

## 8. BUDGET & RESOURCES

### Equipo Requerido (8 semanas)

```
Backend Engineer:       1.0 FTE   (40h/week = 320h total)
ML Engineer:            1.0 FTE   (40h/week = 320h total)
DevOps Engineer:        0.5 FTE   (20h/week = 160h total)
Data/Analytics:         0.5 FTE   (20h/week = 160h total)
Frontend/Streamlit:     0.5 FTE   (20h/week = 160h total)
QA/Testing:             0.5 FTE   (20h/week = 160h total)
Tech Lead/PM:           0.5 FTE   (20h/week = 160h total)
────────────────────────────────────
TOTAL:                  4.5 FTE   (~1,440h = 36 man-weeks)
```

**Budget for Infrastructure (est.):**
- Redis Cloud: ❌ NO (sin presupuesto / stay local cache)
- GitHub Actions: Free (included)
- Render.com add-ons: +$50-100/month (optional)
- **Total:** ~$50-100/month (minimal/ZERO sin Render upgrades)

**Decisión Caching:**
- ✅ DECISIÓN: Mantener local cache (@st.cache_data)
- ⚠️ Monitor scalability con usuarios reales
- 📊 Re-evaluar Redis si load requiere (future)

---

## 9. SUCCESS CRITERIA (EXIT GATES)

### Fase 2 → Ready for Fase 3

Todas MUST be satisfied:

- ✅ ETL execution <5 min (99% of runs)
- ✅ Test coverage >80%
- ✅ CI/CD 100% automated (0 manual deploys)
- ✅ Data contracts passing >99%
- ✅ Risk forecast accuracy >85%
- ✅ Runbooks complete + team trained
- ✅ Documentation <5% stale
- ✅ 0 critical security issues (pen test passed)
- ✅ SLA 99.5% uptime (30-day baseline)

**Sign-Off Authority:** Director Technología + Project Manager

---

## 10. PRÓXIMAS ACCIONES (Immediatamente)

**Antes de 12 de abril (Kick-off):**

- [ ] Confirmar asignación de resources
- [ ] Agendar arquitectura review con team
- [ ] Crear user stories en Jira/GitHub Projects
- [ ] Setup GitHub project board
- [ ] Review & lock decisis arquitectura (sección 7)

**Semana 1 Actions (12-14 abril):**

- [ ] Day 1: Kick-off meeting
- [ ] Day 2: GitHub Actions setup begun
- [ ] Day 2: Pipeline profiling session
- [ ] Day 3: Data contracts drafted
- [ ] Day 5: First sprint planning + standup

---

**Documento Generado:** 11 de abril de 2026  
**Versión:** 1.0 — Initial Plan  
**Estado:** 🟡 AWAITING REVIEW & APPROVAL

👉 **Próximo paso:** Presentar con stakeholders; lock decisions 16-abr; kick-off 19-abr.
