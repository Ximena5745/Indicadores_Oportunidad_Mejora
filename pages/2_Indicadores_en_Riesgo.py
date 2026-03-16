"""
pages/2_Indicadores_en_Riesgo.py — Indicadores en Riesgo con semáforo interactivo.

Mejoras:
  · Indicadores que deterioraron vs período anterior
  · Persistencia en riesgo (períodos consecutivos)
  · Estado OM asociada (cruce con BD)
  · Mapa de calor interactivo
  · Comparación de dos períodos
  · Histórico preconectado al Top 10
"""
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from services.data_loader import cargar_dataset, construir_opciones_indicadores
from core.calculos import obtener_ultimo_registro, calcular_meses_en_peligro
from components.charts import (
    grafico_historico_indicador,
    tabla_historica_indicador,
    exportar_excel,
    panel_detalle_indicador,
    COLOR_CAT,
)
from core.niveles import NIVEL_COLOR, NIVEL_BG, NIVEL_ORDEN
from core.db_manager import registros_om_como_dict

# ── Ruta kawak ────────────────────────────────────────────────────────────────
_DATA_RAW   = Path(__file__).parent.parent / "data" / "raw"
_RUTA_KAWAK = _DATA_RAW / "indicadores_kawak.xlsx"


@st.cache_data(ttl=600, show_spinner=False)
def _kawak_ids() -> set:
    if not _RUTA_KAWAK.exists():
        return set()
    df = pd.read_excel(str(_RUTA_KAWAK), engine="openpyxl",
                       keep_default_na=False, na_values=[""])
    df.columns = [str(c).strip() for c in df.columns]
    col_id = next((c for c in df.columns if c.upper() == "ID"), None)
    if not col_id:
        return set()
    def _clean(x):
        try:
            f = float(x)
            return str(int(f)) if f == int(f) else str(f)
        except (TypeError, ValueError):
            return str(x).strip()
    return set(df[col_id].apply(_clean).dropna().unique())


# ── Carga ─────────────────────────────────────────────────────────────────────
df_raw_all = cargar_dataset()
if df_raw_all.empty:
    st.error("No se pudo cargar Resultados Consolidados.xlsx.")
    st.stop()

kawak_set = _kawak_ids()
if kawak_set and "Id" in df_raw_all.columns:
    df_raw = df_raw_all[df_raw_all["Id"].isin(kawak_set)].copy()
else:
    df_raw = df_raw_all.copy()

# ── OM asociada desde BD ──────────────────────────────────────────────────────
om_dict = registros_om_como_dict()   # {id_indicador: {"tiene_om": bool, "numero_om": str, ...}}

# ── Session state ──────────────────────────────────────────────────────────────
for _k, _v in [
    ("categoria_activa",       "Peligro"),
    ("indicador_detalle_p2",   None),
    ("p2_sel_proceso",         None),
    ("p2_sel_linea",           None),
    ("p2_sel_heatmap_proc",    None),
    ("p2_sel_heatmap_per",     None),
    ("p2_hist_presel_id",      None),
]:
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ── Sidebar — Filtros ──────────────────────────────────────────────────────────
st.sidebar.markdown("## Filtros")

anios_disp  = sorted(df_raw["Anio"].dropna().unique().tolist()) if "Anio" in df_raw.columns else []
default_año = [2025] if 2025 in anios_disp else (anios_disp[-1:] if anios_disp else [])
anios_sel   = st.sidebar.multiselect("Año", options=anios_disp, default=default_año)

meses_disp = sorted(df_raw["Mes"].dropna().unique().tolist()) if "Mes" in df_raw.columns else []
meses_sel  = st.sidebar.multiselect("Mes", options=meses_disp, default=[])

df = df_raw.copy()
if anios_sel:
    df = df[df["Anio"].isin(anios_sel)]
if meses_sel:
    df = df[df["Mes"].isin(meses_sel)]

df_ultimo    = obtener_ultimo_registro(df)
df_con_datos = df_ultimo[df_ultimo["Cumplimiento_norm"].notna()]
total        = len(df_con_datos)

# ── Título ─────────────────────────────────────────────────────────────────────
st.markdown("# ⚠️ Indicadores en Riesgo")
st.markdown("---")

