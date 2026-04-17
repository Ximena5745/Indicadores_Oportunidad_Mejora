# Fuentes de Datos del Proyecto SGIND

## Objetivo

Este documento centraliza las fuentes de datos usadas por el proyecto, su rol funcional y su consumo en código y documentación.

## 1. Fuentes oficiales de negocio

| Fuente | Ruta | Tipo | Hojas/Tabla | Consumida por |
|---|---|---|---|---|
| Resultados Consolidados | data/output/Resultados Consolidados.xlsx | Excel | Consolidado Semestral (principal general), Consolidado Historico (solo Gestión OM), Consolidado Cierres, Catalogo Indicadores | services/data_loader.py, streamlit_app/pages/gestion_om.py, scripts/integrate_consolidado.py |
| API Kawak consolidada | data/raw/Fuentes Consolidadas/Consolidado_API_Kawak.xlsx | Excel | Sheet1 | scripts/actualizar_consolidado.py |
| Catálogo Kawak | data/raw/Fuentes Consolidadas/Indicadores Kawak.xlsx | Excel | Sheet1 | scripts/actualizar_consolidado.py, validaciones de Id/Año |
| Indicadores por CMI | data/raw/Indicadores por CMI.xlsx | Excel | Worksheet | services/data_loader.py, páginas CMI |
| Ficha Técnica | data/raw/Ficha_Tecnica.xlsx | Excel | Hoja1 | services/data_loader.py, vistas de detalle |
| Acciones de mejora | data/raw/acciones_mejora.xlsx | Excel | Acciones | services/data_loader.py, plan de mejoramiento |
| OM fuente histórica | data/raw/OM.xlsx (o OM.xls) | Excel | Worksheet (header=7) | services/data_loader.py (cargar_om) |
| Plan de acción | data/raw/Plan de accion/PA_*.xlsx | Excel | Primera hoja | streamlit_app/pages/gestion_om.py |
| Jerarquía procesos | data/raw/Subproceso-Proceso-Area.xlsx | Excel | Hoja1 y variantes | .github/skills/data-validation, services/data_loader.py |
| LMI reporte | data/raw/lmi_reporte.xlsx | Excel | Worksheet | scripts/actualizar_consolidado.py, análisis auxiliares |
| Salidas no conformes | data/raw/salidas_no_conformes.xlsx | Excel | SNC | procesos de calidad y soporte |

## 2. Fuentes de persistencia (aplicación)

| Fuente | Ruta/Tabla | Tipo | Uso |
|---|---|---|---|
| Registro OM local | data/db/registros_om.db | SQLite | Persistencia local de Oportunidades de Mejora |
| Registro OM remoto | public.registros_om (Supabase/PostgreSQL) | Base de datos | Persistencia remota y sincronización |

## 3. Fuentes de configuración

| Fuente | Ruta | Tipo | Propósito |
|---|---|---|---|
| Settings globales | config/settings.toml | TOML | Parámetros de ejecución ETL/app |
| Contratos de datos | config/data_contracts.yaml | YAML | Reglas de estructura y validación por fuente |
| Contrato legado | config/data_contract.yaml | YAML | Compatibilidad/legado |
| Mapeo de procesos | config/mapeos_procesos.yaml | YAML | Jerarquía proceso/subproceso para filtros y homologación |
| Config raíz | config.toml | TOML | Configuración operativa complementaria |

## 4. Artefactos generados (salidas)

| Artefacto | Ruta | Generado por |
|---|---|---|
| Resultados consolidados | data/output/Resultados Consolidados.xlsx | scripts/actualizar_consolidado.py |
| Seguimiento reporte | data/output/Seguimiento_Reporte.xlsx (si aplica) | scripts/generar_reporte.py |
| CSV/JSON de reportes y diagnósticos | artifacts/ | scripts de benchmark/diagnóstico |

## 5. Regla oficial vigente

- La hoja principal general para consumo de indicadores en la aplicación es Consolidado Semestral.
- Por ahora, Consolidado Historico aplica únicamente para Gestión OM.
- Consolidado Cierres se mantiene para procesos de consolidación.
- Dataset_Unificado.xlsx se considera referencia histórica/no oficial y no debe usarse como fuente primaria en la app.

## 6. Trazabilidad recomendada

Para mantener consistencia cuando cambie una fuente:

1. Actualizar primero config/data_contracts.yaml.
2. Actualizar documentación en docs/03-CONFIG/DATA_CONTRACTS.md y este archivo.
3. Ajustar loaders y páginas consumidoras.
4. Validar visualmente en Streamlit y ejecutar pruebas relevantes.
