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


@st.cache_data(ttl=300, show_spinner="Cargando reporte de seguimiento...")
def cargar_seguimiento_reporte() -> dict:
    """
    Carga Seguimiento_Reporte.xlsx (generado por generar_reporte.py).

    Retorna dict con:
      "seguimiento"  : DataFrame hoja Seguimiento (Revisar==1 ya filtrado)
      "resumen"      : DataFrame hoja Resumen
      "periodicidades": dict {nombre_hoja: DataFrame} por cada hoja de periodicidad
                        (Revisar==1 filtrado, col. de período como strings dd/mm/yyyy)
    """
    from datetime import datetime

    path = DATA_RAW / "Seguimiento_Reporte.xlsx"
    if not path.exists():
        return {}

    xl = pd.ExcelFile(path, engine="openpyxl")
    hojas = xl.sheet_names

    resultado = {"seguimiento": pd.DataFrame(), "resumen": pd.DataFrame(), "periodicidades": {}}

    # ── Hoja Seguimiento ──────────────────────────────────────────────────────
    if "Seguimiento" in hojas:
        df_seg = xl.parse("Seguimiento")
        df_seg.columns = [str(c).strip() for c in df_seg.columns]
        if "Revisar" in df_seg.columns:
            df_seg["Revisar"] = pd.to_numeric(df_seg["Revisar"], errors="coerce").fillna(0)
            df_seg = df_seg[df_seg["Revisar"] == 1].reset_index(drop=True)
        if "Id" in df_seg.columns:
            df_seg["Id"] = df_seg["Id"].apply(_id_a_str)
        resultado["seguimiento"] = df_seg

    # ── Hoja Resumen ──────────────────────────────────────────────────────────
    if "Resumen" in hojas:
        df_res = xl.parse("Resumen")
        df_res.columns = [str(c).strip() for c in df_res.columns]
        resultado["resumen"] = df_res

    # ── Hojas de periodicidad ─────────────────────────────────────────────────
    CORTE = datetime(2024, 1, 1)
    hojas_perio = [h for h in hojas if h not in ("Seguimiento", "Resumen")]

    for hoja in hojas_perio:
        df_p = xl.parse(hoja)
        df_p.columns = [str(c).strip() for c in df_p.columns]

        # Filtrar Revisar==1
        if "Revisar" in df_p.columns:
            df_p["Revisar"] = pd.to_numeric(df_p["Revisar"], errors="coerce").fillna(0)
            df_p = df_p[df_p["Revisar"] == 1].reset_index(drop=True)

        if "Id" in df_p.columns:
            df_p["Id"] = df_p["Id"].apply(_id_a_str)

        # Identificar columnas de período (formato dd/mm/yyyy) y filtrar desde 2024
        cols_fecha = []
        for col in df_p.columns:
            try:
                d = datetime.strptime(str(col), "%d/%m/%Y")
                if d >= CORTE:
                    cols_fecha.append(col)
            except ValueError:
                pass

        # Ordenar fechas ascendente
        cols_fecha_ord = sorted(cols_fecha, key=lambda c: datetime.strptime(c, "%d/%m/%Y"))

        df_p.attrs["cols_periodo"] = cols_fecha_ord
        resultado["periodicidades"][hoja] = df_p

    return resultado


def construir_opciones_indicadores(df: pd.DataFrame) -> dict:
    """
    Retorna dict {label: id_str} con etiquetas "Id — Nombre" únicas.
    """
    if df.empty or "Id" not in df.columns:
        return {}
    sub = df[["Id", "Indicador"]].drop_duplicates(subset="Id").dropna(subset=["Id"])
    sub = sub[sub["Id"] != ""]
    opciones = {}
    for _, row in sub.iterrows():
        label = f"{row['Id']} — {row.get('Indicador', '')}"
        opciones[label] = row["Id"]
    return dict(sorted(opciones.items()))