# ── Semáforo ───────────────────────────────────────────────────────────────────
st.markdown("### Semáforo de Desempeño")
st.caption("Haz clic en una categoría para filtrar todas las visualizaciones.")

semaforo_config = [
    ("Sobrecumplimiento", "🔵", NIVEL_COLOR["Sobrecumplimiento"]),
    ("Cumplimiento",      "🔵", NIVEL_COLOR["Cumplimiento"]),
    ("Alerta",            "🟡", NIVEL_COLOR["Alerta"]),
    ("Peligro",           "🔴", NIVEL_COLOR["Peligro"]),
]

col_sems = st.columns(4)
for i, (cat, icon, color) in enumerate(semaforo_config):
    n_cat  = int((df_con_datos["Categoria"] == cat).sum())
    pct    = round(n_cat / total * 100, 1) if total > 0 else 0
    activa = st.session_state.categoria_activa == cat
    borde  = f"3px solid {color}" if activa else f"1px solid {color}"
    bg     = f"{color}22" if activa else "white"
    with col_sems[i]:
        st.markdown(
            f"""<div style="border:{borde};border-radius:10px;padding:14px;
                text-align:center;background:{bg};cursor:pointer;">
                <span style="font-size:2rem">{icon}</span><br>
                <strong style="font-size:1.4rem;color:{color}">{n_cat}</strong><br>
                <span style="font-size:0.85rem;color:#555">{cat}</span><br>
                <span style="font-size:0.8rem;color:#888">{pct}% del total</span>
            </div>""",
            unsafe_allow_html=True,
        )
        if st.button(f"Ver {cat}", key=f"sem_{cat}", use_container_width=True):
            st.session_state.categoria_activa  = cat
            st.session_state["p2_sel_proceso"] = None
            st.session_state["p2_sel_linea"]   = None
            st.session_state["p2_sel_heatmap_proc"] = None
            st.session_state["p2_sel_heatmap_per"]  = None
            st.rerun()

st.markdown("---")

# ── Indicadores que deterioraron ──────────────────────────────────────────────
def _indicadores_deteriorados(df_full: pd.DataFrame) -> pd.DataFrame:
    """
    Compara los 2 últimos registros por indicador.
    Retorna filas donde la categoría empeoró entre el penúltimo y el último registro.
    """
    _ORDEN = {"Peligro": 0, "Alerta": 1, "Cumplimiento": 2, "Sobrecumplimiento": 3, "Sin dato": -1}
    if "Id" not in df_full.columns or "Fecha" not in df_full.columns:
        return pd.DataFrame()
    df_s = df_full[df_full["Cumplimiento_norm"].notna()].sort_values("Fecha")
    rows = []
    for id_ind, grupo in df_s.groupby("Id"):
        if len(grupo) < 2:
            continue
        prev = grupo.iloc[-2]
        curr = grupo.iloc[-1]
        cat_prev = str(prev.get("Categoria", "Sin dato"))
        cat_curr = str(curr.get("Categoria", "Sin dato"))
        if _ORDEN.get(cat_curr, -1) < _ORDEN.get(cat_prev, -1):
            delta = round(
                (curr["Cumplimiento_norm"] - prev["Cumplimiento_norm"]) * 100, 1
            ) if pd.notna(curr["Cumplimiento_norm"]) and pd.notna(prev["Cumplimiento_norm"]) else None
            rows.append({
                "Id":               id_ind,
                "Indicador":        str(curr.get("Indicador", "")),
                "Proceso":          str(curr.get("Proceso", "")),
                "Categoría anterior": cat_prev,
                "Categoría actual": cat_curr,
                "Δ Cumplimiento%":  f"{delta:+.1f}%" if delta is not None else "—",
            })
    return pd.DataFrame(rows)


df_det = _indicadores_deteriorados(df_raw)
if not df_det.empty:
    with st.expander(f"⬇️ Indicadores que deterioraron de categoría ({len(df_det)})", expanded=False):
        def _estilo_det(row):
            bg = NIVEL_BG.get(str(row.get("Categoría actual", "")), "")
            return [f"background-color:{bg}" if c == "Categoría actual" else "" for c in row.index]
        st.dataframe(
            df_det.style.apply(_estilo_det, axis=1),
            use_container_width=True, hide_index=True,
            column_config={
                "Indicador": st.column_config.TextColumn("Indicador", width="large"),
            },
        )

