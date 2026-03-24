"""
pages/6_Historial_Cierres.py — Historial de Cierres por Indicador
=================================================================
Fuente: data/output/Resultados Consolidados.xlsx → Consolidado Cierres
Catálogo activo: data/raw/Kawak/{año}.xlsx → IDs activos por año

Vistas:
  · Matriz de Calor  → indicadores (filas) × períodos (columnas), coloreado por nivel
  · Consolidado      → tabla filtrable con semáforo de cumplimiento
"""
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from components.charts import exportar_excel

# ── Rutas ──────────────────────────────────────────────────────────────────────
_BASE        = Path(__file__).parent.parent
_RUTA_CONS   = _BASE / "data" / "output" / "Resultados Consolidados.xlsx"
_KAWAK_DIR   = _BASE / "data" / "raw" / "Kawak"

# ── Umbrales (alineados con core/config.py) ────────────────────────────────────
_PELIGRO           = 0.80
_ALERTA            = 1.00
_SOBRECUMPLIMIENTO = 1.05

# ── Paleta ────────────────────────────────────────────────────────────────────
_NIVEL_BG = {
    "Sobrecumplimiento": "#D0E4FF",
    "Cumplimiento":      "#E8F5E9",
    "Alerta":            "#FEF3D0",
    "Peligro":           "#FFCDD2",
    "Sin dato":          "#F5F5F5",
}
_NIVEL_COLOR = {
    "Sobrecumplimiento": "#0D47A1",
    "Cumplimiento":      "#1B5E20",
    "Alerta":            "#7B5800",
    "Peligro":           "#B71C1C",
    "Sin dato":          "#9E9E9E",
}

# Colorscale Plotly: valores decimales 0 → 1.3
# Puntos de corte normalizados al rango [0, 1.3]
_ZMAX = 1.35
_COLORSCALE = [
    [0.000,            "#FFCDD2"],
    [_PELIGRO/_ZMAX,   "#EF9A9A"],
    [_ALERTA/_ZMAX,    "#FEF3D0"],
    [(_ALERTA + 0.001)/_ZMAX, "#C8E6C9"],
    [_SOBRECUMPLIMIENTO/_ZMAX, "#81C784"],
    [1.000,            "#1A3A5C"],
]


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _id_limpio(x) -> str:
    if pd.isna(x): return ""
    try:
        f = float(x)
        return str(int(f)) if f == int(f) else str(f)
    except (ValueError, TypeError):
        return str(x).strip()


def _nivel(c) -> str:
    try:
        v = float(c)
    except (TypeError, ValueError):
        return "Sin dato"
    if v >= _SOBRECUMPLIMIENTO: return "Sobrecumplimiento"
    if v >= _ALERTA:            return "Cumplimiento"
    if v >= _PELIGRO:           return "Alerta"
    return "Peligro"


def _fmt_pct(v) -> str:
    try:
        return f"{float(v)*100:.1f}%"
    except (TypeError, ValueError):
        return "—"


def _color_nivel(row):
    """Estilo por fila: colorea celda Nivel y Cumplimiento."""
    estilos = []
    for col in row.index:
        if col in ("Nivel", "Cumplimiento %"):
            n = row.get("Nivel", "Sin dato")
            bg = _NIVEL_BG.get(n, "")
            estilos.append(f"background-color:{bg}" if bg else "")
        else:
            estilos.append("")
    return estilos


# ══════════════════════════════════════════════════════════════════════════════
# CARGA DE DATOS
# ══════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=300, show_spinner=False)
def _cargar_kawak_ids(year: int) -> set:
    """IDs activos del catálogo Kawak para el año indicado."""
    ruta = _KAWAK_DIR / f"{year}.xlsx"
    if not ruta.exists():
        return set()
    try:
        df = pd.read_excel(str(ruta), engine="openpyxl", usecols=[0])
        df.columns = ["Id"]
        return set(df["Id"].apply(_id_limpio).dropna())
    except Exception:
        return set()


