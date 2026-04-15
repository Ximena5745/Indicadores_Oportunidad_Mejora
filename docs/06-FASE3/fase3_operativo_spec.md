# Fase 3 — Especificación: Tablero Estratégico Operativo (Nivel 3)

Resumen corto
- Objetivo: Entregar un dashboard operativo realista con las capacidades que los datos actuales permiten (principalmente mensual/periodicidad irregular). Priorizar trazabilidad, control de calidad, gestión de OM y detección de incumplimiento de reportes esperados.

Limitaciones de los datos (realista)
- No hay cobertura semanal/quincenal consistente: la fuente principal (`Resultados Consolidados.xlsx`) contiene registros con `Fecha` en distintos meses y periodicidades (Mensual, Trimestral, Semestral, Anual). Por tanto el dashboard no podrá garantizar vistas semanales fiables salvo para indicadores con ingestas con fecha diaria explícita.
- Alta variabilidad y artefactos con duplicados/errores (ver `data/output/artifacts/ingesta_*.json`). Implementar QC y mostrar confianza en la información.

Cuatro módulos nuevos (MVP funcional)
1. Registro de Frecuencia y Alertas
   - Detecta indicadores que debieron reportar según su `Periodicidad` y el último `Fecha` disponible.
   - Muestra lista "Esperados hoy/esta quincena/mes" y genera alertas (visual + CSV).
   - Regla simple: para `Mensual` → espera registro en último mes; `Semestral/Trimestral/Anual` → regla de ventana (ej. semestral → espera registro en últimos 6 meses).

2. Trazabilidad de Origen
   - Por indicador muestra: archivos de ingesta que afectaron el registro (artefactos JSON), nombre físico del archivo, timestamp de carga, y validaciones asociadas.
   - Permite descargar/abrir el archivo origen cuando esté disponible en `data/raw/` o `data/output/artifacts/`.

3. Gestión OM (Oportunidades de Mejora)
   - CRUD mínimo para OM: crear/editar/cerrar OM vinculadas a `Id` de indicador.
   - Persistencia: JSON por OM en `data/output/artifacts/om/` (MVP). Campos: id_om, indicador_id, titulo, descripcion, responsable, estado, fecha_creacion, fecha_compromiso, fecha_cierre.
   - Vista: tablero/lista filtrable, métricas TMO (tiempo medio cierre).

4. Control de Calidad y Panel de Validaciones
   - Consolida resultados de QA (errores, duplicados, nulos, fuera de rango) provenientes de artefactos de ingesta.
   - Muestra top problemas por plantilla y por indicador; permite filtrar por gravedad.

Funcionalidad UI propuesta (pestañas)
- Resumen (KPIs): % reportados (periodo), % en alerta, TMO OM, % registros fallidos QC. Donut + tarjetas. Filtros globales: Periodo (mes/año), Unidad, Proceso.
- Kanban Operativo: columnas (Actualizado / Pendiente / Alerta / Peligro / No aplica) con click → filtra tabla.
- Tabla Consolidado: columnas Id, Indicador, Linea(Unidad), Proceso, Periodicidad, Última Fecha, Cumplimiento, Nivel, Acción (Abrir OM / Ver Trazabilidad). Expanders con sparklines.
- Trazabilidad: resultado por Id con lista de artefactos de ingesta y validaciones.
- OM: CRUD y tablero con filtros por responsable/estado.
- QC: listado de validaciones y detalle por archivo.

KPIs y métricas (definición breve)
- % Reportados = count(Id con registro en ventana esperada) / total IDs activos (Kawak/mapa).
- % En Alerta = count(cumplimiento < umbral amarillo) / total reportados.
- TMO OM = media(días entre fecha_creacion y fecha_cierre) para OM cerradas en período.
- % Registros fallidos QC = registros con error / total registros procesados.

Requisitos de datos mínimos
- `Id`, `fecha` (convertible a datetime), `Cumplimiento` (numérico ratio), `Periodicidad`, `Proceso` o `Subproceso`, mapa de IDs (`indicadores_cmi_mapping_v2.csv`), artefactos de ingesta JSON.

Criterios de aceptación (MVP)
1. La vista Resumen muestra KPIs calculados con los CSV normalizados en menos de 5s en entorno de prueba con ~10k filas.
2. Kanban y Tabla responden a filtros y click cruzado (click kanban filtra tabla).
3. Crear una OM genera archivo JSON y aparece en la lista OM; cerrar OM actualiza TMO.
4. Trazabilidad muestra al menos enlace al artefacto de ingesta y mensaje de QC para registros problemáticos.

Plan de trabajo corto (siguientes acciones)
- Tarea A (hoy): Crear `docs/fase3_operativo_spec.md` (este archivo) y crear estructura de almacenamiento OM (`data/output/artifacts/om/`).
- Tarea B (Sprint 1): Implementar Resumen, Kanban y Tabla básica (scripts/nivel3/data.py + ui.py o refactor de `scripts/prototipo_nivel3.py`).
- Tarea C (Sprint 2): Implementar OM CRUD y persistencia JSON.
- Tarea D (Sprint 3): Implementar trazabilidad y panel QC (usar `ingesta_*.json`).

- Entregables inmediatos que genero si autorizas:
- Archivo de especificación (este). 
- Estructura OM: carpeta `data/output/artifacts/om/` y un helper `scripts/nivel3/om.py` (CRUD JSON básico).
- Sprint 1: implementación de Resumen, Kanban y Tabla básica en `pages/3_Tablero_Estrategico_Operativo.py` reutilizando `scripts/prototipo_nivel3.py`.

¿Procedo a crear la carpeta OM y el helper CRUD, y luego implemento Sprint 1 (Resumen + Kanban + Tabla)?