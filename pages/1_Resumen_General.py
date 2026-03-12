"""
pages/1_Resumen_General.py — Reporte de Cumplimiento.

Fuente: data/output/Resultados Consolidados.xlsx (hoja Consolidado Historico)
  · Selección de año y mes para análisis
  · Niveles: Sobrecumplimiento | Cumplimiento | Alerta | Peligro | No aplica | Pendiente de reporte

Mejoras:
  · Selector de año y mes
  · KPIs con comparativa vs período anterior
  · Caption de tendencia (mejoraron/empeoraron)
  · Desglose por Clasificación
  · Dialog de detalle al seleccionar fila en tabla consolidada
"""
import calendar
import html as _html
import math
from datetime import date as _date

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.charts import exportar_excel, panel_detalle_indicador
from utils.data_loader import cargar_dataset
from utils.niveles import NIVEL_COLOR, NIVEL_BG, NIVEL_ICON, nivel_desde_pct

# ── Rutas ─────────────────────────────────────────────────────────────────────
from pathlib import Path
_DATA_OUTPUT = Path(__file__).parent.parent / "data" / "output"
_DATA_RAW    = Path(__file__).parent.parent / "data" / "raw"
_RUTA_CONSOLIDADOS = _DATA_OUTPUT / "Resultados Consolidados.xlsx"
_RUTA_MAPA         = _DATA_RAW / "Subproceso-Proceso-Area.xlsx"
_RUTA_KAWAK_DIR    = _DATA_RAW / "Kawak"

# Meses en español para selección
MESES_OPCIONES = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
]
_MES_NUM = {m: i+1 for i, m in enumerate(MESES_OPCIONES)}

# ── Niveles extendidos ─────────────────────────────────────────────────────────
_NO_APLICA   = "No aplica"
_PEND        = "Pendiente de reporte"
_METRICA     = "Métrica"

_NIVEL_COLOR = {
    **NIVEL_COLOR,
    _NO_APLICA: "#78909C",
    _PEND:      "#BDBDBD",
    _METRICA:   "#5C6BC0",
}
_NIVEL_BG = {
    **NIVEL_BG,
    _NO_APLICA: "#ECEFF1",
    _PEND:      "#F5F5F5",
    _METRICA:   "#E8EAF6",
}
_NIVEL_ICON = {
    **NIVEL_ICON,
    _NO_APLICA: "⚫",
    _PEND:      "⚪",
    _METRICA:   "📐",
}
_NIVEL_ORDEN = [
    "Peligro", "Alerta", "Cumplimiento", "Sobrecumplimiento",
    _NO_APLICA, _PEND, _METRICA,
]
# Orden de severidad para detectar deterioro/mejora
_ORDEN_NUM = {
    "Peligro": 0, "Alerta": 1, "Cumplimiento": 2, "Sobrecumplimiento": 3,
    _NO_APLICA: -1, _PEND: -1, _METRICA: -1,
}


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _is_null(v) -> bool:
    if v is None:
        return True
    try:
        if pd.isna(v):
            return True
    except (TypeError, ValueError):
        pass
    try:
        f = float(str(v).strip())
        return math.isnan(f)
    except (ValueError, TypeError):
        pass
    return str(v).strip().lower() in ("", "nan", "none")


def _to_num(v):
    if _is_null(v):
        return None
    try:
        f = float(str(v).strip())
        return None if math.isnan(f) else f
    except (ValueError, TypeError):
        return None


def _nivel(row) -> str:
    """Determina el nivel de cumplimiento del indicador."""
    # Indicadores tipo Métrica: no tienen meta de cumplimiento
    tipo = str(row.get("Tipo_Registro", "") or "").strip().lower()
    if tipo == "metrica":
        return _METRICA

    # Solo bloquear si la columna existe y tiene un valor explícito de no aplica
    if "Resultado" in row:
        resultado = str(row.get("Resultado", "")).strip().upper()
        if resultado in ("N/A", "NA", "NO APLICA", "NO"):
            return _NO_APLICA

    c = _to_num(row.get("cumplimiento", ""))
    if c is None:
        return _PEND

    return nivel_desde_pct(c * 100)


def _limpiar(v) -> str:
    if _is_null(v):
        return ""
    return _html.unescape(str(v)).strip()


def _id_limpio(x) -> str:
    if _is_null(x):
        return ""
    try:
        f = float(x)
        return str(int(f)) if f == int(f) else str(f)
    except (ValueError, TypeError):
        return str(x).strip()


def _fmt_num(v) -> str:
    n = _to_num(v)
    if n is None:
        s = str(v).strip()
        return s if s and s.lower() not in ("nan", "none", "") else "—"
    return f"{n:,.2f}".rstrip("0").rstrip(".")


