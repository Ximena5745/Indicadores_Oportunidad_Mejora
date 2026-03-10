"""
pages/5_Reporte_Seguimiento.py — Indicadores con Reporte de Seguimiento.

Fuente: data/output/Seguimiento_Reporte.xlsx (generado por generar_reporte.py).
Solo muestra indicadores con Revisar == 1 (indicador único/primero).

Mapeo (Subproceso-Proceso-Area.xlsx):
  "Proceso" en LMI/Seguimiento == "Subproceso" en el mapeo
  Se agregan: Proceso (padre), Area, Vicerrectoria
"""
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.charts import exportar_excel

# ── Rutas ─────────────────────────────────────────────────────────────────────
_DATA_RAW  = Path(__file__).parent.parent / "data" / "raw"
_RUTA_XLSX = Path(__file__).parent.parent / "data" / "output" / "Seguimiento_Reporte.xlsx"
_RUTA_MAPA = _DATA_RAW / "Subproceso-Proceso-Area.xlsx"
_CORTE     = datetime(2024, 1, 1)

# ── Paleta corporativa ────────────────────────────────────────────────────────
CORP = {
    "reportado":  "#A6CE38",
    "pendiente":  "#EC0677",
    "primario":   "#0F385A",
    "secundario": "#1FB2DE",
    "acento":     "#42F2F2",
    "alerta":     "#FBAF17",
}
COLOR_ESTADO    = {"Reportado": "#EDF7D6", "Pendiente de reporte": "#FDE8F3"}
COLOR_REPORTADO = {"Si": "#EDF7D6", "Sí": "#EDF7D6", "No": "#FDE8F3"}

# ── Columnas ──────────────────────────────────────────────────────────────────
COLS_DESC_CON = ["Id", "Indicador", "Estado del indicador", "Reportado",
                 "Vicerrectoria", "Proceso", "Subproceso",
                 "Tipo", "Sentido", "Periodicidad"]
COLS_DESC     = ["Id", "Indicador", "Vicerrectoria", "Proceso", "Subproceso",
                 "Tipo", "Sentido", "Periodicidad", "Estado del indicador", "Reportado"]

# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _id_limpio(x) -> str:
    if pd.isna(x):
        return ""
    try:
        f = float(x)
        return str(int(f)) if f == int(f) else str(f)
    except (ValueError, TypeError):
        return str(x)


def _cols_periodo_desde_2024(columnas) -> list:
    out = []
    for col in columnas:
        try:
            d = datetime.strptime(str(col), "%d/%m/%Y")
            if d >= _CORTE:
                out.append(col)
        except ValueError:
            pass
    return sorted(out, key=lambda c: datetime.strptime(c, "%d/%m/%Y"))


def _cols_pres(df, preferidas):
    return [c for c in preferidas if c in df.columns]


def _col_nombre(df):
    for c in ["Indicador", "Nombre", "Descripcion", "Descripción"]:
        if c in df.columns:
            return c
    return None


def _estilo_estado(row):
    estilos = []
    for col in row.index:
        if col == "Estado del indicador":
            bg = COLOR_ESTADO.get(str(row[col]), "")
        elif col == "Reportado":
            bg = COLOR_REPORTADO.get(str(row[col]), "")
        else:
            bg = ""
        estilos.append(f"background-color: {bg}" if bg else "")
    return estilos


def _aplicar_filtros_tabla(df: pd.DataFrame, txt_id: str, txt_nombre: str,
                           sel_proc: str, sel_sub: str, sel_estado: str) -> pd.DataFrame:
    mask = pd.Series(True, index=df.index)
    if txt_id.strip() and "Id" in df.columns:
        mask &= df["Id"].astype(str).str.contains(txt_id.strip(), case=False, na=False)
    if txt_nombre.strip():
        col_nom = next((c for c in ["Indicador", "Nombre"] if c in df.columns), None)
        if col_nom:
            mask &= df[col_nom].astype(str).str.contains(txt_nombre.strip(), case=False, na=False)
    if sel_proc and "Proceso" in df.columns:
        mask &= df["Proceso"] == sel_proc
    if sel_sub and "Subproceso" in df.columns:
        mask &= df["Subproceso"] == sel_sub
    if sel_estado and "Estado del indicador" in df.columns:
        mask &= df["Estado del indicador"] == sel_estado
    return df[mask].reset_index(drop=True)


