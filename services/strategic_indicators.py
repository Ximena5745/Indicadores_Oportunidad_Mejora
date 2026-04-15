from __future__ import annotations

import unicodedata
from pathlib import Path

import pandas as pd
import streamlit as st

from core.config import (
    IDS_PLAN_ANUAL, IDS_TOPE_100, CACHE_TTL,
    NIVEL_COLOR, UMBRAL_ALERTA, UMBRAL_PELIGRO, UMBRAL_SOBRECUMPLIMIENTO
)
from core import calculos as _calculos

# Aliases decimales para compatibilidad
UMBRAL_ALERTA_DEC = UMBRAL_ALERTA
UMBRAL_PELIGRO_DEC = UMBRAL_PELIGRO
UMBRAL_SOBRECUMPLIMIENTO_DEC = UMBRAL_SOBRECUMPLIMIENTO

ROOT = Path(__file__).resolve().parents[2]
RAW_XLSX = ROOT / "data" / "raw" / "Indicadores por CMI.xlsx"
OUT_XLSX = ROOT / "data" / "output" / "Resultados Consolidados.xlsx"

NO_APLICA = "No aplica"
PENDIENTE = "Pendiente de reporte"
METRICA = "Metrica"
SOBRECUMPLIMIENTO = "Sobrecumplimiento"

NIVEL_COLOR_EXT = {
    **NIVEL_COLOR,
    NO_APLICA: "#78909C",
    PENDIENTE: "#BDBDBD",
}


def _norm_text(value: str) -> str:
    text = str(value or "").strip().lower()
    text = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in text if unicodedata.category(ch) != "Mn")


def _find_col(df: pd.DataFrame, names: list[str]) -> str | None:
    lookup = {_norm_text(c): c for c in df.columns}
    for name in names:
        hit = lookup.get(_norm_text(name))
        if hit:
            return hit
    return None


def _id_limpio(x) -> str:
    if pd.isna(x):
        return ""
    try:
        f = float(x)
        return str(int(f)) if f == int(f) else str(f)
    except (ValueError, TypeError):
        return str(x).strip()


