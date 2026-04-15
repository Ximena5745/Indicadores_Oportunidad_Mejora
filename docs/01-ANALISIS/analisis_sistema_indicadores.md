# Análisis y Optimización del Sistema de Medición, Seguimiento y Mejora

> Documento generado automáticamente. Incluye todas las secciones: propósito, capas, arquitectura, reglas, modelo de datos, reportes, análisis, alertas, soporte a decisión, técnica, gobernanza, diagnóstico, recomendaciones y plan de trabajo.

---

## 📊 PARTE A: CAPA ESTRATÉGICA (USO DEL DATO)

### 1. PROPÓSITO DEL DASHBOARD

- Habilitar decisiones estratégicas, tácticas, operativas y correctivas basadas en resultados de indicadores ya medidos.
- Optimizar el uso de la información para priorización, gestión de OM, seguimiento de acciones y alertas tempranas.

### 2. MAPA DE USO DE LA INFORMACIÓN

| Usuario                | Decisión                        | Información requerida         | Frecuencia | Nivel de detalle |
|------------------------|---------------------------------|------------------------------|------------|------------------|
| Directivos             | Priorización estratégica        | KPIs, tendencias, alertas    | Mensual    | Alto             |
| Coordinadores/Analistas| Gestión de OM y acciones        | Indicadores en riesgo, OM    | Semanal    | Medio            |
| Responsables de proceso| Acciones correctivas            | Histórico, alertas, detalles | Variable   | Bajo             |

- Problemas actuales: retrasos por procesamiento manual, sobrecarga de información, falta de insights proactivos.

---

## 📈 PARTE B: CAPA DE PROCESAMIENTO Y CONSOLIDACIÓN (CORE)

### 3. ARQUITECTURA DEL FLUJO DE DATOS (POST-INDICADORES)

```
[Fuentes Excel/API]
      │
      ▼
[consolidar_api.py]  ← Paso 1: Unifica fuentes Kawak + API
      │
      ▼
[actualizar_consolidado.py]  ← Paso 2: ETL principal (legacy)
      │
      ▼
[generar_reporte.py]  ← Paso 3: Métricas, QA, artefactos
      │
      ▼
[artifacts/outputs]   ← JSON, CSV, logs, reportes
      │
      ▼
[Dashboard Streamlit] ← Visualización y análisis
```

**Propuesta:**  
Migrar el paso 2 a `consolidation/main.py` (framework modular), manteniendo la orquestación con `run_pipeline.py` y mejorando QA en `generar_reporte.py`.

### 4. REGLAS DE NEGOCIO PARA ACTUALIZACIÓN DE DATOS

- Validación: nulos en campos críticos, duplicados por LLAVE, cumplimiento fuera de 0-200%, fechas incoherentes.
- Transformación: agregaciones por periodo, normalización de IDs, ajuste por año vencido, topes 100%.
- Consolidación: integración multi-fuente, jerarquías (proceso→área), versionamiento por timestamp.
- Actualización: pipeline automático mensual (`run_pipeline.py`), control de cambios en artifacts/logs.

### 5. MODELO DE DATOS PARA REPORTES CONSOLIDADOS

- Tablas históricas (ID, Fecha, Meta, Ejecución, Cumplimiento, Categoría, LLAVE), OM y acciones vinculadas.
- Relaciones 1:N entre indicadores y OM/acciones.
- Versionado por ejecución, trazabilidad en artifacts.

### 6. GENERACIÓN DE REPORTES CONSOLIDADOS

- Tipos: ejecutivos (KPIs, alertas), operativos (detalle por proceso), comparativos (vs periodo anterior), históricos (series completas).
- Niveles de agregación: por periodo, unidad, indicador.
- Automatización: `generar_reporte.py` produce JSON/CSV con métricas, nulos, tendencias, alertas.

---

## 📊 PARTE C: CAPA ANALÍTICA (USO PARA DECISIÓN)

### 7. MODELO DE ANÁLISIS

- Tendencias: evolución histórica, % en peligro/cumplimiento.
- Comparación vs metas: gap análisis, semáforos.
- Desviaciones: cambios bruscos, outliers.
- Segmentación: por área, proceso, tipo de indicador.

### 8. SISTEMA DE ALERTAS E INSIGHTS

- Alertas automáticas: thresholds configurables (ej. <80% peligro, >105% sobrecumplimiento).
- Detección de anomalías: outliers, duplicados, nulos excesivos.
- Insights accionables: reglas en `generar_reporte.py` para resaltar indicadores críticos.
- Clasificación: 🔴 Crítico, 🟡 Atención, 🟢 Normal.

### 9. SOPORTE A TOMA DE DECISIONES

- Decisiones soportadas: priorización, apertura/cierre de OM, ajuste de metas, escalamiento de problemas.
- Información presentada: KPIs, alertas, tendencias, recomendaciones.
- Acciones derivadas: notificaciones, asignación de responsables, seguimiento.

---

## ⚙️ PARTE D: CAPA TÉCNICA

### 10. ARQUITECTURA TECNOLÓGICA

- ETL/ELT: scripts Python (`actualizar_consolidado.py`, `consolidation/`), Pandas, openpyxl.
- Base de datos: Excel outputs, SQLite/PostgreSQL opcional.
- Visualización: Streamlit, Plotly.
- Automatización: GitHub Actions, cron, logs y artefactos.
- Framework moderno: modularización en `consolidation/` (extractors, orchestrator, loaders).