def _filtros_cascada(df: pd.DataFrame, prefix: str):
    """Filtros: ID, Nombre, Proceso (dropdown), Subproceso (dinámico), Estado."""
    with st.expander("🔍 Filtros", expanded=True):
        r1c1, r1c2 = st.columns(2)
        with r1c1:
            txt_id = st.text_input("ID", key=f"{prefix}_id", placeholder="Buscar ID...")
        with r1c2:
            txt_nom = st.text_input("Nombre del indicador", key=f"{prefix}_nom",
                                    placeholder="Buscar nombre...")
        r2c1, r2c2, r2c3 = st.columns(3)
        with r2c1:
            opts_proc = [""] + sorted(df["Proceso"].dropna().unique().tolist()) \
                        if "Proceso" in df.columns else [""]
            sel_proc = st.selectbox("Proceso", opts_proc, key=f"{prefix}_proc",
                                    format_func=lambda x: "— Todos —" if x == "" else x)
        with r2c2:
            if sel_proc and "Proceso" in df.columns and "Subproceso" in df.columns:
                sub_opts = [""] + sorted(
                    df.loc[df["Proceso"] == sel_proc, "Subproceso"].dropna().unique().tolist()
                )
            else:
                sub_opts = [""] + (sorted(df["Subproceso"].dropna().unique().tolist())
                                   if "Subproceso" in df.columns else [])
            sel_sub = st.selectbox("Subproceso", sub_opts, key=f"{prefix}_sub",
                                   format_func=lambda x: "— Todos —" if x == "" else x)
        with r2c3:
            opts_est = [""] + sorted(df["Estado del indicador"].dropna().unique().tolist()) \
                       if "Estado del indicador" in df.columns else [""]
            sel_estado = st.selectbox("Estado del indicador", opts_est, key=f"{prefix}_est",
                                      format_func=lambda x: "— Todos —" if x == "" else x)
    return txt_id, txt_nom, sel_proc, sel_sub, sel_estado


def _bar_h(df_stats, col_cat, height=None):
    """Gráfica de barras horizontales apiladas (Reportado/Pendiente)."""
    col_rep = "Reportado"            if "Reportado"            in df_stats.columns else None
    col_pen = "Pendiente de reporte" if "Pendiente de reporte" in df_stats.columns else None

    # Orden explícito: mayor total arriba — evita desalineación barra/etiqueta
    cats = list(df_stats[col_cat].astype(str))

    fig = go.Figure()
    if col_rep:
        vals = df_stats[col_rep].tolist()
        fig.add_trace(go.Bar(
            y=cats, x=vals,
            orientation="h", name="Reportado", marker_color=CORP["reportado"],
            customdata=["Reportado"] * len(cats),
            text=[v if v > 0 else "" for v in vals],
            textposition="inside", insidetextanchor="middle",
            textfont=dict(size=11, color="white"),
        ))
    if col_pen:
        vals = df_stats[col_pen].tolist()
        fig.add_trace(go.Bar(
            y=cats, x=vals,
            orientation="h", name="Pendiente", marker_color=CORP["pendiente"],
            customdata=["Pendiente de reporte"] * len(cats),
            text=[v if v > 0 else "" for v in vals],
            textposition="inside", insidetextanchor="middle",
            textfont=dict(size=11, color="white"),
        ))

    # Altura: mínimo 40 px por categoría para que barra y etiqueta alineen
    h = height or max(320, len(df_stats) * 42 + 70)
    # Margen izquierdo dinámico según el largo del nombre más largo
    max_len = max((len(str(c)) for c in cats), default=10)
    margin_l = min(max(max_len * 6, 120), 340)

    fig.update_layout(
        barmode="stack", height=h,
        xaxis_title="Indicadores", yaxis_title="",
        yaxis=dict(
            categoryorder="array",
            categoryarray=cats,        # orden fijo = mismo que los datos
            autorange="reversed",
            tickfont=dict(size=10),
        ),
        uniformtext_minsize=9, uniformtext_mode="hide",
        plot_bgcolor="white", paper_bgcolor="white",
        legend=dict(orientation="h", y=-0.12),
        margin=dict(t=15, b=50, l=margin_l, r=30),
    )
    return fig


def _agg_estado(df, col_cat):
    """Agrupa df por col_cat y calcula Reportado/Pendiente/Total."""
    COL_E = "Estado del indicador"
    if COL_E not in df.columns or col_cat not in df.columns:
        return pd.DataFrame()
    df = df.copy()
    # Normalizar espacios para evitar duplicados de categoría
    df[col_cat] = df[col_cat].astype(str).str.strip()
    df = df[df[col_cat].notna() & (df[col_cat] != "nan")]
    stats = (
        df.groupby(col_cat)[COL_E]
        .value_counts().unstack(fill_value=0).reset_index()
    )
    stats["_t"] = stats.drop(columns=[col_cat]).sum(axis=1)
    stats = stats.sort_values("_t", ascending=False).drop(columns="_t")
    return stats


# ══════════════════════════════════════════════════════════════════════════════
# CARGA DE MAPEO
# ══════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=600, show_spinner=False)
def _cargar_mapa_procesos() -> pd.DataFrame:
    """Subproceso → Proceso, Area, Vicerrectoria."""
    if not _RUTA_MAPA.exists():
        return pd.DataFrame()
    df = pd.read_excel(str(_RUTA_MAPA), engine="openpyxl")
    df.columns = [str(c).strip() for c in df.columns]
    col_sub    = next((c for c in df.columns if c.lower() == "subproceso"), None)
    col_proc   = next((c for c in df.columns if c.lower() == "proceso"), None)
    col_area   = next((c for c in df.columns if "rea" in c.lower() and "vicerr" not in c.lower()), None)
    col_vicerr = next((c for c in df.columns if "icerrector" in c.lower()), None)
    if not col_sub or not col_proc:
        return pd.DataFrame()
    rename = {col_sub: "Subproceso", col_proc: "Proceso"}
    if col_area:
        rename[col_area] = "Area"
    if col_vicerr:
        rename[col_vicerr] = "Vicerrectoria"
    df = df.rename(columns=rename)
    cols_keep = [c for c in ["Subproceso", "Proceso", "Area", "Vicerrectoria"] if c in df.columns]
    return (df[cols_keep]
            .dropna(subset=["Subproceso"])
            .drop_duplicates(subset=["Subproceso"])
            .reset_index(drop=True))


