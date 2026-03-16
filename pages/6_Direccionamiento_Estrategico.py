"""
pages/6_Direccionamiento_Estrategico.py — Informe Proceso Direccionamiento Estratégico (temporal).

Subprocesos:
  · Planeación Estratégica     (excluye IDs: 373, 390, 414, 415, 416, 417, 418, 420, 469, 470, 471)
  · Desempeño Institucional
  · Gestión de Proyectos

Secciones por subproceso:
  1. KPIs de estado actual
  2. Avance histórico: tendencia de cumplimiento por período
  3. Cierre de año: distribución por categoría y cumplimiento promedio anual
  4. Tabla interactiva con filtros (año, período, categoría, rango cumplimiento)
  5. Ficha completa de indicador al hacer clic (panel_detalle_indicador)
  6. Tabla de cierre de año por indicador (exportable)

Fuente: data/output/Resultados Consolidados.xlsx → Consolidado Semestral
"""
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from components.charts import (
    colorear_tabla_categoria,
    exportar_excel,
    grafico_detalle_indicador,
    panel_detalle_indicador,
    tabla_historica_indicador,
)
from core.config import (
    COLOR_CATEGORIA,
    COLOR_CATEGORIA_CLARO,
    COLORES,
    ORDEN_CATEGORIAS,
)
from services.data_loader import cargar_dataset

# ── Constantes del proceso ─────────────────────────────────────────────────────
# En el dataset estos tres procesos conforman el bloque Direccionamiento Estratégico
_PROCESOS_DIR = {
    "Planeación Estratégica",
    "Desempeño Institucional",
    "Gestión de Proyectos",
}

# IDs excluidos del proceso Planeación Estratégica
_IDS_EXCLUIR_PLAN = {
    "373", "390", "414", "415", "416", "417", "418", "420", "469", "470", "471"
}

_COLOR_SUB = {
    "Planeación Estratégica":  "#1A3A5C",
    "Desempeño Institucional": "#1565C0",
    "Gestión de Proyectos":    "#2E7D32",
}

_ICONO_CAT = {
    "Peligro":           "🔴",
    "Alerta":            "🟡",
    "Cumplimiento":      "🟢",
    "Sobrecumplimiento": "🔵",
    "Sin dato":          "⚫",
}

# ── Helpers ────────────────────────────────────────────────────────────────────

def _ultimo_por_indicador(df: pd.DataFrame) -> pd.DataFrame:
    """Un registro por indicador: el más reciente por Fecha o Anio."""
    if df.empty or "Id" not in df.columns:
        return df
    col = "Fecha" if "Fecha" in df.columns else ("Anio" if "Anio" in df.columns else None)
    if col:
        return (df.sort_values(col)
                  .drop_duplicates(subset="Id", keep="last")
                  .reset_index(drop=True))
    return df.drop_duplicates(subset="Id", keep="last").reset_index(drop=True)


def _cierre_de_anio(df: pd.DataFrame) -> pd.DataFrame:
    """Para cada (Id, Anio) toma el último registro → cierre anual."""
    if df.empty or "Anio" not in df.columns:
        return df
    col = "Fecha" if "Fecha" in df.columns else "Periodo"
    return (df.sort_values(col)
              .drop_duplicates(subset=["Id", "Anio"], keep="last")
              .reset_index(drop=True))


def _kpis_subproceso(df_ultimo: pd.DataFrame):
    """Calcula total e indicadores por categoría."""
    total = len(df_ultimo)
    cats = {}
    for cat in ORDEN_CATEGORIAS:
        n = int((df_ultimo["Categoria"] == cat).sum()) if "Categoria" in df_ultimo.columns else 0
        cats[cat] = {"n": n, "pct": round(n / total * 100, 1) if total else 0}
    return total, cats


# ── Componentes de visualización ───────────────────────────────────────────────

