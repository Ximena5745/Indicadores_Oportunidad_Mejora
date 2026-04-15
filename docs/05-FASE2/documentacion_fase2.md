# Documentación Técnica - Fase 2: Motor de Consolidación y Reglas

## 1. Resumen de la fase

La Fase 2 tiene como objetivo automatizar la consolidación y el control de reglas de negocio, migrando la lógica ETL legacy a un framework modular e implementando un motor de reglas y alertas.

## 2. Componentes implementados

### 2.1 Motor de Reglas (`consolidation/core/rules_engine.py`)

#### Responsabilidades
- Definir y aplicar reglas de negocio por indicador
- Generar alertas automáticas (semaforización, umbrales)
- Detectar anomalías y variaciones abruptas
- Soportar personalización de reglas por perfil

#### Reglas implementadas por defecto

| ID | Nombre | Tipo | Prioridad | Descripción |
|----|--------|------|-----------|-------------|
| semaforizacion | Semaforización de Cumplimiento | rango_cumplimiento | 1 | Clasifica cumplimiento en niveles según rangos |
| variacion_abrupta | Variación Arupta | variacion | 2 | Detecta cambios bruscos >20% |
| tendencia_descendente | Tendencia Descendente | tendencia | 3 | Detecta tendencia negativa en últimos 3 periodos |
| falta_actualizacion | Falta de Actualización | actualizacion | 2 | Alerta si indicador no actualizado en periodo esperado |
| nulos_excesivos | Nulos Excesivos | nulos | 3 | Detecta >10% valores nulos |

#### Semaforización estándar

| Nivel | Rango de cumplimiento | Color | Descripción |
|-------|---------------------|-------|-------------|
| Crítico | < 70% o > 120% | 🔴 | Requiere atención inmediata |
| Atención | 70-80% o 105-120% | 🟡 | Monitorear de cerca |
| Normal | 80-105% | 🟢 | Dentro de parámetros esperados |

#### Uso del motor de reglas

```python
from scripts.consolidation.core.rules_engine import RulesEngine, NivelAlerta

# Crear motor
motor = RulesEngine()

# Evaluar reglas sobre DataFrame
resultados = motor.evaluar_todo(df)

# Generar alertas formales
alertas = motor.generar_alertas(resultados)

# Exportar a DataFrame
df_alertas = motor.exportar_alertas("df")
```

#### Agregar reglas customizadas

```python
from scripts.consolidation.core.rules_engine import RulesEngine, Regla, TipoRegla

motor = RulesEngine()

motor.agregar_regla(Regla(
    id="mi_regla_custom",
    nombre="Mi Regla Customizada",
    tipo=TipoRegla.RANGO_CUMPLIMIENTO,
    descripcion="Descripción de la regla",
    configuracion={
        "campo": "Cumplimiento",
        "rangos": {
            "critico_low": 0.60,
            "atencion_low": 0.75,
            "normal_low": 0.75,
            "normal_high": 1.10,
            "atencion_high": 1.30,
            "critico_high": 1.30
        }
    },
    prioridad=1
))
```

---

### 2.2 Motor de Auditoría (`consolidation/core/audit.py`)

#### Responsabilidades
- Registrar todas las operaciones del pipeline
- Versionar artefactos generados
- Mantener trazabilidad end-to-end
- Generar reportes de auditoría

#### Estructura de directorios

```
data/output/
├── audit/
│   ├── audit_YYYYMMDD_HHMMSS.log    # Log de operaciones
│   └── run_RUN-YYYYMMDD_HHMMSS.json # Reporte de pipeline run
├── versions/
│   └── {nombre}_{version}.json       # Metadata de artefactos versionados
└── artifacts/
    └── ingesta_YYYYMMDD_HHMMSS.json  # Artefactos de ingesta
```

#### Tipos de operaciones auditadas

| Tipo | Descripción |
|------|-------------|
| EXTRACCION | Extracción de datos de fuentes |
| TRANSFORMACION | Transformación y normalización |
| CONSOLIDACION | Consolidación de múltiples fuentes |
| VALIDACION | Validaciones de calidad |
| ALERTA | Generación de alertas |
| EXPORTACION | Exportación de artefactos |
| ERROR | Errores procesados |