def _fmt_valor(v, signo, decimales) -> str:
    """Formatea un valor numérico concatenando signo y decimales.
    signo: '%' | '$' | 'ENT' | otro texto
    decimales: int o float indicando dígitos decimales
    """
    n = _to_num(v)
    if n is None:
        return "—"
    try:
        d = max(0, int(float(decimales))) if not _is_null(decimales) else 2
    except (ValueError, TypeError):
        d = 2
    s = str(signo).strip() if not _is_null(signo) else "%"
    su = s.upper()
    if s == "%":
        return f"{n:,.{d}f}%"
    elif s == "$":
        # Formato colombiano: . miles, , decimales (ej. $1.234.567,89)
        formatted = f"{n:,.{d}f}"  # "1,234,567.89"
        formatted = formatted.replace(",", "X").replace(".", ",").replace("X", ".")
        return f"${formatted}"
    elif su in ("ENT", "N", ""):
        return f"{int(round(n)):,}"
    elif su == "DEC":
        return f"{n:,.{d}f}"
    elif su in ("NO APLICA", "SIN REPORTE", "NA"):
        # Etiqueta de estado, no unidad — mostrar solo el número
        return f"{n:,.{d}f}" if d > 0 else f"{int(round(n)):,}"
    else:
        return f"{n:,.{d}f} {s}"


# ══════════════════════════════════════════════════════════════════════════════
# CARGA DE DATOS
# ══════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=600, show_spinner=False)
def _cargar_mapa() -> pd.DataFrame:
    if not _RUTA_MAPA.exists():
        return pd.DataFrame()
    df = pd.read_excel(str(_RUTA_MAPA), engine="openpyxl")
    df.columns = [str(c).strip() for c in df.columns]
    col_sub    = next((c for c in df.columns if c.lower() == "subproceso"), None)
    col_proc   = next((c for c in df.columns if c.lower() == "proceso"), None)
    col_area   = next((c for c in df.columns
                       if "rea" in c.lower() and "vicerr" not in c.lower()), None)
    col_vicerr = next((c for c in df.columns if "icerrector" in c.lower()), None)
    if not col_sub or not col_proc:
        return pd.DataFrame()
    rename = {col_sub: "Subproceso", col_proc: "Proceso"}
    if col_area:   rename[col_area]   = "Area"
    if col_vicerr: rename[col_vicerr] = "Vicerrectoria"
    df = df.rename(columns=rename)
    cols_k = [c for c in ["Subproceso", "Proceso", "Area", "Vicerrectoria"] if c in df.columns]
    return (df[cols_k]
            .dropna(subset=["Subproceso"])
            .drop_duplicates(subset=["Subproceso"])
            .reset_index(drop=True))


@st.cache_data(ttl=300, show_spinner="Cargando Resultados Consolidados.xlsx...")
def _cargar_consolidados() -> pd.DataFrame:
    """Carga datos desde Resultados Consolidados.xlsx hoja Consolidado Historico."""
    if not _RUTA_CONSOLIDADOS.exists():
        return pd.DataFrame()
    try:
        df = pd.read_excel(str(_RUTA_CONSOLIDADOS), sheet_name="Consolidado Historico",
                           engine="openpyxl", keep_default_na=False, na_values=[""])
    except Exception:
        return pd.DataFrame()
    
    df.columns = [str(c).strip() for c in df.columns]
    
    col_renames = {
        "Id": "Id", "Indicador": "Indicador", "Proceso": "Proceso",
        "Periodicidad": "Periodicidad", "Sentido": "Sentido",
        "Fecha": "fecha", "Mes": "Mes", "Periodo": "Periodo",
        "Meta": "Meta",
        "Ejecucion": "Ejecucion", "Ejecución": "Ejecucion",   # con y sin acento
        "Cumplimiento": "cumplimiento",
        "Cumplimiento Real": "cumplimiento_real",
        "Tipo_Registro": "Tipo_Registro",
        "Decimales_Meta": "Dec_Meta", "Decimales_Ejecucion": "Dec_Ejec",
    }
    # Signo de Meta y Ejecución — pueden tener variantes: 'Meta s', 'Ejecución s',
    # 'Meta Signo', 'Ejecucion Signo', etc.
    for col in df.columns:
        col_lower = col.lower().strip()
        col_norm  = col_lower.replace("ó", "o").replace("ú", "u").replace("á", "a")
        if "año" in col_lower or "aio" in col_lower:
            col_renames[col] = "Anio"
        elif col_norm in ("meta s", "meta signo", "meta_signo"):
            col_renames[col] = "Meta_Signo"
        elif "meta" in col_norm and "signo" in col_norm:
            col_renames[col] = "Meta_Signo"
        elif col_norm in ("ejecucion s", "ejecuci\u00f3n s", "ejecucion signo"):
            col_renames[col] = "Ejec_Signo"
        elif ("ejec" in col_norm or "ejecuci" in col_norm) and ("signo" in col_norm or col_norm.endswith(" s")):
            col_renames[col] = "Ejec_Signo"

    df = df.rename(columns={k: v for k, v in col_renames.items() if k in df.columns})

    # Garantizar que las columnas de signo/tipo existan
    for col in ("Tipo_Registro", "Meta_Signo", "Ejec_Signo", "Dec_Meta", "Dec_Ejec"):
        if col not in df.columns:
            df[col] = None
    
    if "Anio" in df.columns:
        df["Anio"] = pd.to_numeric(df["Anio"], errors="coerce")
    
    if "Id" in df.columns:
        df["Id"] = df["Id"].apply(_id_limpio)
    for col in ["Indicador", "Proceso", "Periodicidad", "Sentido", "Mes", "Periodo"]:
        if col in df.columns:
            df[col] = df[col].apply(_limpiar)
    
    if "fecha" in df.columns:
        df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
        # Derivar Anio desde Fecha para evitar dependencia de fórmulas Excel cacheadas
        df["Anio"] = df["fecha"].dt.year
    
    # Normalizar columnas de cumplimiento (pueden venir vacías si son fórmulas Excel sin caché)
    if "cumplimiento" in df.columns:
        df["cumplimiento"] = pd.to_numeric(df["cumplimiento"], errors="coerce")
    else:
        df["cumplimiento"] = None

    if "cumplimiento_real" in df.columns:
        df["cumplimiento_real"] = pd.to_numeric(df["cumplimiento_real"], errors="coerce")
    else:
        df["cumplimiento_real"] = None

    # Si cumplimiento está vacío (fórmulas Excel sin caché), calcular desde Meta/Ejecucion
    ejec_col = next((c for c in df.columns
                     if c.lower().replace("ó", "o").replace("ú", "u")
                        in ("ejecucion", "ejecución")), None)
    if ejec_col and "Meta" in df.columns and "Sentido" in df.columns:
        meta_n = pd.to_numeric(df["Meta"], errors="coerce")
        ejec_n = pd.to_numeric(df[ejec_col], errors="coerce")
        valid  = meta_n.notna() & ejec_n.notna() & (meta_n != 0)
        sentido_neg = df["Sentido"].str.strip().str.lower() == "negativo"

        ratio_real = (ejec_n / meta_n).clip(lower=0).where(~sentido_neg,
                      (meta_n / ejec_n).clip(lower=0))
        ratio_cap  = ratio_real.clip(upper=1.3)

        mask_calc = df["cumplimiento"].isna() & valid
        df.loc[mask_calc, "cumplimiento"]      = ratio_cap[mask_calc]
        df.loc[mask_calc, "cumplimiento_real"] = ratio_real[mask_calc]

    # Si cumplimiento aún vacío, rellenar desde cumplimiento_real
    mask_fill = df["cumplimiento"].isna() & df["cumplimiento_real"].notna()
    df.loc[mask_fill, "cumplimiento"] = df.loc[mask_fill, "cumplimiento_real"]
    
    return df


