# Fase 3 — Guía de uso del prototipo Nivel 3

Este documento describe cómo ejecutar e interpretar el prototipo `scripts/prototipo_nivel3.py`.

Requisitos
- Python 3.10+ (el proyecto usa 3.14 en desarrollo)
- Dependencias: ejecutar `pip install -r requirements.txt` (recomiendo crear un virtualenv).

Ejecución
1. Desde la raíz del proyecto:

```bash
pip install -r requirements.txt
streamlit run scripts/prototipo_nivel3.py
```

Controles principales (barra lateral)
- `Nivel`: seleccionar Nivel 3 (operativo) u otros.
- `Periodicidad`: filtrar por periodicidad.
- `Umbral verde` / `Umbral amarillo`: valores entre 0.0 y 1.0 que definen semáforos.
- `Ventana rolling` y `Multiplicador banda confianza`: controlan la gráfica de tendencia.

Componentes de la UI
- KPIs: métricas resumidas (cumplimiento medio, mediana, % en alerta).
- Kanban: conteo por estado (Actualizado/Pendiente/Alerta).
- Tabla de detalle: lista de indicadores filtrados.
- Expanders por fila: sparklines históricos y último valor de cumplimiento.
- Exportar CSV: descarga de los datos filtrados.
- Exportar PPTX: (opcional) requiere `python-pptx` y `kaleido` para generar imágenes.

Interpretación rápida
- `Status` se calcula comparando `Cumplimiento` con los umbrales: >=Umbral verde → `Actualizado`; >=Umbral amarillo → `Pendiente`; <Umbral amarillo → `Alerta`.
- Ajusta umbrales según política institucional.

Notas técnicas
- Mapping de indicadores: `data/output/artifacts/indicadores_cmi_mapping_v2.csv` (generado desde `data/raw/Indicadores por CMI.xlsx`).
- Consolidado temporal: `data/output/Resultados Consolidados.xlsx` (fuente para series históricas y último `Cumplimiento`).

Próximos pasos recomendados
- Validar mapeos manualmente para indicadores críticos.
- Reunión de demo con usuarios operativos (30 min) para recoger feedback UX.