def _render_kpis(total: int, cats: dict):
    cols = st.columns(5)
    definiciones = [
        ("Total activos",          total,                         COLORES["primario"],          ""),
        ("🔴 Peligro",             cats["Peligro"]["n"],          COLORES["peligro"],           f'{cats["Peligro"]["pct"]}%'),
        ("🟡 Alerta",              cats["Alerta"]["n"],           COLORES["alerta"],            f'{cats["Alerta"]["pct"]}%'),
        ("🟢 Cumplimiento",        cats["Cumplimiento"]["n"],     COLORES["cumplimiento"],      f'{cats["Cumplimiento"]["pct"]}%'),
        ("🔵 Sobrecumplimiento",   cats["Sobrecumplimiento"]["n"],COLORES["sobrecumplimiento"], f'{cats["Sobrecumplimiento"]["pct"]}%'),
    ]
    for col, (label, val, color, delta) in zip(cols, definiciones):
        with col:
            delta_html = f"<div style='font-size:0.75rem;color:#888;margin-top:2px'>{delta}</div>" if delta else ""
            st.markdown(
                f"""<div style='background:white;border-left:4px solid {color};
                    border-radius:8px;padding:14px 18px;
                    box-shadow:0 2px 6px rgba(0,0,0,0.07);margin-bottom:8px'>
                    <div style='font-size:0.78rem;color:#555;font-weight:500'>{label}</div>
                    <div style='font-size:2rem;font-weight:700;color:{color};line-height:1.1'>{val}</div>
                    {delta_html}</div>""",
                unsafe_allow_html=True,
            )


def _grafico_tendencia_historica(df: pd.DataFrame, titulo: str = "") -> go.Figure:
    """
    Línea de cumplimiento promedio por período (todos los registros, no solo cierre).
    Muestra la evolución real período a período.
    """
    if df.empty or "Cumplimiento_norm" not in df.columns:
        return go.Figure()

    col_x = "Fecha" if "Fecha" in df.columns else "Periodo"
    agg = (df.groupby(col_x)["Cumplimiento_norm"]
             .mean().reset_index()
             .sort_values(col_x)
             .assign(pct=lambda x: (x["Cumplimiento_norm"] * 100).round(1)))

    if "Periodo" in df.columns and col_x == "Fecha":
        per_map = df.groupby("Fecha")["Periodo"].first().to_dict()
        agg["label"] = agg["Fecha"].map(per_map).fillna(agg["Fecha"].astype(str))
    else:
        agg["label"] = agg[col_x].astype(str)

    fig = go.Figure()

    # Zonas de fondo
    y_max = max(130.0, float(agg["pct"].max()) + 15) if not agg.empty else 130.0
    for y0, y1, fill in [
        (0, 80,    "#FFCDD2"),
        (80, 100,  "#FFF9C4"),
        (100, 105, "#E8F5E9"),
        (105, y_max, "#D0E4FF"),
    ]:
        fig.add_hrect(y0=y0, y1=min(y1, y_max), fillcolor=fill, opacity=0.30, line_width=0)

    # Línea de cumplimiento promedio
    fig.add_trace(go.Scatter(
        x=agg["label"],
        y=agg["pct"],
        mode="lines+markers+text",
        line=dict(color=COLORES["primario"], width=2.5),
        marker=dict(size=10, color=COLORES["secundario"], line=dict(width=2, color="white")),
        text=(agg["pct"].astype(str) + "%").tolist(),
        textposition="top center",
        textfont=dict(size=9),
        hovertemplate="<b>%{x}</b><br>Cumplimiento promedio: %{y:.1f}%<extra></extra>",
        showlegend=False,
    ))

    # Líneas de referencia
    fig.add_hline(y=100, line_dash="dash", line_color="#2E7D32", line_width=1.5,
                  annotation_text="Meta 100%", annotation_position="right")
    fig.add_hline(y=80,  line_dash="dot",  line_color="#C62828", line_width=1.5,
                  annotation_text="Peligro 80%", annotation_position="right")

    fig.update_layout(
        title=titulo or "Avance histórico — cumplimiento promedio por período",
        height=320,
        yaxis=dict(title="Cumplimiento (%)", ticksuffix="%", range=[0, y_max]),
        xaxis=dict(title="Período", type="category", tickangle=-35, tickfont=dict(size=9)),
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(t=45, b=70, l=60, r=80),
    )
    return fig


def _grafico_distribucion_cierre_anio(df_cierre: pd.DataFrame) -> go.Figure:
    """Barras apiladas: distribución de categorías por año (cierre anual)."""
    if df_cierre.empty or "Anio" not in df_cierre.columns:
        return go.Figure()

    anios = sorted(df_cierre["Anio"].dropna().unique())
    fig = go.Figure()
    for cat in ORDEN_CATEGORIAS:
        if cat == "Sin dato":
            continue
        vals = [int((df_cierre[df_cierre["Anio"] == a]["Categoria"] == cat).sum()) for a in anios]
        fig.add_trace(go.Bar(
            x=[str(int(a)) for a in anios],
            y=vals,
            name=cat,
            marker_color=COLOR_CATEGORIA[cat],
            text=[v if v > 0 else "" for v in vals],
            textposition="inside",
            insidetextanchor="middle",
            textfont=dict(color="white", size=11),
        ))

    fig.update_layout(
        barmode="stack",
        title="Distribución por categoría al cierre de cada año",
        height=320,
        xaxis_title="Año",
        yaxis_title="Indicadores",
        plot_bgcolor="white",
        paper_bgcolor="white",
        legend=dict(orientation="h", y=-0.22),
        margin=dict(t=45, b=80),
    )
    return fig


