# Fase 3 — Wireframes detallados y especificaciones

Objetivo: entregar wireframes detallados, criterios de aceptación y especificaciones para implementar los dashboards Nivel 3 (operativo), Nivel 2 (gestión) y Nivel 1 (estratégico).

---

**Resumen rápido**
- Formato: prototipo web (Streamlit) con componentes Plotly interactivos.
- Principio: mostrar lo crítico primero, detalles bajo demanda, máximo 3 clics para acción.
- Entregable: wireframes funcionales para Nivel 3, Nivel 2 y Nivel 1, lista de componentes, flujos de interacción y criterios de aceptación.

---

## Especificaciones comunes (header / layout)

- **Barra superior (persistente)**
  - Logo + título del dashboard.
  - Selectores globales: `Periodo` (Mes/Año/Proyección), `Unidad Organizativa`, `Buscar indicador`.
  - Botones de acción: `Exportar CSV`, `Exportar PPTX`, `Reportar incidencia`.

- **Menú lateral (jerarquía)**
  - Secciones: Estrategia, Acreditación, Procesos, Mejoramiento, Analítica avanzada, Alertas.
  - Contexto: breadcrumb dinámico que muestra ruta (ej. Estrategia > PDI > Objetivo X > Indicador Y).

- **Principios UX**
  - Visualización responsiva; elementos clave arriba; espacio para acciones (abrir OM, validar dato).
  - Semaforización con paleta definida en `Plan_Transformacion_SGIND.md`.

---

## Nivel 3 — Operativo (wireframe detallado)

Layout propuesto (desktop)
- Header (full width)
- Row 1: 3 KPIs clave (Indicadores actualizados %, Indicadores en Alerta %, Tiempo medio resolución OM)
- Row 2: Izquierda (40%): Kanban visual; Derecha (60%): Tabla interactiva con búsqueda/ordenamiento y acciones por fila
- Row 3: Panel inferior: Log de ingesta y actividad reciente

Componentes y comportamiento
- **Kanban**: columnas Actualizado / Pendiente / Alerta; cada tarjeta muestra `Id`, `Indicador` y último `Cumplimiento`; arrastrable opcional (MVP: clic para cambiar estado)
- **Tabla interactiva**: columnas mínimas: `Id`, `Indicador`, `Linea`, `Periodicidad`, `Meta`, `Último cumplimiento (%)`, `Status`, `Acciones`.
  - `Acciones`: botones `Abrir OM`, `Validar`, `Ver histórico` (expander). Exportar fila.
  - Inline sparklines (columna compacta) o expander con gráfico completo.
- **Detalle lateral**: al seleccionar fila, abrir panel derecho con histórico, comentarios, evidencias y botón `Crear OM`.

Criterios de aceptación Nivel 3
- El Kanban muestra conteos correctos según mapeo `indicadores_cmi_mapping_v2.csv` y `Resultados Consolidados.xlsx`.
- Al clicar en `Ver histórico` aparece un sparkline con la serie de `Cumplimiento` ordenada por fecha.
- Los filtros por periodo y periodicidad actualizan la tabla y el Kanban en <1s (dato local).

---

## Nivel 2 — Gestión (wireframe detallado)

Layout propuesto
- Header con 6 KPIs resumidos (Scorecard)
- Panel central: Treemap / Árbol de objetivos (drill-down)
- Panel derecho: Comparativa vs benchmark (barras apiladas) y evolución de brechas

Comportamiento
- Drill-down en treemap: clic en un bloque abre desglose por procesos y listados de indicadores (navegación hacia Nivel 3)
- Benchmarks: seleccionar universidad par para comparar; mostrar delta y semaforización

Criterios de aceptación Nivel 2
- Drill-down funcional entre treemap y tabla de indicadores asociados.
- Benchmark carga dataset de referencias y muestra comparativa con valores y porcentaje de diferencia.

---

## Nivel 1 — Estratégico (wireframe detallado)

Layout propuesto
- Scorecard ejecutivo con 6 métricas y mapa CMI (4 perspectivas)
- Panel central: Índice Salud Institucional (0-100) con semáforo y comentarios
- Panel inferior: Proyección y línea con bandas de confianza

Comportamiento
- Hover sobre mapa CMI muestra KPIs agregados por perspectiva y enlace a Nivel 2.
- Línea de tiempo proyectiva muestra bandas (80% por defecto) y opción para cambiar ventana/prefijo.

Criterios de aceptación Nivel 1
- Scorecard muestra KPIs clave con fuente de datos y versión.
- Proyección usa datos consolidados y muestra bandas con multiplicador configurable.

---

## Mobile / Responsiveness

- Mobile view: priorizar Nivel 3 (operativo) con KPIs y lista comprimida; Kanban en formato swipe o accordion.
- Evitar tablas densas en mobile; usar tarjetas condensadas con botón `Ver detalle`.

---

## Accesibilidad & estándares

- Contraste de colores según WCAG AA para texto y semáforos.
- Todos los gráficos deben poder exportarse como CSV y PNG.
- Soporte para teclado y labels ARIA en componentes interactivos (botones, selectores).

---

## Flujos de interacción prioritarios (user stories)

1. Como analista, quiero ver en un solo view los indicadores en alerta para priorizar correcciones.
2. Como coordinador, quiero abrir un indicador y crear una OM vinculada con evidencia.
3. Como director, quiero ver el Scorecard trimestral y descargar la slide en PPTX.

Para cada user story se definen tests manuales de aceptación (lista aparte en `docs/fase3_guia_uso.md`).

---

## Entregables y estimaciones (MVP)

- Wireframes detallados (este documento). — listo.
- Prototipo Nivel 3 funcional (Streamlit + Plotly): 2 sprints (4 semanas) — ya iniciado.
- Integración Nivel 2 (treemap + benchmarks): 2–3 sprints.
- Panel ejecutivo Nivel 1 + proyecciones: 3 sprints.

---

## Siguientes pasos inmediatos

1. Revisión de estos wireframes con 2–3 usuarios operativos (30 min) — recoger feedback UX.
2. Ajustes y creación de mockups de alta fidelidad (Figma o Miro) si se requiere.
3. Implementación iterativa: completar backlog y preparar demo para la revisión de sprint.

Fecha: 2026-04-07
Autor: Equipo técnico