@st.cache_data(ttl=300, show_spinner=False)
def _obtener_anios_disponibles() -> list:
    """Retorna lista de años disponibles en el dataset."""
    df = _cargar_consolidados()
    if df.empty or "Anio" not in df.columns:
        return []
    anios = sorted(df["Anio"].dropna().unique().tolist())
    return [int(a) for a in anios if not pd.isna(a)]


@st.cache_data(ttl=600, show_spinner="Cargando IDs de Kawak...")
def _obtener_ids_kawak() -> set:
    """Retorna conjunto de IDs únicos de los archivos Kawak."""
    if not _RUTA_KAWAK_DIR.exists():
        return set()
    archivos = list(_RUTA_KAWAK_DIR.glob("*.xlsx"))
    ids_kawak = set()
    for arch in archivos:
        try:
            df = pd.read_excel(arch, engine="openpyxl")
            id_col = "ID" if "ID" in df.columns else ("Id" if "Id" in df.columns else None)
            if id_col:
                ids = df[id_col].dropna().astype(str).unique()
                ids_kawak.update(ids)
        except Exception:
            pass
    return ids_kawak


# Dataset_Unificado para el dialog de detalle (histórico completo)
@st.cache_data(ttl=300, show_spinner=False)
def _cargar_historico_detalle() -> pd.DataFrame:
    return cargar_dataset()


