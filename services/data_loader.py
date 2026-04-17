"""
services/data_loader.py — Carga de datos desde xlsx con caché st.cache_data.

Fuente principal general: data/output/Resultados Consolidados.xlsx (hoja Consolidado Semestral).
Excepción: Gestión OM consume Consolidado Historico desde cargar_dataset_historico().
El Dataset_Unificado.xlsx NO es fuente oficial y NO debe usarse como origen de datos.

Regla de capas:
  - Lógica pura          → core/calculos.py
  - Configuración        → core/config.py
  - Carga con caché Streamlit → aquí (services/)
  - Mapeos de procesos   → services/procesos.py (desde config/mapeos_procesos.yaml)
"""
import unicodedata
import streamlit as st
import pandas as pd
from pathlib import Path

from core.calculos import normalizar_cumplimiento, categorizar_cumplimiento, estado_tiempo_acciones
from core.config import DATA_RAW, DATA_OUTPUT
from services.procesos import obtener_proceso_padre

# Import data validation skill
try:
    import sys
    from pathlib import Path
    skill_path = Path(__file__).resolve().parent.parent / ".github" / "skills" / "data-validation"
    if skill_path.exists():
        sys.path.insert(0, str(skill_path))
    from data_validation import enrich_with_process_hierarchy
except ImportError:
    # Fallback if skill not available
    def enrich_with_process_hierarchy(df, path):
        return df

_RENAME = {
    "Año":           "Anio",
    "Ejecución":     "Ejecucion",
    "Clasificación": "Clasificacion",
    "Ejecución s":   "Ejecucion_s",
    "Meta s":        "Meta_Signo",
}


def _ascii_lower(s: str) -> str:
    return unicodedata.normalize("NFD", str(s)).encode("ascii", "ignore").decode().lower()


def _renombrar(df: pd.DataFrame, mapa: dict) -> pd.DataFrame:
    df.columns = [str(c).strip() for c in df.columns]
    mapping = {}
    for col in df.columns:
        for orig, dest in mapa.items():
            if _ascii_lower(col) == _ascii_lower(orig):
                mapping[col] = dest
                break
    return df.rename(columns=mapping)


def _id_a_str(x) -> str:
    if pd.isna(x):
        return ""
    try:
        f = float(x)
        return str(int(f)) if f == int(f) else str(f)
    except (ValueError, TypeError):
        return str(x)


def _cargar_mapa_proceso_padre() -> dict:
    """DEPRECADO (11-abr-2026): usar services.procesos.obtener_proceso_padre() en su lugar."""
    from services.procesos import cargar_mapeos_procesos
    return cargar_mapeos_procesos()



# ─────────────────────────────────────────────────────────────────────────────
# Funciones privadas de cargar_dataset (una sola responsabilidad cada una)
# ─────────────────────────────────────────────────────────────────────────────

def _leer_consolidado_semestral(path: Path) -> pd.DataFrame:
    """Paso 1: Solo IO — leer hoja principal y normalizar columnas/IDs."""
    df = pd.read_excel(path, sheet_name="Consolidado Semestral", engine="openpyxl")
    df = _renombrar(df, _RENAME)
    if "Id" in df.columns:
        df["Id"] = df["Id"].apply(_id_a_str)
    return df


def _leer_consolidado_historico(path: Path) -> pd.DataFrame:
    """Paso 1 (OM): Solo IO — leer hoja histórico y normalizar columnas/IDs."""
    df = pd.read_excel(path, sheet_name="Consolidado Historico", engine="openpyxl")
    df = _renombrar(df, _RENAME)
    if "Id" in df.columns:
        df["Id"] = df["Id"].apply(_id_a_str)
    return df


def _enriquecer_clasificacion(df: pd.DataFrame, path: Path) -> pd.DataFrame:
    """Paso 2: Join con hoja Catalogo Indicadores para añadir Clasificacion."""
    if "Clasificacion" in df.columns:
        return df
    try:
        df_cat = pd.read_excel(path, sheet_name="Catalogo Indicadores", engine="openpyxl")
        df_cat["Id"] = df_cat["Id"].apply(_id_a_str)
        cols_cat = ["Id"] + [c for c in ["Clasificacion"] if c in df_cat.columns]
        if len(cols_cat) > 1:
            df = df.merge(df_cat[cols_cat].drop_duplicates("Id"), on="Id", how="left")
    except Exception:
        pass
    return df


