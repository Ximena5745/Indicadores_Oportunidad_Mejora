# 🎯 Fase 2 — Enfoque en User Value & Outcomes
## Alineación Técnica ↔ Usuario ↔ Impacto

**Documento:** FASE_2_USER_VALUE_MAP.md  
**Versión:** 1.0  
**Fecha:** 14 de abril de 2026  
**Audiencia:** Product Managers, técnicos, líderes de cambio

---

## TABLA DE CONTENIDOS

1. [Overview: De Features a Outcomes](#overview-de-features-a-outcomes)
2. [Roadmap Fase 2 Actualizado (con User Value)](#roadmap-fase-2-actualizado-con-user-value)
3. [Por Cada Feature: User Outcome + Métrica](#por-cada-feature-user-outcome--métrica)
4. [Estrategia de Adopción](#estrategia-de-adopción)
5. [Validación de Hipótesis](#validación-de-hipótesis)

---

## OVERVIEW: DE FEATURES A OUTCOMES

### El Problema Tradicional de "Feature-Driven" Roadmap

```
FASE 2 TRADICIONAL:
├─ Pilar A: Optimize ETL (target: <5 min)
├─ Pilar B: CI/CD Automático
├─ Pilar C: Data Contracts
├─ Pilar D: Análisis Predictivo
└─ Pilar E: Documentación

PREGUNTA NO RESPONDIDA: ¿Para qué? ¿Qué usuario se beneficia? ¿Cuándo sabemos que funcionó?
```

### La Solución: Value-Driven Roadmap

```
FASE 2 ACTUALIZADA:
├─ OUTCOME 1: "Directivo decide en 5 min"
│  └─ Features que lo habilitan:
│     ├─ Dashboard carga <3s → Performance pipeline (Pilar A)
│     ├─ Data siempre correcta → Data validation (Pilar C)
│     └─ Alertas antes del riesgo → CI/CD para alertas automáticas (Pilar B)
│
├─ OUTCOME 2: "Líder actúa en <24h"
│  └─ Features que lo habilitan:
│     ├─ OM se crea con 1 click → UI mejorada + auto-crear
│     ├─ Notificación inmediata → Sistema de alertas (Pilar B)
│     └─ Responsable ve en tiempo real → API endpoint (Backend)
│
├─ OUTCOME 3: "Auditoría preparedl"
│  └─ Features que lo habilitan:
│     ├─ OMs documentadas 100% → DB schema + validation (Pilar C)
│     ├─ Quién + cuándo + qué cambió → Audit log (Pilar B)
│     └─ Reportería reproducible → Data contracts (Pilar C)
│
└─ OUTCOME 4: "Indicadores mejoran"
   └─ Features que lo habilitan:
      ├─ OM vinculada a indicador → Causal tracking
      ├─ Análisis de qué acciones funcionan → Predictivo (Pilar D)
      └─ Ciclo feedback automático → Monitoring (Pilar D)
```

**Diferencia:** No es "qué hacemos" sino "qué resulta para usuario".

---

## ROADMAP FASE 2 ACTUALIZADO (CON USER VALUE)

### Timeline Integrado

```
SEMANA 1-2                         │ SEMANA 3-4                    │ SEMANA 5-6
(Setup & Identify)                 │ (Optimize & Validate)         │ (Predict & Docs)
────────────────────────────────── │ ───────────────────────────── │ ──────────────────
                                   │                               │
USER OUTCOME 1   (Decisión rápida):│ ✅ PARCIALMENTE FUNCIONAL     │ ✅ FULLY FUNCIONAL
  • Dashboard <3s                  │ • Performance: 45s → 30s      │ • Performance: <5s
  • Datos confiables               │ • Validation: 70% listo       │ • Validation: 100%
  • Alertas tempranas              │ • Alertas básicas funcional   │ • Alertas full-featured
                                   │                               │
USER OUTCOME 2   (Acción rápida):  │ ✅ PARCIALMENTE FUNCIONAL     │ ✅ GO-LIVE USER TEST
  • OM en 1 click                  │ • OM creation UI ready        │ • Tested con 5-10 users
  • Notificación inmedita          │ • Notification system 80%     │ • Feedback incorporado
  • RT visibility                  │ • Status page: basico         │ • Métricas de adopción
                                   │                               │
USER OUTCOME 3   (Auditoría prep): │ ✅ PARCIALMENTE FUNCIONAL     │ ✅ AUDITORÍA READY
  • OM documentadas 100%           │ • Audit log: basic            │ • Audit trail: verificado
  • Quién/cuándo/por qué           │ • Reports reproducible        │ • Report automation works
  • Reportería reproducible        │ • Data contracts              │ • Runbooks escritos
                                   │                               │
USER OUTCOME 4   (Mejora):         │ 🔵 LEARNING PHASE             │ 🔵 POC READY
  • Causal tracking                │ • Forecast POC trained        │ • Risk model > 80%
  • Análisis predictivo            │ • Risk model en progreso      │ • Causal graph: diseño
  • Ciclo feedback                 │ • Data para análisis listo    │ • Ready para Fase 3
```

---

## POR CADA FEATURE: USER OUTCOME + MÉTRICA

### OUTCOME 1: "Directivo Decide en 5 Minutos"

#### Feature 1.1: Performance ETL (<5 min)

**Para quién:** Rector, Vicerrector (necesita dashboard actualizado)

**Por qué importa:** 
- Dashboard no es útil si está "viejo" hace horas
- Decisión rápida requiere data fresca

**Cómo se mide:**
```
MÉTRICA TÉCNICA:         MÉTRICA DE USUARIO:
ETL duration: 45s → 5m   "Puedo ver indicadores actualizados
                          en <5 min después de que ocurren"

                          Validación: 
                          - Rector abre SGIND → ¿le parece data fresca?
                          - Compara timestamp SGIND vs realidad
                          - Rating: "Siempre" / "A veces" / "Nunca" fresco
```

**Roadmap:**
```
Sem 1-2: Profiling → bottleneck identificado (actualizar_consolidado 34-38s)
Sem 3-4: Optimization lote 1 → target 30s (20% improvement)
Sem 5-6: Optimization lote 2 → target <5min TOTAL
Sem 7-8: Fine tuning → 99% <5min en peak hours
```

---

#### Feature 1.2: Data Validation (<1% error)

**Para quién:** Rector, Vicerrector, Especialista Calidad (necesita confianza en datos)

**Por qué importa:** 
- Una decisión basada en data incorrecta = desastre
- "Confío en los números"

**Cómo se mide:**
```
MÉTRICA TÉCNICA:         MÉTRICA DE USUARIO:
Validation tests: 100/100 "Los números que veo en SGIND
Error rate: <0.5%         coinciden con realidad 99%"

                          Validación:
                          - Auditor valida 50 indicadores
                          - Compara SGIND vs Kawak directo
                          - Si mismatch: investigar + fix
                          
                          Target: 0 discrepancias en 50 muestras
```

**Roadmap:**
```
Sem 1-2: Data contracts definidas + validación automatizada
Sem 3-4: 70% de fuentes validadas; manual review descubre errors
Sem 5-6: 100% validadas; residual review semanal
```

---

#### Feature 1.3: Alertas Tempranas (2-4 semanas ANTES)

**Para quién:** Rector, Vicerrector, Líder Proceso (anticipación)

**Por qué importa:** 
- "Me entero ANTES de que auditor me comenta"
- Tiempo para actuar, no solo reportar

**Cómo se mide:**
```
MÉTRICA TÉCNICA:         MÉTRICA DE USUARIO:
Alerts generated: 50+/mes "Cuando indicador baja, me avisan
Alertas ANTES de vencimiento: >80%  en 24-48h ANTES que
                           problema sea crítico"
                          
                          Validación:
                          - Líder recibe alerta → actúa
                          - Compara: fecha alerta vs fecha vencimiento
                          - Si alerta 3 semanas antes → ✅ Éxito
                          - Si alerta 1 día antes → ⚠️ Late
```

**Roadmap:**
```
Sem 1-2: Reglas de alertas diseñadas
Sem 3-4: Alertas automáticas en staging; pruebas manuales
Sem 5-6: Alertas enviadas por email/Slack a usuarios reales
Sem 7-8: Feedback de usuarios incorporado
```

---

### OUTCOME 2: "Líder Actúa en <24 Horas"

#### Feature 2.1: OM en 1 Click

**Para quién:** Líder Proceso, Director (reduce fricción)

**Por qué importa:** 
- Actualmente: OM requiere form manual (20 min)
- Si toma 20 min → no se crea
- Si toma 1 click → se crea mismo día

**Cómo se mide:**
```
MÉTRICA TÉCNICA:         MÉTRICA DE USUARIO:
OM creation: <10s        "Cuando veo indicador en riesgo,
UI usable in 1 click     creo OM en <5 minutos"
Auto-populate: 90%
                          Validación (Sem 7-8 user test):
                          - Demo: Indicador baja → crear OM
                          - Medir tiempo de click a submit
                          - Target: <3 clicks, <2 min total
```

**Roadmap:**
```
Sem 3-4: UI para "Crear OM" desde indicador (botón visible)
Sem 5-6: Auto-populate campos (responsable, descripción template)
Sem 7-8: User testing; feedback; refine UX
```

---

#### Feature 2.2: Notificación en Tiempo Real

**Para quién:** Líder Proceso, Especialista (inmediatez)

**Por qué importa:** 
- "Si crear OM mientras yo no miro → otros se enteran en tiempo real"
- Responsable puede começar acción antes que fin del día

**Cómo se mide:**
```
MÉTRICA TÉCNICA:         MÉTRICA DE USUARIO:
Notification latency: <1m "Cuando OM se crea,
Email/Slack: <30s        responsable lo sabe en <1 hora"
Delivery rate: 99%+
                          Validación (Sem 7-8):
                          - Crear OM → medir tiempo a receiver
                          - Encuesta: "¿Te notificaste en tiempo?"
                          - Target: 95%+ de receivers dicen "sí"
```

**Roadmap:**
```
Sem 1-2: Notification system architecture designed (no Redis, caché local)
Sem 3-4: Email notification integrated; Slack POC
Sem 5-6: Both channels working; latency <1 min validated
Sem 7-8: User test; adjust message wording
```

---

#### Feature 2.3: Visibility en Tiempo Real (OM Status)

**Para quién:** Líder Proceso, Especialista Calidad (accountability)

**Por qué importa:** 
- "Cuando creo OM y delego, ¿cómo sé que avanza?"
- Actualmente: email + call + spreadsheet = caótico
- SGIND: dashboard muestra status actualizado

**Cómo se mide:**
```
MÉTRICA TÉCNICA:         MÉTRICA DE USUARIO:
OM status page: <2s load "En 1 lugar veo status de todas mis OMs
Real-time updates: <10s  sin abrir 5 emails"
                          
                          Validación (Sem 5-6):
                          - Líder abre página OMs
                          - ¿Es clara? ¿Se entiende estado?
                          - Encuesta: "Clarity": 1-5
                          - Target: 4.5+/5
```

**Roadmap:**
```
Sem 1-4: OM database schema designed; CRUD ops implemented
Sem 5-6: Dashboard page for OM viewing + filtering
Sem 7-8: Real-time updates; status transitions
```

---

### OUTCOME 3: "Auditoría Preparada"

#### Feature 3.1: OM Documentadas 100%

**Para quién:** Especialista Calidad, Rector (auditoría external)

**Por qué importa:** 
- Auditor pregunta: "¿Qué hicieron con indicador X?"
- Actualmente: silencio o documentación dispersa
- SGIND: OM vinculada con causa + plan + responsable

**Cómo se mide:**
```
MÉTRICA TÉCNICA:         MÉTRICA DE USUARIO:
OMs in system: 100%      "Cuando auditor pregunta,
Linked to indicator: 100% tengo respuesta documentada"
Data quality checks: pass
                          Validación (Sem 8):
                          - Simular auditoría interna
                          - Auditor externo consultor
                          - Pregunta 20 indicadores
                          - Encontrar OM + plan: 95%+? → ✅
```

**Roadmap:**
```
Sem 1-2: OM schema finalized (all required fields)
Sem 3-4: Auto-creation de OMs por reglas (cuando indicador baja)
Sem 5-6: Validation: quién + qué + cuándo + resultado
Sem 7-8: OM archive & searchability optimized para auditoría
```

---

#### Feature 3.2: Audit Trail (Quién + Cuándo + Qué)

**Para quién:** Especialista Calidad (compliance)

**Por qué importa:** 
- "¿Quién cambió este indicador?"
- Regulación: trazabilidad de cambios
- Confianza: "no fue manipulado"

**Cómo se mide:**
```
MÉTRICA TÉCNICA:         MÉTRICA DE USUARIO:
Audit log entries: 100%  "Si auditor pregunta '¿quién bajó esto?'
Timestamp accuracy: ms   tengo log inmediato"
User attribution: 99%
                          Validación:
                          - Indicador cambió → audit log muestra:
                            • Usuario, timestamp, cambio previo/nuevo
                          - Auditoría: 0 cambios sin explicación
                          - Target: 100% trazabilidad
```

**Roadmap:**
```
Sem 1-2: Audit log architecture designed
Sem 3-4: Logging integrated en todas escrituras DB
Sem 5-6: Audit log visible en UI para investigación
Sem 7-8: Report generator para auditoría (searchable, printable)
```

---

#### Feature 3.3: Reportería Reproducible

**Para quién:** Especialista Calidad (auditoría)

**Por qué importa:** 
- Actualmente: reportes manuales, no reproducibles
  - Mes 1: alguien genera con formula X
  - Mes 2: alguien diferente, formula y (resultado diferente!)
- SGIND: mismo dataset + período = mismo resultado
- Auditoría confía: "no hay manipulación"

**Cómo se mide:**
```
MÉTRICA TÉCNICA:         MÉTRICA DE USER:
Report determinism: 100% "Si genero reporte mes X dos veces,
Data contracts: pass     es idéntico"
Versioning: full traceability
                          Validación (Sem 8):
                          - Generate reporte 2x
                          - Compara byte-by-byte
                          - Si idéntico → ✅ Reproducible
```

**Roadmap:**
```
Sem 1-2: Data contracts definidas (qué datos entran)
Sem 3-4: Report templates creadas (predefinidas, no manuales)
Sem 5-6: Report generation automated; tested
Sem 7-8: Auditor valida reproducibilidad
```

---

### OUTCOME 4: "Indicadores Mejoran"

#### Feature 4.1: Causal Tracking (OM → Indicador)

**Para quién:** Equipo Calidad, Analytics (evidence-based)

**Por qué importa:** 
- "¿Esta OM realmente hizo la diferencia?"
- Actualmente: OMs se cierran sin validar si indicador mejoró
- SGIND: antes/después claro, causabilidad verificable

**Cómo se mide:**
```
MÉTRICA TÉCNICA:         MÉTRICA DE USUARIO:
OM-Indicator linkage: 100% "Cuando cierre OM, veo que
Correlation analysis: done indicador fue del 65% → 78%"
Before/after tracking
                          Validación (Sem 7-8):
                          - 20 OMs cerradas en Fase 2
                          - De esas, % con indicador mejorado?
                          - Target: 70%+ validadas
```

**Roadmap:**
```
Sem 1-2: Schema para linkage (OM → multiple indicadores afectados)
Sem 3-4: Tracking antes/después implementado
Sem 5-6: Analysis: correlation OM acción → indicador mejora
Sem 7-8: Dashboard muestra "OMs exitosas" vs "OMs inconclusas"
```

---

#### Feature 4.2: Análisis Predictivo (Risk Model)

**Para quién:** Analytics, Rector (anticipación)

**Por qué importa:** 
- "¿Qué indicadores van a caer en los próximos 30 días?"
- Actualmente: sin visibility del futuro
- SGIND: modelo predice riesgo → OM preventiva antes de caída

**Cómo se mide:**
```
MÉTRICA TÉCNICA:         MÉTRICA DE USUARIO:
Model accuracy: >85%     "Modelo predice 30 días antes
MAPE: <15%              si indicador va a caer"
Recall (true positives): >80%
                          Validación (Sem 7-8):
                          - Modelo predice 10 indicadores en riesgo
                          - En semana 5: ¿cuántos realmente cayeron?
                          - True positive rate: 80%+? → ✅
```

**Roadmap:**
```
Sem 1-2: Data collection (histórico 2022-2026)
Sem 3-4: Feature engineering; Prophet POC trained
Sem 5-6: Risk model (XGBoost) developed + tested
Sem 7-8: Integration en dashboard; predictions visible
```

---

## ESTRATEGIA DE ADOPCIÓN

### Fase 2: User Engagement Strategy

#### Semana 1-2: Discovery Phase

**Objetivo:** Entender usuarios reales, sus workflows, problemas

**Actividades:**
```
□ Entrevistar 5-10 usuarios clave por rol:
  • 1 Rector/Vicerrector
  • 2-3 Líderes de proceso
  • 1-2 Especialistas calidad
  • 1-2 Docentes
  
□ Preguntas clave:
  - "¿Cómo monitoreas indicadores HOY?"
  - "¿En cuánto tiempo te enteras de un incumplimiento?"
  - "¿Cuántas horas gastas en reportería/mes?"
  - "¿Qué error te ha costado más caro?" (pain discovery)
  - "¿Usarías un dashboard para tomar decisiones?" (willingness)

□ Observación in situ:
  - Reunión de junta: ¿de dónde vienen los datos que citan?
  - Monitoreo líder: ¿cómo consulta status hoy?
  
□ Documentar: "User Discovery Report" con insights clave
```

---

#### Semana 3-4: Pilot Group Recruiting

**Objetivo:** Seleccionar 8-12 usuarios para testear features en tiempo real

**Criterios:**
```
✅ Rol cubierto (evitar sesgo)
✅ Políticamente amigable (no resistentes de nacimiento)
✅ Disponibles 2-3 horas/semana para feedback
✅ Representan diferentes áreas (no todo "DOCENCIA")
```

**Actividades:**
```
□ Reunión de kickoff:
  - Explicar: "Esto es BETA, tu feedback es crítico"
  - Demo: qué features están listos
  - Survey: baseline usage & pain
  
□ Weekly check-ins (30 min):
  - ¿Qué intentaste usar? ¿Funcionó?
  - ¿Qué falta?
  - ¿Qué te confundió?
  
□ Bi-weekly refinement:
  - Escuchar feedback
  - Ajustar UX based on findings
  - Release mejorado
```

---

#### Semana 5-6: Feedback Integration

**Objetivo:** Incorporar aprendizajes en Features

**Actividades (por Feature):**

| Feature | Métrica | Target | Acción si NO se cumple |
|---------|---------|--------|----------------------|
| OM 1-click | Time to create OM | <5 min | Simplif UI |
| Alert notification | Latency | <1 hour | Debug notification stack |
| Dashboard <3s | Load time | <3s | Optimize queries |
| Data validation | Error rate | <1% | Adjust rules, manual review |

---

#### Semana 7-8: Pre-Launch Validation

**Objetivo:** Asegurar producto está listo para full rollout

**Checklist:**
```
□ Adoption Metrics
  ✓ 80%+ de early users activos en última semana
  ✓ Promedio 2+ sesiones/semana por usuario
  ✓ OM creation: 80%+ de expuestas son creadas
  ✓ Dashboard página: visitadas 3+ veces/semana
  
□ Quality Metrics
  ✓ Bug reported: <2 critiques en última semana
  ✓ Performance: <3s en 99% de requests
  ✓ Uptime: 99.5% sin incidentes >5 min
  ✓ Data fidelity: 0 discrepancias auditor valida
  
□ User Satisfaction
  ✓ NPS: >30 (target positivo)
  ✓ "Usefulness": 4+/5 (encuesta 5-point)
  ✓ "Likelihood recommend": 80%+ would recommend colleague
  
□ Operability
  ✓ Runbook para escalation/issues
  ✓ SLA documentado (response time, uptime)
  ✓ On-call rotation assigned
```

---

## VALIDACIÓN DE HIPÓTESIS

### Hypothesis Testing Framework

Para cada OUTCOME, hypothesis-testing explícita:

#### H1: "Directivo decide en 5 minutos"

```
HYPOTHESIS:
"Si dashboard está disponible + muestra data clara + alertas enviadas
 ENTONCES directivo abrirá SGIND + usará para decisión
 AND decisión se tomará en <5 minutos"

OPERATIONALIZATION:
□ "Disponible" = 99.5% uptime, <3s load time
□ "Data clara" = 0 validation errors, semáforo visible, tendencia clara
□ "Alertas" = Email/Slack enviadas cuando indicador baja
□ "Usará para decisión" = Encuesta: "Qué información usaste?"
                           Target: 70%+ citan SGIND
□ "Decisión <5 min" = Observación directa o encuesta

VALIDATION PLAN (Sem 7-8):
1. Scenario: "Indicador baja repentinamente"
   - Crear test data
   - Enviar alerta
   - Pedir a director: "¿Tienes info para decidir?"
   - Medir tiempo desde alerta → respuesta
   - Target: <15 min desde alerta → decisión documentada

2. Survey post-junta:
   - ¿Usaste SGIND? (Yes/No)
   - ¿Cuánto tiempo tardó? (<5min / 5-15 / >15)
   - ¿Confianza en datos? (1-5 scale)
   - Target: 70%+ say <5 min, confians 4+/5

FAILURE MODE:
Si directivo no usa SGIND OR tarda >30 min
  → Investigate why
    - ¿Dashboard no lo convenció?
    - ¿Datos no son creíbles?
    - ¿Política del "siempre llamamos"? (resistencia cultural)
  → Adjust: producto vs comunicación vs training
```

---

#### H2: "Líder actúa en <24 horas"

```
HYPOTHESIS:
"Si líder recibe alerta (email/Slack)
 + puede crear OM con 1 click
 + asignado automáticamente a responsable
 ENTONCES OM se crea el MISMO DÍA"

OPERATIONALIZATION:
□ "Alerta" = Notificación en <1 hour de indicador bajando
□ "1 click" = OM creation UI takes <2 min
□ "Asignado" = Default responsable filled; puede editarse
□ "Same day" = timestamp(alert) - timestamp(OM_created) < 24h

VALIDATION PLAN (Sem 3-4 onwards):
1. Track metrics:
   - Count OMs creadas per day
   - Timestamp de alerta vs timestamp de OM creada
   - % de OMs creadas within 24h of trigger: target 60%+ (Sem 3-4)
                                               target 80%+ (Sem 7-8)

2. User observation (Sem 7-8):
   - Watch líder receive alerta → create OM
   - Medir: time from notification → OM creation
   - Target: <10 min

FAILURE MODE:
Si OMs no se crean, o muy lentas
  → Investigate:
    - ¿Notificación no llegó?
    - ¿UI demasiado complicaда?
    - ¿Responsable no quiso asignar?
  → Adjust accordingly
```

---

#### H3: "Auditoría preparada"

```
HYPOTHESIS:
"Si todas OMs están documentadas (100%)
 + audit trail existe (quién/cuándo/qué)
 + reportería es reproducible
 ENTONCES auditor encontrará 0 sorpresas
 AND considerará institución "bien organizada""

OPERATIONALIZATION:
□ "Doc 100%" = 100% de indicadores críticos tienen OM si cayeron
□ "Audit trail" = Log accesible a auditor
□ "Reproducible" = generate reporte 2x = idéntico
□ "0 sorpresas" = Pre-audit shows all findings documented
□ "Bien organizada" = Auditor feedback positive

VALIDATION PLAN (Sem 8 / Auditoría 2026):
1. Pre-audit (Sem 8):
   - External auditor consultant reviews SGIND
   - Finds 20 indicadores → ¿todas tienen OMs?
   - Target: 95%+ have documentation

2. Simulated audit:
   - Auditor "finds" 5 hallazgos
   - Can you show OM + plan + evidence?
   - Target: 100% covered; auditor says "impressive"

3. Real auditing 2026:
   - Compare hallazgos 2025 vs 2026
   - Less surprised? Less severe?
   - Survey auditor: "Politécnico está mejor organizado?"

FAILURE MODE:
Si auditor aún encuentra sorpresas O hallazgos igual de graves
  → Investigate:
    - ¿OMs no fueron ejecutadas de verdad?
    - ¿Documentación vacía (fake)?
    - ¿Auditor no creyó en el sistema?
  → Adjust: más rigor en OMs, mejor evidence collection
```

---

#### H4: "Indicadores mejoran"

```
HYPOTHESIS:
"Si OMs se ejecutan correctamente
 + seguimiento es claro
 + ciclo realimentación automático
 ENTONCES indicadores directamente afectados suben 10-15%
 AND la mejora es atribuible a OM (causalidad)"

OPERATIONALIZATION:
□ "OM ejecutada" = Status = "Cerrada" con evidencia
□ "Seguimiento claro" = Weekly updates visible
□ "Ciclo feedback" = Indicador actualizado post-OM = automáticamente revisado
□ "Suben 10-15%" = Indicadores_before vs Indicadores_after
□ "Causal" = Regression analysis OM acción → outcome

VALIDATION PLAN (Sem 5-8 ongoing):
1. Continuous tracking:
   - Monitor 20-30 OMs during Fase 2
   - Track: before OM indicator value → after OM indicator value
   - Calculate: delta = % change
   - Aggregate: median delta
   - Target: positive median; 70%+ of OMs show improvement

2. Causal analysis (Sem 7-8):
   - For OMs that "worked": what was the action exactly?
   - Document as "good practices"
   - Can be replicated?

3. Comparison:
   - OMs created vs OMs not created (control group?)
   - Indicators with OM: trending up?
   - Indicators without OM: trending down or flat?
   - Difference = impact of SGIND?

FAILURE MODE:
Si indicadores no mejoran (o mejoran muy lentamente)
  → Investigate:
    - ¿OMs no son la causa? (indicator has other drivers)
    - ¿Acciones insuficientes?
    - ¿Indicator mide la cosa correcta?
  → Replantear: causal hypothesis, OM quality, metric validity
```

---

## CONCLUSIÓN: "SUCCESS CRITERIA" PARA FASE 2

**Fase 2 es exitosa si:**

```
✅ ADOPTION
  • 60%+ del target user base usa SGIND semanalmente
  • 50+ OMs creadas desde dashboard (vs manual forms)
  • 2+ sesiones promedio por usuario per week

✅ OUTCOME ACHIEVEMENT
  • H1: 70%+ de decisiones citan SGIND
  • H2: 80%+ de OMs creadas <24h de alerta
  • H3: Auditor pre-check: 95%+ findings covered
  • H4: 70%+ de OMs con indicador improvement

✅ QUALITY
  • Dashboard <3s, 99.5% uptime
  • Data validation: <1% error rate
  • 0 critical bugs in last 2 weeks

✅ READINESS FOR PHASE 3
  • Runbooks documentados
  • Team capacitado y motivated
  • Predictive models trained & validated
  • Roadmap claro (Fase 3: 3 niveles analytics)
```

---

**Próximo:** [Diagnóstico de Efectividad Actual](DIAGNOSTICO_EFECTIVIDAD.md) - Validar supuestos antes de Fase 2 full-go.