def _preparar_datos_por_fecha(df_all: pd.DataFrame, anio: int, mes: str) -> pd.DataFrame:
    """
    Selecciona los datos según el año y mes seleccionados.
    Para cada indicador, toma el último registro disponible hasta esa fecha.
    Solo incluye indicadores que existen en los archivos de Kawak.
    """
    if df_all.empty:
        return df_all
    
    ids_kawak = _obtener_ids_kawak()
    
    mes_num = _MES_NUM.get(mes, 12)
    ultimo_dia_mes = calendar.monthrange(anio, mes_num)[1]
    fecha_corte = pd.Timestamp(anio, mes_num, ultimo_dia_mes, 23, 59, 59)
    
    df_filtrado = df_all[df_all["fecha"].notna() & (df_all["fecha"] <= fecha_corte)].copy()
    
    if df_filtrado.empty:
        df_filtrado = df_all.copy()
    
    if ids_kawak:
        df_filtrado = df_filtrado[df_filtrado["Id"].isin(ids_kawak)]
    
    df = (df_filtrado.sort_values("fecha")
          .groupby("Id", as_index=False)
          .last())
    
    df["Nivel de cumplimiento"] = df.apply(_nivel, axis=1)
    _cum_display = "cumplimiento_real" if "cumplimiento_real" in df.columns else "cumplimiento"

    # Cumplimiento: Métrica no tiene → mostrar "—"; resto como porcentaje + icono nivel
    def _fmt_cum(row):
        niv = str(row.get("Nivel de cumplimiento", ""))
        if niv == _METRICA:
            return "—"
        v = _to_num(row.get(_cum_display))
        if v is None:
            return "—"
        icon = NIVEL_ICON.get(niv, "")
        pct  = f"{v * 100:,.2f}%"
        return f"{icon} {pct}" if icon else pct

    df["Cumplimiento"] = df.apply(_fmt_cum, axis=1)

    if "cumplimiento_real" in df.columns:
        def _fmt_cum_real(row):
            if str(row.get("Nivel de cumplimiento", "")) == _METRICA:
                return "—"
            v = _to_num(row.get("cumplimiento_real"))
            return f"{v * 100:,.2f}%" if v is not None else "—"
        df["Cumplimiento Real"] = df.apply(_fmt_cum_real, axis=1)

    # Meta y Ejecución formateadas con signo y decimales
    df["Meta_fmt"] = df.apply(
        lambda r: _fmt_valor(r.get("Meta"), r.get("Meta_Signo"), r.get("Dec_Meta")), axis=1)
    df["Ejecucion_fmt"] = df.apply(
        lambda r: _fmt_valor(r.get("Ejecucion"), r.get("Ejec_Signo"), r.get("Dec_Ejec")), axis=1)

    df["Fecha reporte"] = df["fecha"].dt.strftime("%d/%m/%Y").fillna("—") \
                          if "fecha" in df.columns else "—"
    
    mapa = _cargar_mapa()
    if not mapa.empty:
        if "Proceso" in df.columns:
            mapa_cols = list(mapa.columns)
            proc_col = next((c for c in mapa_cols if "proceso" in c.lower()), "Proceso")
            vic_col = next((c for c in mapa_cols if "icerrector" in c.lower()), None)
            # Merge al nivel de Proceso (excluir Subproceso: es más granular y rompe unicidad)
            cols_proc = [c for c in [proc_col, vic_col] if c]
            if cols_proc and proc_col:
                mapa_proc = (mapa[cols_proc]
                             .drop_duplicates(subset=[proc_col])
                             .reset_index(drop=True))
                df = df.merge(mapa_proc,
                             left_on="Proceso",
                             right_on=proc_col,
                             how="left")
                if vic_col and vic_col in df.columns:
                    df = df.rename(columns={vic_col: "Vicerrectoria"})
    
    return df


# ══════════════════════════════════════════════════════════════════════════════
# GRÁFICOS
# ══════════════════════════════════════════════════════════════════════════════

def _fig_donut(df):
    counts = df["Nivel de cumplimiento"].value_counts()
    labels = [n for n in _NIVEL_ORDEN if n in counts.index]
    values = [int(counts[n]) for n in labels]
    colors = [_NIVEL_COLOR[n] for n in labels]
    total  = sum(values)
    fig = go.Figure(go.Pie(
        labels=labels, values=values, hole=0.55,
        marker=dict(colors=colors, line=dict(color="white", width=2)),
        textinfo="label+value", textfont=dict(size=12),
        hovertemplate="<b>%{label}</b><br>%{value} indicadores (%{percent})<extra></extra>",
    ))
    fig.update_layout(
        height=340, showlegend=True,
        legend=dict(orientation="v", x=1.02, y=0.5),
        margin=dict(t=10, b=10, l=10, r=160),
        paper_bgcolor="white",
        annotations=[dict(text=f"<b>{total}</b><br>total",
                          x=0.5, y=0.5, font_size=16, showarrow=False)],
    )
    return fig


def _fig_barras_nivel(df, col_cat):
    if col_cat not in df.columns or df.empty:
        return go.Figure()
    tmp = df.copy()
    tmp[col_cat] = tmp[col_cat].astype(str).str.strip()
    tmp = tmp[tmp[col_cat].notna() & (tmp[col_cat] != "nan")]

    stats = (tmp.groupby([col_cat, "Nivel de cumplimiento"])
             .size().unstack(fill_value=0).reset_index())

    niveles = [n for n in _NIVEL_ORDEN if n in stats.columns]
    stats["_t"] = stats[niveles].sum(axis=1)
    stats = stats.sort_values("_t", ascending=False).drop(columns="_t")
    cats  = list(stats[col_cat].astype(str))

    max_len  = max((len(c) for c in cats), default=10)
    margin_l = min(max(max_len * 6, 120), 360)
    h        = max(300, len(stats) * 44 + 70)

    fig = go.Figure()
    for nivel in niveles:
        if nivel not in stats.columns:
            continue
        vals = stats[nivel].tolist()
        fig.add_trace(go.Bar(
            y=cats, x=vals, orientation="h", name=nivel,
            marker_color=_NIVEL_COLOR.get(nivel, "#BDBDBD"),
            customdata=[nivel] * len(cats),
            text=[v if v > 0 else "" for v in vals],
            textposition="inside", insidetextanchor="middle",
            textfont=dict(size=10, color="white"),
        ))

    fig.update_layout(
        barmode="stack", height=h,
        xaxis_title="Indicadores", yaxis_title="",
        yaxis=dict(categoryorder="array", categoryarray=cats,
                   autorange="reversed", tickfont=dict(size=10)),
        uniformtext_minsize=9, uniformtext_mode="hide",
        plot_bgcolor="white", paper_bgcolor="white",
        legend=dict(orientation="h", y=-0.12),
        margin=dict(t=10, b=55, l=margin_l, r=30),
    )
    return fig