def _enriquecer_cmi_y_procesos(df: pd.DataFrame) -> pd.DataFrame:
    """Paso 3: Join con CMI (Subproceso/Linea/Objetivo) y mapeo Proceso padre."""
    # CMI — NO se toma Sentido (puede estar desactualizado respecto a Kawak)
    try:
        df_cmi = pd.read_excel(
            DATA_RAW / "Indicadores por CMI.xlsx",
            sheet_name="Worksheet", engine="openpyxl",
        )
        df_cmi = _renombrar(df_cmi, _RENAME)
        df_cmi["Id"] = df_cmi["Id"].apply(_id_a_str)
        cols_cmi = ["Id"] + [c for c in ["Subproceso", "Linea", "Objetivo"] if c in df_cmi.columns]
        if len(cols_cmi) > 1:
            df = df.merge(df_cmi[cols_cmi].drop_duplicates("Id"), on="Id", how="left")
    except Exception:
        pass

    # Jerarquía de procesos oficial (Data Validation Skill)
    df = enrich_with_process_hierarchy(df, DATA_RAW / "Subproceso-Proceso-Area.xlsx")

    # Proceso padre desde YAML
    if "Proceso" in df.columns:
        df["ProcesoPadre"] = df["Proceso"].apply(obtener_proceso_padre)

    return df


def _reconstruir_columnas_formula(df: pd.DataFrame) -> pd.DataFrame:
    """Paso 4a: Recalcula columnas derivadas de fórmulas Excel (Año/Mes/Periodo)."""
    if "Fecha" not in df.columns:
        return df
    _fecha = pd.to_datetime(df["Fecha"], errors="coerce")
    _MESES_ES = {
        1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
        5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
        9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
    }
    if "Año" in df.columns:
        df["Año"] = df["Año"].fillna(_fecha.dt.year)
    if "Mes" in df.columns:
        df["Mes"] = df["Mes"].where(
            df["Mes"].notna() & (df["Mes"] != ""),
            _fecha.dt.month.map(_MESES_ES),
        )
    if "Periodo" in df.columns:
        _periodo_calc = (
            _fecha.dt.year.astype("Int64").astype(str)
            + "-"
            + _fecha.dt.month.apply(lambda m: "1" if m <= 6 else "2")
        )
        df["Periodo"] = df["Periodo"].where(
            df["Periodo"].notna() & (df["Periodo"] != ""), _periodo_calc
        )
    return df


