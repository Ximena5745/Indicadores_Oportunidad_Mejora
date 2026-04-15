# Fase 3 — Wireframes y diseño de dashboards (Nivel 1/2/3)

Objetivo: especificar la estructura visual mínima para el prototipo Nivel 3 y escalado a Niveles 2 y 1.

## Principios de diseño
- Jerarquía informativa: métricas críticas arriba, detalle bajo demanda.
- Acción directa: cada alerta tiene botón sugerido para `Abrir OM` o `Validar dato`.
- Consistencia: mismo header, selectores de periodo/unidad y semaforización.

## Barra superior (persistente)
- Selector `Periodo` (Mes/Año/Proyección)
- Selector `Unidad Organizativa`
- Buscador `Ir a indicador`

## Layout Nivel 3 — Operativo (prototipo)
- Header: Título + 3 KPIs (Indicadores actualizados %, Indicadores en alerta %, TMO OM)
- Columna izquierda (40%): Kanban (Actualizado / Pendiente / Alerta)
- Columna derecha (60%): Tabla interactiva de indicadores + botón `Validar` por fila
- Footer: Log de ingesta reciente y botón `Reportar incidencia`

Interacciones clave:
- Click en indicador → panel lateral con histórico (sparklines) y acciones (abrir OM, marcar revisado).
- Filtros persistentes: periodo, unidad, proceso.

## Layout Nivel 2 — Gestión
- Header: Scorecard con 6 KPIs (cumplimiento por proceso, brecha promedio, tasa cierre OM, etc.)
- Panel central: Árbol de objetivos (treemap) con drill-down a indicadores
- Panel derecho: Comparativa vs benchmark (barras apiladas)

## Layout Nivel 1 — Estratégico
- Scorecard ejecutivo (círculos y semáforos) + Índice Salud Institucional
- Mapa CMI (4 perspectivas) con indicator hover y enlaces a Nivel 2
- Proyección en línea con bandas de confianza (línea + bandas 80%)

## Componentes técnicos y archivos relacionados
- Prototipo Nivel 3: `scripts/prototipo_nivel3.py`
- Plantillas gráficas: `scripts/plot_templates.py` (funciones reutilizables Plotly)
- Mapeo indicadores: `data/output/artifacts/indicadores_cmi_mapping_v2.csv`

## Siguientes pasos de diseño
1. Iterar el mockup del Kanban con usuarios operativos (1 sesión de 30 min).
2. Definir 6 KPIs del Scorecard Nivel 2 con datos reales.
3. Implementar templates Plotly y sustituir componentes estáticos por figuras dinámicas.

Fecha: 2026-04-07
Autor: Equipo técnico