# ══════════════════════════════════════════════════════════════════════════════
# FILTROS
# ══════════════════════════════════════════════════════════════════════════════

def _aplicar_filtros(df, txt_id, txt_nom, sel_vicerr, sel_proc, sel_sub, sel_nivel):
    mask = pd.Series(True, index=df.index)
    if txt_id.strip():
        mask &= df["Id"].astype(str).str.contains(txt_id.strip(), case=False, na=False)
    if txt_nom.strip() and "Indicador" in df.columns:
        mask &= df["Indicador"].astype(str).str.contains(txt_nom.strip(), case=False, na=False)
    if sel_vicerr and "Vicerrectoria" in df.columns:
        mask &= df["Vicerrectoria"] == sel_vicerr
    if sel_proc and "Proceso" in df.columns:
        mask &= df["Proceso"] == sel_proc
    if sel_sub and "Subproceso" in df.columns:
        mask &= df["Subproceso"] == sel_sub
    if sel_nivel:
        mask &= df["Nivel de cumplimiento"] == sel_nivel
    return df[mask].reset_index(drop=True)


def _filtros_ui(df_opciones, prefix):
    with st.expander("🔍 Filtros", expanded=True):
        r1c1, r1c2 = st.columns(2)
        with r1c1:
            txt_id = st.text_input("ID", key=f"{prefix}_id", placeholder="Buscar ID...")
        with r1c2:
            txt_nom = st.text_input("Nombre del indicador", key=f"{prefix}_nom",
                                    placeholder="Buscar nombre...")
        r2c1, r2c2, r2c3, r2c4 = st.columns(4)
        with r2c1:
            opts_v = [""] + sorted(df_opciones["Vicerrectoria"].dropna().unique().tolist()) \
                     if "Vicerrectoria" in df_opciones.columns else [""]
            sel_vicerr = st.selectbox("Vicerrectoría", opts_v, key=f"{prefix}_vicerr",
                                      format_func=lambda x: "— Todas —" if x == "" else x)
        with r2c2:
            if sel_vicerr and "Vicerrectoria" in df_opciones.columns:
                proc_pool = df_opciones.loc[df_opciones["Vicerrectoria"] == sel_vicerr,
                                            "Proceso"].dropna().unique().tolist() \
                            if "Proceso" in df_opciones.columns else []
            else:
                proc_pool = df_opciones["Proceso"].dropna().unique().tolist() \
                            if "Proceso" in df_opciones.columns else []
            opts_p = [""] + sorted(proc_pool)
            sel_proc = st.selectbox("Proceso", opts_p, key=f"{prefix}_proc",
                                    format_func=lambda x: "— Todos —" if x == "" else x)
        with r2c3:
            if sel_proc and "Proceso" in df_opciones.columns:
                sub_pool = df_opciones.loc[df_opciones["Proceso"] == sel_proc,
                                           "Subproceso"].dropna().unique().tolist() \
                           if "Subproceso" in df_opciones.columns else []
            else:
                sub_pool = df_opciones["Subproceso"].dropna().unique().tolist() \
                           if "Subproceso" in df_opciones.columns else []
            opts_s = [""] + sorted(sub_pool)
            sel_sub = st.selectbox("Subproceso", opts_s, key=f"{prefix}_sub",
                                   format_func=lambda x: "— Todos —" if x == "" else x)
        with r2c4:
            niv_opts = [""] + [n for n in _NIVEL_ORDEN
                               if n in df_opciones["Nivel de cumplimiento"].unique()]
            sel_niv = st.selectbox("Nivel de cumplimiento", niv_opts, key=f"{prefix}_niv",
                                   format_func=lambda x: "— Todos —" if x == "" else x)
    return txt_id, txt_nom, sel_vicerr, sel_proc, sel_sub, sel_niv


def _estilo_nivel(row):
    bg = _NIVEL_BG.get(str(row.get("Nivel de cumplimiento", "")), "")
    return [f"background-color: {bg}" if c == "Nivel de cumplimiento" else ""
            for c in row.index]


# ══════════════════════════════════════════════════════════════════════════════
# PÁGINA
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("# 🏠 Reporte de Cumplimiento")
st.caption("Fuente: **Resultados Consolidados.xlsx** · Hoja: Consolidado Historico · Solo indicadores de Kawak")

# Carga de datos
_raw = _cargar_consolidados()
if _raw.empty:
    st.error("No se encontró **Resultados Consolidados.xlsx** en `data/output/`.")
    st.stop()

# Obtener años disponibles
anios_disponibles = _obtener_anios_disponibles()
if not anios_disponibles:
    st.error("No se encontraron años en los datos.")
    st.stop()

