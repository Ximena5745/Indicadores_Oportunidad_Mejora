Interfaz Visual

Actúa como un arquitecto senior de producto, UX/UI designer y desarrollador full stack especializado en dashboards analíticos institucionales para educación superior.

Necesito que diseñes y describas con máximo detalle un módulo llamado “Inicio estratégico” para un “Sistema de Indicadores” del Politécnico Grancolombiano, listo para implementarse en GitHub Copilot con Python + Streamlit + Plotly.

Tu objetivo NO es responder de forma general. Tu objetivo es producir una especificación funcional, visual, técnica y de datos completamente accionable, pensada para convertirse después en código real dentro de un proyecto Streamlit modular.

Quiero que diseñes el módulo replicando la lógica y la sofisticación de un dashboard ejecutivo moderno con IA, analítica estratégica, navegación jerárquica, indicadores semafóricos, visualizaciones interactivas, modales por indicador y componentes reutilizables.

---

# INSTRUCCIONES CRÍTICAS DE RESPUESTA

1. Responde en español.
2. Usa formato Markdown.
3. Estructura la respuesta con títulos, subtítulos, listas y bloques muy claros.
4. No hagas un resumen. Entrega una especificación exhaustiva.
5. Describe cada componente desde cuatro perspectivas:
   - propósito funcional,
   - comportamiento UX/UI,
   - datos necesarios,
   - recomendación técnica para implementarlo en Streamlit.
6. Cuando describas una visualización, especifica:
   - tipo de gráfica,
   - variables de entrada,
   - interacción esperada,
   - colores,
   - estados,
   - filtros,
   - drill-down,
   - tooltip,
   - y uso ejecutivo.
7. Además de la especificación, al final entrega:
   - arquitectura técnica sugerida,
   - árbol de carpetas,
   - componentes Streamlit,
   - organización del estado,
   - estrategia de datos mock,
   - y plan para MVP.

---

# 1) OBJETIVO DEL MÓDULO

Diseña el módulo principal “Inicio estratégico”, que funcionará como pantalla ejecutiva del Sistema de Indicadores institucional.

Debe presentar una visión de alto nivel de:
- estado general de indicadores,
- cumplimiento institucional,
- riesgo predictivo,
- alertas inteligentes,
- desempeño por proceso,
- avance estratégico,
- calidad del pipeline,
- observaciones derivadas de auditoría,
- y acciones sugeridas por rol.

Debe servir tanto para lectura ejecutiva rápida como para navegación detallada por indicador, proceso, auditoría y acción de mejora.

---

# 2) ESTILO VISUAL Y LENGUAJE DE INTERFAZ

Quiero una interfaz:
- ejecutiva,
- moderna,
- limpia,
- sobria,
- altamente legible,
- con jerarquía visual clara,
- orientada a toma de decisiones,
- con alta densidad de información controlada,
- pero sin saturar la pantalla.

## Estética general
La interfaz debe mezclar:
- sidebar oscura institucional,
- colores corporativos,
- y gráficos interactivos con animaciones suaves.

## Tipografía sugerida
- Títulos: Manrope o equivalente sans-serif de alto peso visual.
- Texto de interfaz y cuerpo: Inter o equivalente.
- Títulos de secciones: semibold o bold.
- KPIs: extra bold o bold.
- Labels secundarios: uppercase, tracking leve, tamaño pequeño.

## Densidad visual
- Sidebar compacta pero clara.
- Cards con suficiente padding.
- Espaciado vertical consistente entre secciones.
- Máximo foco en escaneo rápido.
- Los datos críticos deben verse sin scroll excesivo.

---

# 3) PALETA DE COLORES DETALLADA

Define y utiliza esta paleta base como design system del módulo:

## Base institucional
- Azul primario profundo: #04122e
- Azul contenedor / sidebar activa: #1a2744
- Azul secundario: #325f99
- Azul claro soporte: #93bdfd
- Fondo general: #f8f9fa
- Superficie principal: #ffffff
- Superficie secundaria: #edeeef
- Borde suave: #c5c6ce
- Texto principal: #191c1d
- Texto secundario: #45464d

## Colores de IA y analítica
- Índigo / IA primaria: #6200ea
- Lila de apoyo: #8a82e9
- Tercero suave IA: #e4dfff
- Cian analítico / información: #00b8d4
- Coral destacado: #ff7043