# ── Filtrar por categoría activa ───────────────────────────────────────────────
cat_act    = st.session_state.categoria_activa
df_cat     = df_con_datos[df_con_datos["Categoria"] == cat_act].copy()
df_cat["Cumplimiento%"] = (df_cat["Cumplimiento_norm"] * 100).round(1)
color_act  = NIVEL_COLOR.get(cat_act, "#9E9E9E")

# ── Persistencia en riesgo ─────────────────────────────────────────────────────
def _periodos_en_riesgo(id_ind: str, df_full: pd.DataFrame, cat: str) -> int:
    df_ind = df_full[df_full["Id"] == id_ind].sort_values("Fecha", ascending=False)
    if df_ind.empty:
        return 0
    return calcular_meses_en_peligro(df_ind.assign(Categoria=df_ind["Categoria"]))

if not df_cat.empty:
    df_cat["Períodos en riesgo"] = df_cat["Id"].apply(
        lambda i: _periodos_en_riesgo(i, df_raw, cat_act)
    )

# ── Estado OM en df_cat ────────────────────────────────────────────────────────
if not df_cat.empty:
    df_cat["Estado OM"] = df_cat["Id"].apply(
        lambda i: "✅ Con OM" if om_dict.get(i, {}).get("tiene_om") else "❌ Sin OM"
    )
    df_cat["N° OM"] = df_cat["Id"].apply(
        lambda i: om_dict.get(i, {}).get("numero_om", "")
    )

# ── Filtros gráfico activo ─────────────────────────────────────────────────────
sel_proceso = st.session_state.get("p2_sel_proceso")
sel_linea   = st.session_state.get("p2_sel_linea")
sel_hm_proc = st.session_state.get("p2_sel_heatmap_proc")
sel_hm_per  = st.session_state.get("p2_sel_heatmap_per")

filtros_activos = [v for v in (sel_proceso, sel_linea,
                                f"Mapa:{sel_hm_proc}/{sel_hm_per}" if sel_hm_proc else None)
                   if v]
if filtros_activos:
    fc1, fc2 = st.columns([6, 1])
    with fc1:
        st.info("📊 Filtro gráfico: " + " · ".join(f"**{v}**" for v in filtros_activos))
    with fc2:
        if st.button("✖ Limpiar", key="p2_clear_graf"):
            st.session_state["p2_sel_proceso"]    = None
            st.session_state["p2_sel_linea"]      = None
            st.session_state["p2_sel_heatmap_proc"] = None
            st.session_state["p2_sel_heatmap_per"]  = None
            st.rerun()

# ── Gráficos (4) ──────────────────────────────────────────────────────────────
st.markdown(f"### Visualizaciones — {cat_act}")

col_g1, col_g2 = st.columns(2)

