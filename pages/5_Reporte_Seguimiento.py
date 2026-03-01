"""
pages/5_Reporte_Seguimiento.py — Indicadores con Reporte de Seguimiento.

Fuente: data/raw/Seguimiento_Reporte.xlsx (generado por generar_reporte.py).
Solo muestra indicadores con Revisar == 1 (indicador único/primero).
Página autocontenida: no depende de funciones externas de data_loader.
"""
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.charts import exportar_excel

# ── Rutas ─────────────────────────────────────────────────────────────────────
_DATA_RAW = Path(__file__).parent.parent / "data" / "raw"
_RUTA_XLSX = _DATA_RAW / "Seguimiento_Reporte.xlsx"
_CORTE = datetime(2024, 1, 1)

# ── Columnas descriptivas preferidas ─────────────────────────────────────────
COLS_DESC = ["Id", "Indicador", "Proceso", "Subproceso", "Tipo", "Sentido",
             "Periodicidad", "Estado del indicador", "Reportado"]

# ── Colores ───────────────────────────────────────────────────────────────────
COLOR_ESTADO    = {"Reportado": "#C8E6C9", "Pendiente de reporte": "#FFF9C4"}
COLOR_REPORTADO = {"Si": "#C8E6C9", "No": "#FFCDD2",
                   "Sí": "#C8E6C9"}   # con y sin tilde


# ── Helpers ───────────────────────────────────────────────────────────────────

def _id_limpio(x) -> str:
    if pd.isna(x):
        return ""
    try:
        f = float(x)
        return str(int(f)) if f == int(f) else str(f)
    except (ValueError, TypeError):
        return str(x)


def _cols_periodo_desde_2024(columnas) -> list:
    resultado = []
    for col in columnas:
        try:
            d = datetime.strptime(str(col), "%d/%m/%Y")
            if d >= _CORTE:
                resultado.append(col)
        except ValueError:
            pass
    return sorted(resultado, key=lambda c: datetime.strptime(c, "%d/%m/%Y"))


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


# ── Carga de datos (caché local, no depende de data_loader) ──────────────────

@st.cache_data(ttl=300, show_spinner="Cargando Seguimiento_Reporte.xlsx...")
def _cargar_datos() -> dict:
    """
    Retorna dict:
      seguimiento   : DataFrame (Revisar==1)
      resumen       : DataFrame hoja Resumen
      periodicidades: list de dict {nombre, df, cols_periodo}
    """
    if not _RUTA_XLSX.exists():
        return {}

    xl = pd.ExcelFile(str(_RUTA_XLSX), engine="openpyxl")
    hojas = xl.sheet_names
    out = {
        "seguimiento":    pd.DataFrame(),
        "resumen":        pd.DataFrame(),
        "periodicidades": [],
    }

    # Hoja Seguimiento
    if "Seguimiento" in hojas:
        df = xl.parse("Seguimiento")
        df.columns = [str(c).strip() for c in df.columns]
        if "Revisar" in df.columns:
            df["Revisar"] = pd.to_numeric(df["Revisar"], errors="coerce").fillna(0)
            df = df[df["Revisar"] == 1].reset_index(drop=True)
        if "Id" in df.columns:
            df["Id"] = df["Id"].apply(_id_limpio)
        out["seguimiento"] = df

    # Hoja Resumen
    if "Resumen" in hojas:
        df = xl.parse("Resumen")
        df.columns = [str(c).strip() for c in df.columns]
        out["resumen"] = df

    # Hojas de periodicidad
    for hoja in hojas:
        if hoja in ("Seguimiento", "Resumen"):
            continue
        df = xl.parse(hoja)
        df.columns = [str(c).strip() for c in df.columns]
        if "Revisar" in df.columns:
            df["Revisar"] = pd.to_numeric(df["Revisar"], errors="coerce").fillna(0)
            df = df[df["Revisar"] == 1].reset_index(drop=True)
        if "Id" in df.columns:
            df["Id"] = df["Id"].apply(_id_limpio)
        cols_p = _cols_periodo_desde_2024(df.columns)
        out["periodicidades"].append({"nombre": hoja, "df": df, "cols_periodo": cols_p})

    return out


# ══════════════════════════════════════════════════════════════════════════════
# CARGA
# ══════════════════════════════════════════════════════════════════════════════
datos = _cargar_datos()

if not datos:
    st.error(
        "No se encontró **Seguimiento_Reporte.xlsx** en `data/raw/`.  \n"
        "Ejecuta primero `generar_reporte.py` para generarlo."
    )
    st.stop()