## Colores semafóricos
- Peligro: #ff3b30
- Alerta: #ffab00
- Cumplimiento: #00c853
- Sobrecumplimiento / excelencia: #00b8d4
- Estado neutro / pendiente: #75777e

## Reglas de uso
- Sidebar: azul profundo.
- Elemento activo sidebar: azul contenedor + acento lila.
- KPIs: blanco con borde por estado.
- Banner IA: gradiente entre índigo, azul secundario y cian.
- Alertas críticas: rojo.
- Alertas medias: ámbar.
- Confirmaciones / cumplimiento: verde.
- Módulos IA: lila / índigo.
- Información técnica / sync / pipeline: cian o azul.

Incluye recomendaciones de:
- contraste,
- accesibilidad,
- hover,
- disabled,
- active,
- badges,
- bordes,
- fondos,
- chips,
- tooltips.

---

# 4) ESTRUCTURA GENERAL DEL LAYOUT

Diseña un layout con dos grandes zonas:

## A. Sidebar izquierda fija

Debe incluir:

### Encabezado / logo
- Título: “Sistema de Indicadores”
- Subtítulo: “Politécnico Grancolombiano · v2.0 Estratégico”

### Sección “Dashboard”
- Opción activa: “Inicio estratégico”

### Sección “Seguimiento”
- “Seg. de reportes”
- “Reporte cumplimiento”
- “Gestión de OM”
- “Tablero operativo”

### Sección “Analítica IA”
- “Predicción IRIP”
- “Detector anomalías”
- “Coherencia metas”
- “Eficiencia OM (SEAC)”

### Sección “Estratégico”
- “CMI Estratégico”
- “Indicadores acreditación”
- “Indicadores Plan de mejoramiento”
- “Plan de mejoramiento”

### Sección “Resumen por proceso”
- “Análisis de resultados históricos”
- “Hallazgos por proceso”
- “Texto auto por proceso”

### Sección “Informes”
- “Direcc. estratégico”
- “Exportar / reportes”

### Bloque inferior de estado del pipeline
- Título: “Pipeline”
- Última ejecución: “Últ. ejec: hoy 06:00”
- Barra de progreso
- Texto de calidad: “QA: 89% · 87 indicadores”

Explica:
- comportamiento del menú,
- estados activos,
- jerarquía visual,
- permisos por rol,
- y cómo navegaría el usuario entre módulos.

---

## B. Zona principal

Debe incluir:
- topbar superior,
- área de contenido scrolleable,
- cards,
- grids,
- paneles analíticos,
- alertas,
- módulos integrados,
- acciones rápidas por rol,
- y franja inferior de CTAs.

Debe ser totalmente modular para Streamlit.

---

# 5) TOPBAR SUPERIOR

La topbar debe contener:

## Izquierda
- Título principal: “Inicio estratégico”
- Subtítulo: “Dic 2025 · 387 indicadores · Generado 07/04/2026”

## Derecha
- selector de año,
- selector de mes,
- filtro/chip de área: “Todas las áreas”,
- botón primario: “Actualizar datos”,
- iconos opcionales de notificaciones y calendario.

Describe:
- comportamiento de filtros,
- dependencia entre filtros,
- persistencia del estado,
- actualización del dashboard,
- uso de session_state en Streamlit,
- y estrategia para recarga parcial o total.

---

# 6) BANNER SUPERIOR DE ALERTA IA

Debajo de la topbar debe ir una banda destacada de alerta inteligente con gradiente institucional entre índigo, azul y cian.

Contenido:
- “IA detectó: 9 indicadores con riesgo alto de incumplimiento (IRIP >70%)”
- “3 anomalías en datos (z-score >3)”
- “7 metas fuera de rango estadístico óptimo”

Debe incluir un CTA:
- “Ver detalle IA ↗”

Describe:
- composición visual,
- iconografía,
- jerarquía textual,
- animación sutil opcional,
- acción al clic,
- navegación resultante,
- drawer/modal/tab de destino,
- y reglas de prioridad.

---

# 7) FILA DE KPIS GLOBALES

Mostrar una fila de 5 KPI cards con valor, etiqueta, subtexto, color de estado y tooltip:

1. Total indicadores
   - Valor: 387
   - Subtexto: “Kawak + API”

2. En peligro
   - Valor: 20
   - Subtexto: “+19 vs ant. · 5.2%”
   - Color: rojo

3. En alerta
   - Valor: 24
   - Subtexto: “+21 vs ant. · 6.2%”
   - Color: ámbar