# ══════════════════════════════════════════════════════════════════════════════
# CARGA DE DATOS
# ══════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=300, show_spinner="Cargando Seguimiento_Reporte.xlsx...")
def _cargar_datos() -> dict:
    if not _RUTA_XLSX.exists():
        return {}

    xl    = pd.ExcelFile(str(_RUTA_XLSX), engine="openpyxl")
    hojas = xl.sheet_names
    out   = {"consolidado": pd.DataFrame(), "periodicidades": []}

    mapa = _cargar_mapa_procesos()

    COLS_MANTENER = ["Id", "Indicador", "Vicerrectoria", "Area", "Proceso", "Subproceso",
                     "Tipo", "Sentido", "Periodicidad",
                     "Estado del indicador", "Reportado", "Revisar"]

    trozos = []
    for hoja in hojas:
        if hoja in ("Seguimiento", "Resumen"):
            continue

        df = xl.parse(hoja)
        df.columns = [str(c).strip() for c in df.columns]

        # Filtrar Revisar == 1 y deduplicar
        if "Revisar" in df.columns:
            revisar = pd.to_numeric(df["Revisar"], errors="coerce").fillna(0)
            df = df[revisar == 1].copy()
        if "Id" in df.columns:
            df["Id"] = df["Id"].apply(_id_limpio)
            df = df.drop_duplicates(subset="Id", keep="first").reset_index(drop=True)

        # Renombrar "Proceso" → "Subproceso" y agregar jerarquía
        if "Proceso" in df.columns:
            df = df.rename(columns={"Proceso": "Subproceso"})
        if not mapa.empty and "Subproceso" in df.columns:
            df = df.merge(mapa, on="Subproceso", how="left")

        cols_p = _cols_periodo_desde_2024(df.columns)
        out["periodicidades"].append({"nombre": hoja, "df": df, "cols_periodo": cols_p})

        cols_desc = [c for c in COLS_MANTENER if c in df.columns]
        trozos.append(df[cols_desc].copy())

    if trozos:
        df_con = pd.concat(trozos, ignore_index=True)
        if "Id" in df_con.columns:
            df_con = df_con.drop_duplicates(subset="Id", keep="first").reset_index(drop=True)
        out["consolidado"] = df_con

    return out


# ══════════════════════════════════════════════════════════════════════════════
# CARGA
# ══════════════════════════════════════════════════════════════════════════════
datos = _cargar_datos()

if not datos:
    st.error("No se encontró **Seguimiento_Reporte.xlsx** en `data/output/`. "
             "Ejecuta primero `generar_reporte.py`.")
    st.stop()

df_con = datos["consolidado"]
perios = datos["periodicidades"]

if df_con.empty and not perios:
    st.error("No se encontraron hojas de periodicidad con indicadores (Revisar = 1).")
    st.stop()

COL_ESTADO = "Estado del indicador"
COL_REP    = "Reportado"

# ══════════════════════════════════════════════════════════════════════════════
# TÍTULO
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("# 📊 Reporte de Seguimiento de Indicadores")
st.caption("Solo indicadores con **Revisar = 1** · Períodos desde **2024-01-01** · Corte: **Diciembre 2025**")
st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════════════════════
nombres_tabs = ["📋 Resumen", "📊 Consolidado"] + [f"📅 {p['nombre']}" for p in perios]
tabs = st.tabs(nombres_tabs)

