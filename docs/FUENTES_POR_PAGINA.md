# Fuentes y Hojas por Página del Proyecto SGIND

## Resumen Ejecutivo

Este documento detalla las fuentes de datos (archivos y hojas específicas) utilizadas por cada página de la aplicación Streamlit.

**Regla general:**
- `cargar_dataset()` → Lee **Consolidado Semestral** (fuente general para la mayoría de páginas)
- `cargar_dataset_historico()` → Lee **Consolidado Historico** (exclusivo para Gestión OM)

---

## 1. Resumen General (`resumen_general.py` / `resumen_general_real.py`)

| Función/Dataset | Fuente (Archivo) | Hoja | Descripción |
|----------------|------------------|------|-------------|
| `_load_consolidado_cierres()` | `data/output/Resultados Consolidados.xlsx` | **Consolidado Cierres** | Datos de cierres semestrales para el dashboard principal |
| `load_pdi_catalog()` (indirecto) | `data/raw/Indicadores por CMI.xlsx` | Worksheet | Catálogo PDI para líneas y objetivos estratégicos |

**Nota:** Usa `Consolidado Cierres` directamente, no pasa por `cargar_dataset()`.

---

## 2. CMI Estratégico (`cmi_estrategico.py`)

| Función/Dataset | Fuente (Archivo) | Hoja | Descripción |
|----------------|------------------|------|-------------|
| `load_cierres()` | `data/output/Resultados Consolidados.xlsx` | **Consolidado Cierres** | Datos de cierres para CMI estratégico |
| `load_pdi_catalog()` | `data/raw/Indicadores por CMI.xlsx` | Worksheet | Catálogo de indicadores PDI |
| `preparar_pdi_con_cierre()` | Derivado de cierres + catálogo | - | Preparación de datos PDI con cumplimiento |

---

## 3. Plan de Mejoramiento (`plan_mejoramiento.py`)

| Función/Dataset | Fuente (Archivo) | Hoja | Descripción |
|----------------|------------------|------|-------------|
| `load_cierres()` | `data/output/Resultados Consolidados.xlsx` | **Consolidado Cierres** | Datos de cierres para CNA |
| `load_cna_catalog()` | `data/raw/Indicadores por CMI.xlsx` | Worksheet | Catálogo CNA (Factor/Característica) |
| `cargar_acciones_mejora()` | `data/raw/acciones_mejora.xlsx` | **Acciones** | Acciones de mejora registradas |
| `preparar_cna_con_cierre()` | Derivado de cierres + catálogo CNA | - | Preparación de datos CNA |

---

## 4. Gestión OM (`gestion_om.py`)

| Función/Dataset | Fuente (Archivo) | Hoja | Descripción |
|----------------|------------------|------|-------------|
| `cargar_dataset_historico()` | `data/output/Resultados Consolidados.xlsx` | **Consolidado Historico** | ⚠️ **EXCLUSIVO:** Indicadores en peligro/alerta para asociar OM |
| `cargar_acciones_mejora()` | `data/raw/acciones_mejora.xlsx` | **Acciones** | Acciones de mejora existentes |
| `_cargar_avance_om()` | `data/raw/Plan de accion/PA_*.xlsx` | Primera hoja | Planes de acción por OM para calcular avance |
| `_cargar_plan_accion_para_om()` | `data/raw/Plan de accion/PA_*.xlsx` | Primera hoja | Detalle de actividades del plan de acción |
| `cargar_om()` (indirecto) | `data/raw/OM.xlsx` / `OM.xls` | Worksheet (header=7) | Fuente histórica de OM |
| `registros_om_como_dict()` | `data/db/registros_om.db` / `public.registros_om` (PostgreSQL) | Tabla `registros_om` | Registros de OM persistidos |

**Nota importante:** Esta es la única página que usa `Consolidado Historico` en lugar de `Consolidado Semestral`.

---

## 5. Resumen por Proceso (`resumen_por_proceso.py`)

| Función/Dataset | Fuente (Archivo) | Hoja | Descripción |
|----------------|------------------|------|-------------|
| `_load_calidad_data()` | `data/raw/Monitoreo/Monitoreo_Informacion_Procesos 2025.xlsx` | Primera hoja (skiprows=4) | Datos de calidad por proceso |
| `_load_auditoria_mentions()` | `data/raw/auditoria/*.pdf` | - | PDFs de auditoría para búsqueda de menciones |
| `DataService` (indirecto) | `data/output/Resultados Consolidados.xlsx` | **Consolidado Semestral** | Vía `cargar_dataset()` |

---

## 6. Seguimiento de Reportes (`seguimiento_reportes.py`)

| Función/Dataset | Fuente (Archivo) | Hoja | Descripción |
|----------------|------------------|------|-------------|
| `_cargar_tracking()` | `data/output/Seguimiento_Reporte.xlsx` | **Tracking Mensual** | Seguimiento mensual de reportes por indicador |

---

## 7. Tablero Operativo (`tablero_operativo.py`)