4. Cumplimiento
   - Valor: 85
   - Subtexto: “+70 vs ant. · 22%”
   - Color: verde

5. Sobrecumplimiento
   - Valor: 115
   - Subtexto: “+108 vs ant. · 29.7%”
   - Color: azul/cian

Para cada KPI define:
- estructura visual,
- regla de cálculo,
- datos requeridos,
- tooltip,
- variación vs periodo anterior,
- al hacer clic qué abre,
- y cómo se conecta con una vista detalle.

---

# 8) SUBNAVEGACIÓN INTERNA DEL MÓDULO

Incluye una barra tipo tabs / segmented control con estas vistas:
- Resumen ejecutivo
- Por proceso
- Por vicerrectoría
- Analítica IA
- PDI / Acreditación
- Auditorías

La tab activa por defecto debe ser “Resumen ejecutivo”.

Explica:
- contenido de cada tab,
- filtros heredados,
- qué componentes cambian,
- qué componentes son persistentes,
- y cómo se organiza el estado en Streamlit.

---

# 9) 3 MÓDULOS INTEGRABLES PRINCIPALES

El dashboard debe integrar como mínimo estos tres módulos analíticos, explicando su función, sus visualizaciones y cómo se cruzan entre sí:

## Módulo 1: IRIP Predictivo
Objetivo:
- anticipar riesgo de incumplimiento 30–60 días antes.

Debe incluir:
- score de probabilidad de incumplimiento por indicador,
- ranking de riesgo,
- tendencia histórica,
- variación reciente,
- variables explicativas,
- estatus actual vs meta,
- nivel de criticidad,
- recomendación sugerida.

Visualizaciones sugeridas:
- barras horizontales ordenadas por probabilidad,
- línea temporal de riesgo,
- scatter de riesgo vs cumplimiento actual,
- heatmap por proceso / área,
- tarjetas de top riesgos.

## Módulo 2: DAD / Detector de anomalías
Objetivo:
- detectar outliers, inconsistencias o desviaciones relevantes antes del reporte ejecutivo.

Debe incluir:
- detección por z-score > 3,
- anomalías por serie temporal,
- validación de calidad de datos,
- desviación respecto a comportamiento esperado,
- severidad,
- fuente afectada,
- trazabilidad del dato.

Visualizaciones sugeridas:
- serie temporal con puntos anómalos resaltados,
- boxplot por periodo,
- tabla priorizada de anomalías,
- scatter de valor real vs esperado,
- badges de criticidad,
- timeline de eventos anómalos.

## Módulo 3: CMI Estratégico / KPIs institucionales / Acreditación
Objetivo:
- conectar el desempeño institucional con perspectivas estratégicas, acreditación y avance de metas.

Debe incluir:
- 4 perspectivas BSC / CMI,
- indicadores institucionales por objetivo,
- alineación con PDI,
- trazabilidad con acreditación,
- semáforo por perspectiva,
- brechas,
- hallazgos,
- líneas estratégicas,
- y cumplimiento agregado.

Visualizaciones sugeridas:
- radar o spider chart por perspectiva,
- barras apiladas por línea estratégica,
- matriz de cumplimiento vs acreditación,
- scorecards por objetivo,
- sunburst o treemap para desglose institucional,
- mapa de brechas por factor CNA.

Explica además:
- cómo se integran los 3 módulos,
- qué datasets comparten,
- cómo se relacionan con OM,
- cómo impactan alertas,
- y cómo se muestran dentro del Inicio estratégico sin recargar la pantalla.

---

# 10) SECCIÓN “MÓDULOS INTEGRADOS”

Diseña una grilla de tarjetas clicables para estos 3 módulos principales:
- IRIP predictivo
- DAD / Detector anomalías
- CMI Estratégico / KPIs institucionales

Cada tarjeta debe contener:
- icono,
- nombre corto,
- badge de tipo,
- descripción corta,
- número de indicadores activos,
- estado general,
- color distintivo,
- CTA implícito o explícito,
- hover state,
- y acción al clic.

Además, contempla tarjetas secundarias opcionales:
- Coherencia de metas ICM
- Eficiencia OM (SEAC)
- Auditorías PDF
- Recomendaciones por rol

Explica:
- cuándo mostrar las secundarias,
- cómo se organizan visualmente,
- y cómo no romper la jerarquía del dashboard principal.

---

# 11) VISUALIZACIONES PRINCIPALES DEL DASHBOARD

Diseña e integra estas visualizaciones:

## A. Curva de desempeño institucional
Una visualización compuesta tipo barra + línea para mostrar desempeño institucional agregado de los módulos IRIP, DAD y CMI.

Debe incluir:
- barras de valor realizado por mes,
- línea de proyección o referencia,
- eje temporal mensual,
- leyenda clara,
- tooltip por punto,
- y lectura ejecutiva simple.

Define:
- tipo de gráfica en Plotly,
- colores por serie,
- datos necesarios,
- interacción hover,
- clic para drill-down,
- y explicación de negocio.

## B. Semáforo global
Tarjeta resumen con 4 cajas:
- Peligro
- Alerta
- Cumplimiento
- Sobrecumplimiento

Debe indicar:
- valor absoluto,
- porcentaje,
- recalibración dinámica,
- y badge “Nuevo” si aplica.

## C. Ranking IRIP
Tarjeta con barras horizontales de mayor riesgo:
- Graduación oportuna pregrado — 87%
- Cobertura banda ancha campus — 82%
- Publicaciones indexadas — 79%
- Tasa retención 2do año — 73%
- Financiación externa I+D — 71%

## D. Alertas inteligentes
Feed de alertas por criticidad con colores:
- rojo: urgentes,
- ámbar: monitoreo,
- azul/cian: informativas.

## E. Cumplimiento por proceso
Barras horizontales comparativas con:
- porcentaje actual,
- variación vs periodo anterior,
- semaforización,
- clic por proceso.

## F. PDI — Avance estratégico
Barras por línea estratégica:
- Formación
- Investigación
- Extensión
- Internacionalización

## G. QA Pipeline
Visual de progreso + consistencia + flags + validaciones activas.

## H. Visualizaciones opcionales avanzadas
Incluye recomendaciones para futuras visualizaciones:
- heatmap de riesgo por proceso y mes,
- red de relación indicador–hallazgo–OM,
- diagrama de flujo del pipeline,
- sunburst de acreditación,
- radar por perspectivas CMI,
- scatter de meta vs real vs riesgo,
- waterfall de evolución del cumplimiento,
- timeline de alertas.

Para cada visualización detalla:
- objetivo,
- prioridad,
- insumos,
- métrica principal,
- interacción,
- y recomendación técnica Plotly.

---

# 12) MODALES / VENTANAS EMERGENTES POR INDICADOR

Debe habilitarse un modal, drawer lateral o panel expandible por indicador.

Cuando el usuario haga clic sobre un indicador, debe abrir una vista detalle con:

## Encabezado del detalle
- nombre del indicador,
- código,
- proceso,
- área,
- meta,
- valor actual,
- estado,
- tendencia,
- responsable.

## Tabs internas del detalle
1. Predicción IRIP
2. Detector anomalías
3. Coherencia metas
4. Eficiencia OM (SEAC)

## Contenido esperado por tab
### Predicción IRIP
- score,
- drivers del riesgo,
- tendencia,
- ventana de predicción,
- recomendación.

### Detector anomalías
- anomalías históricas,
- puntos atípicos,
- validación de fuente,
- severidad.

### Coherencia metas
- distancia entre meta y comportamiento histórico,
- percentiles,
- razonabilidad,
- recomendación de ajuste.

### Eficiencia OM (SEAC)
- OM asociadas,
- tiempo de cierre,
- efectividad,
- reincidencia,
- impacto real en el indicador.

Explica:
- patrón de navegación,
- cierre del modal,
- persistencia,
- cómo implementarlo en Streamlit,
- y qué limitaciones técnicas deben considerarse.

---

# 13) RESUMEN POR PROCESO Y ANÁLISIS HISTÓRICO

Diseña una vista “Resumen por proceso” que combine:
- histórico,
- auditoría,
- acreditación,
- hallazgos,
- indicadores vinculados,
- indicadores propuestos,
- y recomendaciones.

Debe incluir un flujo visual del proceso:
“Ingesta de datos → Validación/calidad → Cálculo de indicadores → Publicación en tableros → Detección de alertas → Generación de OM → Asignación y seguimiento”

Incluye un ejemplo completo para:
## Gestión del Talento Humano
- indicadores actuales,
- tendencia,
- relación con acreditación,
- hallazgos de auditoría interna y externa,
- indicadores que evidencian cumplimiento,
- propuesta de nuevos indicadores,
- recomendaciones de seguimiento.

Explica cómo modelar esta vista en componentes reutilizables.

---

