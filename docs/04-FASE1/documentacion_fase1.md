# Documentación Técnica - Fase 1: Gobierno y Calidad de Datos

## 1. Resumen de la fase

La Fase 1 tiene como objetivo garantizar la integridad, trazabilidad y calidad de los datos extraídos de los archivos Excel y PDF. Para ello, se implementó un módulo de ingesta y validación que detecta automáticamente el tipo de plantilla, extrae los datos y aplica validaciones definidas por cada schema.

## 2. Arquitectura del módulo de ingesta

### 2.1 Componentes principales

```
scripts/ingesta_plantillas.py
├── PLANTILLAS (dict): Catálogo de schemas de plantillas conocidas
├── ResultadoValidacion (dataclass): Resultado de una validación individual
├── ResultadoIngesta (dataclass): Resultado completo de la ingesta de un archivo
└── IngestorPlantillas (class): Motor de ingesta y validación
    ├── detectar_plantilla(): Identifica el tipo de plantilla
    ├── validar_registros(): Aplica validaciones definidas en el schema
    ├── ingesta_archivo(): Procesa un archivo individual
    ├── ingesta_total(): Procesa todos los archivos en data/raw/
    ├── generar_artefactos(): Genera JSON con resultados de calidad
    └── generar_reporte_qa(): Genera reporte textual de calidad
```

### 2.2 Flujo de ejecución

1. Se recorre recursivamente el directorio `data/raw/`
2. Para cada archivo Excel encontrado:
   - Se detecta el tipo de plantilla (matching con >= 70% de columnas requeridas)
   - Se lee el archivo usando el schema correspondiente
   - Se aplican las validaciones definidas
   - Se clasifica la ingesta como exitosa o fallida
3. Se generan artefactos JSON y reportes QA en `data/output/`

## 3. Plantillas soportadas

| Plantilla | Archivo | Hoja | Clave primaria |
|-----------|---------|------|----------------|
| Acciones de Mejora | acciones_mejora.xlsx | Acciones | ID |
| Dataset Unificado | Dataset_Unificado.xlsx | Unificado | Id |
| Ficha Técnica | Ficha_Tecnica.xlsx | Hoja1 | Id Ind |
| Kawak | Kawak/YYYY.xlsx | Hoja1/Worksheet | Id |
| API | API/YYYY.xlsx | Indicadores | ID |
| Plan de Acción | Plan de accion/PA_*.xlsx | Worksheet | Id Acción |
| Salidas No Conformes | salidas_no_conformes.xlsx | SNC | id_salida |

## 4. Tipos de validaciones implementadas

### 4.1 Validación de únicos
- Detecta valores duplicados en campos marcados como clave
- Detecta valores nulos en campos requeridos

### 4.2 Validación de rango
- Verifica que los valores estén dentro de un rango definido (ej. 0-100 para porcentajes)

### 4.3 Validación de valores válidos
- Verifica que los valores estén dentro de una lista de permitidos
- Ejemplo: Periodicidad en ["Mensual", "Trimestral", "Semestral", "Anual"]

### 4.4 Validación de fecha
- Verifica que el campo pueda convertirse a formato de fecha

### 4.5 Validación booleana
- Verifica valores booleanos o convertibles (0/1, Si/No, True/False)

## 5. Semaforización estándar

| Nivel | Rango | Color | Descripción |
|-------|-------|-------|--------------|
| Crítico | < 70% o > 120% | 🔴 | Requiere atención inmediata |
| Atención | 70% - 80% o 105% - 120% | 🟡 | Monitorear de cerca |
| Normal | 80% - 105% | 🟢 | Dentro de los parámetros esperados |

## 6. Artefactos generados

### 6.1 Artefacto JSON (data/output/artifacts/ingesta_YYYYMMDD_HHMMSS.json)

Contiene:
- Resumen: total de archivos, exitosos, fallidos, registros
- Detalle: por cada archivo, el resultado de validaciones

### 6.2 Reporte QA (data/output/logs/reporte_qa_YYYYMMDD_HHMMSS.txt)

Contiene:
- Resumen ejecutivo de la ingesta
- Listado de archivos con errores
- Detalle de validaciones por tipo (errores y warnings)

### 6.3 Logs (data/output/logs/ingesta_YYYYMMDD_HHMMSS.log)

Contiene:
- Log detallado de la ejecución
- Información de cada archivo procesado

## 7. Reglas de negocio aplicadas

### 7.1 Acciones de Mejora
- ID debe ser único y no nulo
- FECHA_IDENTIFICACION debe ser fecha válida
- AVANCE debe estar entre 0 y 100%
- ESTADO debe ser uno de: ["Abierto", "Cerrado", "En proceso", "Pendiente"]

### 7.2 Dataset Unificado
- Id debe ser único
- Indicador no nulo
- Periodicidad válida
- Sentido: ["Ascendente", "Descendente"]

### 7.3 Kawak / API
- ID debe ser único
- Campos de clasificación y proceso no nulos
- Sentido válido

### 7.4 Plan de Acción
- Id Acción único
- Fecha creación válida
- Avance (%) entre 0-100%
- Estado válido

### 7.5 Salidas No Conformes
- id_salida único
- Estado en ["Abierto", "Cerrado", "En proceso"]
- Activo booleano

## 8. Uso del módulo

### 8.1 Ejecución completa

```bash
python scripts/ingesta_plantillas.py
```

### 8.2 Uso programático

```python
from scripts.ingesta_plantillas import IngestorPlantillas

ingestor = IngestorPlantillas()
resultados = ingestor.ingesta_total()
artefactos = ingestor.generar_artefactos()
reporte_qa = ingestor.generar_reporte_qa()
```

### 8.3 Agregar nueva plantilla

```python
# Agregar en PLANTILLAS (dict)
PLANTILLAS["nueva_plantilla"] = PlantillaSchema(
    nombre="Nueva Plantilla",
    hoja="Hoja1",
    columnas_requeridas=["ID", "Nombre"],
    columnas_opcionales=[],
    clave_primaria="ID",
    validaciones={
        "ID": {"tipo": "unico", "nulos": False},
        "Nombre": {"tipo": "texto", "nulos": False}
    },
    semaforizacion={}
)
```

## 9. Próximos pasos de la fase

1. [ ] Validar estructura de cada plantilla con usuarios clave
2. [ ] Documentar reglas de negocio específicas por indicador
3. [ ] Implementar módulo de ingesta para cada plantilla
4. [ ] Configurar validaciones y logs de calidad
5. [ ] Desarrollar panel de monitoreo de cargas

## 10. Métricas de éxito

| Indicador | Meta | Medición |
|-----------|------|----------|
| Archivos procesados exitosamente | 100% | Artefactos JSON |
| Validaciones aplicadas | 100% de schemas | Código |
| Reportes QA generados | 100% | Logs |
| Tiempo de ejecución | < 5 min | Logs |
