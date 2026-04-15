# Fase 3 — Kickoff y plan inicial (Analítica descriptiva, diagnóstica y visualización avanzada)

Objetivo: arrancar la Fase 3 entregando un MVP operativo (Nivel 3) y preparar backlog para Niveles 2 y 1.

Duración sprint inicial: 2 semanas

Sprint 1 — Objetivo
- Entregar prototipo Nivel 3 funcional y probado con datos consolidados: Kanban, tabla con sparklines, filtros, export CSV/PPTX.

Backlog priorizado (Sprint 1)
1. Validar mapeo `Indicadores por CMI.xlsx` → `indicadores_cmi_mapping_v2.csv` (completado).
2. Ejecutar `scripts/integrate_consolidado.py` y verificar CSVs generados (timeseries + latest).
3. Ajustar umbrales y parámetros por defecto según responsable de datos.
4. Demo interna con 2–3 usuarios operativos (30 min) — recoger feedback UX/funcional.
5. Corregir observaciones y desplegar versión estable del prototipo en entorno de pruebas.

Entregables Sprint 1
- `scripts/prototipo_nivel3.py` (MVP interactivo). 
- CSVs normalizados: `data/output/analytics/resultados_consolidados_timeseries.csv` y `data/output/artifacts/resultados_consolidados_latest.csv`.
- Documentación corta de uso: `docs/fase3_guia_uso.md`.

Agenda para la demo de revisión con usuarios (30 min)
- 0–2 min: Objetivo de la demo.
- 2–10 min: Tour rápido del prototipo (Kanban, filtros, detalle y sparklines, export).
- 10–18 min: Casos de uso — usuarios prueban filtros y verificación de 3 indicadores críticos.
- 18–25 min: Recoger feedback: problemas de comprensión, datos faltantes, requests.
- 25–30 min: Próximos pasos y responsables.

Criterios de aceptación (definition of done)
- Kanban y tabla muestran correctamente el estado calculado desde `Cumplimiento` del consolidado.
- Sparklines muestran series históricas por indicador.
- Export CSV/PPTX funciona para datos filtrados.
- Feedback crítico recogido y plan de corrección acordado.

Responsables sugeridos
- Líder técnico: preparar demo y ejecutar integración (`scripts/integrate_consolidado.py`).
- Analista de datos: validar mapeo y revisar indicadores críticos.
- Usuario operativo (2 personas): validar usabilidad y datos.

Pasos inmediatos (esta tarea)
1. Ejecutar `python scripts/integrate_consolidado.py` y verificar outputs.
2. Ejecutar `streamlit run scripts/prototipo_nivel3.py` y validar la vista Nivel 3.
3. Agendar demo (sugerencia: dentro de 3 días hábiles).

Notas
- Archivos y rutas relevantes: `data/raw/Indicadores por CMI.xlsx`, `data/output/artifacts/indicadores_cmi_mapping_v2.csv`, `data/output/Resultados Consolidados.xlsx`, `scripts/prototipo_nivel3.py`.

Fecha inicio Fase 3: 2026-04-07