def _aplicar_calculos_cumplimiento(df: pd.DataFrame) -> pd.DataFrame:
    """Paso 4b: Detectar métricas/sin-reporte, recalcular y categorizar cumplimiento."""
    from core.config import IDS_PLAN_ANUAL

    _col_tipo_reg = next((c for c in ["TipoRegistro", "Tipo_Registro"] if c in df.columns), None)
    _col_ejec_signo = next((c for c in ["EjecS", "Ejecucion_Signo"] if c in df.columns), None)

    # Detectar métricas
    if _col_tipo_reg:
        _mask_metrica = df[_col_tipo_reg].astype(str).str.strip().str.lower() == "metrica"
    elif "Indicador" in df.columns:
        _mask_metrica = df["Indicador"].astype(str).str.lower().str.contains(r"\bmetrica\b", na=False)
    else:
        _mask_metrica = pd.Series(False, index=df.index)

    # Detectar sin meta / No Aplica
    _mask_sin_meta = (
        pd.to_numeric(df["Meta"], errors="coerce").isna()
        | (pd.to_numeric(df["Meta"], errors="coerce") == 0)
    ) if "Meta" in df.columns else pd.Series(False, index=df.index)

    if _col_tipo_reg:
        _mask_no_aplica = df[_col_tipo_reg].astype(str).str.strip().str.lower().eq("no aplica")
    elif _col_ejec_signo:
        _mask_no_aplica = df[_col_ejec_signo].astype(str).str.strip().str.lower().eq("no aplica")
    else:
        _mask_no_aplica = pd.Series(False, index=df.index)

    _mask_sin_reporte = (~_mask_metrica) & (_mask_sin_meta | _mask_no_aplica)

    # Recalcular cumplimiento faltante
    if "Cumplimiento" in df.columns and "Meta" in df.columns and "Ejecucion" in df.columns:
        mask_nan = df["Cumplimiento"].isna() & ~_mask_metrica & ~_mask_sin_reporte
        if mask_nan.any():
            def _recalc_cumpl(row: pd.Series) -> float:
                try:
                    m, e = float(row["Meta"]), float(row["Ejecucion"])
                except (TypeError, ValueError):
                    return float("nan")
                if m == 0 or pd.isna(m) or pd.isna(e):
                    return float("nan")
                sentido = str(row.get("Sentido", "Positivo"))
                raw = (e / m) if sentido == "Positivo" else (m / e if e != 0 else float("nan"))
                if pd.isna(raw):
                    return float("nan")
                tope = 1.0 if str(row.get("Id", "")).strip() in IDS_PLAN_ANUAL else 1.3
                return min(max(raw, 0.0), tope)
            df.loc[mask_nan, "Cumplimiento"] = df[mask_nan].apply(_recalc_cumpl, axis=1)

    # Normalizar
    df["Cumplimiento_norm"] = (
        df["Cumplimiento"].apply(normalizar_cumplimiento)
        if "Cumplimiento" in df.columns
        else float("nan")
    )
    df.loc[_mask_metrica | _mask_sin_reporte, "Cumplimiento_norm"] = float("nan")

    # Categorizar
    df["Categoria"] = df.apply(
        lambda r: categorizar_cumplimiento(
            r["Cumplimiento_norm"],
            r.get("Sentido", "Positivo"),
            id_indicador=r.get("Id"),
        ),
        axis=1,
    )

    # Fechas y tipos finales
    if "Fecha" in df.columns:
        df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
    if "Anio" in df.columns:
        df["Anio"] = pd.to_numeric(df["Anio"], errors="coerce")
        if "Fecha" in df.columns and df["Anio"].isna().any():
            df["Anio"] = df["Anio"].fillna(df["Fecha"].dt.year)
        df["Anio"] = df["Anio"].astype("Int64")

    return df


# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=300, show_spinner="Cargando datos principales...")
def cargar_dataset() -> pd.DataFrame:
    """
    Carga el dataset principal desde Resultados Consolidados.xlsx (fuente oficial).
    La hoja principal general para consumo en app es Consolidado Semestral.

    Pipeline interno (cada paso tiene una sola responsabilidad):
      1. _leer_consolidado_semestral()    → IO + renombrar columnas
      2. _enriquecer_clasificacion()      → join Catalogo Indicadores
      3. _enriquecer_cmi_y_procesos()     → join CMI + mapeo procesos
      4. _reconstruir_columnas_formula()  → Año/Mes/Periodo desde Fecha
      5. _aplicar_calculos_cumplimiento() → normalizar + categorizar

    El Sentido se toma SIEMPRE del Consolidado (calculado desde Kawak/API).
    """
    path = DATA_OUTPUT / "Resultados Consolidados.xlsx"
    if not path.exists():
        st.error(f"Archivo no encontrado: {path}")
        return pd.DataFrame()

    df = _leer_consolidado_semestral(path)
    df = _enriquecer_clasificacion(df, path)
    df = _enriquecer_cmi_y_procesos(df)
    df = _reconstruir_columnas_formula(df)
    df = _aplicar_calculos_cumplimiento(df)
    return df