# Gráfico 1 — Top 10 menor/mayor cumplimiento
with col_g1:
    st.markdown("**Top 10 — Cumplimiento**")
    st.caption("💡 Clic en una barra para ver el detalle del indicador.")
    if cat_act in ("Peligro", "Alerta"):
        df_top     = df_cat.nsmallest(10, "Cumplimiento_norm")
        titulo_top = "10 indicadores con menor cumplimiento"
    else:
        df_top     = df_cat.nlargest(10, "Cumplimiento_norm")
        titulo_top = "10 indicadores con mayor cumplimiento"

    if not df_top.empty:
        etiquetas = (df_top["Id"] + " — " + df_top["Indicador"].str[:35]).tolist()
        per_riesgo = df_top.get("Períodos en riesgo", pd.Series([0]*len(df_top))).fillna(0).astype(int).tolist()
        fig_top = go.Figure(go.Bar(
            x=df_top["Cumplimiento%"].tolist(),
            y=etiquetas,
            orientation="h",
            marker_color=color_act,
            text=df_top["Cumplimiento%"].round(1).astype(str) + "%",
            textposition="outside",
            customdata=list(zip(df_top["Id"].tolist(), per_riesgo)),
            hovertemplate=(
                "<b>%{y}</b><br>"
                "Cumplimiento: %{x:.1f}%<br>"
                "Períodos consecutivos en riesgo: %{customdata[1]}<extra></extra>"
            ),
        ))
        fig_top.update_layout(
            height=400,
            xaxis=dict(title="Cumplimiento (%)", ticksuffix="%"),
            yaxis=dict(title="", autorange="reversed"),
            plot_bgcolor="white", paper_bgcolor="white",
            margin=dict(l=10, r=60, t=30, b=30),
            title=titulo_top,
        )
        event_top = st.plotly_chart(fig_top, use_container_width=True, on_select="rerun",
                                    selection_mode="points", key="fig_top10")
        if event_top and event_top.selection and event_top.selection.get("points"):
            pt_idx = event_top.selection["points"][0].get("point_index")
            if pt_idx is not None:
                id_click = df_top["Id"].iloc[pt_idx]
                st.session_state.indicador_detalle_p2 = id_click
                # Pre-seleccionar en histórico manual
                st.session_state["p2_hist_presel_id"] = id_click
    else:
        st.info("Sin datos para esta categoría.")

# Gráfico 2 — Distribución por Proceso (dona)
with col_g2:
    st.markdown("**Distribución por Proceso**")
    st.caption("💡 Clic en un segmento para filtrar la tabla.")
    if not df_cat.empty and "Proceso" in df_cat.columns:
        proc_counts = df_cat.groupby("Proceso").size().reset_index(name="count")
        proc_colors = [
            "#1A3A5C","#1565C0","#0277BD","#0288D1","#0097A7",
            "#00897B","#43A047","#7CB342","#C0CA33","#FDD835",
        ]
        fig_dona = go.Figure(go.Pie(
            labels=proc_counts["Proceso"].tolist(),
            values=proc_counts["count"].tolist(),
            hole=0.4,
            marker=dict(colors=proc_colors[:len(proc_counts)]),
            hovertemplate="<b>%{label}</b><br>%{value} indicadores<br>%{percent}<extra></extra>",
        ))
        fig_dona.update_layout(
            height=400,
            legend=dict(orientation="v", x=1.02),
            plot_bgcolor="white", paper_bgcolor="white",
            margin=dict(t=20, b=20),
        )
        ev_dona = st.plotly_chart(fig_dona, use_container_width=True,
                                  on_select="rerun", key="fig_dona_proc")
        if ev_dona and ev_dona.selection and ev_dona.selection.get("points"):
            clicked_proc = ev_dona.selection["points"][0].get("label")
            if clicked_proc and clicked_proc != st.session_state.get("p2_sel_proceso"):
                st.session_state["p2_sel_proceso"] = clicked_proc
                st.session_state["p2_sel_linea"]   = None
                st.rerun()
    else:
        st.info("Sin datos.")

col_g3, col_g4 = st.columns(2)

# Gráfico 3 — Comparativo por Línea Estratégica
with col_g3:
    st.markdown("**Comparativo por Línea Estratégica**")
    st.caption("💡 Clic en una barra para filtrar la tabla.")
    col_linea = "Linea" if "Linea" in df_cat.columns else None
    if col_linea and not df_cat.empty:
        linea_avg = (
            df_cat.groupby(col_linea)["Cumplimiento_norm"]
            .mean().reset_index()
            .assign(Cumplimiento_pct=lambda x: x["Cumplimiento_norm"] * 100)
            .sort_values("Cumplimiento_pct")
        )
        fig_linea = go.Figure(go.Bar(
            x=linea_avg[col_linea].tolist(),
            y=linea_avg["Cumplimiento_pct"].round(1).tolist(),
            marker_color=color_act,
            text=linea_avg["Cumplimiento_pct"].round(1).astype(str) + "%",
            textposition="outside",
            hovertemplate="<b>%{x}</b><br>Promedio: %{y:.1f}%<extra></extra>",
        ))
        fig_linea.add_hline(y=100, line_dash="dash", line_color="#1FB2DE", line_width=1.5)
        fig_linea.add_hline(y=80,  line_dash="dot",  line_color="#EC0677", line_width=1)
        fig_linea.update_layout(
            height=380,
            yaxis=dict(title="Cumplimiento promedio (%)", ticksuffix="%"),
            xaxis=dict(title="Línea Estratégica"),
            plot_bgcolor="white", paper_bgcolor="white",
            margin=dict(t=20, b=60),
        )
        ev_linea = st.plotly_chart(fig_linea, use_container_width=True,
                                   on_select="rerun", key="fig_linea_est")
        if ev_linea and ev_linea.selection and ev_linea.selection.get("points"):
            clicked_linea = ev_linea.selection["points"][0].get("x")
            if clicked_linea and clicked_linea != st.session_state.get("p2_sel_linea"):
                st.session_state["p2_sel_linea"]   = clicked_linea
                st.session_state["p2_sel_proceso"] = None
                st.rerun()
    else:
        st.info("No hay columna Linea en los datos.")