# 14) ACCIONES RÁPIDAS POR ROL

Construye una sección con tarjetas por rol:
- Directivo
- Coordinador
- Analista
- Auditor

Cada tarjeta debe tener:
- color lateral distintivo,
- 2 recomendaciones,
- icono,
- prioridad,
- CTA si aplica.

Ejemplos:
## Directivo
- Convocar comité revisión PDI
- Revisar indicadores en peligro

## Coordinador
- Cerrar OM vencidas urgente
- Revisar indicadores IRIP alto

## Analista
- Verificar anomalías DAD
- Ajustar metas ICM > 0.2

## Auditor
- Revisar indicadores sin medición
- Vincular hallazgos PDF pendientes

Explica cómo se generan automáticamente estas recomendaciones.

---

# 15) DATOS Y MODELO LÓGICO

Supón que el sistema consume:
- indicadores,
- mediciones históricas,
- metas,
- clasificación semafórica,
- riesgos IRIP,
- anomalías DAD,
- coherencia ICM,
- score SEAC,
- OM,
- auditorías,
- hallazgos,
- acreditación,
- líneas PDI,
- procesos,
- subprocesos,
- usuarios,
- roles,
- logs de pipeline,
- validaciones QA.

Define:
- entidades,
- atributos mínimos,
- relaciones,
- periodicidad,
- tablas sugeridas,
- catálogos,
- versionamiento,
- trazabilidad,
- reglas de negocio,
- umbrales dinámicos,
- alertas automáticas,
- recomendaciones por rol.

Incluye una propuesta de modelo de datos relacional o híbrido apto para MVP y escalamiento posterior.

---

# 16) REQUISITOS FUNCIONALES Y DE INTERACCIÓN

El módulo debe contemplar:
- filtros por año, mes y área,
- navegación lateral,
- tabs internas,
- tarjetas clicables,
- tooltips,
- modales,
- drill-down,
- actualización de datos,
- estados de carga,
- estados vacíos,
- errores,
- permisos por rol,
- exportación,
- trazabilidad de navegación,
- y comportamiento ante datos faltantes.

Explica todo esto con enfoque práctico para implementación.

---

# 17) REQUISITOS TÉCNICOS PARA STREAMLIT

Describe cómo implementar esto en Streamlit considerando:
- organización por páginas,
- componentes reutilizables,
- funciones helper,
- manejo de session_state,
- filtros globales,
- separación entre UI, lógica y datos,
- integración de Plotly,
- modularidad,
- caché,
- mocks,
- y pruebas básicas.

Incluye recomendaciones sobre:
- st.sidebar
- st.container
- st.columns
- st.tabs
- st.expander
- st.metric
- plotly charts
- componentes custom HTML/CSS si se requieren
- e inyección controlada de estilos.

---

# 18) ESTRUCTURA DEL PROYECTO

Entrega una estructura sugerida de carpetas y archivos para un proyecto limpio, por ejemplo:
- app.py
- pages/
- components/
- services/
- data/
- models/
- utils/
- config/
- styles/
- assets/

Explica qué debe ir en cada carpeta.

---

# 19) MVP Y ROADMAP

Propón:
- MVP funcional,
- fase 2,
- fase 3,
- backlog inicial,
- riesgos técnicos,
- mitigaciones,
- y mejoras futuras.

---

# 20) FORMATO DE SALIDA OBLIGATORIO

Devuelve la respuesta exactamente en este orden:

1. Visión funcional del módulo
2. Arquitectura de información
3. Mapa de navegación
4. Sistema visual y paleta de colores
5. Diseño visual por secciones
6. Visualizaciones y gráficas recomendadas
7. Descripción de los 3 módulos integrables
8. Componentes UI reutilizables
9. Modelo de datos sugerido
10. Lógica de negocio por bloque
11. Eventos e interacciones del usuario
12. Requisitos funcionales y estados
13. Requisitos técnicos para implementación en Streamlit
14. Estructura recomendada de archivos/proyecto
15. Roadmap de desarrollo por fases
16. Riesgos de implementación
17. Recomendaciones de mejora futura
18. Arquitectura técnica sugerida por capas
19. Organización del estado y filtros
20. Próximos pasos para construir el MVP
21. Árbol inicial del proyecto
22. Recomendaciones para que luego generes el código base

Además, al final agrega un apartado extra llamado:
## “Siguiente paso”
donde indiques qué prompt debería usarse a continuación para pedirte el scaffold inicial en Streamlit.