# ─────────────────────────────────────────────────────────────────────────────
# TAB 0 — RESUMEN
# ─────────────────────────────────────────────────────────────────────────────
with tabs[0]:

    total        = len(df_con)
    n_reportados = int((df_con[COL_ESTADO] == "Reportado").sum())            if COL_ESTADO in df_con.columns else 0
    n_pendientes = int((df_con[COL_ESTADO] == "Pendiente de reporte").sum()) if COL_ESTADO in df_con.columns else 0
    n_rep_hoy    = int((df_con[COL_REP].isin(["Sí", "Si"])).sum())           if COL_REP    in df_con.columns else 0
    pct_rep      = round(n_rep_hoy / total * 100, 1) if total else 0

    # ── KPIs ──────────────────────────────────────────────────────────────────
    st.markdown("### Vista Resumen")
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1: st.metric("Total indicadores", total)
    with c2: st.metric("✅ Reportados (estado)", n_reportados,
                       delta=f"{round(n_reportados/total*100,1)}%" if total else None)
    with c3: st.metric("⏳ Pendientes (estado)", n_pendientes,
                       delta=f"{round(n_pendientes/total*100,1)}%" if total else None,
                       delta_color="inverse")
    with c4: st.metric("📤 Reportados período actual", n_rep_hoy)
    with c5: st.metric("% Reporte período actual", f"{pct_rep}%",
                       delta_color="normal" if pct_rep >= 80 else "inverse")

    st.markdown("---")

    # ── Pie + Por Periodicidad (calculado desde df_con deduplicado) ───────────
    gc1, gc2 = st.columns([1, 2])
    with gc1:
        st.markdown("#### Estado general")
        if n_reportados + n_pendientes > 0:
            fig_pie = go.Figure(go.Pie(
                labels=["Reportados", "Pendientes"],
                values=[n_reportados, n_pendientes],
                hole=0.52,
                marker=dict(colors=[CORP["reportado"], CORP["pendiente"]],
                            line=dict(color="white", width=2)),
                textinfo="label+percent", textfont=dict(size=13),
                hovertemplate="<b>%{label}</b><br>%{value} indicadores (%{percent})<extra></extra>",
            ))
            fig_pie.update_layout(
                height=280, showlegend=False,
                margin=dict(t=10, b=10, l=10, r=10),
                paper_bgcolor="white",
                annotations=[dict(text=f"<b>{total}</b><br>total",
                                  x=0.5, y=0.5, font_size=16, showarrow=False)],
            )
            st.plotly_chart(fig_pie, use_container_width=True)

    with gc2:
        st.markdown("#### Por Periodicidad")
        if "Periodicidad" in df_con.columns:
            # Calcular desde df_con (deduplicado, Revisar==1) — sin usar hoja Resumen
            agg_dict: dict = {"Total indicadores": ("Id", "count")}
            if COL_REP    in df_con.columns:
                agg_dict["Reportados"] = (COL_REP, lambda x: x.isin(["Sí","Si"]).sum())
            if COL_ESTADO in df_con.columns:
                agg_dict["Pendientes"] = (COL_ESTADO, lambda x: (x=="Pendiente de reporte").sum())

            per_agg = df_con.groupby("Periodicidad").agg(**agg_dict).reset_index()
            if "Reportados" in per_agg.columns:
                per_agg["% Reporte"] = (per_agg["Reportados"] / per_agg["Total indicadores"] * 100).round(1).astype(str) + "%"

            col_r = "Reportados" if "Reportados" in per_agg.columns else None
            col_p = "Pendientes" if "Pendientes" in per_agg.columns else None

            fig_per = go.Figure()
            if col_r:
                fig_per.add_trace(go.Bar(
                    x=per_agg["Periodicidad"], y=per_agg[col_r],
                    name="Reportados", marker_color=CORP["reportado"],
                    text=per_agg[col_r], textposition="outside",
                ))
            if col_p:
                fig_per.add_trace(go.Bar(
                    x=per_agg["Periodicidad"], y=per_agg[col_p],
                    name="Pendientes", marker_color=CORP["pendiente"],
                    text=per_agg[col_p], textposition="outside",
                ))
            fig_per.update_layout(
                barmode="group", height=280,
                xaxis_title="Periodicidad", yaxis_title="Indicadores",
                plot_bgcolor="white", paper_bgcolor="white",
                legend=dict(orientation="h", y=-0.35),
                margin=dict(t=15, b=80),
            )
            st.plotly_chart(fig_per, use_container_width=True)
            st.dataframe(per_agg, use_container_width=True, hide_index=True)

    st.markdown("---")

    # ── Por Vicerrectoría — interactivo ───────────────────────────────────────
    _COL_V = "Vicerrectoria"
    _COL_S = "Subproceso"

    if _COL_V in df_con.columns and COL_ESTADO in df_con.columns:
        st.markdown("#### Por Vicerrectoría")
        st.caption("💡 Haz clic en una barra para ver el detalle de subprocesos. "
                   "Haz clic en una fila de subproceso para ver sus indicadores.")

        vicerr_stats = _agg_estado(df_con, _COL_V)
        fig_v = _bar_h(vicerr_stats, _COL_V)
        ev_v  = st.plotly_chart(fig_v, on_select="rerun",
                                key="t0_chart_vicerr", use_container_width=True)

        # Capturar selección del gráfico
        sel_vicerr = None
        if ev_v.selection and ev_v.selection.get("points"):
            sel_vicerr = ev_v.selection["points"][0].get("y")

        # Guardar en session_state solo al cambiar
        if sel_vicerr and sel_vicerr != st.session_state.get("t0_sel_vicerr"):
            st.session_state["t0_sel_vicerr"] = sel_vicerr
            st.session_state["t0_sel_sub"]    = None   # resetear sub al cambiar vicerr

        current_v = st.session_state.get("t0_sel_vicerr") or sel_vicerr

        if current_v:
            hd1, hd2 = st.columns([6, 1])
            with hd1:
                st.markdown(f"**Subprocesos — {current_v}**")
            with hd2:
                if st.button("✖ Limpiar", key="t0_clear_v"):
                    st.session_state["t0_sel_vicerr"] = None
                    st.session_state["t0_sel_sub"]    = None
                    st.rerun()

            df_v_drill = df_con[df_con[_COL_V] == current_v]

            if _COL_S in df_v_drill.columns:
                sub_agg = df_v_drill.groupby(_COL_S).agg(
                    Total=("Id", "count"),
                    Reportados=(COL_ESTADO, lambda x: (x == "Reportado").sum()),
                    Pendientes=(COL_ESTADO, lambda x: (x == "Pendiente de reporte").sum()),
                ).reset_index()
                sub_agg["% Reporte"] = (sub_agg["Reportados"] / sub_agg["Total"] * 100).round(1).astype(str) + "%"
                sub_agg = sub_agg.sort_values("Total", ascending=False).reset_index(drop=True)

                ev_sub = st.dataframe(
                    sub_agg, use_container_width=True, hide_index=True,
                    on_select="rerun", selection_mode="single-row",
                    key="t0_sub_drill_table",
                )
                if ev_sub.selection and ev_sub.selection.get("rows"):
                    clicked_sub = sub_agg.iloc[ev_sub.selection["rows"][0]][_COL_S]
                    st.session_state["t0_sel_sub"] = clicked_sub

                current_sub = st.session_state.get("t0_sel_sub")
                if current_sub:
                    st.markdown(f"**Indicadores del subproceso: {current_sub}**")
                    df_inds = df_v_drill[df_v_drill[_COL_S] == current_sub]
                    cols_ind = _cols_pres(df_inds,
                                         ["Id", "Indicador", "Estado del indicador",
                                          "Reportado", "Proceso", "Tipo", "Sentido"])
                    st.dataframe(
                        df_inds[cols_ind].style.apply(_estilo_estado, axis=1),
                        use_container_width=True, hide_index=True,
                    )

    # ── Por Proceso ───────────────────────────────────────────────────────────
    elif "Proceso" in df_con.columns and COL_ESTADO in df_con.columns:
        st.markdown("#### Por Proceso")
        proc_stats = _agg_estado(df_con, "Proceso")
        fig_proc   = _bar_h(proc_stats, "Proceso")
        ev_proc    = st.plotly_chart(fig_proc, on_select="rerun",
                                     key="t0_chart_proc", use_container_width=True)

        sel_proc_r = None
        if ev_proc.selection and ev_proc.selection.get("points"):
            sel_proc_r = ev_proc.selection["points"][0].get("y")

        if sel_proc_r and sel_proc_r != st.session_state.get("t0_sel_proc"):
            st.session_state["t0_sel_proc"] = sel_proc_r
            st.session_state["t0_sel_sub"]  = None

        current_proc = st.session_state.get("t0_sel_proc") or sel_proc_r
        if current_proc and _COL_S in df_con.columns:
            st.markdown(f"**Subprocesos — {current_proc}**")
            df_p_drill = df_con[df_con["Proceso"] == current_proc]
            sub_agg_p  = df_p_drill.groupby(_COL_S).agg(
                Total=("Id", "count"),
                Reportados=(COL_ESTADO, lambda x: (x == "Reportado").sum()),
                Pendientes=(COL_ESTADO, lambda x: (x == "Pendiente de reporte").sum()),
            ).reset_index()
            sub_agg_p["% Reporte"] = (sub_agg_p["Reportados"] / sub_agg_p["Total"] * 100).round(1).astype(str) + "%"

            ev_sub_p = st.dataframe(
                sub_agg_p.sort_values("Total", ascending=False).reset_index(drop=True),
                use_container_width=True, hide_index=True,
                on_select="rerun", selection_mode="single-row",
                key="t0_sub_proc_table",
            )
            if ev_sub_p.selection and ev_sub_p.selection.get("rows"):
                clicked_sp = sub_agg_p.iloc[ev_sub_p.selection["rows"][0]][_COL_S]
                st.session_state["t0_sel_sub"] = clicked_sp

            current_sub_p = st.session_state.get("t0_sel_sub")
            if current_sub_p:
                st.markdown(f"**Indicadores del subproceso: {current_sub_p}**")
                df_ind_p  = df_p_drill[df_p_drill[_COL_S] == current_sub_p]
                cols_ip   = _cols_pres(df_ind_p, ["Id", "Indicador", "Estado del indicador",
                                                   "Reportado", "Tipo", "Sentido"])
                st.dataframe(df_ind_p[cols_ip].style.apply(_estilo_estado, axis=1),
                             use_container_width=True, hide_index=True)

    st.markdown("---")

    # ── 🚨 Ranking procesos sin reporte ───────────────────────────────────────
    col_rank = "Vicerrectoria" if "Vicerrectoria" in df_con.columns else \
               ("Proceso" if "Proceso" in df_con.columns else None)

    if col_rank and COL_ESTADO in df_con.columns:
        df_pen_r = df_con[df_con[COL_ESTADO] == "Pendiente de reporte"]
        if not df_pen_r.empty:
            st.markdown("#### 🚨 Ranking sin reporte")
            ranking = (
                df_pen_r.groupby(col_rank).size()
                .reset_index(name="Sin reporte")
                .sort_values("Sin reporte", ascending=False)
            )
            tot_r   = df_con.groupby(col_rank).size().reset_index(name="Total")
            ranking = ranking.merge(tot_r, on=col_rank, how="left")
            ranking["% Sin reporte"] = (ranking["Sin reporte"] / ranking["Total"] * 100).round(1)

            cr1, cr2 = st.columns([3, 2])
            with cr1:
                fig_rank = go.Figure(go.Bar(
                    x=ranking["Sin reporte"], y=ranking[col_rank],
                    orientation="h",
                    marker=dict(
                        color=ranking["% Sin reporte"],
                        colorscale=[[0, CORP["reportado"]], [0.5, CORP["alerta"]], [1, CORP["pendiente"]]],
                        showscale=True,
                        colorbar=dict(title="% sin<br>reporte", ticksuffix="%"),
                    ),
                    text=[f"{n}  ({p}%)" for n, p in
                          zip(ranking["Sin reporte"], ranking["% Sin reporte"])],
                    textposition="outside",
                    hovertemplate="<b>%{y}</b><br>Sin reporte: %{x}<br>%{marker.color:.1f}%<extra></extra>",
                ))
                fig_rank.update_layout(
                    height=max(300, len(ranking) * 36 + 60),
                    xaxis_title="Sin reporte",
                    yaxis=dict(title="", autorange="reversed", tickfont=dict(size=11)),
                    plot_bgcolor="white", paper_bgcolor="white",
                    margin=dict(t=10, b=40, l=10, r=80),
                )
                st.plotly_chart(fig_rank, use_container_width=True)
            with cr2:
                df_rk = ranking.rename(columns={col_rank: "Categoría"}).copy()
                df_rk["% Sin reporte"] = df_rk["% Sin reporte"].astype(str) + "%"

                def _color_rank(row):
                    try:
                        pct = float(str(row["% Sin reporte"]).replace("%", ""))
                    except ValueError:
                        pct = 0
                    bg = "#FDE8F3" if pct >= 80 else "#FEF3D0" if pct >= 50 else "#EDF7D6"
                    return ["", f"background-color: {bg}", "", f"background-color: {bg}"]

                st.dataframe(
                    df_rk[["Categoría", "Sin reporte", "Total", "% Sin reporte"]]
                    .style.apply(_color_rank, axis=1),
                    use_container_width=True, hide_index=True,
                )
                st.download_button(
                    "📥 Exportar ranking",
                    data=exportar_excel(df_rk[["Categoría", "Sin reporte", "Total", "% Sin reporte"]],
                                        "Sin reporte"),
                    file_name="procesos_sin_reporte.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="exp_rank_proc",
                )
        else:
            st.success("✅ No hay indicadores pendientes de reporte.")