# Gráfico 4 — Mapa de calor Proceso × Periodo (interactivo)
with col_g4:
    st.markdown("**Mapa de Calor — Proceso × Periodo**")
    st.caption("💡 Clic en una celda para filtrar la tabla.")
    if not df_cat.empty and "Proceso" in df_cat.columns and "Periodo" in df_cat.columns:
        df_heat_src = df[df["Categoria"] == cat_act].copy() if not df.empty else df_cat
        pivot = (
            df_heat_src.groupby(["Proceso", "Periodo"])["Cumplimiento_norm"]
            .mean().unstack(fill_value=None) * 100
        )
        fig_heat = go.Figure(go.Heatmap(
            z=pivot.values.tolist(),
            x=pivot.columns.tolist(),
            y=pivot.index.tolist(),
            colorscale="RdYlGn",
            zmid=90, zmin=0, zmax=130,
            hovertemplate=(
                "<b>Proceso:</b> %{y}<br>"
                "<b>Periodo:</b> %{x}<br>"
                "<b>Cum. prom:</b> %{z:.1f}%<extra></extra>"
            ),
            colorbar=dict(ticksuffix="%"),
        ))
        fig_heat.update_layout(
            height=380,
            xaxis=dict(title="Periodo"),
            yaxis=dict(title="Proceso"),
            margin=dict(t=20, b=40),
        )
        ev_heat = st.plotly_chart(fig_heat, use_container_width=True,
                                  on_select="rerun", key="fig_heatmap")
        if ev_heat and ev_heat.selection and ev_heat.selection.get("points"):
            pt_h = ev_heat.selection["points"][0]
            st.session_state["p2_sel_heatmap_proc"] = pt_h.get("y")
            st.session_state["p2_sel_heatmap_per"]  = pt_h.get("x")
            st.session_state["p2_sel_proceso"]      = None
            st.session_state["p2_sel_linea"]        = None
            st.rerun()
    else:
        st.info("Sin datos suficientes para el mapa de calor.")

st.markdown("---")

# ── Tabla detallada ─────────────────────────────────────────────────────────────
titulo_tabla = f"### Tabla Detallada — {cat_act}"
if sel_proceso:
    titulo_tabla += f" · Proceso: *{sel_proceso}*"
elif sel_linea:
    titulo_tabla += f" · Línea: *{sel_linea}*"
elif sel_hm_proc:
    titulo_tabla += f" · Proceso: *{sel_hm_proc}* · Periodo: *{sel_hm_per}*"
st.markdown(titulo_tabla)

df_tabla_det = df_cat.copy()
if sel_proceso and "Proceso" in df_tabla_det.columns:
    df_tabla_det = df_tabla_det[df_tabla_det["Proceso"] == sel_proceso]
elif sel_linea and "Linea" in df_tabla_det.columns:
    df_tabla_det = df_tabla_det[df_tabla_det["Linea"] == sel_linea]
elif sel_hm_proc and "Proceso" in df_tabla_det.columns:
    df_tabla_det = df_tabla_det[df_tabla_det["Proceso"] == sel_hm_proc]
    if sel_hm_per and "Periodo" in df_tabla_det.columns:
        df_tabla_det = df_tabla_det[df_tabla_det["Periodo"] == sel_hm_per]

