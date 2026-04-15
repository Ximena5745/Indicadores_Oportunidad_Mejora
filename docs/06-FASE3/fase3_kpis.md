# Fase 3 — KPIs por nivel

**Objetivo:** Definir los KPIs mínimos necesarios para prototipos y pruebas de aceptación por nivel.

## Nivel 1 — CMI Estratégico (frecuencia: trimestral)

- **Índice Salud Institucional** (`indice_salud`): Índice agregado 0–100. Fórmula: suma ponderada de indicadores críticos normalizados. Fuente: indicadores críticos consolidados. Umbrales: >=95 (verde), 80–94 (amarillo), <80 (rojo).
- **Cumplimiento Global (%)** (`cumplimiento_global`): Promedio ponderado del % de cumplimiento de indicadores estratégicos.

## Nivel 2 — Gestión y Cumplimiento (frecuencia: semanal/mensual)

- **Cumplimiento por Proceso (%)** (`cumplimiento_proceso`): Promedio de cumplimiento de indicadores asociados al proceso.
- **Brecha Promedio (pp)** (`brecha_promedio`): Promedio(meta - actual) en puntos porcentuales.
- **Tasa de cierre OM (%)** (`tasa_cierre_OM`): OM cerradas / OM totales * 100. Fuente: módulo OM.

## Nivel 3 — Operativo y Calidad (frecuencia: diaria/semanal)

- **Indicadores Actualizados (%)** (`indicadores_actualizados`): indicadores con actualización en el periodo / total * 100.
- **Indicadores en Alerta (%)** (`indicadores_alerta`): count(cumplimiento < 80%) / total * 100.
- **Tiempo medio resolución OM (días)** (`tmo_OM`): mean(fecha_cierre - fecha_apertura).
- **Errores validación por carga** (`errores_validacion`): count(errores)/records_por_carga.

## Esquema mínimo de metadatos por indicador

Propuesta JSON para cada indicador (ejemplo):

```
{
  "id": "PR-05",
  "nombre": "Porcentaje cumplimiento PR-05",
  "unidad": "%",
  "meta": 85,
  "actual": 72,
  "periodo": "2026-03",
  "fuente": "consolidado_v1",
  "owner": "Coordinador X",
  "last_update": "2026-03-28",
  "semaforo": "amarillo"
}
```

## Mapeo y siguientes pasos

1. Mapear cada KPI a la(s) plantilla(s) o artefacto(s) en `data/output/artifacts/`.
2. Implementar funciones de cálculo en el consolidator (`consolidation/core/`) y pruebas unitarias.
3. Usar estos KPIs en el prototipo Nivel 3 (Sprint 1).

Archivos relacionados: [docs/fase3_prioritizacion.md](docs/fase3_prioritizacion.md)

Fecha: 2026-04-07
Autor: Equipo técnico

## Mapeo desde el archivo fuente

- Archivo origen: `data/raw/Indicadores por CMI.xlsx`.
- Regla automática aplicada para asignar niveles:
  - Si `Indicadores Vicerrectoria` = 1 o `Indicadores Plan estrategico` = 1 → **Nivel 2** (Gestión y Cumplimiento).
  - Si `Clasificación` contiene "estrat" → **Nivel 1** (CMI Estratégico).
  - Si `Clasificación` contiene "oper" → **Nivel 3** (Operativo y Calidad).
  - En caso contrario → **Nivel no asignado** (revisión manual requerida).

- Resultado guardado en: `data/output/artifacts/indicadores_cmi_mapping_v2.csv` (incluye columnas: Id, Indicador, Clasificacion, Linea, Periodicidad, Meta, Objetivo, Orden CMI, Indicadores Vicerrectoria, Indicadores Plan estrategico, Nivel).

Conteo por nivel (archivo generado):

- Nivel 1: 255
- Nivel 2: 111
- Nivel 3: 211

Siguiente paso recomendado: revisar manualmente los registros marcados como "Nivel no asignado" y confirmar el mapeo para indicadores críticos.