# ── Selector de Año y Mes ─────────────────────────────────────────────────────
st.markdown("### 📅 Selección de Período")

col_sel1, col_sel2 = st.columns(2)
with col_sel1:
    anio_default = 2025 if 2025 in anios_disponibles else (anios_disponibles[-1] if anios_disponibles else 2024)
    anio_seleccionado = st.selectbox(
        "Año",
        options=anios_disponibles,
        index=anios_disponibles.index(anio_default) if anio_default in anios_disponibles else 0,
        key="anio_seleccionado"
    )
with col_sel2:
    mes_seleccionado = st.selectbox(
        "Mes",
        options=MESES_OPCIONES,
        index=11,  # Diciembre por defecto
        key="mes_seleccionado"
    )

# Calcular mes anterior para comparativa
mes_num = _MES_NUM[mes_seleccionado]
if mes_num == 1:
    anio_prev = anio_seleccionado - 1
    mes_prev = 12
else:
    anio_prev = anio_seleccionado
    mes_prev = mes_num - 1

with st.spinner("Procesando niveles de cumplimiento..."):
    df_raw = _preparar_datos_por_fecha(_raw, anio_seleccionado, mes_seleccionado)
    df_prev = _preparar_datos_por_fecha(_raw, anio_prev, MESES_OPCIONES[mes_prev - 1])

# Calcular fecha de corte
corte_actual = pd.Timestamp(anio_seleccionado, mes_num, 1)

# ── Banner de fecha de corte ──────────────────────────────────────────────────
st.markdown(
    f"""<div style="background:#E3EAF4;border-radius:8px;padding:10px 18px;
        border-left:4px solid #1A3A5C;margin-bottom:12px;">
        📅 <b>Corte de análisis:</b> {mes_seleccionado} {anio_seleccionado}
        &nbsp;·&nbsp; Generado: {_date.today().strftime('%d/%m/%Y')}
    </div>""",
    unsafe_allow_html=True,
)

st.markdown("---")

# ── KPIs con comparativa ──────────────────────────────────────────────────────
total = len(df_raw)
cnts  = df_raw["Nivel de cumplimiento"].value_counts()

# Previos
cnts_p = df_prev["Nivel de cumplimiento"].value_counts() if not df_prev.empty else pd.Series(dtype=int)

kc = st.columns(6)
metricas = [
    ("Total",              total,                                                  None, "off"),
    ("🔴 Peligro",         int(cnts.get("Peligro", 0)),         int(cnts_p.get("Peligro", 0)),         "inverse"),
    ("🟡 Alerta",          int(cnts.get("Alerta", 0)),           int(cnts_p.get("Alerta", 0)),           "off"),
    ("🔵 Cumplimiento",    int(cnts.get("Cumplimiento", 0))
                         + int(cnts.get("Sobrecumplimiento", 0)),
                           int(cnts_p.get("Cumplimiento", 0))
                         + int(cnts_p.get("Sobrecumplimiento", 0)),                                    "normal"),
    ("⚫ No aplica",       int(cnts.get(_NO_APLICA, 0)),         int(cnts_p.get(_NO_APLICA, 0)),         "off"),
    ("⚪ Pendiente",       int(cnts.get(_PEND, 0)),              int(cnts_p.get(_PEND, 0)),              "off"),
]

for i, (label, val, val_prev, dc) in enumerate(metricas):
    with kc[i]:
        if val_prev is not None and label != "Total":
            delta    = val - val_prev
            delta_str = f"{delta:+d} vs período ant."
            st.metric(label, val, delta=delta_str, delta_color=dc)
        else:
            pct = f"{round(val/total*100,1)}%" if total and label != "Total" else None
            st.metric(label, val, delta=pct, delta_color=dc)

# Caption de tendencia general
if not df_prev.empty:
    # Comparar nivel por indicador (solo indicadores presentes en ambos)
    merge_niv = df_raw[["Id", "Nivel de cumplimiento"]].merge(
        df_prev[["Id", "Nivel de cumplimiento"]].rename(
            columns={"Nivel de cumplimiento": "Nivel_prev"}),
        on="Id", how="inner",
    )
    merge_niv["ord_act"]  = merge_niv["Nivel de cumplimiento"].map(_ORDEN_NUM)
    merge_niv["ord_prev"] = merge_niv["Nivel_prev"].map(_ORDEN_NUM)
    validos = merge_niv[(merge_niv["ord_act"] >= 0) & (merge_niv["ord_prev"] >= 0)]
    n_mejor  = int((validos["ord_act"] > validos["ord_prev"]).sum())
    n_peor   = int((validos["ord_act"] < validos["ord_prev"]).sum())
    if n_mejor or n_peor:
        st.caption(
            f"📈 **{n_mejor}** indicadores mejoraron de categoría · "
            f"📉 **{n_peor}** empeoraron · respecto al período anterior"
        )

st.markdown("---")

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_res, tab_con = st.tabs(["📊 Resumen", "📋 Consolidado"])