def _nivel_desde_cumplimiento(cumplimiento_dec) -> str:
    try:
        c = float(cumplimiento_dec)
    except (TypeError, ValueError):
        return PENDIENTE
    if c >= UMBRAL_SOBRECUMPLIMIENTO_DEC:
        return SOBRECUMPLIMIENTO
    if c >= UMBRAL_ALERTA_DEC:
        return "Cumplimiento"
    if c >= UMBRAL_PELIGRO_DEC:
        return "Alerta"
    return "Peligro"


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def load_pdi_catalog() -> pd.DataFrame:
    if not RAW_XLSX.exists():
        return pd.DataFrame(columns=["Linea", "Objetivo"])
    try:
        df = pd.read_excel(RAW_XLSX, sheet_name="PDI", engine="openpyxl")
    except Exception:
        return pd.DataFrame(columns=["Linea", "Objetivo"])

    df.columns = [str(c).strip() for c in df.columns]
    c_linea = _find_col(df, ["LINEA ESTRATEGICA", "LÍNEA ESTRATÉGICA", "Linea estrategica"])
    c_obj = _find_col(df, ["OBJETIVO ESTRATEGICO", "OBJETIVO ESTRATÉGICO", "Objetivo estrategico"])
    if not c_linea or not c_obj:
        return pd.DataFrame(columns=["Linea", "Objetivo"])

    out = df[[c_linea, c_obj]].copy().rename(columns={c_linea: "Linea", c_obj: "Objetivo"})
    out["Linea"] = out["Linea"].astype(str).str.strip()
    out["Objetivo"] = out["Objetivo"].astype(str).str.strip()
    out = out[(out["Linea"] != "") & (out["Objetivo"] != "")]
    return out.drop_duplicates().reset_index(drop=True)


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def load_cna_catalog() -> pd.DataFrame:
    if not RAW_XLSX.exists():
        return pd.DataFrame(columns=["Factor", "Caracteristica"])
    try:
        df = pd.read_excel(RAW_XLSX, sheet_name="CNA", engine="openpyxl")
    except Exception:
        return pd.DataFrame(columns=["Factor", "Caracteristica"])

    df.columns = [str(c).strip() for c in df.columns]
    c_factor = _find_col(df, ["Factor", "FACTOR"])
    c_car = _find_col(df, ["Caracteristicas", "Características", "Caracteristica", "CARACTERISTICA"])
    if not c_factor or not c_car:
        return pd.DataFrame(columns=["Factor", "Caracteristica"])

    out = df[[c_factor, c_car]].copy().rename(columns={c_factor: "Factor", c_car: "Caracteristica"})
    out["Factor"] = out["Factor"].astype(str).str.strip()
    out["Caracteristica"] = out["Caracteristica"].astype(str).str.strip()
    out = out[(out["Factor"] != "") & (out["Caracteristica"] != "")]
    return out.drop_duplicates().reset_index(drop=True)


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def load_worksheet_flags() -> pd.DataFrame:
    if not RAW_XLSX.exists():
        return pd.DataFrame()

    try:
        df = pd.read_excel(RAW_XLSX, sheet_name="Worksheet", engine="openpyxl")
    except Exception:
        return pd.DataFrame()

    df.columns = [str(c).strip() for c in df.columns]

    c_id = _find_col(df, ["Id", "ID"])
    c_ind = _find_col(df, ["Indicador"])
    c_linea = _find_col(df, ["Linea"])
    c_obj = _find_col(df, ["Objetivo"])
    c_factor = _find_col(df, ["FACTOR", "Factor"])
    c_car = _find_col(df, ["CARACTERISTICA", "Caracteristica", "CARACTERÍSTICA"])
    c_plan = _find_col(df, ["Indicadores Plan estrategico"])
    c_cna = _find_col(df, ["CNA"])
    c_proyecto = _find_col(df, ["Proyecto", "PROYECTO"])

    needed = [c for c in [c_id, c_ind, c_linea, c_obj, c_factor, c_car, c_plan, c_cna] if c]
    if not needed:
        return pd.DataFrame()

    out = df[needed].copy()
    rename_map = {
        c_id: "Id",
        c_ind: "Indicador",
        c_linea: "Linea",
        c_obj: "Objetivo",
        c_factor: "Factor",
        c_car: "Caracteristica",
        c_plan: "FlagPlanEstrategico",
        c_cna: "FlagCNA",
    }
    if c_proyecto:
        out = df[needed + [c_proyecto]].copy()
        rename_map[c_proyecto] = "Proyecto"

    out = out.rename(columns={k: v for k, v in rename_map.items() if k is not None})

    if "Id" not in out.columns:
        return pd.DataFrame()

    out["Id"] = out["Id"].apply(_id_limpio)
    for c in ["Indicador", "Linea", "Objetivo", "Factor", "Caracteristica"]:
        if c in out.columns:
            out[c] = out[c].astype(str).str.strip()
            out.loc[out[c].isin(["", "nan", "None"]), c] = None

    for flag in ["FlagPlanEstrategico", "FlagCNA"]:
        if flag in out.columns:
            out[flag] = pd.to_numeric(out[flag], errors="coerce").fillna(0).astype(int)
        else:
            out[flag] = 0

    if "Proyecto" in out.columns:
        out["Proyecto"] = pd.to_numeric(out["Proyecto"], errors="coerce").fillna(0).astype(int)

    out = out[out["Id"] != ""].copy()
    return out.drop_duplicates(subset=["Id"], keep="first").reset_index(drop=True)


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def load_cierres() -> pd.DataFrame:
    if not OUT_XLSX.exists():
        return pd.DataFrame()

    try:
        xl = pd.ExcelFile(OUT_XLSX, engine="openpyxl")
    except Exception:
        return pd.DataFrame()

    sheet = "Cierre historico" if "Cierre historico" in xl.sheet_names else (
        "Consolidado Cierres" if "Consolidado Cierres" in xl.sheet_names else None
    )
    if not sheet:
        return pd.DataFrame()

    try:
        df = xl.parse(sheet)
    except Exception:
        return pd.DataFrame()

    df.columns = [str(c).strip() for c in df.columns]

    c_id = _find_col(df, ["Id", "ID"])
    c_ind = _find_col(df, ["Indicador"])
    c_fecha = _find_col(df, ["Fecha"])
    c_anio = _find_col(df, ["Año", "Anio"])
    c_mes = _find_col(df, ["Mes"])
    c_periodo = _find_col(df, ["Periodo"])
    c_meta = _find_col(df, ["Meta"])
    c_ejec = _find_col(df, ["Ejecucion", "Ejecución"])
    c_sentido = _find_col(df, ["Sentido"])
    c_tipo = _find_col(df, ["Tipo_Registro", "Tipo Registro"])

    if not c_id:
        return pd.DataFrame()

    out = pd.DataFrame()
    out["Id"] = df[c_id].apply(_id_limpio)
    out["Indicador"] = df[c_ind].astype(str).str.strip() if c_ind else None
    out["Fecha"] = pd.to_datetime(df[c_fecha], errors="coerce") if c_fecha else pd.NaT
    out["Anio"] = pd.to_numeric(df[c_anio], errors="coerce") if c_anio else pd.NA
    out["Mes"] = pd.to_numeric(df[c_mes], errors="coerce") if c_mes else pd.NA
    out["Periodo"] = df[c_periodo].astype(str).str.strip() if c_periodo else None
    out["Meta"] = pd.to_numeric(df[c_meta], errors="coerce") if c_meta else pd.NA
    out["Ejecucion"] = pd.to_numeric(df[c_ejec], errors="coerce") if c_ejec else pd.NA
    out["Sentido"] = df[c_sentido].astype(str).str.strip() if c_sentido else ""
    out["Tipo_Registro"] = df[c_tipo].astype(str).str.strip() if c_tipo else ""

    out = out[out["Id"] != ""].copy()

    # Completar Año/Mes desde Fecha para filas donde no vienen informadas.
    if "Fecha" in out.columns:
        out.loc[out["Anio"].isna(), "Anio"] = out.loc[out["Anio"].isna(), "Fecha"].dt.year
        out.loc[out["Mes"].isna(), "Mes"] = out.loc[out["Mes"].isna(), "Fecha"].dt.month

    meta_n = out["Meta"]
    ejec_n = out["Ejecucion"]
    valid = meta_n.notna() & ejec_n.notna() & (meta_n != 0)
    sentido_neg = out["Sentido"].str.lower() == "negativo"

    ratio_real = (ejec_n / meta_n).clip(lower=0).where(~sentido_neg, (meta_n / ejec_n).clip(lower=0))
    ids_str = out["Id"].astype(str).str.strip()
    tope = pd.Series(1.3, index=out.index)
    tope[ids_str.isin(IDS_PLAN_ANUAL | IDS_TOPE_100)] = 1.0
    ratio_cap = ratio_real.clip(upper=tope)

    es_metrica = out["Tipo_Registro"].str.lower() == METRICA.lower()
    out["cumplimiento_dec"] = pd.NA
    out.loc[valid & ~es_metrica, "cumplimiento_dec"] = ratio_cap[valid & ~es_metrica]
    out["cumplimiento_pct"] = pd.to_numeric(out["cumplimiento_dec"], errors="coerce") * 100

    out["Nivel de cumplimiento"] = out["cumplimiento_dec"].apply(_nivel_desde_cumplimiento)
    out.loc[es_metrica, "Nivel de cumplimiento"] = NO_APLICA
    out.loc[out["cumplimiento_pct"].isna() & ~es_metrica, "Nivel de cumplimiento"] = PENDIENTE

    return out.reset_index(drop=True)