df_tabla_det["Cumplimiento%"] = df_tabla_det["Cumplimiento_norm"].apply(
    lambda x: f"{round(x*100,1)}%" if pd.notna(x) else "—"
)

def _estilo_cat(row):
    bg = NIVEL_BG.get(str(row.get("Categoria", "")), "")
    return [f"background-color: {bg}" if c == "Categoria" else "" for c in row.index]

cols_show = ["Id", "Indicador", "Proceso", "Subproceso", "Periodicidad",
             "Periodo", "Cumplimiento%", "Categoria", "Períodos en riesgo", "Estado OM", "N° OM"]
cols_disp = [c for c in cols_show if c in df_tabla_det.columns]

st.caption(f"Mostrando **{len(df_tabla_det)}** indicadores")

event_tabla = st.dataframe(
    df_tabla_det[cols_disp].style.apply(_estilo_cat, axis=1),
    use_container_width=True, hide_index=True,
    on_select="rerun", selection_mode="single-row",
    key="tabla_riesgo",
    column_config={
        "Indicador":          st.column_config.TextColumn("Indicador",       width="large"),
        "Períodos en riesgo": st.column_config.NumberColumn("Períodos en riesgo", format="%d"),
        "Estado OM":          st.column_config.TextColumn("Estado OM",       width="small"),
    },
)

