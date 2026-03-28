"""
scripts/etl/
Paquete ETL modular para consolidación de indicadores.

Módulos:
  config        — lee AÑO_CIERRE_ACTUAL, IDS_PLAN_ANUAL, etc. desde settings.toml
  normalizacion — utilidades de texto, IDs, NaN
  periodos      — fechas y periodicidades
  cumplimiento  — cálculo de cumplimiento
  no_aplica     — detección de registros No Aplica
  extraccion    — estrategias de extracción meta/ejec
  fuentes       — carga de fuentes de datos
  catalogo      — carga unificada del catálogo de indicadores
  desglose      — expansión de series/variables/análisis
  signos        — extracción de signos
  formulas_excel— utilidades openpyxl y fórmulas Excel
  escritura     — escritura de filas al workbook
  purga         — limpieza y deduplicación
  builders      — constructores de registros por hoja
"""
