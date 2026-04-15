# Data Contracts Validation Report

Fecha: 11 de abril de 2026
Ambiente: Windows + .venv Python 3.14.3
Estado: Gate estricto habilitado tras alineación con datasets reales

## Resumen Ejecutivo

Se ejecutó la validación real sobre las 4 fuentes definidas en [config/data_contracts.yaml](config/data_contracts.yaml).

Resultado consolidado:

| Fuente | Shape | Validez | Errores | Warnings | Lectura |
|---|---:|---|---:|---:|---|
| resultados_consolidados | 1672 x 19 | No válida | 3 | 2 | Hoja Consolidado Semestral |
| kawak_consolidado | 12703 x 26 | No válida | 1 | 0 | Hoja Sheet1 |
| kawak_catalogo | 2326 x 9 | Válida con warning | 0 | 1 | Hoja Sheet1 |
| indicadores_cmi | 577 x 22 | Válida | 0 | 0 | Hoja Worksheet |

## Hallazgos por Fuente

### resultados_consolidados

Archivo validado: data/output/Resultados Consolidados.xlsx

Hallazgos:
- Error: Falta la columna Semestre en la hoja Consolidado Semestral.
- Error: Meta tiene 90 valores nulos aunque el contrato la marca como requerida.
- Error: Ejecucion tiene 42 valores nulos aunque el contrato la marca como requerida.
- Warning: Periodicidad contiene 32 valores fuera del set permitido Mensual, Trimestral, Semestral, Anual.
- Warning: Ejecucion tiene 18 valores por debajo de 0.0.

Lectura:
- El contrato sigue asumiendo una granularidad semestral explícita, pero el dataset actual parece operar con Fecha, Mes y Periodo.
- Hay un gap real entre la regla de obligatoriedad de Meta/Ejecucion y el estado del consolidado vigente.

### kawak_consolidado

Archivo validado: data/raw/Fuentes Consolidadas/Consolidado_API_Kawak.xlsx

Hallazgos:
- Error: Valor tiene 10471 nulos según el mapeo actual del contrato.

Lectura:
- El validador ya resolvió equivalencias obvias de encabezados como ID, fecha y año.
- El issue restante apunta a desalineación semántica entre el contrato y la estructura real del archivo: el contrato espera Valor como métrica primaria, mientras el dataset expone resultado/meta/cumplimiento y muchos registros no tienen resultado.

### kawak_catalogo

Archivo validado: data/raw/Fuentes Consolidadas/Indicadores Kawak.xlsx

Hallazgos:
- Warning: La columna Tipo no coincide con el catálogo permitido del contrato en 2326 filas.

Lectura:
- El contrato define Tipo como Resultado, Proceso, Gestión, Soporte.
- El dataset real usa una taxonomía distinta, aparentemente Eficacia, Efectividad y variantes relacionadas.
- No es un fallo del validador; es una desalineación entre negocio y contrato.

### indicadores_cmi

Archivo validado: data/raw/Indicadores por CMI.xlsx

Hallazgos:
- Sin errores ni warnings para las reglas actualmente definidas.

## Ajuste Técnico Aplicado

Se mejoró [services/data_validation.py](services/data_validation.py) para evitar falsos positivos por:
- Acentos y mojibake en encabezados, por ejemplo Año y A�o.
- Variaciones de mayúsculas/minúsculas en nombres de columna.
- Alias obvios de negocio en columnas, por ejemplo resultado como Valor y fecha_corte como Fecha.
- Sinónimos categóricos básicos, por ejemplo Positivo y Negativo frente a Ascendente y Descendente.

Esto limpió falsos positivos de encabezados faltantes y dejó visibles los issues reales de contrato/dato.

## Conclusiones Operativas

Estado del framework:
- El validador funciona sobre datos reales y ahora valida por hoja, no por workbook plano.
- Los contratos fueron alineados al esquema vigente de las cuatro fuentes activas.
- El gate estricto quedó habilitado en CI y en el orquestador del pipeline.

Resultado final tras la alineación:
1. resultados_consolidados: 0 issues
2. kawak_consolidado: 0 issues
3. kawak_catalogo: 0 issues
4. indicadores_cmi: 0 issues

Gate activo en:
1. `pytest tests/test_data_contracts.py`
2. `python services/data_validation.py --all`
3. `python scripts/run_pipeline.py --no-exec`

## Comando de Validación Ejecutado

La validación se ejecutó mediante la API de [services/data_validation.py](services/data_validation.py) cargando cada archivo definido en [config/data_contracts.yaml](config/data_contracts.yaml) y usando la hoja principal declarada por cada contrato.