def cierre_por_corte(df_cierres: pd.DataFrame, anio: int, mes: int) -> pd.DataFrame:
    if df_cierres.empty:
        return df_cierres

    df = df_cierres.copy()
    cutoff = int(anio) * 100 + int(mes)
    cutoff_date = pd.Timestamp(int(anio), int(mes), 1) + pd.offsets.MonthEnd(0)

    if "Anio" in df.columns and "Mes" in df.columns:
        ym = pd.to_numeric(df["Anio"], errors="coerce") * 100 + pd.to_numeric(df["Mes"], errors="coerce")
        by_period = ym.notna() & (ym <= cutoff)
        if "Fecha" in df.columns:
            by_date = ym.isna() & df["Fecha"].notna() & (pd.to_datetime(df["Fecha"], errors="coerce") <= cutoff_date)
            df = df[by_period | by_date].copy()
        else:
            df = df[by_period].copy()
    elif "Fecha" in df.columns:
        df = df[pd.to_datetime(df["Fecha"], errors="coerce") <= cutoff_date].copy()

    if df.empty:
        return df

    if "Fecha" in df.columns:
        df = df.sort_values(["Id", "Fecha"]).drop_duplicates(subset=["Id"], keep="last")
    else:
        df = df.drop_duplicates(subset=["Id"], keep="last")
    return df.reset_index(drop=True)