| Función/Dataset | Fuente (Archivo) | Hoja | Descripción |
|----------------|------------------|------|-------------|
| `_cargar_base()` → `cargar_dataset()` | `data/output/Resultados Consolidados.xlsx` | **Consolidado Semestral** | Indicadores con categoría y cumplimiento |
| `_cargar_acciones()` → `cargar_acciones_mejora()` | `data/raw/acciones_mejora.xlsx` | **Acciones** | Acciones de mejora / OM |
| `_cargar_artefactos_qc()` | `data/output/artifacts/ingesta_*.json` | - | Artefactos QC de ingesta de datos |

---

## 8. PDI Acreditación (`pdi_acreditacion.py`)

| Función/Dataset | Fuente (Archivo) | Hoja | Descripción |
|----------------|------------------|------|-------------|
| `cargar_dataset()` | `data/output/Resultados Consolidados.xlsx` | **Consolidado Semestral** | Indicadores generales |
| `cargar_acciones_mejora()` | `data/raw/acciones_mejora.xlsx` | **Acciones** | Acciones de mejora |
| Lectura directa | `data/db/Indicadores por CMI.xlsx` | **Worksheet** | Catálogo CNA para completar columnas |

---

## 9. Diagnóstico (`diagnostico.py`)

| Función/Dataset | Fuente (Archivo) | Hoja | Descripción |
|----------------|------------------|------|-------------|
| Verificación de imports | - | - | No carga datos, solo verifica imports |
| Files check | `core/proceso_types.py`, `app.py`, etc. | - | Verifica existencia de archivos del proyecto |

---

## Resumen Consolidado por Fuente

### Fuentes Principales (data/output/)

| Archivo | Hojas Utilizadas | Páginas que la Usan |
|:--------|:-----------------|:--------------------|
| `Resultados Consolidados.xlsx` | **Consolidado Semestral** | Resumen General, Tablero Operativo, PDI Acreditación |
| `Resultados Consolidados.xlsx` | **Consolidado Cierres** | Resumen General, CMI Estratégico, Plan Mejoramiento |
| `Resultados Consolidados.xlsx` | **Consolidado Historico** | ⚠️ **Solo Gestión OM** |
| `Seguimiento_Reporte.xlsx` | **Tracking Mensual** | Seguimiento de Reportes |

### Fuentes Secundarias (data/raw/)

| Archivo | Hoja | Páginas que la Usan |
|:--------|:-----|:--------------------|
| `acciones_mejora.xlsx` | **Acciones** | Plan Mejoramiento, Gestión OM, Tablero Operativo, PDI Acreditación |
| `Indicadores por CMI.xlsx` | **Worksheet** | CMI Estratégico, Plan Mejoramiento, PDI Acreditación |
| `Plan de accion/PA_*.xlsx` | **Primera hoja** | Gestión OM |
| `OM.xlsx` / `OM.xls` | **Worksheet** (header=7) | Gestión OM (histórico) |
| `Monitoreo/Monitoreo_Informacion_Procesos 2025.xlsx` | **Primera hoja** | Resumen por Proceso |
| `auditoria/*.pdf` | — | Resumen por Proceso |

### Fuentes de Persistencia

| Fuente | Tipo | Páginas que la Usan |
|:-------|:-----|:--------------------|
| `data/db/registros_om.db` | SQLite | Gestión OM |
| `public.registros_om` (PostgreSQL/Supabase) | Base de datos | Gestión OM (sincronización) |

---

## Diagrama de Dependencias

```
┌─────────────────────────────────────────────────────────────────┐
│                    FUENTES PRINCIPALES                           │
├─────────────────────────────────────────────────────────────────┤
│  Resultados Consolidados.xlsx                                    │
│  ├── Consolidado Semestral  →  Resumen General, CMI, Plan, etc. │
│  ├── Consolidado Cierres    →  Resumen General, CMI, Plan        │
│  └── Consolidado Historico  →  ⚠️ SOLO Gestión OM                 │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────────┐
│  CMI          │    │  Plan         │    │  Gestión OM       │
│  Estratégico  │    │  Mejoramiento │    │  (especial)       │
├───────────────┤    ├───────────────┤    ├───────────────────┤
│ Consolidado   │    │ Consolidado   │    │ Consolidado       │
│ Cierres       │    │ Cierres       │    │ Historico ⚠️      │
│ Indicadores   │    │ CNA Catalog   │    │ Plan de acción    │
│ por CMI       │    │ Acciones      │    │ OM.xlsx           │
│               │    │ Mejora        │    │ registros_om.db   │
└───────────────┘    └───────────────┘    └───────────────────┘
```

---

## Notas de Implementación

1. **Gestión OM es el único módulo** que requiere `Consolidado Historico` para mostrar indicadores en estado de peligro/alerta históricos.

2. **Las páginas de CMI y Plan de Mejoramiento** usan `Consolidado Cierres` porque necesitan datos de corte semestral específico.

3. **El resto de páginas** (Resumen General, Tablero Operativo, PDI Acreditación) usan `Consolidado Semestral` vía `cargar_dataset()`.

4. **Seguimiento de Reportes** tiene su propia fuente independiente (`Seguimiento_Reporte.xlsx`).

5. **Resumen por Proceso** carga datos de calidad desde un archivo específico de monitoreo y PDFs de auditoría.

---

*Documento generado el 16 de abril de 2026*
*Última actualización: Fase 2 - Refactorización de fuentes*
