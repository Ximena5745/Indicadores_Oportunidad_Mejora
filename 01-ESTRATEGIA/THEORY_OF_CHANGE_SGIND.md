# 🧠 Theory of Change — SGIND
## Cómo la Consolidación de Indicadores Genera Impacto Institucional

**Documento:** THEORY_OF_CHANGE_SGIND.md  
**Versión:** 1.0  
**Fecha:** 14 de abril de 2026  
**Audiencia:** Ejecutivos, sponsors, líderes de transformación

---

## TABLA DE CONTENIDOS

1. [Resumen Visión](#resumen-visión)
2. [Cadena de Valor Completa (Inputs → Impacto)](#cadena-de-valor-completa)
3. [Hipótesis Críticas de Cambio](#hipótesis-críticas-de-cambio)
4. [Indicadores por Nivel](#indicadores-por-nivel)
5. [Asunciones Clave](#asunciones-clave)
6. [Riesgos & Mitigación](#riesgos--mitigación)

---

## RESUMEN VISIÓN

### El Problema
Politécnico entrega **1,000+ indicadores** a acreditadores, pero:
- ❌ Datos dispersos en 5 portales diferentes
- ❌ Consolidación manual, error-prone (40% de OMs nunca se cierran)
- ❌ Decisiones se toman **reactivas** (descubrimiento tardío)
- ❌ Auditorías encuentran hallazgos **sorpresivos** (no hay anticipación)
- ❌ Responsabilidad **diluida** (¿quién cierra qué OM?)

**Impacto:** Acreditaciones en riesgo, credibilidad institucional afectada

---

### La Solución
**SGIND:** Centralización + Automatización + Trazabilidad

```
┌────────────────────────────────────────────────────────────┐
│  INPUTS                                                     │
│  • Datos Kawak (1,000 indicadores)                         │
│  • Excel histórico (2022-2026)                             │
│  • Procesos (14 procesos, 47 subprocesos)                  │
│  • OMs (50-100 planes de acción/mes)                       │
├────────────────────────────────────────────────────────────┤
│  PROCESOS                                                   │
│  • Consolidación ETL (3-5 min)                             │
│  • Aplicación de reglas (normalización, categorización)    │
│  • Generación de alertas (automático)                      │
│  • Registro de OMs (trazabilidad)                          │
├────────────────────────────────────────────────────────────┤
│  OUTPUTS                                                    │
│  • Dashboard centralizado (7 páginas)                      │
│  • Alertas tempranas (indicador pasa de Cumpl → Alerta)   │
│  • OMs documentadas (trazabilidad quién→qué→cuándo)       │
│  • Reportería automática (auditoría lista)                 │
├────────────────────────────────────────────────────────────┤
│  OUTCOMES (CAMBIO EN COMPORTAMIENTO)                       │
│  • Directivos toman decisiones en 5 min (no 2 horas)     │
│  • Líderes actúan en <24h (no 2-4 semanas)               │
│  • Auditoría encuentran 0 sorpresas (preparados)          │
│  • OMs se cierran en 50% menos tiempo (15 días vs 30)    │
├────────────────────────────────────────────────────────────┤
│  IMPACTO (CAMBIO EN RESULTADOS)                            │
│  • % Indicadores en cumplimiento: 70% → 85% (Fase 2-3)   │
│  • Acreditación: Score +2-3%                               │
│  • Eficiencia institucional: -30% OMs abiertas crónicas   │
│  • Credibilidad: "Estamos organizados" (interno + externo)│
└────────────────────────────────────────────────────────────┘
```

---

## CADENA DE VALOR COMPLETA

### NIVEL 1: INPUTS (Recursos Disponibles)

| Input | Fuente | Volumen | Confiabilidad |
|-------|--------|---------|--------------|
| **Datos Kawak** | API sistema web | 1,000 indicadores × 12 períodos | 🟢 Alta |
| **Catálogos Excel** | Archivo histórico | Estructura 2022-2026 | 🟡 Media (manual) |
| **LMI Reporte** | Archivo mensual | 1,000+ indicadores por mes | 🟢 Alta |
| **Procesos & Subprocesos** | YAML config | 14 procesos, 47 subprocesos | 🟢 Alta |
| **Recurso: Equipo** | Especialista BI + Devs | 1 FTE consolidación + 0.5 FTE ops | 🟡 Limitado |
| **Recurso: Infraestructura** | Streamlit + PostgreSQL | Servidor staging + prod | 🟢 Funcional |
| **Recurso: Presupuesto** | $0 nuevo (sin Redis Cloud) | Aprovecha existentes | 🟢 OK |

**Validación:** ✅ Todos los inputs están disponibles

---

### NIVEL 2: OUTPUTS (Entregables del Sistema)

#### Output 2.1: Dashboard Centralizado

```
Métrica de Output:
  • 7 páginas Streamlit activas
  • 30+ gráficos interactivos
  • Filtros dinámicos (proceso, período, estado)
  • Exportación Excel automática

Indicador de Éxito:
  ✅ Dashboard carga en <3 segundos
  ✅ 0 errores de datos en report
  ✅ Usable sin entrenamiento (UX claro)
```

#### Output 2.2: Alertas Tempranas

```
Métrica de Output:
  • 50-100 alertas/mes (indicadores que pasan a Alerta/Peligro)
  • 80% de alertas ANTES del vencimiento (2-4 semanas)
  • Comunicación automática (email + Slack)

Indicador de Éxito:
  ✅ 90%+ de líderes reciben alerta del indicador antes que superior
  ✅ Falso positivos <5% (no alertas innecesarias)
```

#### Output 2.3: OMs Documentadas

```
Métrica de Output:
  • 50-100 OMs creadas/mes
  • 100% tiene: ID, responsable, descripción, plazo
  • 100% vinculada a indicador que disparó
  • Trazabilidad: quién creó, cuándo, cambios

Indicador de Éxito:
  ✅ Auditoría encuentra 0 OMs "huérfanas" (sin responsable)
  ✅ Ciclo vida OM claro: abierta → en ejecución → cerrada
```

#### Output 2.4: Reportería Automática

```
Métrica de Output:
  • Reporte mensual: 20 páginas, auto-generado
  • Incluye: status, tendencias, OMs vencidas, recomendaciones
  • Tiempo generación: <5 minutos
  • Preformatted para junta directiva

Indicador de Éxito:
  ✅ <2 horas de ajustes manuales (antes: 8h)
  ✅ Reporte listo 48 horas antes de junta (antes: 1 día antes)
```

---

### NIVEL 3: OUTCOMES (Cambio en Comportamiento)

#### Outcome 3.1: Decisión Ágil

**Para:** Rector, Vicerrector

```
HIPÓTESIS:
"Si directivo ve visibilidad centralizada → recibe alertas tempranas
 → asigna responsable documentado
 ENTONCES: Decisiones en 5 min (vs 2h), proactividad +90%"

MECANISMO:
  Antes: ¿Cómo va X? → llamadas + emails → respuesta conflictiva
  Ahora: ¿Cómo va X? → abre SGIND → respuesta clara en 30s

MÉTRICA DE OUTCOME (Qué cambia):
  ✅ % Decisiones tomadas en <1 hora (antes: <1 día)
  ✅ % Decisiones basadas en data centralizada (target 90%+)
  ✅ % Directivos dicen "SGIND me ayuda a decidir" (target 85%+)

VALIDACIÓN (Cómo se mide):
  Encuesta post-junta: "¿Qué información usó para decisión?"
  → Respuesta: "Dashboard SGIND" vs "Email + llamadas"
  
  Métrica temporal: Tiempo desde "alerta" → "decisión" documentada
  → Target: <5 horas (ahora: 2-4 días)
```

#### Outcome 3.2: Acción Rápida

**Para:** Líder de Proceso, Director

```
HIPÓTESIS:
"Si líder detecta riesgo en <24h (alerta automática)
 → crea OM con un click desde dashboard
 → responsable ve en tiempo real
 ENTONCES: Ciclo investigación-acción de 24h (vs 2-4 semanas)"

MECANISMO:
  Antes: Indicador baja → auditor comenta → investigación manual
         → 2-4 semanas de latencia
  Ahora: Indicador baja → alerta SGIND → acción en <24h
         → "Investigación + OM + ejecutor conoce" en paralelo

MÉTRICA DE OUTCOME (Qué cambia):
  ✅ % OMs creadas en <24h de detectar incumplimiento (target 80%+)
  ✅ Días promedio "problema detectado → OM creada" (target 1 día)
  ✅ % Líderes que usan "Crear OM" desde dashboard (target 75%+)

VALIDACIÓN (Cómo se mide):
  Estadística ETL: timestamp(indicador_baja) vs timestamp(OM_crea)
  → Comparar Fase 1 vs Fase 2 vs Fase 3
  
  Encuesta: "¿Cuánto tiempo toma crear OM cuando incumple?"
  → Antes: "No sé" / "Varios días"
  → Ahora: "<1 hora después que me doy cuenta"
```

#### Outcome 3.3: Auditoría Preparada

**Para:** Especialista Calidad, Rector

```
HIPÓTESIS:
"Si auditor revisa indicador X → encuentra:
  • OM documentada con causas raíz
  • Plan de acción con responsable claro
  • Evidencias de seguimiento semanal
  • Si cerrada: resultado verificado
 ENTONCES: Auditoría encuentran 0 sorpresas, enfoque en mejora (no corrección)"

MECANISMO:
  Antes: Auditor pregunta → "No sé" (no hay documentación)
         → Hallazgo crítico, propuesta corrección
  Ahora: Auditor pregunta → Dashboard + OM + evidencias
         → Hallazgo + plan de acción + prueba de ejecución

MÉTRICA DE OUTCOME (Qué cambia):
  ✅ % Hallazgos resultados de "sorpresa" (target <10%, actualmente 60%)
  ✅ % Hallazgos donde institución ya tiene OM (target 90%+)
  ✅ Auditor dice "Estaban organizados" (confianza +)

VALIDACIÓN (Cómo se mide):
  Análisis auditoría: Hallazgos con OM vs sin OM previo
  → Correlación: Si hay OM → auditor ve menor severidad
  
  Feedback auditor post-auditoría:
  → "Institucional muestra preparación" (mejora percepción)
```

#### Outcome 3.4: Ciclo de Mejora Acelerado

**Para:** Equipo de Calidad

```
HIPÓTESIS:
"Si OM está documentada y vinculada a indicador
 → responsable sabe qué mejorar exactamente
 → progreso se ve en tiempo real
 → indicador mejora, OM se cierra
 → ciclo se repite 50% más rápido
 ENTONCES: 'Cultura de mejora continua' visible en métricas"

MECANISMO:
  Antes: OM abierta → ejecución opaca → cierre sin validación
         → "Mejora" no se verifica
  Ahora: OM abierta → estado público → indicador sube → cierre verificado feedback

MÉTRICA DE OUTCOME (Qué cambia):
  ✅ Ciclo cierre OM (días): 45 días → 20 días (target Fase 2)
  ✅ % de OMs cerradas exitosas (target 70% vs actual 40%)
  ✅ % de OMs que resultaron en mejora verificada (target 80%+)

VALIDACIÓN (Cómo se mide):
  En base de datos: timestamp(OM_abierta) - timestamp(OM_cerrada)
  + indicador_antes vs indicador_después
  
  Encuesta: "Cuando cerramos OM, sabemos por qué funcionó?"
  → Ahora: Si, datos lo confirman
```

---

### NIVEL 4: IMPACTO (Cambio en Resultados Estratégicos)

#### Impacto 4.1: Cumplimiento Institucional

```
HIPÓTESIS:
"Si decisiones son 50% + rápidas
 + alertas son 2 meses ANTES del vencimiento
 + OMs se ejecutan 2x más rápido
 + ciclo realimentación es automático
 ENTONCES: % indicadores en cumplimiento sube 10-15 puntos"

MÉTRICA DE IMPACTO (Qué resulta):
  Línea base (Fase 1): 70% indicadores en cumplimiento (700/1000)
  
  Target Fase 2 (8 sem): 75% (50 indicadores más en cumplimiento)
                         → Acciones rápidas + alertas tempranas
  
  Target Fase 3 (24 sem): 85% (150 indicadores más)
                         → Analítica + predictivo + benchmark
  
  Target 2026 cierre: 85-90%
                      → Cultura de medición sostenida

VALIDACIÓN (Cómo se mide):
  Métrica ETL mensual: 
    = SUM(indicadores en cumplimiento) / TOTAL indicadores
  
  Comparación temporal: Mes 1 → Mes 3 → Mes 6 → Mes 12
  Curva esperada: ↑ rápida en Fase 2 (automatización)
                  ↑ gradual en Fase 3 (predictivo + cultura)
  
  Causabilidad: Cambios de indicadores vinculados a OMs cerradas
  → Si OM de "Tasa Aprobación" cierra → indicador sube? ✅ Sí
  → Prueba que SGIND realmente cataliza mejora
```

#### Impacto 4.2: Acreditación & Credibilidad Externa

```
HIPÓTESIS:
"Si auditoría no encuentra sorpresas (0 hallazgos inesperados)
 + institución muestra 85%+ cumplimiento (vs 60-70% antes)
 + planes de acción son verificables y ejecutados
 ENTONCES: Acreditadores dan score +2-3% [factores específicos]"

MÉTRICA DE IMPACTO (Qué resulta):
  Línea base: Score acreditación 2025 = X%
  
  Target 2026: Score = X% + 2-3%
              (mejora atribuible a SGIND)
  
  Indicadores clave acreditación que mejorarían:
    • Factor "Gestión de la calidad" → prueba OMs documentadas
    • Factor "Seguimiento de indicadores" → prueba dashboard centralizado
    • Factor "Respuesta a hallazgos auditoria" → prueba OMs pre-auditoría

VALIDACIÓN (Cómo se mide):
  Post-auditoría 2026:
    • Comparar hallazgos 2025 vs 2026
    • ¿Menos hallazgos? → sí → SGIND contribuyó
    • ¿Hallazgos menos severos? → sí → mejor preparación
    
  Score acreditación: Before / After
    • 2025 → 2026, aumentó X%?
    • Atribuible a qué factor? (Gestión calidad + Gobernanza)
```

#### Impacto 4.3: Eficiencia Operativa Institucional

```
HIPÓTESIS:
"Si reportería pasa de 8h manual → 2h total (generación + ajustes)
 + monitoreos pasan de 10 llamadas/semana → 1 dashboard
 + OMs se crean 1 click (no form manual de 20 min)
 ENTONCES: Equipo calidad/gobernanza se reduce 40% en tiempo operativo"

MÉTRICA DE IMPACTO (Qué resulta):
  FTE ahorrados/ mes (antes): 
    • Reportería: 8h
    • Monitoreos: 10h
    • Consolidación manual: 6h
    • Total: 24h = 0.3 FTE

  FTE ahorrados/mes (después):
    • Reportería: 2h (generación + ajustes)
    • Monitoreos: 2h (anomalías específicas)
    • OMs: <1h (clic, no formas)
    • Total: 5h = 0.06 FTE
  
  AHORRO: 19 horas/mes = 0.24 FTE
  → Puede dedicarse a análisis estratégico, no administrativo

VALIDACIÓN (Cómo se mide):
  Encuesta: "¿Cuánto tiempo dedicas a SGIND?"
    • Antes: "8h reportes + 10h reuniones"
    • Ahora: "<2h revisión"
  
  Análisis de tiempos en calendario:
    • Reuniones "consolidación" reducidas?
    • Dedicación a "análisis estratégico" aumentada?
```

#### Impacto 4.4: Cultura de Gobernanza

```
HIPÓTESIS:
"Si indicadores son visibles → responsabilidad clara
 Si OMs están públicas → accountability aumenta
 Si decisiones son data-driven → confianza aumenta
 ENTONCES: Cultura institucional transita de 'compliance' a 'excelencia'"

MÉTRICA DE IMPACTO (Qué resulta):
  Indicadores blandos (encuesta):
    • % líderes que dicen "gestiono con datos" (target 75%+)
    • % que sienten "presión positiva" de transparencia (target 60%+)
    • % que consideran sistemas de gestión "útil" (target 80%+)
  
  Indicadores en comportamiento:
    • # reuniones que citan SGIND en documento (trending up)
    • # decisiones documentadas en SGIND vs email (trending SGIND)
    • # líderes de proceso que usan dashboard en su gestión

VALIDACIÓN (Cómo se mide):
  Encuesta clima Fase 1 (11 abril) vs Fase 2 (+8 sem) vs Fase 3 (+24 sem)
  
  Análisis logs usuario:
    • Uso SGIND por rol: ¿Crece o estable?
    • Hora login (durante laboral vs fuera): Pattern cambia?
  
  Análisis de decisiones:
    • Documentos de junta directiva: Top 3 fuentes info?
    • Pregunta en surveys: "¿Cómo se informó para esta decisión?"
```

---

## HIPÓTESIS CRÍTICAS DE CAMBIO

Para que SGIND genere **impacto real**, se requiere que estas hipótesis sean verdaderas:

| # | Hipótesis | Si es FALSA → Problema | Criticidad |
|---|-----------|----------------------|-|
| H1 | "Directivos usarán SGIND + tomarán decisiones con él" | SGIND es solo dashboard, sin impacto | 🔴 Crítica |
| H2 | "Líderes actuarán en <24h cuando indicador baja" | OMs se crean tarde, latencia igual | 🔴 Crítica |
| H3 | "OMs se ejecutan porque son públicas + accountable" | OMs zombie (abiertas meses sin cierre) | 🔴 Crítica |
| H4 | "Indicadores realmente suben cuando OM se ejecuta" | "Mejora" es cosmética, no real | 🔴 Crítica |
| H5 | "Auditor verá OMs pre-auditoría + dará beneficio duda" | Sin diferencia en auditoría, sigue sorpresas | 🟡 Mayor |
| H6 | "Equipo tiene capacidad para mantener SGIND" | Abandono en Fase 3, deuda técnica regresa | 🟡 Mayor |
| H7 | "<15 usuarios concurrentes máximo" | Scale > 15 requiere Redis (presupuesto) | 🟡 Mayor |
| H8 | "Data Kawak es confiable para decisiones" | Auditoría descubre inconsistencias | 🟡 Mayor |

---

## INDICADORES POR NIVEL

### Indicadores de INPUT (Recursos Disponibles)

✅ **Ya medido/validado:**
- Data Kawak: 1,000+ indicadores disponibles (disponible)
- Procesos documentados: 14 procesos, 47 subprocesos en YAML (ready)
- Equipo: 1.5 FTE asignado (confirmado)
- Infraestructura: PostgreSQL, Streamlit funcionando (ready)

### Indicadores de OUTPUT (Qué entega el sistema)

📊 **Métrica de Seguimiento (Fase 2):**

| KPI | Baseline | Target Sem 4 | Target Sem 8 |
|-----|----------|-------------|-------------|
| Dashboard uptime | - | 99%+ | 99.5%+ |
| Alertas generadas/mes | 0 | 50+ | 80+ |
| OMs en sistema | 0 | 100+ | 150+ |
| Reportes auto-gen/mes | 0 | 3+ | 4 |
| Usuarios activos | 0 | 15+ | 25+ |

### Indicadores de OUTCOME (Cambio en Comportamiento)

📈 **Métrica de Seguimiento (Fase 2 - 3):**

| KPI | Baseline | Target Sem 8 | Target Sem 24 |
|-----|----------|-------------|--------------|
| Tiempo decisión | 48h | <5h | <2h |
| Latencia OM | 2-4 sem | 1 sem | <24h |
| % OMs cerradas exitosas | 40% | 60% | 75%+ |
| Auditoría sorpresas | 12-15 | 8-10 | <5 |
| Índice confianza (encuesta) | - | 60% | 80%+ |

### Indicadores de IMPACTO (Cambio en Resultados)

🎯 **Métrica de Seguimiento (Fase 3 - Cierre 2026):**

| KPI | Baseline | Target 2026 |
|-----|----------|-----------|
| % Cumplimiento indicadores | 70% | 85%+ |
| Acreditación score | X% | X%+2-3 |
| Eficiencia (FTE ahorrado) | - | +0.24 FTE |
| Cultura data-driven (encuesta) | - | 75%+ |

---

## ASUNCIONES CLAVE

Estas asunciones **deben estar explícitas** para detectar si la hipótesis se quiebra:

| Asunción | Validación | Riesgo |
|----------|-----------|---------|
| **Directivos usarán SGIND** | Encuesta post-Fase 2: "¿Lo usas?" | Si <50% → abandono |
| **Decisiones cambiarán** | Análisis de docs post-Junta: "Fuente info?" | Si <30% citan SGIND → fracaso |
| **OMs se ejecutarán** | Indicador mejora después de OM? | Si no correlaciona → OMs fake |
| **Data Kawak es confiable** | Validación con 3 auditores externos | Si discrepancias → auditoría falla |
| **Equipo continuará** | Encuesta + planning post-Fase 2 | Si equipo se va → sistema muere |
| **<15 concurrent users** | Load test real (Fase 2 finales) | Si >50 → necesita reinversión |

---

## RIESGOS & MITIGACIÓN

### Riesgo R1: Dashboard se vuelve "vanity metric"

**Descripción:** SGIND es bonito, datos están, pero nadie actúa. OMs se crean pero no se cierran.

**Probabilidad:** 🟡 Media  
**Impacto:** 🔴 Alto (inversión sin ROI)

**Mitigación:**
```
1. Fase 2: Crear regla = "OMs abiertas >30 días → Alerta a jefe"
2. Fase 2: Dashboard tiene pestaña "OMs vencidas" (rojo = spotlight negativa)
3. Fase 3: Métrica de bonificación: "% OMs cerradas" entra en evaluación líder
4. Measurement: Cada mes, medir:
   - OMs creadas vs OMs cerradas (ratio)
   - Si ratio estancado → investigar bloqueador
```

---

### Riesgo R2: Auditoría no reconoce el esfuerzo

**Descripción:** A pesar de SGIND documentado, auditor sigue encontrando los mismos hallazgos.

**Probabilidad:** 🟡 Media  
**Impacto:** 🔴 Alto (validación externa)

**Mitigación:**
```
1. Fase 2: Pre-auditoría interna con auditor externo consultores
   - Validar que OMs son "suficientemente documentadas"
   - Ajustar antes de auditoría real
   
2. Fase 3: Pack auditoría preparado
   - "Auditor, aquí están nuestros indicadores, OMs, planes"
   - Proactivo, no reactivo
   
3. Measurement: Comparar auditoría 2025 vs 2026
   - Si halazgos <20%, SGIND aportó
   - Si hallazgos ≥80%, replantear
```

---

### Riesgo R3: Indicadores no mejoran a pesar de OMs

**Descripción:** OMs están, se ejecutan, pero indicador no sube. ("¿Para qué entonces?")

**Probabilidad:** 🟠 Media-Baja  
**Impacto:** 🔴 Alto (propuesta de valor se quiebra)

**Mitigación:**
```
1. Fase 2: Diagnóstico raíz de OMs que no resultaron
   - ¿Acción fue insuficiente? → Necesita +recursos
   - ¿Causa raíz fue mal identificada? → OM no era la solución
   - ¿Indicador tiene lag (demora resultados)? → Esperar más tiempo
   
2. Fase 3: Análisis causal
   - Técnica: Regression análisis → qué acciones correlacionan con mejora
   - Seleccionar OMs que funcionaron → documentar como "buenas prácticas"
   
3. Measurement: 
   - Indicador: % de OMs "exitosas" (indicador mejora post-cierre)
   - Target: 70%+ (aceptable 3/10 que no correlacionan)
```

---

### Riesgo R4: Equipo se agota en Fase 2, abandona en Fase 3

**Descripción:** 8 semanas de sprint intenso → burnout → Team wants out

**Probabilidad:** 🟠 Media-Baja  
**Impacto:** 🔴 Alto (sistema muere)

**Mitigación:**
```
1. Estructura Fase 2: 1 semana buffer cada 4 semanas
   - 4 sem sprint → 1 sem "limpieza" + documentación + descanso
   
2. Roles claro:
   - No todos de todo. Especialista B = only backend, no "todo"
   
3. Fase 3 = "modo mantenimiento"
   - Fase 2 es 100% construcción
   - Fase 3 = 50% mantenimiento + 50% nuevas features
   
4. Compensación:
   - Reconocimiento público (bono, mención)
   - Oportunidades desarrollo (ej: ML eng puede trabajar predictivo)
```

---

### Riesgo R5: Load real supera "< 15 concurrent users"

**Descripción:** Mayo 2026, escuela agrega 50 usuarios simultáneamente → sistema cae. Necesita Redis + $$$.

**Probabilidad:** 🟡 Media  
**Impacto:** 🟡 Media (recoverable con inversión)

**Mitigación:**
```
1. Fase 2, Semana 6: Load test con 30 usuarios simultáneos
   - Simular + antecipar
   
2. Si falla:
   - Opción A: Caché optimización local (rápido, 8h)
   - Opción B: Redis Cloud ($30/mes, 16h implementación)
   - Decision tree: Si >20 users → necesita B
   
3. Contingency: Ya está budgeted en Fase 3 (opcional)
```

---

## CONCLUSIÓN: CADENA CAUSAL

```
┌─────────────────────────────────────────────────────────────────┐
│ Si SGIND existe                                                  │
│ ↓                                                                │
│ Entonces directivo ve datos → decide rápido                     │
│ ↓                                                                │
│ Y líder detecta riesgo → crea OM → ejecuta → indicador sube    │
│ ↓                                                                │
│ Y auditor ve OMs + indicadores → confía                         │
│ ↓                                                                │
│ RESULTANDO EN: Cumplimiento ↑ | Acreditación ↑ | Confianza ↑    │
│                                                                  │
│ Esta cadena es VÁLIDA si:                                       │
│ • Equipos usan el sistema (adoption >50%)                       │
│ • OMs se ejecutan (ratio cierre >60%)                           │
│ • Indicadores mejoran post-OM (correlación >70%)                │
│ • Auditoría reconoce preparación (hallazgos <50% de 2025)       │
│                                                                  │
│ Si alguno falla, cadena se quiebra → replantear hipótesis       │
└─────────────────────────────────────────────────────────────────┘
```

---

**Próximo Paso:** [Diagnosticar Efectividad Actual](DIAGNOSTICO_EFECTIVIDAD.md) - Validar qué hipótesis son verdaderas en datos reales.
