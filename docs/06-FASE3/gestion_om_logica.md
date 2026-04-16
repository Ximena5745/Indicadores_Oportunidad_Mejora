# Gestión OM - Lógica de Cálculo de Avance

## Descripción

La funcionalidad de **Gestión de Oportunidades de Mejora (OM)** permite registrar y hacer seguimiento de las acciones correctivas asociadas a indicadores en estado de "Peligro".

## Cálculo de Avance de OM

### Fuente de Datos

El avance de las OM se calcula a partir de los archivos ubicados en:
```
data/raw/Plan de accion/
├── PA_1.xlsx
├── PA_2.xlsx
└── ... (otros archivos .xlsx)
```

### Estructura de Archivos

Cada archivo debe contener las siguientes columnas:
- `Id Acción`: Identificador único de la acción
- `Avance (%)`: Porcentaje de avance (0-100)
- `Id Oportunidad de mejora`: Número de OM asociada al indicador

### Algoritmo de Cálculo

1. **Lectura**: Se leen todos los archivos Excel de la carpeta `Plan de accion`
2. **Unión**: Se concatenan en un único DataFrame
3. **Limpieza**: Se eliminan registros sin Id de OM o sin avance
4. **Agrupación**: Se agrupa por `Id Oportunidad de mejora`
5. **Promedio**: Se calcula el promedio del campo `Avance (%)` por cada Id de OM
6. **Resultado**: Se genera un diccionario `{id_om: avance_promedio}`

```python
def _cargar_avance_om() -> dict:
    """
    Carga los archivos de Plan de accion y calcula el avance promedio por Id Oportunidad de mejora.
    Retorna: {id_oportunidad: avance_promedio}
    """
    base_path = Path("data/raw/Plan de accion")
    dfs = []
    
    for f in base_path.glob("*.xlsx"):
        df = pd.read_excel(f, dtype=str, na_filter=False)
        # Extraer columnas relevantes
        df_subset = df[["Id Acción", "Avance (%)", "Id Oportunidad de mejora"]]
        dfs.append(df_subset)
    
    df_all = pd.concat(dfs, ignore_index=True)
    df_all["Avance (%)"] = pd.to_numeric(df_all["Avance (%)"], errors="coerce")
    
    # Agrupar por Id Oportunidad de mejora y promediar
    resultado = df_all.groupby("Id Oportunidad de mejora")["Avance (%)"].mean().to_dict()
    
    return {str(k): round(v, 1) for k, v in resultado.items()}
```

### Integración con la Tabla de Indicadores

El avance calculado se integra en la tabla de la siguiente manera:

1. Al cargar los datos de OM, también se llama a `_cargar_avance_om()`
2. En `_resumen_om_por_id()` se recibe el diccionario de avances como parámetro
3. Para cada indicador con OM, se busca el avance en el diccionario usando el número de OM
4. Si no hay datos de avance, se usa 100% por defecto (para OM activas sin plan de acción)

```python
def _resumen_om_por_id(df_reg: pd.DataFrame, avances_om: dict = None) -> pd.DataFrame:
    # ... procesamiento ...
    
    if avances_om:
        out["avance_om"] = out["identificador"].apply(
            lambda x: avances_om.get(str(x).strip(), 0)
        )
    else:
        out["avance_om"] = out["tiene_om"].apply(lambda x: 100 if x == 1 else 0)
```

## Columnas de la Tabla

| Columna | Descripción |
|---------|-------------|
| **Meta** | Meta del indicador para el período |
| **Ejecución** | Ejecución real del período |
| **Cumplimiento** | Porcentaje de cumplimiento con icono por nivel |
| **Subproceso** | Subproceso al que pertenece el indicador |
| **Id** | Identificador único del indicador |
| **Indicador** | Nombre del indicador |
| **Periodicidad** | Frecuencia de reporte |
| **Categoria** | Nivel de cumplimiento (Peligro/Alerta) |
| **Tipo de Acción** | Tipo de OM asignada (OM Kawak, Reto, Proyecto, Otro) |
| **OM** | Identificador de la acción |
| **Avance OM** | Porcentaje de avance de la OM (desde archivos Plan de accion) |

## Tipos de Acción

| Tipo | Color en UI |
|------|------------|
| OM Kawak | 🔵 Azul (#3B82F6) |
| Reto Plan Anual | 🟠 Naranja (#F59E0B) |
| Proyecto Institucional | 🟣 Púrpura (#8B5CF6) |
| Otro | ⚪ Gris (#6B7280) |
| Sin acción | ⚪ Gris claro (#9CA3AF) |

## Notas

- El avance de OM solo se muestra si existe un plan de acción asociado en los archivos de `Plan de accion`
- Si no hay datos de avance, se muestra "-" en la tabla
- La función `_cargar_avance_om()` tiene cache de 1 hora para evitar lecturas repetitivas