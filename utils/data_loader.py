"""
utils/data_loader.py — Carga de datos desde xlsx con caché st.cache_data.
"""
import unicodedata
import streamlit as st
import pandas as pd
from pathlib import Path

from utils.calculos import normalizar_cumplimiento, categorizar_cumplimiento

DATA_RAW = Path(__file__).parent.parent / "data" / "raw"

_RENAME = {
    "Año":           "Anio",
    "Ejecución":     "Ejecucion",
    "Clasificación": "Clasificacion",
    "Ejecución s":   "Ejecucion_s",
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


@st.cache_data(ttl=300, show_spinner="Cargando datos principales...")
def cargar_dataset() -> pd.DataFrame:
    path = DATA_RAW / "Dataset_Unificado.xlsx"
    if not path.exists():
        st.error(f"Archivo no encontrado: {path}")
        return pd.DataFrame()

    df = pd.read_excel(path, sheet_name="Unificado", engine="openpyxl")
    df = _renombrar(df, _RENAME)

    # Normalizar cumplimiento
    if "Cumplimiento" in df.columns:
        df["Cumplimiento_norm"] = df["Cumplimiento"].apply(normalizar_cumplimiento)
    else:
        df["Cumplimiento_norm"] = float("nan")

    # Categorizar
    df["Categoria"] = df.apply(
        lambda r: categorizar_cumplimiento(
            r["Cumplimiento_norm"],
            r.get("Sentido", "Positivo"),
        ),
        axis=1,
    )

    # Fechas
    if "Fecha" in df.columns:
        df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")

    # Año como Int64
    if "Anio" in df.columns:
        df["Anio"] = pd.to_numeric(df["Anio"], errors="coerce").astype("Int64")

    # Id como string limpio
    if "Id" in df.columns:
        df["Id"] = df["Id"].apply(_id_a_str)

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

    # Estado_Tiempo
    df["Estado_Tiempo"] = "A tiempo"
    if "DIAS_VENCIDA" in df.columns and "ESTADO" in df.columns:
        df.loc[df["DIAS_VENCIDA"] > 0, "Estado_Tiempo"] = "Vencida"
        df.loc[
            (df["DIAS_VENCIDA"] >= -30)
            & (df["DIAS_VENCIDA"] <= 0)
            & (df["ESTADO"] != "Cerrada"),
            "Estado_Tiempo",
        ] = "Por vencer"
        df.loc[df["ESTADO"] == "Cerrada", "Estado_Tiempo"] = "Cerrada"

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


def df_indicadores_unicos(df: pd.DataFrame) -> pd.DataFrame:
    """
    Retorna solo las filas que representan indicadores únicos.
    Prioridad:
      1. Si existe columna 'Revisar', filtra Revisar == 1 y luego deduplica por Id.
      2. Si no existe, deduplica por Id (keep='last' para tomar el registro más reciente).
    """
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
    """
    Retorna dict {label: id_str} con etiquetas "Id — Nombre" únicas.
    Usa Revisar == 1 si la columna existe; si no, deduplica por Id.
    """
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