#### Uso del motor de auditoría

```python
from scripts.consolidation.core.audit import AuditEngine, TipoOperacion, TipoArtefacto
from pathlib import Path

# Crear motor
audit = AuditEngine(Path("data/output"))

# Registrar operación
audit.registrar_operacion(
    operacion=TipoOperacion.CONSOLIDACION,
    detalle="Consolidación mensual de indicadores",
    registros_procesados=100,
    registros_exitosos=95,
    registros_fallidos=5
)

# Versionar artefacto
artefacto = audit.versionar_artefacto(
    nombre="consolidado_mensual",
    tipo=TipoArtefacto.DATASET,
    ruta=Path("data/output/consolidado.xlsx"),
    pipeline_run="RUN-20260406"
)

# Generar reporte
reporte = audit.generar_reporte_auditoria()
print(reporte)
```

---

## 3. Integración con framework existente

### 3.1 Flujo de integración

```
scripts/ingesta_plantillas.py (Fase 1)
    │
    ▼
consolidation/main.py (orquestador)
    │
    ├──► extraction (extractors/)
    │       │
    ├──► rules_engine (core/rules_engine.py)
    │       │       └──► Validación de reglas de negocio
    │       │       └──► Generación de alertas
    │       │
    ├──► audit (core/audit.py)
    │       │       └──► Registro de operaciones
    │       │       └──► Versionado de artefactos
    │       │
    └──► output (loaders/)
            └──► Generación de artefactos
```

### 3.2 Punto de integración en orchestrator.py

```python
# En consolidation/pipeline/orchestrator.py

from ..core.rules_engine import RulesEngine, NivelAlerta
from ..core.audit import AuditEngine, TipoOperacion

class ConsolidationOrchestrator:
    def __init__(self):
        # ... código existente ...
        self.rules_engine = RulesEngine()
        self.audit_engine = AuditEngine(self.paths['OUTPUT_PATH'])
    
    def run(self):
        # Iniciar pipeline run
        run_id = self.audit_engine.iniciar_pipeline_run()
        
        # ... ejecución del pipeline ...
        
        # Registrar operación
        self.audit_engine.registrar_operacion(
            operacion=TipoOperacion.CONSOLIDACION,
            detalle="Consolidación completada",
            pipeline_run=run_id,
            registros_procesados=len(processed)
        )
        
        # Evaluar reglas
        alertas = self.rules_engine.evaluar_todo(processed)
        alertas_df = self.rules_engine.exportar_alertas("df")
        
        # Versionar output
        self.audit_engine.versionar_artefacto(
            nombre="consolidado",
            tipo=TipoArtefacto.DATASET,
            ruta=output_file,
            pipeline_run=run_id
        )
```

---

## 4. Artefactos generados

### 4.1 Artefactos de la Fase 2

| Artefacto | Ubicación | Descripción |
|-----------|-----------|-------------|
| rules_engine.py | scripts/consolidation/core/ | Motor de reglas y alertas |
| audit.py | scripts/consolidation/core/ | Motor de auditoría y versionado |
| Metadata de versionado | data/output/versions/ | JSON con historial de versiones |
| Logs de auditoría | data/output/audit/ | Logs de operaciones |
| Reportes de pipeline | data/output/audit/run_*.json | Resumen de ejecuciones |

---

## 5. Métricas de éxito

| Indicador | Meta | Medición |
|-----------|------|----------|
| Reglas implementadas | 100% de las definidas | Código |
| Alertas generadas | >0 por ejecución | Logs |
| Artefactos versionados | 100% | Metadata |
| Pipeline runs registrados | 100% | Reportes |
| Trazabilidad end-to-end | Completa | Auditoría |

---

## 6. Próximos pasos

1. [ ] Integrar rules_engine con orchestrator existente
2. [ ] Integrar audit con orchestrator existente
3. [ ] Ejecutar pipeline completo con nuevas funcionalidades
4. [ ] Validar alertas generadas con usuarios clave
5. [ ] Documentar reglas específicas por indicador