def _grafico_cumplimiento_cierre_anio(df_cierre: pd.DataFrame) -> go.Figure:
    """Línea: cumplimiento promedio por año (cierre anual)."""
    if df_cierre.empty or "Anio" not in df_cierre.columns or "Cumplimiento_norm" not in df_cierre.columns:
        return go.Figure()

    agg = (df_cierre.groupby("Anio")["Cumplimiento_norm"]
                     .mean().reset_index()
                     .sort_values("Anio")
                     .assign(pct=lambda x: (x["Cumplimiento_norm"] * 100).round(1)))

    y_max = max(130.0, float(agg["pct"].max()) + 15)

    fig = go.Figure()
    for y0, y1, fill in [(0, 80, "#FFCDD2"), (80, 100, "#FFF9C4"), (100, 105, "#E8F5E9"), (105, y_max, "#D0E4FF")]:
        fig.add_hrect(y0=y0, y1=min(y1, y_max), fillcolor=fill, opacity=0.25, line_width=0)

    fig.add_trace(go.Scatter(
        x=agg["Anio"].astype(str),
        y=agg["pct"],
        mode="lines+markers+text",
        line=dict(color="#E65100", width=2.5),
        marker=dict(size=12, color="#E65100", line=dict(width=2, color="white")),
        text=(agg["pct"].astype(str) + "%").tolist(),
        textposition="top center",
        textfont=dict(size=10),
        hovertemplate="<b>Año %{x}</b><br>Cumplimiento al cierre: %{y:.1f}%<extra></extra>",
    ))
    fig.add_hline(y=100, line_dash="dash", line_color="#2E7D32", line_width=1.5)
    fig.add_hline(y=80,  line_dash="dot",  line_color="#C62828", line_width=1.5)

    fig.update_layout(
        title="Cumplimiento promedio al cierre de año",
        height=320,
        yaxis=dict(title="Cumplimiento (%)", ticksuffix="%", range=[0, y_max]),
        xaxis_title="Año",
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(t=45, b=40, l=60, r=40),
    )
    return fig


# ── Filtros de tabla ───────────────────────────────────────────────────────────

