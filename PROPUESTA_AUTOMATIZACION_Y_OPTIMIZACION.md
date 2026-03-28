# Propuesta de automatizacion con agentes y optimizacion de `actualizar_consolidado.py`

## 1) Objetivo

Implementar un flujo automatico, repetible y auditable para:

1. Consolidar fuentes (`Kawak` + `API`)
2. Actualizar `Resultados Consolidados.xlsx`
3. Generar `Seguimiento_Reporte.xlsx`
4. Validar calidad de datos y publicar artefactos

Ademas, reducir la complejidad y el tiempo de ejecucion de `scripts/actualizar_consolidado.py`.


## 2) Alcance

- Automatizacion del pipeline de datos con agentes (orquestacion + QA)
- Refactor por etapas de `scripts/actualizar_consolidado.py`
- Estandarizacion de configuracion y logging
- Validaciones automaticas de calidad
- Base para CI/CD del proceso


## 3) Situacion actual (resumen tecnico)

- Hay logica de negocio critica hardcodeada (anios, fechas de cierre, reglas especiales).
- `scripts/actualizar_consolidado.py` es monolitico (muy grande) y mezcla:
  - reglas de negocio
  - lectura/escritura Excel
  - normalizacion/parseo
  - logging y control de flujo
- Alta dependencia de formulas Excel y materializacion posterior.
- Repeticion de utilidades (normalizacion de ID, meses, deteccion de no aplica).
- Falta de un contrato de datos centralizado para ejecutar de forma confiable con agentes.


## 4) Arquitectura propuesta de agentes

### 4.1 Agente Orquestador (principal)

Responsable de ejecutar el pipeline completo con una sola instruccion:

1. Pre-check de insumos y estructura de hojas/columnas
2. Ejecutar `scripts/consolidar_api.py`
3. Ejecutar `scripts/actualizar_consolidado.py`
4. Ejecutar `generar_reporte.py`
5. Ejecutar validaciones de calidad
6. Generar reporte de corrida (Markdown + JSON)

Salida:
- Estado final (OK/ERROR)
- Tiempos por etapa
- Conteos de filas/IDs/periodos
- Alertas de calidad

### 4.2 Agente QA de datos

Responsable de validar calidad de resultados:

- Esquema minimo por hoja
- Porcentaje de nulos en campos criticos
- Rangos permitidos de `Cumplimiento`
- Coherencia de periodos (mes de cierre segun periodicidad)
- Deteccion de cambios anormales vs corrida anterior

Salida:
- `artifacts/qa_report.json`
- semaforo QA (verde/amarillo/rojo)

### 4.3 Agente Refactor (tecnico)

Responsable de mejoras de codigo:

- extraer funciones a modulos
- reducir duplicacion
- introducir tests
- optimizar cuellos de botella (vectorizacion y menos I/O)

Salida:
- PRs incrementales, pequenas y reversibles


## 5) Estandar de configuracion (clave para agentes)

Crear `config/settings.toml` con:

- rutas de entrada/salida
- anio de cierre (o regla dinamica)
- fecha de referencia
- reglas de negocio especiales:
  - `ids_anio_vencido`
  - `ids_vigencia_desde`
  - `procesos_no_aplica`
- parametros de validacion QA
- opciones de logging

Beneficio: los agentes no dependen de editar codigo para cambios operativos.


## 6) Refactor propuesto para `scripts/actualizar_consolidado.py`

## 6.1 Estructura objetivo

Separar en modulos:

- `etl/io_excel.py`  
  Lectura/escritura, carga de hojas, manejo de plantillas

- `etl/normalizacion.py`  
  IDs, textos, parseo seguro

- `etl/no_aplica.py`  
  Deteccion de registros no aplica

- `etl/cumplimiento.py`  
  Calculo vectorizado de cumplimiento y topes

- `etl/reglas_periodo.py`  
  Periodicidades, cierres y filtros temporales

- `etl/consolidado_builder.py`  
  Construccion de hojas y consolidado final

- `scripts/actualizar_consolidado.py`  
  Solo CLI + orquestacion + logging

## 6.2 Optimizaciones prioritarias

1. **Vectorizar calculos**
   - evitar `apply`/loops por fila para cumplimiento y campos derivados.
2. **Reducir I/O Excel**
   - cargar una vez por archivo (`pd.ExcelFile`) y reutilizar parseos.
3. **Eliminar dependencia de formulas en celdas**
   - escribir valores calculados desde Python (fuente de verdad).
4. **Parametrizar anio y cortes**
   - usar CLI + `settings.toml`; no hardcodear `2025`.
5. **Logging estructurado**
   - tiempos por etapa y conteos clave.
6. **Validaciones integradas**
   - chequeos al final de cada etapa antes de continuar.


## 7) Contrato de datos minimo

Definir `config/data_contract.yaml` con:

- hojas obligatorias por archivo
- columnas minimas por hoja
- tipos esperados (ID string, fechas parseables, etc.)
- reglas de calidad (umbrales de nulos y rangos)

Si falla el contrato, el agente detiene la corrida.


## 8) Plan de implementacion (4 semanas)

### Semana 1: Base operativa
- Crear `settings.toml` + `data_contract.yaml`
- Crear `scripts/run_pipeline.py` (orquestador local)
- Agregar logging estructurado y reporte de corrida

### Semana 2: Refactor funcional (sin cambiar resultado)
- Extraer utilidades comunes
- Mover logica de no aplica y periodos a modulos
- Mantener outputs equivalentes (prueba de regresion)

### Semana 3: Performance
- Vectorizar cumplimiento y columnas derivadas
- Reducir lecturas Excel repetidas
- Medir mejora de tiempo y memoria

### Semana 4: QA + CI
- Agregar tests unitarios de reglas criticas
- Agregar validaciones QA automaticas post-run
- Integrar pipeline en CI para corridas controladas


## 9) Indicadores de exito

- Reduccion >= 40% del tiempo total de `actualizar_consolidado.py`
- 0 cambios manuales de codigo por cambio de anio
- 100% de corridas con reporte QA generado
- Cobertura minima de tests en modulos core del ETL (>= 70%)
- Disminucion de incidencias por inconsistencia de formulas Excel


## 10) Riesgos y mitigaciones

- **Riesgo:** diferencias de salida durante refactor  
  **Mitigacion:** pruebas de regresion por hoja + muestreo de IDs.

- **Riesgo:** dependencias de formato Excel final  
  **Mitigacion:** separar calculo (pandas) y formateo final (openpyxl controlado).

- **Riesgo:** reglas de negocio no documentadas  
  **Mitigacion:** mover reglas a config y versionarlas.


## 11) Siguiente paso inmediato recomendado

Implementar primero una version minima de:

1. `config/settings.toml`
2. `scripts/run_pipeline.py`
3. refactor inicial de `actualizar_consolidado.py` para usar configuracion y logging

Con esto ya se habilita ejecucion por agentes de forma automatica y trazable, sin esperar el refactor completo.