# ─────────────────────────────────────────────────────────────────────────────
# TAB RESUMEN — Gráficas principales
# ─────────────────────────────────────────────────────────────────────────────
with tab_res:
    st.markdown("### Distribución General de Cumplimiento")
    gr1, gr2 = st.columns([1, 2])
    with gr1:
        st.markdown("#### Por Nivel")
        st.plotly_chart(_fig_donut(df_raw), use_container_width=True, key="res_donut")
    with gr2:
        st.markdown("#### Por Vicerrectoría")
        if "Vicerrectoria" in df_raw.columns:
            st.plotly_chart(_fig_barras_nivel(df_raw, "Vicerrectoria"),
                            use_container_width=True, key="res_vicerr")
        else:
            st.info("No hay datos de Vicerrectoría disponibles.")

    st.markdown("---")
    st.markdown("#### Por Proceso")
    if "Proceso" in df_raw.columns:
        st.plotly_chart(_fig_barras_nivel(df_raw, "Proceso"),
                        use_container_width=True, key="res_proceso")

    st.markdown("---")
    st.markdown("#### Por Clasificación")
    if "Clasificacion" in df_raw.columns:
        df_clasif = df_raw[df_raw["Clasificacion"].notna() &
                           (df_raw["Clasificacion"].astype(str).str.strip() != "")]
        if not df_clasif.empty:
            st.plotly_chart(_fig_barras_nivel(df_clasif, "Clasificacion"),
                            use_container_width=True, key="res_clasif")
        else:
            st.info("Sin datos de Clasificación disponibles.")


