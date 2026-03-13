"""
utils/data_loader.py — Carga de datos desde xlsx con caché st.cache_data.

Fuente principal: data/output/Resultados Consolidados.xlsx (hoja Consolidado Semestral).
El Dataset_Unificado.xlsx NO es fuente oficial y NO debe usarse como origen de datos.
"""
import unicodedata
import streamlit as st
import pandas as pd
from pathlib import Path

from utils.calculos import normalizar_cumplimiento, categorizar_cumplimiento, estado_tiempo_acciones

DATA_RAW    = Path(__file__).parent.parent / "data" / "raw"
DATA_OUTPUT = Path(__file__).parent.parent / "data" / "output"

_RENAME = {
    "Año":           "Anio",
    "Ejecución":     "Ejecucion",
    "Clasificación": "Clasificacion",
    "Ejecución s":   "Ejecucion_s",
    "Meta s":        "Meta_Signo",
    "Ejecución s":   "Ejec_Signo",
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
    """
    Carga el dataset principal desde Resultados Consolidados.xlsx (fuente oficial).
    Enriquece con Clasificacion (Catálogo) y Subproceso/Linea (CMI).
    El Sentido se toma SIEMPRE del Consolidado (calculado desde Kawak/API).
    """
    path = DATA_OUTPUT / "Resultados Consolidados.xlsx"
    if not path.exists():
        st.error(f"Archivo no encontrado: {path}")
        return pd.DataFrame()

    df = pd.read_excel(path, sheet_name="Consolidado Semestral", engine="openpyxl")
    df = _renombrar(df, _RENAME)

    # Id como string limpio (hacer antes de los joins)
    if "Id" in df.columns:
        df["Id"] = df["Id"].apply(_id_a_str)

    # ── Enriquecer con Clasificacion desde Catalogo Indicadores ──────────────
    if "Clasificacion" not in df.columns:
        try:
            df_cat = pd.read_excel(path, sheet_name="Catalogo Indicadores", engine="openpyxl")
            df_cat["Id"] = df_cat["Id"].apply(_id_a_str)
            cols_cat = ["Id"] + [c for c in ["Clasificacion"] if c in df_cat.columns]
            if len(cols_cat) > 1:
                df = df.merge(df_cat[cols_cat].drop_duplicates("Id"), on="Id", how="left")
        except Exception:
            pass

    # ── Enriquecer con Subproceso y Linea desde Indicadores por CMI ──────────
    # (NO se toma Sentido del CMI — puede estar desactualizado)
    try:
        df_cmi = pd.read_excel(
            DATA_RAW / "Indicadores por CMI.xlsx",
            sheet_name="Worksheet", engine="openpyxl",
        )
        df_cmi = _renombrar(df_cmi, _RENAME)
        df_cmi["Id"] = df_cmi["Id"].apply(_id_a_str)
        cols_cmi = ["Id"] + [c for c in ["Subproceso", "Linea", "Objetivo"]
                             if c in df_cmi.columns]
        if len(cols_cmi) > 1:
            df = df.merge(df_cmi[cols_cmi].drop_duplicates("Id"), on="Id", how="left")
    except Exception:
        pass

    # ── Normalizar cumplimiento ───────────────────────────────────────────────
    if "Cumplimiento" in df.columns:
        df["Cumplimiento_norm"] = df["Cumplimiento"].apply(normalizar_cumplimiento)
    else:
        df["Cumplimiento_norm"] = float("nan")

    # ── Categorizar ───────────────────────────────────────────────────────────
    df["Categoria"] = df.apply(
        lambda r: categorizar_cumplimiento(
            r["Cumplimiento_norm"],
            r.get("Sentido", "Positivo"),
        ),
        axis=1,
    )

    # ── Fechas ────────────────────────────────────────────────────────────────
    if "Fecha" in df.columns:
        df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")

    # ── Año como Int64 ────────────────────────────────────────────────────────
    if "Anio" in df.columns:
        df["Anio"] = pd.to_numeric(df["Anio"], errors="coerce").astype("Int64")

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
    """
    Lee un archivo Excel (.xlsx preferido, .xls como fallback con xlrd).
    Si la ruta apunta a .xls pero existe la versión .xlsx, usa la .xlsx.
    """
    # Preferir .xlsx si existe
    xlsx = path.with_suffix(".xlsx")
    if path.suffix.lower() == ".xls" and xlsx.exists():
        path = xlsx

    ext = path.suffix.lower()
    if ext == ".xlsx":
        return pd.read_excel(str(path), header=header, engine="openpyxl")
    # Fallback .xls → requiere xlrd
    return pd.read_excel(str(path), header=header, engine="xlrd")


@st.cache_data(ttl=300, show_spinner="Cargando Oportunidades de Mejora...")
def cargar_om() -> pd.DataFrame:
    """
    Carga OM.xlsx (preferido) o OM.xls.
    · OM.xlsx (convertido): encabezados ya en fila 1 → header=0
    · OM.xls  (original):   encabezados en fila 8   → header=7
    """
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

    # Eliminar filas sin Id
    if "Id" in df.columns:
        df = df[df["Id"].notna() & (df["Id"].astype(str).str.strip() != "")].reset_index(drop=True)
        df["Id"] = df["Id"].apply(_id_a_str)

    # Fechas
    for col in ["Fecha de identificación", "Fecha de creación",
                "Fecha estimada de cierre", "Fecha real de cierre"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    # Avance: normalizar a escala 0-100
    col_av = next((c for c in df.columns if "avance" in c.lower()), None)
    if col_av:
        df[col_av] = pd.to_numeric(df[col_av], errors="coerce")
        mask = df[col_av].notna()
        if mask.any() and df.loc[mask, col_av].max() <= 1.5:
            df[col_av] = df[col_av] * 100

    return df


@st.cache_data(ttl=300, show_spinner="Cargando Plan de Acción...")
def cargar_plan_accion() -> pd.DataFrame:
    """
    Consolida todos los archivos de data/raw/Plan de accion/.
    Prioriza .xlsx sobre .xls (mismo nombre base).
    """
    folder = DATA_RAW / "Plan de accion"
    if not folder.exists():
        return pd.DataFrame()

    # Construir lista sin duplicados: si existe .xlsx, omitir el .xls homónimo
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
            st.warning(f"No se pudo leer **{p.name}**: {e}")

    if not frames:
        return pd.DataFrame()

    df_all = pd.concat(frames, ignore_index=True)

    # Fechas
    for col in df_all.columns:
        low = col.lower()
        if any(kw in low for kw in ["fecha", "ejecuci", "seguimiento", "evaluaci"]):
            try:
                df_all[col] = pd.to_datetime(df_all[col], errors="coerce")
            except Exception:
                pass

    # Avance 0-100
    col_av = next((c for c in df_all.columns if "avance" in c.lower()), None)
    if col_av:
        df_all[col_av] = pd.to_numeric(df_all[col_av], errors="coerce")
        mask = df_all[col_av].notna()
        if mask.any() and df_all.loc[mask, col_av].max() <= 1.5:
            df_all[col_av] = df_all[col_av] * 100

    # Id Oportunidad de mejora como string
    for col in df_all.columns:
        if "id oportunidad" in col.lower():
            df_all[col] = df_all[col].apply(_id_a_str)

    return df_all


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