def preparar_pdi_con_cierre(anio: int, mes: int) -> pd.DataFrame:
    base = load_worksheet_flags()
    pdi_catalog = load_pdi_catalog()
    cierres = load_cierres()
    if base.empty or cierres.empty:
        return pd.DataFrame()

    plan = base[base["FlagPlanEstrategico"] == 1].copy()
    if plan.empty:
        return pd.DataFrame()

    # Excluir indicadores de tipo Proyecto (Proyecto=1)
    if "Proyecto" in plan.columns:
        plan = plan[plan["Proyecto"] != 1].copy()
    if plan.empty:
        return pd.DataFrame()

    close = cierre_por_corte(cierres, anio, mes)
    cols_close = ["Id", "Indicador", "cumplimiento_pct", "Nivel de cumplimiento", "Anio", "Mes", "Fecha"]
    for _ec in ["Meta", "Ejecucion", "Sentido"]:
        if _ec in close.columns:
            cols_close.append(_ec)
    merged = plan.merge(
        close[cols_close],
        on="Id",
        how="left",
        suffixes=("", "_cierre"),
    )

    if "Indicador_cierre" in merged.columns:
        merged["Indicador"] = merged["Indicador"].fillna(merged["Indicador_cierre"])
        merged = merged.drop(columns=["Indicador_cierre"])

    if not pdi_catalog.empty and "Linea" in merged.columns and "Objetivo" in merged.columns:
        merged = merged.merge(pdi_catalog, on=["Linea", "Objetivo"], how="left")

    # Asegurar que exista columna `cumplimiento_pct` usando las fuentes disponibles
    # 1) Si ya existe (desde load_cierres), respetarla.
    if "cumplimiento_pct" not in merged.columns:
        merged["cumplimiento_pct"] = pd.NA

    # 2) Si existe columna 'Cumplimiento' (posible capitalización desde Excel), intentar parsearla
    if "Cumplimiento" in merged.columns:
        # eliminar % y normalizar coma decimal
        merged.loc[merged["cumplimiento_pct"].isna(), "cumplimiento_pct"] = (
            pd.to_numeric(
                merged.loc[merged["cumplimiento_pct"].isna(), "Cumplimiento"].astype(str)
                .str.replace('%', '', regex=False)
                .str.replace(',', '.', regex=False)
                .str.strip(),
                errors="coerce",
            )
        )

    # 3) Si aún falta, pero hay Meta/Ejecucion, calcular a nivel fila (similar a load_cierres)
    for cols in [("Meta", "Ejecucion"), ("Meta", "Ejecucion_cierre")]:
        meta_col, ejec_col = cols
        if meta_col in merged.columns and ejec_col in merged.columns:
            meta_n = pd.to_numeric(merged[meta_col], errors="coerce")
            ejec_n = pd.to_numeric(merged[ejec_col], errors="coerce")
            valid = meta_n.notna() & ejec_n.notna() & (meta_n != 0)
            if valid.any():
                sentido_col = "Sentido" if "Sentido" in merged.columns else ("Sentido_cierre" if "Sentido_cierre" in merged.columns else None)
                sentido_neg = merged[sentido_col].astype(str).str.lower() == "negativo" if sentido_col is not None else pd.Series([False] * len(merged))
                ratio = pd.Series(pd.NA, index=merged.index)
                ratio.loc[valid & ~sentido_neg] = (ejec_n[valid & ~sentido_neg] / meta_n[valid & ~sentido_neg])
                ratio.loc[valid & sentido_neg] = (meta_n[valid & sentido_neg] / ejec_n[valid & sentido_neg])
                merged.loc[merged["cumplimiento_pct"].isna(), "cumplimiento_pct"] = pd.to_numeric(ratio, errors="coerce") * 100

    # 4) Normalizar tipo numérico para cumplimiento_pct
    merged["cumplimiento_pct"] = pd.to_numeric(merged.get("cumplimiento_pct"), errors="coerce")

    merged["Nivel de cumplimiento"] = merged["Nivel de cumplimiento"].fillna(PENDIENTE)

    # Omitir filas que no contienen ninguna fuente de cumplimiento: Meta, Ejecucion o Cumplimiento
    def _has_source(row):
        for c in ["Meta", "Ejecucion", "Cumplimiento"]:
            if c in merged.columns:
                v = row.get(c)
                if pd.notna(v) and str(v).strip() != "":
                    return True
        return False

    if not merged.empty:
        merged = merged[merged.apply(_has_source, axis=1)].reset_index(drop=True)

    return merged


def preparar_cna_con_cierre(anio: int, mes: int) -> pd.DataFrame:
    base = load_worksheet_flags()
    cna_catalog = load_cna_catalog()
    cierres = load_cierres()
    if base.empty or cierres.empty:
        return pd.DataFrame()

    cna = base[base["FlagCNA"] == 1].copy()
    if cna.empty:
        return pd.DataFrame()

    close = cierre_por_corte(cierres, anio, mes)
    cols_close_cna = ["Id", "Indicador", "cumplimiento_pct", "Nivel de cumplimiento", "Anio", "Mes", "Fecha"]
    for _ec in ["Meta", "Ejecucion", "Sentido"]:
        if _ec in close.columns:
            cols_close_cna.append(_ec)
    merged = cna.merge(
        close[cols_close_cna],
        on="Id",
        how="left",
        suffixes=("", "_cierre"),
    )

    if "Indicador_cierre" in merged.columns:
        merged["Indicador"] = merged["Indicador"].fillna(merged["Indicador_cierre"])
        merged = merged.drop(columns=["Indicador_cierre"])

    if not cna_catalog.empty and "Factor" in merged.columns and "Caracteristica" in merged.columns:
        merged = merged.merge(cna_catalog, on=["Factor", "Caracteristica"], how="left")

    merged["Nivel de cumplimiento"] = merged["Nivel de cumplimiento"].fillna(PENDIENTE)

    return merged