@st.cache_data(ttl=300, show_spinner="Cargando datos históricos para Gestión OM...")
def cargar_dataset_historico() -> pd.DataFrame:
    """
    Carga la hoja Consolidado Historico para casos específicos de Gestión OM.
    No reemplaza la fuente general del resto de módulos.
    """
    path = DATA_OUTPUT / "Resultados Consolidados.xlsx"
    if not path.exists():
        st.error(f"Archivo no encontrado: {path}")
        return pd.DataFrame()

    df = _leer_consolidado_historico(path)
    df = _enriquecer_clasificacion(df, path)
    df = _enriquecer_cmi_y_procesos(df)
    df = _reconstruir_columnas_formula(df)
    df = _aplicar_calculos_cumplimiento(df)
    return df


@st.cache_data(ttl=300, show_spinner="Cargando acciones de mejora...")
def cargar_acciones_mejora() -> pd.DataFrame:
    path = DATA_RAW / "acciones_mejora.xlsx"
    if not path.exists():
        st.error(f"Archivo no encontrado: {path}")
        return pd.DataFrame()

    df = pd.read_excel(path, sheet_name="Acciones", engine="openpyxl")
    df.columns = [str(c).strip() for c in df.columns]

    for col in ["FECHA_IDENTIFICACION", "FECHA_ESTIMADA_CIERRE", "FECHA_CIERRE", "FECHA_CREACION"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    for col in ["DIAS_VENCIDA", "MESES_SIN_AVANCE", "AVANCE"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    df = estado_tiempo_acciones(df)
    return df


@st.cache_data(ttl=300, show_spinner="Cargando ficha técnica...")
def cargar_ficha_tecnica() -> pd.DataFrame:
    path = DATA_RAW / "Ficha_Tecnica.xlsx"
    if not path.exists():
        return pd.DataFrame()

    df = pd.read_excel(path, sheet_name="Hoja1", engine="openpyxl")
    df.columns = [str(c).strip() for c in df.columns]
    if "Id Ind" in df.columns:
        df["Id"] = df["Id Ind"].apply(_id_a_str)
    return df


def _leer_excel(path: Path, header: int = 0) -> pd.DataFrame:
    """Lee .xlsx (openpyxl) o .xls (xlrd) con preferencia por .xlsx."""
    xlsx = path.with_suffix(".xlsx")
    if path.suffix.lower() == ".xls" and xlsx.exists():
        path = xlsx
    ext = path.suffix.lower()
    if ext == ".xlsx":
        return pd.read_excel(str(path), header=header, engine="openpyxl")
    return pd.read_excel(str(path), header=header, engine="xlrd")


@st.cache_data(ttl=300, show_spinner="Cargando Oportunidades de Mejora...")
def cargar_om() -> pd.DataFrame:
    """Carga OM.xlsx (preferido) o OM.xls. Encabezados en fila 8 (header=7)."""
    xlsx = DATA_RAW / "OM.xlsx"
    xls  = DATA_RAW / "OM.xls"

    if xlsx.exists():
        path, header = xlsx, 7
    elif xls.exists():
        path, header = xls, 7
    else:
        return pd.DataFrame()

    try:
        engine = "openpyxl" if path.suffix.lower() == ".xlsx" else "xlrd"
        df = pd.read_excel(str(path), header=header, engine=engine)
    except Exception as e:
        st.error(f"Error leyendo {path.name}: {e}")
        return pd.DataFrame()

    df.columns = [str(c).strip() for c in df.columns]
    df = df.dropna(how="all").reset_index(drop=True)

    if "Id" in df.columns:
        df = df[df["Id"].notna() & (df["Id"].astype(str).str.strip() != "")].reset_index(drop=True)
        df["Id"] = df["Id"].apply(_id_a_str)

    for col in ["Fecha de identificación", "Fecha de creación",
                "Fecha estimada de cierre", "Fecha real de cierre"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    col_av = next((c for c in df.columns if "avance" in c.lower()), None)
    if col_av:
        df[col_av] = pd.to_numeric(df[col_av], errors="coerce")
        mask = df[col_av].notna()
        if mask.any() and df.loc[mask, col_av].max() <= 1.5:
            df[col_av] = df[col_av] * 100

    return df


@st.cache_data(ttl=300, show_spinner="Cargando Plan de Acción...")
def cargar_plan_accion() -> pd.DataFrame:
    """Consolida todos los archivos de data/raw/Plan de accion/. Prioriza .xlsx sobre .xls."""
    folder = DATA_RAW / "Plan de accion"
    if not folder.exists():
        return pd.DataFrame()

    xlsx_stems = {p.stem for p in folder.glob("*.xlsx")}
    archivos = []
    for p in sorted(folder.iterdir()):
        ext = p.suffix.lower()
        if ext == ".xlsx":
            archivos.append(p)
        elif ext == ".xls" and p.stem not in xlsx_stems:
            archivos.append(p)

    frames = []
    for p in archivos:
        try:
            engine = "openpyxl" if p.suffix.lower() == ".xlsx" else "xlrd"
            df = pd.read_excel(str(p), engine=engine)
            df.columns = [str(c).strip() for c in df.columns]
            df = df.dropna(how="all").reset_index(drop=True)
            frames.append(df)
        except Exception as e:
            print(f"[data_loader] No se pudo leer {p.name}: {e}")

    if not frames:
        return pd.DataFrame()

    df_all = pd.concat(frames, ignore_index=True)

    for col in df_all.columns:
        if any(kw in col.lower() for kw in ["fecha", "ejecuci", "seguimiento", "evaluaci"]):
            try:
                df_all[col] = pd.to_datetime(df_all[col], errors="coerce")
            except Exception:
                pass

    col_av = next((c for c in df_all.columns if "avance" in c.lower()), None)
    if col_av:
        df_all[col_av] = pd.to_numeric(df_all[col_av], errors="coerce")
        mask = df_all[col_av].notna()
        if mask.any() and df_all.loc[mask, col_av].max() <= 1.5:
            df_all[col_av] = df_all[col_av] * 100

    for col in df_all.columns:
        if "id oportunidad" in col.lower():
            df_all[col] = df_all[col].apply(_id_a_str)

    return df_all


@st.cache_data(ttl=300, show_spinner=False)
def cargar_analisis_usuarios() -> pd.DataFrame:
    """
    Carga la hoja 'Desglose Analisis' de Resultados Consolidados.xlsx.
    Retorna columnas: Id (str), fecha, analisis_fecha, analisis_autor, analisis_texto.
    """
    path = DATA_OUTPUT / "Resultados Consolidados.xlsx"
    if not path.exists():
        return pd.DataFrame()
    try:
        df = pd.read_excel(path, sheet_name="Desglose Analisis", engine="openpyxl")
        df.columns = [str(c).strip() for c in df.columns]
        if "Id" in df.columns:
            df["Id"] = df["Id"].apply(_id_a_str)
        for col in ("analisis_fecha", "fecha"):
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")
        return df
    except Exception:
        return pd.DataFrame()


def df_indicadores_unicos(df: pd.DataFrame) -> pd.DataFrame:
    """Retorna un registro único por Id (el más reciente por Fecha)."""
    if df.empty or "Id" not in df.columns:
        return df
    if "Revisar" in df.columns:
        revisar = pd.to_numeric(df["Revisar"], errors="coerce").fillna(0)
        return df[revisar == 1].drop_duplicates(subset="Id", keep="first").reset_index(drop=True)
    col_fecha = "Fecha" if "Fecha" in df.columns else None
    if col_fecha:
        return df.sort_values(col_fecha).drop_duplicates(subset="Id", keep="last").reset_index(drop=True)
    return df.drop_duplicates(subset="Id", keep="last").reset_index(drop=True)


def construir_opciones_indicadores(df: pd.DataFrame) -> dict:
    """Retorna dict {label: id_str} con etiquetas 'Id — Nombre' únicas."""
    if df.empty or "Id" not in df.columns:
        return {}
    unicos = df_indicadores_unicos(df)
    sub = unicos[["Id", "Indicador"]].dropna(subset=["Id"])
    sub = sub[sub["Id"] != ""]
    opciones = {}
    for _, row in sub.iterrows():
        label = f"{row['Id']} — {row.get('Indicador', '')}"
        opciones[label] = row["Id"]
    return dict(sorted(opciones.items()))