@st.cache_data(ttl=300, show_spinner="Cargando cierres históricos...")
def _cargar_cierres() -> pd.DataFrame:
    if not _RUTA_CONS.exists():
        return pd.DataFrame()
    try:
        df = pd.read_excel(str(_RUTA_CONS),
                           sheet_name="Consolidado Cierres", engine="openpyxl")
    except Exception:
        return pd.DataFrame()

    df.columns = [str(c).strip() for c in df.columns]
    if "Id" in df.columns:
        df["Id"] = df["Id"].apply(_id_limpio)
    if "Fecha" in df.columns:
        df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
    for col in ("Cumplimiento", "Cumplimiento Real"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    # Columna Año puede venir con encoding roto; detectar por posición/contenido
    anio_col = next((c for c in df.columns
                     if c.startswith("A") and c.endswith("o") and len(c) <= 4), None)
    if anio_col and anio_col != "Año":
        df = df.rename(columns={anio_col: "Año"})
    if "Año" in df.columns:
        df["Año"] = pd.to_numeric(df["Año"], errors="coerce").astype("Int64")
    return df


# ── Cargar datos base ──────────────────────────────────────────────────────────
df_all = _cargar_cierres()

if df_all.empty:
    st.error("No se encontró la hoja **Consolidado Cierres** en `Resultados Consolidados.xlsx`.")
    st.stop()

# ── Años de catálogo disponibles ───────────────────────────────────────────────
_años_kawak = sorted(
    int(p.stem) for p in _KAWAK_DIR.glob("*.xlsx")
    if p.stem.isdigit()
)

# ══════════════════════════════════════════════════════════════════════════════
# ENCABEZADO Y FILTROS
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("# 📊 Historial de Cierres por Indicador")

fc1, fc2, fc3, fc4 = st.columns(4)

with fc1:
    _año_kawak = st.selectbox(
        "Catálogo activo (año)",
        _años_kawak,
        index=len(_años_kawak) - 1 if _años_kawak else 0,
        key="hc_año_kawak",
        help="Filtra a los indicadores activos en ese año según Kawak",
    )

with fc2:
    _perios_disp = ["Todas"] + sorted(df_all["Periodicidad"].dropna().unique().tolist()) \
                   if "Periodicidad" in df_all.columns else ["Todas"]
    _perio_sel = st.selectbox("Periodicidad", _perios_disp, key="hc_perio")

with fc3:
    _procs_disp = ["Todos"] + sorted(df_all["Proceso"].dropna().unique().tolist()) \
                  if "Proceso" in df_all.columns else ["Todos"]
    _proc_sel = st.selectbox("Proceso", _procs_disp, key="hc_proc")

with fc4:
    _periodos_hist = ["Todos"] + sorted(df_all["Periodo"].dropna().unique().tolist()) \
                     if "Periodo" in df_all.columns else ["Todos"]
    _periodo_sel = st.selectbox("Período", _periodos_hist,
                                index=len(_periodos_hist) - 1,
                                key="hc_periodo")

st.markdown("---")

# ── Aplicar filtros ─────────────────────────────────────────────────────────
ids_activos = _cargar_kawak_ids(_año_kawak)
df = df_all[df_all["Id"].isin(ids_activos)].copy() if ids_activos else df_all.copy()

if _perio_sel != "Todas" and "Periodicidad" in df.columns:
    df = df[df["Periodicidad"] == _perio_sel]
if _proc_sel != "Todos" and "Proceso" in df.columns:
    df = df[df["Proceso"] == _proc_sel]

# df_tabla: aplica también filtro de período
df_tabla = df.copy()
if _periodo_sel != "Todos" and "Periodo" in df_tabla.columns:
    df_tabla = df_tabla[df_tabla["Periodo"] == _periodo_sel]

st.caption(
    f"**{df['Id'].nunique()}** indicadores activos · "
    f"**{df['Periodo'].nunique() if 'Periodo' in df.columns else '—'}** períodos · "
    f"**{len(df):,}** registros totales"
)

# ══════════════════════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════════════════════
tab_calor, tab_tabla = st.tabs(["🌡️ Matriz de Calor", "📋 Consolidado Cierres"])


# ─────────────────────────────────────────────────────────────────────────────
# TAB 1 — MATRIZ DE CALOR
# ─────────────────────────────────────────────────────────────────────────────
with tab_calor:
    if df.empty or "Periodo" not in df.columns or "Cumplimiento" not in df.columns:
        st.info("Sin datos para mostrar.")
    else:
        # Pivot: Id × Periodo → último valor de Cumplimiento
        pivot = (
            df.sort_values("Fecha")
            .groupby(["Id", "Periodo"])["Cumplimiento"]
            .last()
            .unstack()
        )
        # Ordenar columnas cronológicamente
        pivot = pivot.reindex(sorted(pivot.columns), axis=1)

        # Etiquetas de fila: "ID — Nombre"
        meta = (df.drop_duplicates(subset=["Id"], keep="last")
                .set_index("Id")[["Indicador", "Proceso"]]
                if "Indicador" in df.columns else pd.DataFrame(index=pivot.index))

        y_labels = []
        for kid in pivot.index:
            ind = str(meta.loc[kid, "Indicador"])[:45] if kid in meta.index else kid
            y_labels.append(f"{kid} — {ind}")

        # Texto de celda: porcentaje o vacío
        z_text = pivot.applymap(
            lambda v: f"{v*100:.1f}%" if pd.notna(v) else ""
        )

        h = max(400, len(pivot) * 28 + 80)

        fig_calor = go.Figure(go.Heatmap(
            z=pivot.values.tolist(),
            x=pivot.columns.tolist(),
            y=y_labels,
            text=z_text.values.tolist(),
            texttemplate="%{text}",
            textfont=dict(size=10),
            colorscale=_COLORSCALE,
            zmin=0,
            zmax=_ZMAX,
            showscale=True,
            colorbar=dict(
                title="Cumplimiento",
                tickvals=[0, _PELIGRO, _ALERTA, _SOBRECUMPLIMIENTO, 1.30],
                ticktext=["0%", "80% Peligro", "100% Cumpl.", "105% Sobre", "130%+"],
                len=0.7,
            ),
            hovertemplate=(
                "<b>%{y}</b><br>"
                "Período: <b>%{x}</b><br>"
                "Cumplimiento: <b>%{text}</b>"
                "<extra></extra>"
            ),
        ))
        fig_calor.update_layout(
            height=h,
            xaxis=dict(title="Período", side="top", tickangle=0),
            yaxis=dict(title="", autorange="reversed",
                       tickfont=dict(size=10)),
            plot_bgcolor="white",
            paper_bgcolor="white",
            margin=dict(t=60, b=20, l=10, r=120),
        )
        st.plotly_chart(fig_calor, use_container_width=True)

        # Leyenda compacta
        leg_c = st.columns(4)
        for col_l, (nivel, bg) in zip(leg_c, [
            ("Peligro < 80%",           _NIVEL_BG["Peligro"]),
            ("Alerta 80–99%",           _NIVEL_BG["Alerta"]),
            ("Cumplimiento ≥ 100%",     _NIVEL_BG["Cumplimiento"]),
            ("Sobrecumplimiento ≥ 105%", _NIVEL_BG["Sobrecumplimiento"]),
        ]):
            col_l.markdown(
                f"<div style='background:{bg};padding:6px 10px;"
                f"border-radius:6px;text-align:center;font-size:12px'>{nivel}</div>",
                unsafe_allow_html=True,
            )

        st.download_button(
            "📥 Exportar datos de la matriz",
            data=exportar_excel(pivot.reset_index(), "Matriz Calor"),
            file_name="matriz_calor.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="exp_matriz",
        )


# ─────────────────────────────────────────────────────────────────────────────
# TAB 2 — CONSOLIDADO CIERRES
# ─────────────────────────────────────────────────────────────────────────────
with tab_tabla:
    if df_tabla.empty:
        st.info("Sin datos para el período seleccionado.")
    else:
        # Agregar columnas formateadas
        df_show = df_tabla.copy()
        df_show["Nivel"]         = df_show["Cumplimiento"].apply(_nivel)
        df_show["Cumplimiento %"] = df_show["Cumplimiento"].apply(_fmt_pct)

        # KPIs rápidos del período
        k1, k2, k3, k4, k5 = st.columns(5)
        cnts = df_show["Nivel"].value_counts()
        total_k = len(df_show)
        with k1: st.metric("Total", total_k)
        with k2: st.metric("🔴 Peligro",           int(cnts.get("Peligro",           0)))
        with k3: st.metric("🟡 Alerta",             int(cnts.get("Alerta",             0)))
        with k4: st.metric("🟢 Cumplimiento",       int(cnts.get("Cumplimiento",       0)))
        with k5: st.metric("🔵 Sobrecumplimiento",  int(cnts.get("Sobrecumplimiento",  0)))

        st.markdown("---")

        # Filtros de tabla
        with st.expander("🔍 Filtros", expanded=False):
            tf1, tf2, tf3 = st.columns(3)
            with tf1:
                txt_id = st.text_input("ID", key="hc_tid", placeholder="Buscar ID…")
            with tf2:
                txt_ind = st.text_input("Indicador", key="hc_tind", placeholder="Buscar nombre…")
            with tf3:
                opts_niv = [""] + sorted(df_show["Nivel"].dropna().unique().tolist())
                sel_niv = st.selectbox("Nivel", opts_niv, key="hc_tniv",
                                       format_func=lambda x: "— Todos —" if x == "" else x)

        mask = pd.Series(True, index=df_show.index)
        if txt_id.strip():
            mask &= df_show["Id"].astype(str).str.contains(txt_id.strip(), case=False, na=False)
        if txt_ind.strip() and "Indicador" in df_show.columns:
            mask &= df_show["Indicador"].astype(str).str.contains(txt_ind.strip(), case=False, na=False)
        if sel_niv:
            mask &= df_show["Nivel"] == sel_niv
        df_show = df_show[mask].reset_index(drop=True)

        st.caption(f"Mostrando **{len(df_show):,}** registros")

        # Columnas a mostrar
        _COLS = ["Id", "Indicador", "Proceso", "Periodicidad", "Sentido",
                 "Fecha", "Periodo", "Meta", "Ejecucion",
                 "Cumplimiento %", "Nivel"]
        cols_show = [c for c in _COLS if c in df_show.columns]
        df_disp = df_show[cols_show].copy()
        if "Fecha" in df_disp.columns:
            df_disp["Fecha"] = df_disp["Fecha"].dt.strftime("%d/%m/%Y").fillna("—")

        col_cfg = {}
        if "Indicador" in df_disp.columns:
            col_cfg["Indicador"] = st.column_config.TextColumn("Indicador", width="large")
        if "Nivel" in df_disp.columns:
            col_cfg["Nivel"] = st.column_config.TextColumn("Nivel", width="medium")

        st.dataframe(
            df_disp.style.apply(_color_nivel, axis=1),
            use_container_width=True, hide_index=True,
            column_config=col_cfg,
        )

        st.download_button(
            "📥 Exportar Excel",
            data=exportar_excel(df_disp, "Consolidado Cierres"),
            file_name="consolidado_cierres.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="exp_cierres",
        )