def _filtros_tabla(df: pd.DataFrame, prefix: str):
    """Panel de filtros para la tabla histórica de indicadores."""
    with st.expander("🔍 Filtros", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            txt_id = st.text_input("Buscar ID", key=f"{prefix}_id", placeholder="ej: 400")
        with c2:
            txt_nom = st.text_input("Buscar nombre", key=f"{prefix}_nom", placeholder="texto del indicador...")

        c3, c4, c5 = st.columns(3)
        with c3:
            anios_d = sorted([int(a) for a in df["Anio"].dropna().unique()]) if "Anio" in df.columns else []
            sel_anios = st.multiselect("Año", anios_d, key=f"{prefix}_anio")
        with c4:
            pers_d = sorted(df["Periodo"].dropna().unique().tolist()) if "Periodo" in df.columns else []
            sel_periodos = st.multiselect("Período", pers_d, key=f"{prefix}_per")
        with c5:
            cats_d = [c for c in ORDEN_CATEGORIAS if "Categoria" in df.columns and c in df["Categoria"].unique()]
            sel_cats = st.multiselect("Categoría", cats_d, key=f"{prefix}_cat")

        # Rango de cumplimiento
        if "Cumplimiento_norm" in df.columns:
            cum_vals = df["Cumplimiento_norm"].dropna() * 100
            vmax = float(max(200.0, cum_vals.max())) if not cum_vals.empty else 200.0
            rng_cum = st.slider(
                "Rango Cumplimiento (%)", 0.0, vmax, (0.0, vmax),
                step=1.0, key=f"{prefix}_cum",
            )
        else:
            rng_cum = (0.0, 200.0)

    return txt_id, txt_nom, sel_anios, sel_periodos, sel_cats, rng_cum


def _aplicar_filtros(df: pd.DataFrame, txt_id, txt_nom, sel_anios,
                     sel_periodos, sel_cats, rng_cum) -> pd.DataFrame:
    m = pd.Series(True, index=df.index)
    if txt_id.strip() and "Id" in df.columns:
        m &= df["Id"].str.contains(txt_id.strip(), case=False, na=False)
    if txt_nom.strip() and "Indicador" in df.columns:
        m &= df["Indicador"].astype(str).str.contains(txt_nom.strip(), case=False, na=False)
    if sel_anios and "Anio" in df.columns:
        m &= df["Anio"].isin(sel_anios)
    if sel_periodos and "Periodo" in df.columns:
        m &= df["Periodo"].isin(sel_periodos)
    if sel_cats and "Categoria" in df.columns:
        m &= df["Categoria"].isin(sel_cats)
    if "Cumplimiento_norm" in df.columns:
        cum_pct = df["Cumplimiento_norm"] * 100
        m &= cum_pct.isna() | ((cum_pct >= rng_cum[0]) & (cum_pct <= rng_cum[1]))
    return df[m].reset_index(drop=True)


def _cols_tabla_vis(df: pd.DataFrame) -> list:
    preferidas = [
        "Id", "Indicador", "Subproceso", "Anio", "Periodo",
        "Meta", "Ejecucion", "Cumplimiento_norm",
        "Categoria", "Sentido", "Periodicidad",
    ]
    return [c for c in preferidas if c in df.columns]


def _tabla_display(df: pd.DataFrame) -> pd.DataFrame:
    """Renombra y formatea columnas para visualización."""
    df = df.copy()
    if "Cumplimiento_norm" in df.columns:
        df["Cumplimiento_norm"] = (df["Cumplimiento_norm"] * 100).round(1).astype(str) + "%"
    return df.rename(columns={
        "Cumplimiento_norm": "Cumplimiento%",
        "Ejecucion":         "Ejecución",
        "Anio":              "Año",
    })


# ── Render de cada subproceso ──────────────────────────────────────────────────

def _render_tab_subproceso(
    df_sub: pd.DataFrame,
    nombre_sub: str,
    prefix: str,
    df_global: pd.DataFrame,
):
    """
    Renderiza el informe completo de un subproceso:
    KPIs · Avance histórico · Cierre de año · Tabla con filtros · Fichas de indicador
    """
    if df_sub.empty:
        st.info(f"No se encontraron indicadores para **{nombre_sub}**.")
        return

    color = _COLOR_SUB.get(nombre_sub, COLORES["primario"])
    st.markdown(
        f"<h3 style='color:{color};margin-bottom:4px'>{nombre_sub}</h3>",
        unsafe_allow_html=True,
    )

    n_inds = df_sub["Id"].nunique() if "Id" in df_sub.columns else len(df_sub)
    anios_sub = sorted([int(a) for a in df_sub["Anio"].dropna().unique()]) if "Anio" in df_sub.columns else []
    st.caption(
        f"**{n_inds}** indicadores únicos · "
        f"Años disponibles: **{min(anios_sub)}–{max(anios_sub)}**" if anios_sub else f"**{n_inds}** indicadores únicos"
    )
    st.markdown("---")

    # ── KPIs (último registro por indicador) ──────────────────────────────────
    df_ult = _ultimo_por_indicador(df_sub)
    total, cats = _kpis_subproceso(df_ult)
    _render_kpis(total, cats)
    st.markdown("<br>", unsafe_allow_html=True)

    # ── Avance histórico ──────────────────────────────────────────────────────
    st.markdown("### 📈 Avance histórico por período")
    st.caption("Cumplimiento promedio del subproceso a lo largo de todos los períodos registrados.")
    fig_hist = _grafico_tendencia_historica(df_sub)
    st.plotly_chart(fig_hist, use_container_width=True)

    st.markdown("---")

    # ── Cierre de año ──────────────────────────────────────────────────────────
    st.markdown("### 🗓️ Cierre de año")
    st.caption("Último período registrado por indicador en cada año (resultado final anual).")

    df_cierre = _cierre_de_anio(df_sub)

    gc1, gc2 = st.columns(2)
    with gc1:
        fig_dist = _grafico_distribucion_cierre_anio(df_cierre)
        st.plotly_chart(fig_dist, use_container_width=True)
    with gc2:
        fig_cum_a = _grafico_cumplimiento_cierre_anio(df_cierre)
        st.plotly_chart(fig_cum_a, use_container_width=True)

    # Tabla cierre de año
    with st.expander("📋 Ver tabla de cierre de año por indicador", expanded=False):
        cols_c = [c for c in ["Id", "Indicador", "Subproceso", "Anio", "Periodo",
                               "Meta", "Ejecucion", "Cumplimiento_norm",
                               "Categoria", "Sentido"] if c in df_cierre.columns]
        df_cierre_disp = _tabla_display(df_cierre[cols_c].sort_values(
            ["Id", "Anio"] if "Anio" in df_cierre.columns else ["Id"]
        ))
        st.dataframe(
            colorear_tabla_categoria(df_cierre_disp, "Categoria"),
            use_container_width=True, hide_index=True,
        )
        st.download_button(
            f"📥 Exportar cierre de año — {nombre_sub}",
            data=exportar_excel(df_cierre_disp, nombre_sub[:31]),
            file_name=f"cierre_anio_{prefix}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key=f"exp_cierre_{prefix}",
        )

    st.markdown("---")

    # ── Tabla histórica con filtros + ficha de indicador ──────────────────────
    st.markdown("### 🔎 Detalle de indicadores (histórico completo)")
    st.caption(
        "Todos los registros históricos. "
        "Haz clic en una fila para abrir la **ficha completa** del indicador."
    )

    txt_id, txt_nom, sel_anios, sel_periodos, sel_cats, rng_cum = _filtros_tabla(df_sub, prefix)
    df_fil = _aplicar_filtros(df_sub, txt_id, txt_nom, sel_anios, sel_periodos, sel_cats, rng_cum)

    st.caption(f"Mostrando **{len(df_fil)}** registros de **{len(df_sub)}** (histórico)")

    cols_vis = _cols_tabla_vis(df_fil)
    df_show  = _tabla_display(df_fil[cols_vis])

    # Mapa inverso para recuperar Id original desde fila seleccionada
    col_cfg = {}
    if "Indicador" in df_show.columns:
        col_cfg["Indicador"] = st.column_config.TextColumn("Indicador", width="large")
    if "Cumplimiento%" in df_show.columns:
        col_cfg["Cumplimiento%"] = st.column_config.TextColumn("Cumpl.%", width="small")
    if "Ejecución" in df_show.columns:
        col_cfg["Ejecución"] = st.column_config.NumberColumn("Ejecución", format="%.2f")
    if "Meta" in df_show.columns:
        col_cfg["Meta"] = st.column_config.NumberColumn("Meta", format="%.2f")

    event = st.dataframe(
        df_show,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key=f"tabla_{prefix}",
        column_config=col_cfg,
    )

    # ── Ficha de indicador (dialog) ────────────────────────────────────────────
    if event and event.selection and event.selection.get("rows"):
        idx_sel  = event.selection["rows"][0]
        id_sel   = str(df_fil.iloc[idx_sel]["Id"])
        nom_sel  = str(df_fil.iloc[idx_sel].get("Indicador", ""))

        # Historial completo del indicador desde el dataset global
        df_ind_hist = df_global[df_global["Id"] == id_sel].copy() if not df_global.empty else pd.DataFrame()
        if df_ind_hist.empty:
            df_ind_hist = df_sub[df_sub["Id"] == id_sel].copy()

        @st.dialog(f"📊 {id_sel} — {nom_sel[:60]}", width="large")
        def _ficha_indicador():
            panel_detalle_indicador(df_ind_hist, id_sel, df_global)

        _ficha_indicador()

    # Exportar tabla filtrada
    st.download_button(
        f"📥 Exportar histórico — {nombre_sub}",
        data=exportar_excel(df_show, nombre_sub[:31]),
        file_name=f"historico_{prefix}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key=f"exp_hist_{prefix}",
    )


# ══════════════════════════════════════════════════════════════════════════════
# CARGA Y FILTRADO DEL PROCESO
# ══════════════════════════════════════════════════════════════════════════════

df_raw = cargar_dataset()

if df_raw.empty:
    st.error("No se encontró el dataset principal. Ejecuta primero `actualizar_consolidado.py`.")
    st.stop()

# Los tres procesos del bloque Direccionamiento Estratégico están como Proceso directo
if "Proceso" in df_raw.columns:
    df_dir = df_raw[df_raw["Proceso"].isin(_PROCESOS_DIR)].copy()
else:
    df_dir = pd.DataFrame()

if df_dir.empty:
    st.error("No se encontraron indicadores para los procesos del bloque Direccionamiento Estratégico.")
    if "Proceso" in df_raw.columns:
        procs = sorted(df_raw["Proceso"].dropna().unique())
        st.info("Procesos disponibles: " + " · ".join(procs))
    st.stop()

# Aplicar exclusiones en Planeación Estratégica (filtro por Proceso, no Subproceso)
mask_excl = (df_dir["Proceso"] == "Planeación Estratégica") & df_dir["Id"].isin(_IDS_EXCLUIR_PLAN)
df_dir = df_dir[~mask_excl].copy()

# DataFrames por proceso
def _df_proceso(nombre_proceso: str) -> pd.DataFrame:
    return df_dir[df_dir["Proceso"] == nombre_proceso].copy()

df_plan   = _df_proceso("Planeación Estratégica")
df_desemp = _df_proceso("Desempeño Institucional")
df_gest   = _df_proceso("Gestión de Proyectos")

# ══════════════════════════════════════════════════════════════════════════════
# UI — CABECERA
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("# 🏛️ Proceso de Direccionamiento Estratégico")
st.caption(
    "Informe por subproceso: **Planeación Estratégica** · "
    "**Desempeño Institucional** · **Gestión de Proyectos**"
)
st.markdown("---")

# Resumen ejecutivo del proceso completo
anios_dir = sorted([int(a) for a in df_dir["Anio"].dropna().unique()]) if "Anio" in df_dir.columns else []
df_ult_dir = _ultimo_por_indicador(df_dir)
total_dir, cats_dir = _kpis_subproceso(df_ult_dir)

col_h1, col_h2, col_h3, col_h4 = st.columns(4)
with col_h1:
    st.metric("Total indicadores proceso", total_dir)
with col_h2:
    rango = f"{min(anios_dir)}–{max(anios_dir)}" if len(anios_dir) > 1 else str(anios_dir[0]) if anios_dir else "—"
    st.metric("Años disponibles", rango)
with col_h3:
    n_peligro = cats_dir["Peligro"]["n"]
    st.metric("🔴 En Peligro", n_peligro, delta=f"{cats_dir['Peligro']['pct']}%", delta_color="inverse")
with col_h4:
    n_ok = cats_dir["Cumplimiento"]["n"] + cats_dir["Sobrecumplimiento"]["n"]
    pct_ok = round((n_ok / total_dir * 100), 1) if total_dir else 0
    st.metric("🟢 Cumpliendo+", n_ok, delta=f"{pct_ok}%")

# Semáforo general del proceso
st.markdown("#### Distribución general del proceso (estado actual)")
fig_resumen = go.Figure()
for cat in [c for c in ORDEN_CATEGORIAS if c != "Sin dato"]:
    fig_resumen.add_trace(go.Bar(
        x=[cats_dir[cat]["n"]],
        y=["Proceso"],
        orientation="h",
        name=f"{_ICONO_CAT.get(cat, '')} {cat}",
        marker_color=COLOR_CATEGORIA[cat],
        text=[f"{cats_dir[cat]['n']} ({cats_dir[cat]['pct']}%)"],
        textposition="inside",
        insidetextanchor="middle",
        textfont=dict(color="white", size=11),
    ))

fig_resumen.update_layout(
    barmode="stack",
    height=120,
    showlegend=True,
    legend=dict(orientation="h", y=-0.8),
    plot_bgcolor="white",
    paper_bgcolor="white",
    margin=dict(t=10, b=60, l=10, r=10),
    xaxis=dict(showticklabels=False, showgrid=False),
    yaxis=dict(showticklabels=False),
)
st.plotly_chart(fig_resumen, use_container_width=True)
st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# TABS POR SUBPROCESO
# ══════════════════════════════════════════════════════════════════════════════

tab_plan, tab_desemp, tab_gest = st.tabs([
    "📋 Planeación Estratégica",
    "📊 Desempeño Institucional",
    "🗂️ Gestión de Proyectos",
])

with tab_plan:
    _render_tab_subproceso(df_plan, "Planeación Estratégica", "plan", df_raw)

with tab_desemp:
    _render_tab_subproceso(df_desemp, "Desempeño Institucional", "desemp", df_raw)

with tab_gest:
    _render_tab_subproceso(df_gest, "Gestión de Proyectos", "gest", df_raw)
