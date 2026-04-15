# Fase 3 — Priorización de entregables

**Objetivo:** Priorizar los entregables de la Fase 3 para generar impacto rápido y medible.

## Resumen de priorización (orden recomendado)

1. **Prioridad Alta — Nivel 3: Operativo y Calidad**
   - Entregables: Kanban de Indicadores; Detalle de OM y Acciones; Validación de datos en tiempo real; Trazabilidad Hallazgo→Indicador→Acción.
   - Justificación: Impacto operativo inmediato, ciclo de retroalimentación corto, permite validar datos y procesos.
   - Estimación: 1–2 sprints (2–4 semanas).

2. **Prioridad Media — Nivel 2: Gestión y Cumplimiento**
   - Entregables: Árbol de Objetivos (drill-down); Comparativa vs benchmark; Evolución de brechas; Matriz de Acreditación.
   - Justificación: Soporta decisiones tácticas y requiere consolidación y enriquecimiento de datos.
   - Estimación: 2–3 sprints (4–8 semanas).

3. **Prioridad Alta-Largo Plazo — Nivel 1: CMI Estratégico**
   - Entregables: Scorecard estratégico; Mapa CMI; Índice Salud Institucional; Línea de tiempo predictiva.
   - Justificación: Alto valor estratégico pero requiere modelos y validaciones; secuenciar después de pruebas operativas.
   - Estimación: 3–6 sprints (6–12 semanas) + integración predictiva.

## Recomendaciones técnicas

- Stack recomendado para prototipos: Streamlit + Plotly (rápido de iterar y desplegar). 
- Origen de datos: usar artefactos consolidados en `data/output/artifacts/`.
- UX: Priorizar legibilidad y acciones directas (máx. 3 clics para detalles); barra de contexto global.
- Semaforización: aplicar paleta y rangos definidos en el plan maestro.

## Sprint sugerido (Sprint 1 — 2 semanas)

- Objetivo: Entregar prototipo funcional Nivel 3 (Kanban + lista OM + filtros básicos).
- Entregables Sprint 1: App Streamlit con Kanban; endpoint local para cargar artefactos; validaciones visuales básicas.
- Revisión: Demo con usuarios operativos al cierre del sprint.

## Próximos pasos inmediatos

1. Completar `Definir KPIs por nivel` (en progreso). 
2. Prototipar Nivel 3 (Sprint 1). 
3. Revisión con usuarios clave y ajustes.

## Referencias

- [Plan_Transformacion_SGIND.md](Plan_Transformacion_SGIND.md)

Fecha: 2026-04-07
Autor: Equipo técnico