### 11. GOBERNANZA DE DATOS

- Roles: Data Owner (reglas), Data Steward (operación), Data Consumer (decisión), Admin (infraestructura).
- Control de calidad: validaciones automáticas, artefactos QA, logs.
- Seguridad: acceso controlado a outputs, auditoría en artifacts.

---

## 🔄 PARTE E: EVALUACIÓN Y MEJORA

### 12. DIAGNÓSTICO DEL SISTEMA ACTUAL

| Problema                  | Severidad | Ubicación                       |
|---------------------------|-----------|---------------------------------|
| Duplicación de código     | 🔴        | ETL legacy vs consolidation/    |
| Procesamiento fila a fila | 🔴        | actualizar_consolidado.py       |
| Dependencia de Excel      | 🔴        | Fórmulas, outputs               |
| QA limitado               | 🟡        | generar_reporte.py, pipeline    |
| Buenas prácticas          | 🟢        | Configuración centralizada, logs|

### 13. RECOMENDACIONES PRIORIZADAS

| Acción                                    | Plazo      | Impacto   |
|--------------------------------------------|------------|-----------|
| Completar migración a `consolidation/`     | 1 mes      | 🔴        |
| Vectorizar cálculos en ETL                 | 2 semanas  | 🟢        |
| Mejorar QA en `generar_reporte.py`         | 2 semanas  | 🟡        |
| Implementar notificaciones automáticas     | 1 mes      | 🟡        |
| Documentar reglas y flujos                 | 1 mes      | 🟢        |

---

## 🛠️ RECOMENDACIONES DETALLADAS PARA SCRIPTS Y REPORTING

### 1. Diagrama de Flujo de Scripts (Pipeline Actual y Propuesto)

```
[Fuentes Excel/API]
      │
      ▼
[consolidar_api.py]  ← Paso 1: Unifica fuentes Kawak + API
      │
      ▼
[actualizar_consolidado.py]  ← Paso 2: ETL principal (legacy)
      │
      ▼
[generar_reporte.py]  ← Paso 3: Métricas, QA, artefactos
      │
      ▼
[artifacts/outputs]   ← JSON, CSV, logs, reportes
      │
      ▼
[Dashboard Streamlit] ← Visualización y análisis
```

**Propuesta:**  
Migrar el paso 2 a `consolidation/main.py` (framework modular), manteniendo la orquestación con `run_pipeline.py` y mejorando QA en `generar_reporte.py`.

---

### 2. Tabla de Validaciones Automáticas (QA)

| Validación                      | Script                | Acción si falla         | Severidad |
|----------------------------------|-----------------------|------------------------|-----------|
| Nulos en campos críticos         | generar_reporte.py    | Flag en reporte        | 🟡        |
| Duplicados por LLAVE             | generar_reporte.py    | Alerta crítica         | 🔴        |
| Cumplimiento fuera de 0-200%     | generar_reporte.py    | Flag de revisión       | 🟡        |
| Fechas incoherentes              | generar_reporte.py    | Alerta en QA           | 🟡        |
| Outliers (z-score > 3)           | generar_reporte.py    | Alerta de anomalía     | 🟡        |
| Hojas/outputs faltantes          | run_pipeline.py       | Detener pipeline       | 🔴        |
| Error en escritura de Excel      | actualizar_consolidado.py | Rollback/backup   | 🔴        |

---

### 3. Acciones para la Migración y Refactorización

**Corto Plazo (1-2 semanas):**
- Agregar validaciones de calidad y alertas automáticas en `generar_reporte.py`.
- Implementar sistema de reintentos y notificaciones en `run_pipeline.py`.
- Documentar reglas de negocio y QA en `docs/`.

**Mediano Plazo (1 mes):**
- Migrar lógica de ETL a `consolidation/` (builders, extractors, writers).
- Vectorizar cálculos y eliminar dependencias de fórmulas Excel.
- Integrar validaciones post-ETL y QA en el pipeline.

**Largo Plazo (2-3 meses):**
- Completar integración del framework moderno y activar feature flag.
- Deprecar/eliminar scripts legacy (`etl/`).
- Ampliar cobertura de tests unitarios y automatizados.

---

### 4. Entregables Sugeridos

- **Reporte Ejecutivo Markdown** (generado por script):
  - Resumen de KPIs, % en peligro/cumplimiento, tendencias, alertas y recomendaciones.
- **Artefactos QA**:
  - JSON/CSV con métricas, validaciones y alertas.
- **Documentación Técnica**:
  - Diagramas de flujo, reglas de negocio, ejemplos de validaciones.
- **Tablas de roles y responsabilidades**:
  - Para gobernanza y operación del pipeline.

---

### 5. Indicadores de Éxito

| Indicador                        | Meta         | Medición                |
|----------------------------------|-------------|------------------------|
| Tiempo de ejecución ETL          | -40%        | Logs de pipeline       |
| Corridas con reporte QA          | 100%        | Artifacts generados    |
| Alertas de calidad detectadas    | >0          | Conteo en reportes     |
| Cobertura de tests               | ≥70%        | pytest coverage        |
| Incidencias por inconsistencias  | -50%        | Tickets reportados     |

---

¿Te gustaría que detalle ejemplos de código para validaciones automáticas, plantillas de reportes ejecutivos, o un plan de trabajo para la migración? ¿O prefieres un entregable visual (diagrama, tabla) listo para presentación?