df_seg = datos["seguimiento"]
df_res = datos["resumen"]
perios = datos["periodicidades"]

if df_seg.empty:
    st.error("La hoja 'Seguimiento' no contiene indicadores con Revisar = 1.")
    st.stop()

# ══════════════════════════════════════════════════════════════════════════════
# TÍTULO
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("# 📊 Reporte de Seguimiento de Indicadores")
st.caption("Solo indicadores con **Revisar = 1** · Periodos desde **2024-01-01**")
st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════════════════════
nombres_tabs = ["📋 Consolidado"] + [f"📅 {p['nombre']}" for p in perios]
tabs = st.tabs(nombres_tabs)

# ─────────────────────────────────────────────────────────────────────────────
# TAB 0 — CONSOLIDADO
# ─────────────────────────────────────────────────────────────────────────────
with tabs[0]:
    COL_ESTADO = "Estado del indicador"
    COL_REP    = "Reportado"
    col_proc   = next((c for c in df_seg.columns if c.lower() == "proceso"), None)

    total        = len(df_seg)
    n_reportados = int((df_seg[COL_ESTADO] == "Reportado").sum())            if COL_ESTADO in df_seg.columns else 0
    n_pendientes = int((df_seg[COL_ESTADO] == "Pendiente de reporte").sum()) if COL_ESTADO in df_seg.columns else 0
    n_rep_hoy    = int((df_seg[COL_REP].isin(["Sí", "Si"])).sum())           if COL_REP    in df_seg.columns else 0
    pct_rep      = round(n_rep_hoy / total * 100, 1) if total else 0

    # ── KPIs ──────────────────────────────────────────────────────────────────
    st.markdown("### Vista Consolidada")
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.metric("Total indicadores", total)
    with c2:
        st.metric("✅ Reportados (estado)", n_reportados,
                  delta=f"{round(n_reportados/total*100,1)}%" if total else None)
    with c3:
        st.metric("⏳ Pendientes (estado)", n_pendientes,
                  delta=f"{round(n_pendientes/total*100,1)}%" if total else None,
                  delta_color="inverse")
    with c4:
        st.metric("📤 Reportados período actual", n_rep_hoy)
    with c5:
        st.metric("% Reporte período actual", f"{pct_rep}%",
                  delta_color="normal" if pct_rep >= 80 else "inverse")

    st.markdown("---")

    # ── Por Periodicidad ──────────────────────────────────────────────────────
    if not df_res.empty:
        st.markdown("#### Por Periodicidad")
        col_per = df_res.columns[0]
        col_rpt = next((c for c in df_res.columns if "reportad" in c.lower()), None)
        col_pen = next((c for c in df_res.columns if "pendiente" in c.lower()), None)

        if col_rpt:
            fig_per = go.Figure()
            fig_per.add_trace(go.Bar(
                x=df_res[col_per], y=df_res[col_rpt],
                name="Reportados", marker_color="#2E7D32",
                text=df_res[col_rpt], textposition="outside",
            ))
            if col_pen:
                fig_per.add_trace(go.Bar(
                    x=df_res[col_per], y=df_res[col_pen],
                    name="Pendientes", marker_color="#F57F17",
                    text=df_res[col_pen], textposition="outside",
                ))
            fig_per.update_layout(
                barmode="group", height=300,
                xaxis_title="Periodicidad", yaxis_title="Indicadores",
                plot_bgcolor="white", paper_bgcolor="white",
                legend=dict(orientation="h", y=-0.3),
                margin=dict(t=15, b=70),
            )
            st.plotly_chart(fig_per, use_container_width=True)
        st.dataframe(df_res, use_container_width=True, hide_index=True)
        st.markdown("")

    # ── Por Proceso ───────────────────────────────────────────────────────────
    if col_proc and COL_ESTADO in df_seg.columns:
        st.markdown("#### Por Proceso")
        proc_stats = (
            df_seg.groupby(col_proc)[COL_ESTADO]
            .value_counts().unstack(fill_value=0).reset_index()
        )
        proc_stats["_t"] = proc_stats.drop(columns=[col_proc]).sum(axis=1)
        proc_stats = proc_stats.sort_values("_t", ascending=False).drop(columns="_t")

        col_rep_p = "Reportado"            if "Reportado"            in proc_stats.columns else None
        col_pen_p = "Pendiente de reporte" if "Pendiente de reporte" in proc_stats.columns else None

        cg1, cg2 = st.columns([3, 2])
        with cg1:
            fig_proc = go.Figure()
            if col_rep_p:
                fig_proc.add_trace(go.Bar(
                    y=proc_stats[col_proc], x=proc_stats[col_rep_p],
                    orientation="h", name="Reportado", marker_color="#2E7D32",
                    text=proc_stats[col_rep_p], textposition="outside",
                ))
            if col_pen_p:
                fig_proc.add_trace(go.Bar(
                    y=proc_stats[col_proc], x=proc_stats[col_pen_p],
                    orientation="h", name="Pendiente", marker_color="#F57F17",
                    text=proc_stats[col_pen_p], textposition="outside",
                ))
            fig_proc.update_layout(
                barmode="stack",
                height=max(300, len(proc_stats) * 35 + 60),
                xaxis_title="Indicadores", yaxis_title="",
                plot_bgcolor="white", paper_bgcolor="white",
                legend=dict(orientation="h", y=-0.15),
                margin=dict(t=15, b=50, l=10, r=10),
            )
            st.plotly_chart(fig_proc, use_container_width=True)
        with cg2:
            total_proc = proc_stats.drop(columns=[col_proc]).sum(axis=1)
            df_pct = proc_stats[[col_proc]].copy()
            if col_rep_p:
                df_pct["Reportados"] = proc_stats[col_rep_p]
                df_pct["% Reporte"]  = (proc_stats[col_rep_p] / total_proc * 100).round(1).astype(str) + "%"
            df_pct["Total"] = total_proc
            st.dataframe(df_pct, use_container_width=True, hide_index=True)

    st.markdown("---")

    # ── 🚨 Ranking procesos sin reporte ───────────────────────────────────────
    if col_proc and COL_ESTADO in df_seg.columns:
        df_pen = df_seg[df_seg[COL_ESTADO] == "Pendiente de reporte"]

        if not df_pen.empty:
            st.markdown("#### 🚨 Procesos con más indicadores sin reporte")
            ranking = (
                df_pen.groupby(col_proc).size()
                .reset_index(name="Sin reporte")
                .sort_values("Sin reporte", ascending=False)
            )
            tot_p   = df_seg.groupby(col_proc).size().reset_index(name="Total")
            ranking = ranking.merge(tot_p, on=col_proc, how="left")
            ranking["% Sin reporte"] = (ranking["Sin reporte"] / ranking["Total"] * 100).round(1)

            cr1, cr2 = st.columns([3, 2])
            with cr1:
                fig_rank = go.Figure(go.Bar(
                    x=ranking["Sin reporte"],
                    y=ranking[col_proc],
                    orientation="h",
                    marker=dict(
                        color=ranking["% Sin reporte"],
                        colorscale=[[0, "#FFF9C4"], [0.5, "#FF8C00"], [1, "#C62828"]],
                        showscale=True,
                        colorbar=dict(title="% sin<br>reporte", ticksuffix="%"),
                    ),
                    text=[f"{n}  ({p}%)" for n, p in
                          zip(ranking["Sin reporte"], ranking["% Sin reporte"])],
                    textposition="outside",
                    hovertemplate=(
                        "<b>%{y}</b><br>Sin reporte: %{x}<br>"
                        "% Sin reporte: %{marker.color:.1f}%<extra></extra>"
                    ),
                ))
                fig_rank.update_layout(
                    height=max(300, len(ranking) * 36 + 60),
                    xaxis_title="Indicadores sin reporte",
                    yaxis=dict(title="", autorange="reversed", tickfont=dict(size=11)),
                    plot_bgcolor="white", paper_bgcolor="white",
                    margin=dict(t=10, b=40, l=10, r=80),
                )
                st.plotly_chart(fig_rank, use_container_width=True)

            with cr2:
                df_rk = ranking.rename(columns={col_proc: "Proceso"}).copy()
                df_rk["% Sin reporte"] = df_rk["% Sin reporte"].astype(str) + "%"

                def _color_rank(row):
                    try:
                        pct = float(str(row["% Sin reporte"]).replace("%", ""))
                    except ValueError:
                        pct = 0
                    bg = "#FFCDD2" if pct >= 80 else "#FFF9C4" if pct >= 50 else "#C8E6C9"
                    return ["", f"background-color: {bg}", "", f"background-color: {bg}"]

                st.dataframe(
                    df_rk[["Proceso", "Sin reporte", "Total", "% Sin reporte"]]
                    .style.apply(_color_rank, axis=1),
                    use_container_width=True, hide_index=True,
                )
                st.download_button(
                    "📥 Exportar ranking",
                    data=exportar_excel(
                        df_rk[["Proceso", "Sin reporte", "Total", "% Sin reporte"]],
                        "Sin reporte por proceso",
                    ),
                    file_name="procesos_sin_reporte.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="exp_rank_proc",
                )
        else:
            st.success("✅ No hay indicadores pendientes de reporte.")

    st.markdown("---")

    # ── Tabla consolidada ─────────────────────────────────────────────────────
    st.markdown("#### Tabla Consolidada (todos los indicadores únicos)")
    cols_mostrar = _cols_pres(df_seg, COLS_DESC) or list(df_seg.columns)[:10]
    df_tabla_con = df_seg[cols_mostrar].copy()
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
# TABS DE PERIODICIDAD
# ─────────────────────────────────────────────────────────────────────────────
for tab_idx, perio in enumerate(perios, 1):
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
        n_rep_p   = int((df_p[COL_E] == "Reportado").sum())              if COL_E in df_p.columns else 0
        n_pen_p   = int((df_p[COL_E] == "Pendiente de reporte").sum())   if COL_E in df_p.columns else 0
        pct_rep_p = round(n_rep_p / total_p * 100, 1) if total_p else 0

        kc1, kc2, kc3, kc4 = st.columns(4)
        with kc1: st.metric("Total indicadores", total_p)
        with kc2: st.metric("✅ Reportados", n_rep_p, delta=f"{pct_rep_p}%")
        with kc3: st.metric("⏳ Pendientes", n_pen_p,
                            delta=f"{round(n_pen_p/total_p*100,1)}%" if total_p else None,
                            delta_color="inverse")
        with kc4: st.metric("% Reporte", f"{pct_rep_p}%",
                            delta_color="normal" if pct_rep_p >= 80 else "inverse")

        # Gráfico por proceso
        col_proc_p = next((c for c in df_p.columns if c.lower() == "proceso"), None)
        if col_proc_p and COL_E in df_p.columns:
            proc_p = (
                df_p.groupby(col_proc_p)[COL_E]
                .value_counts().unstack(fill_value=0).reset_index()
            )
            fig_pg = go.Figure()
            for est, color in [("Reportado", "#2E7D32"), ("Pendiente de reporte", "#F57F17")]:
                if est in proc_p.columns:
                    fig_pg.add_trace(go.Bar(
                        x=proc_p[col_proc_p], y=proc_p[est],
                        name=est, marker_color=color,
                        text=proc_p[est], textposition="outside",
                    ))
            fig_pg.update_layout(
                barmode="stack", height=280,
                xaxis=dict(title="Proceso", tickangle=-30),
                yaxis_title="Indicadores",
                plot_bgcolor="white", paper_bgcolor="white",
                legend=dict(orientation="h", y=-0.35),
                margin=dict(t=10, b=80),
            )
            st.plotly_chart(fig_pg, use_container_width=True)

        st.markdown("---")
        st.markdown("#### Detalle de Indicadores")

        cols_desc_p  = [c for c in COLS_DESC if c in df_p.columns and c not in (COL_E, COL_R)]
        cols_estado_p = [c for c in (COL_E, COL_R) if c in df_p.columns]
        cols_finales  = cols_desc_p + cols_p + cols_estado_p
        seen = set()
        cols_finales = [c for c in cols_finales
                        if c in df_p.columns and not (c in seen or seen.add(c))]

        df_tabla_p = df_p[cols_finales].copy()

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
            use_container_width=True,
            hide_index=True,
            column_config=col_cfg,
            on_select="rerun",
            selection_mode="single-row",
            key=f"tabla_{nombre_p}",
        )

        # Panel de detalle al clic en fila
        if event_p and event_p.selection and event_p.selection.get("rows"):
            idx_sel = event_p.selection["rows"][0]
            fila    = df_tabla_p.iloc[idx_sel]
            id_ind  = str(fila.get("Id", ""))
            col_nom = _col_nombre(df_tabla_p)
            nombre_ind = str(fila.get(col_nom, "")) if col_nom else ""
            proceso_i = str(fila.get("Proceso", ""))
            tipo_i    = str(fila.get("Tipo", ""))
            sentido_i = str(fila.get("Sentido", ""))
            estado_i  = str(fila.get(COL_E, ""))
            badge_c   = COLOR_ESTADO.get(estado_i, "#9E9E9E")

            @st.dialog(f"{id_ind} — {nombre_ind[:60]}", width="large")
            def _panel_detalle():
                st.markdown(
                    f"**Proceso:** {proceso_i} &nbsp;|&nbsp; "
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
                for fc in ["Id", "Indicador", "Proceso", "Subproceso",
                           "Tipo", "Sentido", "Periodicidad"]:
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