col_exp, _ = st.columns([1, 4])
with col_exp:
    st.download_button(
        label="📥 Exportar Excel",
        data=exportar_excel(df_tabla_det[cols_disp], "Indicadores en Riesgo"),
        file_name=f"indicadores_{cat_act.lower()}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

if event_tabla and event_tabla.selection and event_tabla.selection.get("rows"):
    idx = event_tabla.selection["rows"][0]
    if "Id" in df_tabla_det.columns:
        id_click_tabla = df_tabla_det["Id"].iloc[idx]
        st.session_state.indicador_detalle_p2 = id_click_tabla
        st.session_state["p2_hist_presel_id"] = id_click_tabla

st.markdown("---")

# ── Panel de detalle (dialog) ──────────────────────────────────────────────────
if st.session_state.indicador_detalle_p2:
    id_det     = st.session_state.indicador_detalle_p2
    df_ind_det = df_raw[df_raw["Id"] == id_det].copy()

    @st.dialog(f"Detalle del indicador: {id_det}", width="large")
    def mostrar_detalle_p2():
        if st.button("✖ Cerrar"):
            st.session_state.indicador_detalle_p2 = None
            st.rerun()
        # Mostrar OM asociada si existe
        om_info = om_dict.get(id_det)
        if om_info and om_info.get("tiene_om"):
            st.markdown(
                f"""<div style="background:#E8F5E9;border-radius:6px;padding:8px 14px;
                    border-left:3px solid #43A047;margin-bottom:10px;font-size:0.9rem;">
                    ✅ <b>OM asociada:</b> N° {om_info['numero_om']}
                    &nbsp;·&nbsp; Período: {om_info['periodo']}
                </div>""",
                unsafe_allow_html=True,
            )
        elif om_info is not None:
            st.warning("❌ Sin OM registrada para este indicador.")
        panel_detalle_indicador(df_ind_det, id_det, df_raw)

    mostrar_detalle_p2()

# ── Histórico por Indicador (búsqueda manual) ─────────────────────────────────
st.markdown("### Histórico por Indicador (búsqueda manual)")
st.caption("💡 También se preselecciona al hacer clic en el Top 10 o en la tabla.")

opciones_historico = construir_opciones_indicadores(df_raw)
labels_hist_list   = ["— Selecciona —"] + list(opciones_historico.keys())

# Calcular índice del indicador preseleccionado
hist_presel_id = st.session_state.get("p2_hist_presel_id")
hist_idx = 0
if hist_presel_id:
    for i, lbl in enumerate(labels_hist_list):
        if opciones_historico.get(lbl) == hist_presel_id:
            hist_idx = i
            break

label_hist = st.selectbox(
    "Selecciona un indicador",
    options=labels_hist_list,
    index=hist_idx,
    key="hist_manual_p2",
)

if label_hist != "— Selecciona —":
    id_hist    = opciones_historico[label_hist]
    df_ind_hist = df_raw[df_raw["Id"] == id_hist].sort_values("Fecha")
    if not df_ind_hist.empty:
        fig_h = grafico_historico_indicador(df_ind_hist, titulo=label_hist)
        st.plotly_chart(fig_h, use_container_width=True)
        df_th = tabla_historica_indicador(df_ind_hist)
        st.dataframe(df_th, use_container_width=True, hide_index=True)
    else:
        st.warning("Sin datos.")

# ── Comparación de dos períodos ────────────────────────────────────────────────
st.markdown("---")
with st.expander("📅 Comparar dos períodos", expanded=False):
    periodos_disp = sorted(df_raw["Periodo"].dropna().unique().tolist()) \
                    if "Periodo" in df_raw.columns else []
    if len(periodos_disp) < 2:
        st.info("Se necesitan al menos 2 períodos disponibles para comparar.")
    else:
        cp1, cp2 = st.columns(2)
        per_a = cp1.selectbox("Período A", options=periodos_disp,
                              index=max(0, len(periodos_disp)-2), key="cmp_per_a")
        per_b = cp2.selectbox("Período B", options=periodos_disp,
                              index=len(periodos_disp)-1, key="cmp_per_b")

        df_a = df_raw[df_raw["Periodo"] == per_a][["Id", "Indicador", "Proceso", "Categoria", "Cumplimiento_norm"]].copy()
        df_b = df_raw[df_raw["Periodo"] == per_b][["Id", "Categoria", "Cumplimiento_norm"]].copy()

        df_cmp = df_a.merge(df_b, on="Id", suffixes=(f"_{per_a}", f"_{per_b}"))
        if df_cmp.empty:
            st.info("Sin indicadores comunes entre los dos períodos.")
        else:
            # Conteo por categoría en cada período
            col_cat_a = f"Categoria_{per_a}"
            col_cat_b = f"Categoria_{per_b}"
            cats_a = df_cmp[col_cat_a].value_counts().rename("Período A")
            cats_b = df_cmp[col_cat_b].value_counts().rename("Período B")
            df_cnt = pd.concat([cats_a, cats_b], axis=1).fillna(0).astype(int)
            df_cnt = df_cnt.reindex([c for c in NIVEL_ORDEN if c in df_cnt.index])

            fig_cmp = go.Figure()
            colors_bar = ["#90CAF9", "#1A3A5C"]
            for j, (col_name, label_bar) in enumerate(
                [(col_cat_a, f"Período A: {per_a}"), (col_cat_b, f"Período B: {per_b}")]
            ):
                cnts_j = df_cmp[col_name].value_counts()
                fig_cmp.add_trace(go.Bar(
                    name=label_bar,
                    x=[c for c in NIVEL_ORDEN if c in cnts_j.index],
                    y=[int(cnts_j.get(c, 0)) for c in NIVEL_ORDEN if c in cnts_j.index],
                    marker_color=colors_bar[j],
                ))
            fig_cmp.update_layout(
                barmode="group", height=320,
                xaxis_title="Categoría", yaxis_title="N° Indicadores",
                plot_bgcolor="white", paper_bgcolor="white",
                margin=dict(t=20, b=30),
            )
            st.plotly_chart(fig_cmp, use_container_width=True)

            # Tabla de indicadores que cambiaron
            df_cmp["cambio"] = df_cmp[col_cat_a] != df_cmp[col_cat_b]
            df_cambios = df_cmp[df_cmp["cambio"]][[
                "Id", "Indicador", "Proceso", col_cat_a, col_cat_b,
            ]].rename(columns={col_cat_a: f"Cat {per_a}", col_cat_b: f"Cat {per_b}"})
            if not df_cambios.empty:
                st.caption(f"**{len(df_cambios)}** indicadores cambiaron de categoría entre los dos períodos.")
                st.dataframe(df_cambios, use_container_width=True, hide_index=True,
                             column_config={"Indicador": st.column_config.TextColumn("Indicador", width="large")})