# ─────────────────────────────────────────────────────────────────────────────
# TAB 1 — CONSOLIDADO
# ─────────────────────────────────────────────────────────────────────────────
with tabs[1]:
    st.markdown("### Tabla Consolidada")

    # ── Gráfico por Vicerrectoría (interactivo → filtra tabla) ────────────────
    _CON_V = "Vicerrectoria"
    _KEY_CON_V = "con_sel_vicerr"
    _KEY_CON_E = "con_sel_estado"

    if _CON_V in df_con.columns and COL_ESTADO in df_con.columns:
        st.markdown("#### Por Vicerrectoría")
        st.caption("💡 Haz clic en una barra (Reportado/Pendiente) para filtrar la tabla por vicerrectoría y estado.")

        vicerr_stats_con = _agg_estado(df_con, _CON_V)
        fig_con_v = _bar_h(vicerr_stats_con, _CON_V)
        ev_con_v  = st.plotly_chart(fig_con_v, use_container_width=True,
                                    on_select="rerun", key="con_chart_vicerr")

        if ev_con_v.selection and ev_con_v.selection.get("points"):
            pt = ev_con_v.selection["points"][0]
            clicked_con_v = pt.get("y")
            clicked_con_e = pt.get("customdata")
            if (clicked_con_v != st.session_state.get(_KEY_CON_V) or
                    clicked_con_e != st.session_state.get(_KEY_CON_E)):
                st.session_state[_KEY_CON_V] = clicked_con_v
                st.session_state[_KEY_CON_E] = clicked_con_e

        sel_con_v = st.session_state.get(_KEY_CON_V)
        sel_con_e = st.session_state.get(_KEY_CON_E)
        if sel_con_v or sel_con_e:
            hv1, hv2 = st.columns([7, 1])
            with hv1:
                partes = []
                if sel_con_v: partes.append(f"Vicerrectoría: **{sel_con_v}**")
                if sel_con_e: partes.append(f"Estado: **{sel_con_e}**")
                st.info("📊 Filtro activo: " + " · ".join(partes))
            with hv2:
                if st.button("✖ Todos", key="con_clear_vicerr"):
                    st.session_state[_KEY_CON_V] = None
                    st.session_state[_KEY_CON_E] = None
                    st.rerun()

        st.markdown("---")

    # ── Filtros y tabla ───────────────────────────────────────────────────────
    _sel_v_con = st.session_state.get(_KEY_CON_V) if _CON_V in df_con.columns else None
    _sel_e_con = st.session_state.get(_KEY_CON_E) if COL_ESTADO in df_con.columns else None
    df_con_base = df_con.copy()
    if _sel_v_con and _CON_V in df_con_base.columns:
        df_con_base = df_con_base[df_con_base[_CON_V] == _sel_v_con]
    if _sel_e_con and COL_ESTADO in df_con_base.columns:
        df_con_base = df_con_base[df_con_base[COL_ESTADO] == _sel_e_con]

    f_id_con, f_nom_con, f_proc_con, f_sub_con, f_est_con = _filtros_cascada(df_con_base, "con")
    df_filtrado = _aplicar_filtros_tabla(df_con_base, f_id_con, f_nom_con,
                                         f_proc_con, f_sub_con, f_est_con)
    st.caption(f"Mostrando **{len(df_filtrado)}** de **{len(df_con)}** indicadores")

    cols_mostrar = _cols_pres(df_filtrado, COLS_DESC_CON) or list(df_filtrado.columns)[:10]
    df_tabla_con = df_filtrado[cols_mostrar].copy()
    st.dataframe(
        df_tabla_con.style.apply(_estilo_estado, axis=1),
        use_container_width=True, hide_index=True,
    )
    st.download_button(
        "📥 Exportar Excel",
        data=exportar_excel(df_tabla_con, "Consolidado"),
        file_name="seguimiento_consolidado.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="exp_consolidado",
    )