# ─────────────────────────────────────────────────────────────────────────────
# TAB CONSOLIDADO — Gráficas interactivas como filtros + tabla
# ─────────────────────────────────────────────────────────────────────────────
with tab_con:
    # Usar los mismos datos del período seleccionado en el encabezado
    df_con = df_raw.copy()

    # ── Claves de sesión para selecciones de gráficas ─────────────────────
    _SK_VC = "con_sel_vicerr"
    _SK_PR = "con_sel_proc"
    _KEY_DET = "rc_con_det_id"
    for _k in (_SK_VC, _SK_PR, _KEY_DET):
        if _k not in st.session_state:
            st.session_state[_k] = "" if _k != _KEY_DET else None

    # ── Gráficas clicables ────────────────────────────────────────────────
    st.markdown("### Distribución por Vicerrectoría y Proceso")
    st.caption("Haz clic en una barra para filtrar la tabla. Haz clic fuera para deseleccionar.")

    col_vc, col_pr = st.columns(2)

    with col_vc:
        st.markdown("#### Por Vicerrectoría")
        if "Vicerrectoria" in df_con.columns:
            fig_vc = _fig_barras_nivel(df_con, "Vicerrectoria")
            ev_vc = st.plotly_chart(
                fig_vc, use_container_width=True, key="con_chart_vicerr",
                on_select="rerun", selection_mode="points",
            )
            pts_vc = (ev_vc.selection or {}).get("points", [])
            if pts_vc:
                clicked_vc = str(pts_vc[0].get("y", "")).strip()
                if clicked_vc and clicked_vc != st.session_state[_SK_VC]:
                    st.session_state[_SK_VC] = clicked_vc
                    st.session_state[_SK_PR] = ""
                    st.rerun()
            else:
                # Sin puntos seleccionados → limpiar selección de vicerrectoría
                if st.session_state[_SK_VC]:
                    st.session_state[_SK_VC] = ""
                    st.session_state[_SK_PR] = ""
                    st.rerun()

    # Filtrar procesos según vicerrectoría seleccionada
    df_para_proc = (
        df_con[df_con["Vicerrectoria"] == st.session_state[_SK_VC]]
        if st.session_state[_SK_VC] and "Vicerrectoria" in df_con.columns
        else df_con
    )

    with col_pr:
        st.markdown("#### Por Proceso")
        if "Proceso" in df_para_proc.columns:
            fig_pr = _fig_barras_nivel(df_para_proc, "Proceso")
            ev_pr = st.plotly_chart(
                fig_pr, use_container_width=True, key="con_chart_proc",
                on_select="rerun", selection_mode="points",
            )
            pts_pr = (ev_pr.selection or {}).get("points", [])
            if pts_pr:
                clicked_pr = str(pts_pr[0].get("y", "")).strip()
                if clicked_pr and clicked_pr != st.session_state[_SK_PR]:
                    st.session_state[_SK_PR] = clicked_pr
                    st.rerun()
            else:
                if st.session_state[_SK_PR]:
                    st.session_state[_SK_PR] = ""
                    st.rerun()

    # ── Chips de filtros activos ──────────────────────────────────────────
    activos = []
    if st.session_state[_SK_VC]:
        activos.append(f"Vicerrectoría: **{st.session_state[_SK_VC]}**")
    if st.session_state[_SK_PR]:
        activos.append(f"Proceso: **{st.session_state[_SK_PR]}**")

    inf_col, btn_col = st.columns([5, 1])
    with inf_col:
        if activos:
            st.info("🔍 " + " · ".join(activos))
    with btn_col:
        if activos and st.button("✖ Limpiar", key="con_clear_btn"):
            st.session_state[_SK_VC] = ""
            st.session_state[_SK_PR] = ""
            st.rerun()

    st.markdown("---")

    # ── Filtros adicionales de texto y nivel ──────────────────────────────
    with st.expander("🔍 Filtros adicionales", expanded=False):
        fa1, fa2, fa3 = st.columns(3)
        with fa1:
            txt_id  = st.text_input("ID", key="con_txt_id",  placeholder="Buscar ID...")
        with fa2:
            txt_nom = st.text_input("Indicador", key="con_txt_nom", placeholder="Buscar nombre...")
        with fa3:
            niv_opts = [""] + [n for n in _NIVEL_ORDEN
                               if n in df_con["Nivel de cumplimiento"].unique()]
            sel_niv = st.selectbox("Nivel de cumplimiento", niv_opts, key="con_niv",
                                   format_func=lambda x: "— Todos —" if x == "" else x)

    # ── Aplicar todos los filtros ─────────────────────────────────────────
    df_filt = df_con.copy()
    if st.session_state[_SK_VC] and "Vicerrectoria" in df_filt.columns:
        df_filt = df_filt[df_filt["Vicerrectoria"] == st.session_state[_SK_VC]]
    if st.session_state[_SK_PR] and "Proceso" in df_filt.columns:
        df_filt = df_filt[df_filt["Proceso"] == st.session_state[_SK_PR]]
    if txt_id.strip():
        df_filt = df_filt[df_filt["Id"].astype(str).str.contains(txt_id.strip(), case=False, na=False)]
    if txt_nom.strip() and "Indicador" in df_filt.columns:
        df_filt = df_filt[df_filt["Indicador"].astype(str).str.contains(txt_nom.strip(), case=False, na=False)]
    if sel_niv:
        df_filt = df_filt[df_filt["Nivel de cumplimiento"] == sel_niv]

    st.caption(f"Mostrando **{len(df_filt)}** de **{len(df_con)}** indicadores · clic en una fila para ver el detalle histórico")

    # ── Tabla ─────────────────────────────────────────────────────────────
    _COLS_CON = [
        "Id", "Indicador", "Nivel de cumplimiento",
        "Meta_fmt", "Ejecucion_fmt", "Cumplimiento",
        "Fecha reporte",
        "Vicerrectoria", "Proceso", "Periodicidad", "Sentido", "linea",
    ]
    cols_show = [c for c in _COLS_CON if c in df_filt.columns]
    df_mostrar = df_filt[cols_show].copy()

    col_cfg = {
        "Id":                    st.column_config.TextColumn("ID",           width="small"),
        "Indicador":             st.column_config.TextColumn("Indicador",    width="large"),
        "Nivel de cumplimiento": st.column_config.TextColumn("Nivel",        width="medium"),
        "Meta_fmt":              st.column_config.TextColumn("Meta",         width="small"),
        "Ejecucion_fmt":         st.column_config.TextColumn("Ejecución",    width="small"),
        "Cumplimiento":          st.column_config.TextColumn("Cumplimiento", width="small"),
        "Fecha reporte":         st.column_config.TextColumn("Fecha",        width="small"),
        "Vicerrectoria":         st.column_config.TextColumn("Vicerrectoría", width="medium"),
        "Proceso":               st.column_config.TextColumn("Proceso",      width="medium"),
        "Periodicidad":          st.column_config.TextColumn("Periodicidad", width="small"),
        "Sentido":               st.column_config.TextColumn("Sentido",      width="small"),
        "linea":                 st.column_config.TextColumn("Línea",        width="medium"),
    }

    ev_tabla = st.dataframe(
        df_mostrar.style.apply(_estilo_nivel, axis=1),
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        column_config=col_cfg,
        key="con_tabla_detalle",
    )

    # ── Dialog de detalle ─────────────────────────────────────────────────
    if ev_tabla.selection and ev_tabla.selection.get("rows"):
        idx_det = ev_tabla.selection["rows"][0]
        st.session_state[_KEY_DET] = df_filt["Id"].iloc[idx_det]

    id_det = st.session_state.get(_KEY_DET)
    if id_det:
        df_hist = _cargar_historico_detalle()
        if not df_hist.empty and "Id" in df_hist.columns:
            df_ind_det = df_hist[df_hist["Id"] == id_det].copy()
        else:
            df_ind_det = _raw[_raw["Id"] == id_det].copy()
            if "Fecha" not in df_ind_det.columns and "fecha" in df_ind_det.columns:
                df_ind_det = df_ind_det.rename(columns={"fecha": "Fecha"})

        @st.dialog(f"Detalle: {id_det}", width="large")
        def _dialog_detalle():
            if st.button("✖ Cerrar"):
                st.session_state[_KEY_DET] = None
                st.rerun()
            panel_detalle_indicador(df_ind_det, id_det, df_ind_det)

        _dialog_detalle()

    # ── Exportar ──────────────────────────────────────────────────────────
    st.download_button(
        "📥 Exportar Excel",
        data=exportar_excel(df_mostrar, "Cumplimiento"),
        file_name="reporte_cumplimiento.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="exp_cumplimiento",
    )