# ─────────────────────────────────────────────────────────────────────────────
# TABS DE PERIODICIDAD (inician en tabs[2])
# ─────────────────────────────────────────────────────────────────────────────
for tab_idx, perio in enumerate(perios, 2):
    nombre_p = perio["nombre"]
    df_p     = perio["df"]
    cols_p   = perio["cols_periodo"]

    with tabs[tab_idx]:
        st.markdown(f"### {nombre_p}")

        if df_p.empty:
            st.info(f"No hay indicadores para {nombre_p}.")
            continue

        COL_E = "Estado del indicador"
        COL_R = "Reportado"
        total_p   = len(df_p)
        n_rep_p   = int((df_p[COL_E] == "Reportado").sum())             if COL_E in df_p.columns else 0
        n_pen_p   = int((df_p[COL_E] == "Pendiente de reporte").sum())  if COL_E in df_p.columns else 0
        pct_rep_p = round(n_rep_p / total_p * 100, 1) if total_p else 0

        kc1, kc2, kc3, kc4 = st.columns(4)
        with kc1: st.metric("Total indicadores", total_p)
        with kc2: st.metric("✅ Reportados", n_rep_p, delta=f"{pct_rep_p}%")
        with kc3: st.metric("⏳ Pendientes", n_pen_p,
                            delta=f"{round(n_pen_p/total_p*100,1)}%" if total_p else None,
                            delta_color="inverse")
        with kc4: st.metric("% Reporte", f"{pct_rep_p}%",
                            delta_color="normal" if pct_rep_p >= 80 else "inverse")

        # Gráfico por Proceso — interactivo: clic filtra la tabla inferior
        col_proc_p  = "Proceso" if "Proceso" in df_p.columns else None
        _key_chart  = f"chart_proc_{nombre_p}"
        _key_sel    = f"sel_proc_chart_{nombre_p}"

        _key_sel_e = f"sel_estado_chart_{nombre_p}"

        if col_proc_p and COL_E in df_p.columns:
            proc_p_s = _agg_estado(df_p, col_proc_p)
            fig_pg   = _bar_h(proc_p_s, col_proc_p)
            ev_pg    = st.plotly_chart(fig_pg, use_container_width=True,
                                       on_select="rerun", key=_key_chart)

            # Capturar clic: proceso (y) + estado (customdata)
            if ev_pg.selection and ev_pg.selection.get("points"):
                pt = ev_pg.selection["points"][0]
                clicked   = pt.get("y")
                clicked_e = pt.get("customdata")
                if (clicked != st.session_state.get(_key_sel) or
                        clicked_e != st.session_state.get(_key_sel_e)):
                    st.session_state[_key_sel]   = clicked
                    st.session_state[_key_sel_e] = clicked_e

        # Proceso y estado seleccionados desde el gráfico
        chart_proc   = st.session_state.get(_key_sel)
        chart_estado = st.session_state.get(_key_sel_e)

        # Encabezado + botón limpiar
        st.markdown("---")
        if chart_proc or chart_estado:
            hc1, hc2 = st.columns([7, 1])
            with hc1:
                partes = []
                if chart_proc:   partes.append(f"Proceso: *{chart_proc}*")
                if chart_estado: partes.append(f"Estado: **{chart_estado}**")
                st.markdown(f"#### Detalle de Indicadores — 📊 {' · '.join(partes)}")
            with hc2:
                if st.button("✖ Todos", key=f"clear_chart_{nombre_p}"):
                    st.session_state[_key_sel]   = None
                    st.session_state[_key_sel_e] = None
                    st.rerun()
        else:
            st.markdown("#### Detalle de Indicadores")
            st.caption("💡 Haz clic en una barra (Reportado/Pendiente) para filtrar por proceso y estado.")

        # Datos pre-filtrados por selección del gráfico
        df_p_base = df_p.copy()
        if chart_proc and col_proc_p:
            df_p_base = df_p_base[df_p_base[col_proc_p] == chart_proc]
        if chart_estado and COL_E in df_p_base.columns:
            df_p_base = df_p_base[df_p_base[COL_E] == chart_estado]

        f_id_p, f_nom_p, f_proc_p, f_sub_p, f_est_p = _filtros_cascada(df_p_base, f"p_{nombre_p}")
        df_p_fil = _aplicar_filtros_tabla(df_p_base, f_id_p, f_nom_p, f_proc_p, f_sub_p, f_est_p)
        st.caption(f"Mostrando **{len(df_p_fil)}** de **{len(df_p)}** indicadores")

        # Columna "Estado del indicador" en posición 4: Id, Indicador, Proceso, Estado, ...
        _DISPLAY_ORDER = ["Id", "Indicador", "Proceso", COL_E, COL_R,
                          "Subproceso", "Vicerrectoria", "Tipo", "Sentido", "Periodicidad"]
        cols_base    = [c for c in _DISPLAY_ORDER if c in df_p_fil.columns]
        cols_finales = cols_base + [c for c in cols_p if c in df_p_fil.columns]
        seen = set()
        cols_finales = [c for c in cols_finales if not (c in seen or seen.add(c))]

        df_tabla_p = df_p_fil[cols_finales].copy()

        for c in cols_p:
            if c in df_tabla_p.columns:
                df_tabla_p[c] = df_tabla_p[c].apply(
                    lambda v: "" if pd.isna(v) or str(v).strip() in
                              ("nan", "NaN", "-", "None") else v
                )

        col_cfg = {}
        if "Indicador" in df_tabla_p.columns:
            col_cfg["Indicador"] = st.column_config.TextColumn("Indicador", width="large")
        if COL_E in df_tabla_p.columns:
            col_cfg[COL_E] = st.column_config.TextColumn("Estado", width="medium")
        for c in cols_p:
            col_cfg[c] = st.column_config.TextColumn(c, width="small")

        event_p = st.dataframe(
            df_tabla_p.style.apply(_estilo_estado, axis=1),
            use_container_width=True, hide_index=True,
            column_config=col_cfg,
            on_select="rerun", selection_mode="single-row",
            key=f"tabla_{nombre_p}",
        )

        # Panel de detalle al clic en fila
        if event_p and event_p.selection and event_p.selection.get("rows"):
            idx_sel    = event_p.selection["rows"][0]
            fila       = df_tabla_p.iloc[idx_sel]
            id_ind     = str(fila.get("Id", ""))
            col_nom    = _col_nombre(df_tabla_p)
            nombre_ind = str(fila.get(col_nom, "")) if col_nom else ""
            proceso_i  = str(fila.get("Proceso", ""))
            subproc_i  = str(fila.get("Subproceso", ""))
            unidad_i   = str(fila.get("Vicerrectoria", fila.get("Area", "")))
            tipo_i     = str(fila.get("Tipo", ""))
            sentido_i  = str(fila.get("Sentido", ""))
            estado_i   = str(fila.get(COL_E, ""))
            badge_c    = COLOR_ESTADO.get(estado_i, "#9E9E9E")

            @st.dialog(f"{id_ind} — {nombre_ind[:60]}", width="large")
            def _panel_detalle():
                st.markdown(
                    f"**Vicerrectoría:** {unidad_i}  \n"
                    f"**Proceso:** {proceso_i}  \n"
                    f"**Subproceso:** {subproc_i}  \n"
                    f"**Tipo:** {tipo_i} &nbsp;|&nbsp; **Sentido:** {sentido_i}"
                )
                st.markdown(
                    f"<span style='background:{badge_c};padding:4px 14px;"
                    f"border-radius:12px'><b>Estado: {estado_i}</b></span>",
                    unsafe_allow_html=True,
                )
                st.markdown("---")
                if cols_p:
                    st.markdown("**Histórico de períodos (desde 2024)**")
                    hist = [{"Período": c, "Valor": fila.get(c, "")} for c in cols_p]
                    st.dataframe(pd.DataFrame(hist), use_container_width=True, hide_index=True)
                else:
                    st.info("No hay columnas de período disponibles desde 2024.")
                st.markdown("---")
                st.markdown("**Ficha técnica**")
                for fc in ["Id", "Indicador", "Vicerrectoria", "Proceso",
                           "Subproceso", "Tipo", "Sentido", "Periodicidad"]:
                    if fc in fila.index:
                        st.markdown(f"- **{fc}:** {fila.get(fc, '—')}")

            _panel_detalle()

        st.download_button(
            f"📥 Exportar {nombre_p}",
            data=exportar_excel(df_tabla_p, nombre_p[:31]),
            file_name=f"seguimiento_{nombre_p.lower()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key=f"exp_{nombre_p}",
        )
