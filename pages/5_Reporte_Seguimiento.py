"""
pages/5_Reporte_Seguimiento.py — Indicadores con Reporte de Seguimiento.

Fuente: Seguimiento_Reporte.xlsx (generado por generar_reporte.py).
Solo muestra indicadores con Revisar == 1 (indicador único/primero).
"""
from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

from utils.data_loader import cargar_seguimiento_reporte
from utils.charts import exportar_excel

# ── Columnas descriptivas a mostrar ──────────────────────────────────────────
# Se buscan flexiblemente por coincidencia parcial (sin tildes) para tolerar
# variaciones en los nombres exactos del xlsx fuente.
COLS_DESCRIPTIVAS_PREF = ["Id", "Indicador", "Proceso", "Subproceso", "Tipo", "Sentido",
                           "Periodicidad", "Estado del indicador", "Reportado"]

# Colores semáforo de estado
COLOR_ESTADO = {
    "Reportado":             "#C8E6C9",
    "Pendiente de reporte":  "#FFF9C4",
}
COLOR_REPORTADO = {
    "Sí": "#C8E6C9",
    "No": "#FFCDD2",
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def _cols_presentes(df: pd.DataFrame, preferidas: list) -> list:
    """Retorna las columnas de `preferidas` que existen en df."""
    return [c for c in preferidas if c in df.columns]


def _col_nombre_indicador(df: pd.DataFrame) -> str | None:
    """Detecta la columna de nombre del indicador."""
    for candidato in ["Indicador", "Nombre", "Descripcion", "Descripción"]:
        if candidato in df.columns:
            return candidato
    return None


def _estilo_estado(row):
    col_estado = "Estado del indicador"
    col_rep    = "Reportado"
    estilos = []
    for col in row.index:
        if col == col_estado:
            bg = COLOR_ESTADO.get(str(row[col]), "")
        elif col == col_rep:
            bg = COLOR_REPORTADO.get(str(row[col]), "")
        else:
            bg = ""
        estilos.append(f"background-color: {bg}" if bg else "")
    return estilos


# ── Carga de datos ────────────────────────────────────────────────────────────
datos = cargar_seguimiento_reporte()

if not datos:
    st.error(
        "No se encontró **Seguimiento_Reporte.xlsx** en `data/raw/`.  \n"
        "Ejecuta primero `generar_reporte.py` para generarlo."
    )
    st.stop()

df_seg   = datos.get("seguimiento", pd.DataFrame())
df_res   = datos.get("resumen", pd.DataFrame())
perios   = datos.get("periodicidades", {})

if df_seg.empty:
    st.error("La hoja 'Seguimiento' está vacía o no contiene indicadores con Revisar = 1.")
    st.stop()

# ══════════════════════════════════════════════════════════════════════════════
# TÍTULO
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("# 📊 Reporte de Seguimiento de Indicadores")
st.caption("Solo indicadores con **Revisar = 1** · Periodos desde **2024-01-01**")
st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# TABS: Consolidado + una por periodicidad
# ══════════════════════════════════════════════════════════════════════════════
nombres_tabs = ["📋 Consolidado"] + [f"📅 {p}" for p in perios.keys()]
tabs = st.tabs(nombres_tabs)

# ─────────────────────────────────────────────────────────────────────────────
# TAB 0 — CONSOLIDADO (Resumen General)
# ─────────────────────────────────────────────────────────────────────────────
with tabs[0]:
    total_ind = len(df_seg)

    # KPIs globales
    col_estado_seg = "Estado del indicador"
    col_rep_seg    = "Reportado"

    n_reportados  = (df_seg[col_estado_seg] == "Reportado").sum()       if col_estado_seg in df_seg.columns else 0
    n_pendientes  = (df_seg[col_estado_seg] == "Pendiente de reporte").sum() if col_estado_seg in df_seg.columns else 0
    n_rep_hoy     = (df_seg[col_rep_seg] == "Sí").sum()                if col_rep_seg    in df_seg.columns else 0
    pct_rep       = round(n_rep_hoy / total_ind * 100, 1) if total_ind else 0

    st.markdown("### Indicadores — Vista Consolidada")
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.metric("Total indicadores", total_ind)
    with c2:
        st.metric("✅ Reportados (estado)", n_reportados,
                  delta=f"{round(n_reportados/total_ind*100,1)}%" if total_ind else None)
    with c3:
        st.metric("⏳ Pendientes (estado)", n_pendientes,
                  delta=f"{round(n_pendientes/total_ind*100,1)}%" if total_ind else None,
                  delta_color="inverse")
    with c4:
        st.metric("📤 Reportados (período actual)", n_rep_hoy)
    with c5:
        st.metric("% Reporte período actual", f"{pct_rep}%",
                  delta_color="normal" if pct_rep >= 80 else "inverse")

    st.markdown("---")

    # ── Resumen por periodicidad (desde hoja Resumen del xlsx) ────────────────
    if not df_res.empty:
        st.markdown("#### Por Periodicidad")
        col_tot = next((c for c in df_res.columns if "total" in c.lower()), None)
        col_rpt = next((c for c in df_res.columns if "reportad" in c.lower()), None)
        col_pen = next((c for c in df_res.columns if "pendiente" in c.lower()), None)
        col_pct = next((c for c in df_res.columns if "%" in c or "porcentaje" in c.lower()), None)
        col_per = df_res.columns[0]  # primera columna = Periodicidad

        if col_tot and col_rpt:
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
                barmode="group",
                height=320,
                xaxis_title="Periodicidad",
                yaxis_title="Indicadores",
                plot_bgcolor="white", paper_bgcolor="white",
                legend=dict(orientation="h", y=-0.25),
                margin=dict(t=20, b=60),
            )
            st.plotly_chart(fig_per, use_container_width=True)

        st.dataframe(df_res, use_container_width=True, hide_index=True)
        st.markdown("")

    # ── Por Proceso ───────────────────────────────────────────────────────────
    col_proc = next((c for c in df_seg.columns if "proceso" in c.lower()), None)
    if col_proc and col_estado_seg in df_seg.columns:
        st.markdown("#### Por Proceso")

        proc_stats = (
            df_seg.groupby(col_proc)[col_estado_seg]
            .value_counts()
            .unstack(fill_value=0)
            .reset_index()
        )

        # Ordenar por total descendente
        proc_stats["_total"] = proc_stats.drop(columns=[col_proc]).sum(axis=1)
        proc_stats = proc_stats.sort_values("_total", ascending=False).drop(columns="_total")

        # Añadir % reporte
        col_rep_proc = "Reportado" if "Reportado" in proc_stats.columns else None
        col_pen_proc = "Pendiente de reporte" if "Pendiente de reporte" in proc_stats.columns else None

        col_g1, col_g2 = st.columns([3, 2])

        with col_g1:
            fig_proc = go.Figure()
            if col_rep_proc:
                fig_proc.add_trace(go.Bar(
                    y=proc_stats[col_proc], x=proc_stats[col_rep_proc],
                    orientation="h", name="Reportado",
                    marker_color="#2E7D32",
                    text=proc_stats[col_rep_proc], textposition="outside",
                ))
            if col_pen_proc:
                fig_proc.add_trace(go.Bar(
                    y=proc_stats[col_proc], x=proc_stats[col_pen_proc],
                    orientation="h", name="Pendiente",
                    marker_color="#F57F17",
                    text=proc_stats[col_pen_proc], textposition="outside",
                ))
            fig_proc.update_layout(
                barmode="stack",
                height=max(300, len(proc_stats) * 35 + 60),
                xaxis_title="Indicadores",
                yaxis_title="",
                plot_bgcolor="white", paper_bgcolor="white",
                legend=dict(orientation="h", y=-0.15),
                margin=dict(t=20, b=50, l=10, r=10),
            )
            st.plotly_chart(fig_proc, use_container_width=True)

        with col_g2:
            # Tabla % por proceso
            df_pct_proc = proc_stats[[col_proc]].copy()
            total_proc  = proc_stats.drop(columns=[col_proc]).sum(axis=1)
            if col_rep_proc:
                df_pct_proc["Reportados"] = proc_stats[col_rep_proc]
                df_pct_proc["% Reporte"]  = (
                    proc_stats[col_rep_proc] / total_proc * 100
                ).round(1).astype(str) + "%"
            df_pct_proc["Total"] = total_proc
            st.dataframe(df_pct_proc, use_container_width=True, hide_index=True)

    st.markdown("---")

    # ── Procesos con más indicadores sin reporte ──────────────────────────────
    col_proc2 = next((c for c in df_seg.columns if "proceso" in c.lower()), None)
    if col_proc2 and col_estado_seg in df_seg.columns:
        df_pen_seg = df_seg[df_seg[col_estado_seg] == "Pendiente de reporte"]

        if not df_pen_seg.empty:
            st.markdown("#### 🚨 Procesos con más indicadores sin reporte")

            ranking = (
                df_pen_seg.groupby(col_proc2)
                .size()
                .reset_index(name="Sin reporte")
                .sort_values("Sin reporte", ascending=False)
            )

            # Total por proceso para calcular %
            total_por_proc = df_seg.groupby(col_proc2).size().reset_index(name="Total")
            ranking = ranking.merge(total_por_proc, on=col_proc2, how="left")
            ranking["% Sin reporte"] = (
                ranking["Sin reporte"] / ranking["Total"] * 100
            ).round(1)

            col_rk1, col_rk2 = st.columns([3, 2])

            with col_rk1:
                fig_rank = go.Figure(go.Bar(
                    x=ranking["Sin reporte"],
                    y=ranking[col_proc2],
                    orientation="h",
                    marker=dict(
                        color=ranking["% Sin reporte"],
                        colorscale=[[0, "#FFF9C4"], [0.5, "#FF8C00"], [1, "#C62828"]],
                        showscale=True,
                        colorbar=dict(title="% sin<br>reporte", ticksuffix="%"),
                    ),
                    text=[
                        f"{n}  ({p}%)"
                        for n, p in zip(ranking["Sin reporte"], ranking["% Sin reporte"])
                    ],
                    textposition="outside",
                    hovertemplate=(
                        "<b>%{y}</b><br>"
                        "Sin reporte: %{x}<br>"
                        "% Sin reporte: %{marker.color:.1f}%<extra></extra>"
                    ),
                ))
                fig_rank.update_layout(
                    height=max(300, len(ranking) * 36 + 60),
                    xaxis=dict(title="Indicadores sin reporte"),
                    yaxis=dict(
                        title="",
                        autorange="reversed",
                        tickfont=dict(size=11),
                    ),
                    plot_bgcolor="white",
                    paper_bgcolor="white",
                    margin=dict(t=10, b=40, l=10, r=80),
                )
                st.plotly_chart(fig_rank, use_container_width=True)

            with col_rk2:
                df_tabla_rank = ranking.rename(columns={col_proc2: "Proceso"}).copy()
                df_tabla_rank["% Sin reporte"] = (
                    df_tabla_rank["% Sin reporte"].astype(str) + "%"
                )

                def _color_pct(row):
                    try:
                        pct = float(str(row["% Sin reporte"]).replace("%", ""))
                    except ValueError:
                        pct = 0
                    if pct >= 80:
                        bg = "#FFCDD2"
                    elif pct >= 50:
                        bg = "#FFF9C4"
                    else:
                        bg = "#C8E6C9"
                    return ["", f"background-color: {bg}", "", f"background-color: {bg}"]

                styled_rank = df_tabla_rank[
                    ["Proceso", "Sin reporte", "Total", "% Sin reporte"]
                ].style.apply(_color_pct, axis=1)

                st.dataframe(styled_rank, use_container_width=True, hide_index=True)

                st.download_button(
                    label="📥 Exportar ranking",
                    data=exportar_excel(
                        df_tabla_rank[["Proceso", "Sin reporte", "Total", "% Sin reporte"]],
                        "Sin reporte por proceso",
                    ),
                    file_name="procesos_sin_reporte.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="exp_rank_proc",
                )
        else:
            st.success("✅ No hay indicadores pendientes de reporte.")

    st.markdown("---")

    # ── Tabla consolidada completa ────────────────────────────────────────────
    st.markdown("#### Tabla Consolidada (todos los indicadores únicos)")

    cols_mostrar = _cols_presentes(df_seg, COLS_DESCRIPTIVAS_PREF)
    if not cols_mostrar:
        cols_mostrar = list(df_seg.columns)[:10]

    df_tabla_con = df_seg[cols_mostrar].copy()

    styled_con = df_tabla_con.style.apply(_estilo_estado, axis=1)
    st.dataframe(styled_con, use_container_width=True, hide_index=True)

    st.download_button(
        label="📥 Exportar Excel",
        data=exportar_excel(df_tabla_con, "Consolidado"),
        file_name="seguimiento_consolidado.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

# ─────────────────────────────────────────────────────────────────────────────
# TABS 1..N — POR PERIODICIDAD
# ─────────────────────────────────────────────────────────────────────────────
for tab_idx, (nombre_perio, df_p) in enumerate(perios.items(), 1):
    with tabs[tab_idx]:
        st.markdown(f"### {nombre_perio}")

        cols_periodo = df_p.attrs.get("cols_periodo", [])

        if df_p.empty:
            st.info(f"No hay indicadores para {nombre_perio}.")
            continue

        # ── KPIs de esta periodicidad ─────────────────────────────────────────
        total_p   = len(df_p)
        n_rep_p   = (df_p["Estado del indicador"] == "Reportado").sum()         if "Estado del indicador" in df_p.columns else 0
        n_pen_p   = (df_p["Estado del indicador"] == "Pendiente de reporte").sum() if "Estado del indicador" in df_p.columns else 0
        pct_rep_p = round(n_rep_p / total_p * 100, 1) if total_p else 0

        kc1, kc2, kc3, kc4 = st.columns(4)
        with kc1:
            st.metric("Total indicadores", total_p)
        with kc2:
            st.metric("✅ Reportados", n_rep_p, delta=f"{pct_rep_p}%")
        with kc3:
            st.metric("⏳ Pendientes", n_pen_p,
                      delta=f"{round(n_pen_p/total_p*100,1)}%" if total_p else None,
                      delta_color="inverse")
        with kc4:
            color_pct = "normal" if pct_rep_p >= 80 else "inverse"
            st.metric("% Reporte", f"{pct_rep_p}%", delta_color=color_pct)

        # ── Gráfico por proceso ───────────────────────────────────────────────
        col_proc_p = next((c for c in df_p.columns if c.lower() == "proceso"), None)
        if col_proc_p and "Estado del indicador" in df_p.columns:
            proc_p = (
                df_p.groupby(col_proc_p)["Estado del indicador"]
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
                barmode="stack", height=300,
                xaxis=dict(title="Proceso", tickangle=-30),
                yaxis_title="Indicadores",
                plot_bgcolor="white", paper_bgcolor="white",
                legend=dict(orientation="h", y=-0.3),
                margin=dict(t=10, b=70),
            )
            st.plotly_chart(fig_pg, use_container_width=True)

        st.markdown("---")

        # ── Tabla: columnas descriptivas + períodos desde 2024 ───────────────
        st.markdown("#### Detalle de Indicadores")

        # Construir lista de columnas a mostrar
        cols_desc_p = _cols_presentes(df_p, COLS_DESCRIPTIVAS_PREF)

        # Columnas de período ordenadas ascendente (ya desde 2024)
        # Separar las que ya están en COLS_DESCRIPTIVAS_PREF para no duplicar
        cols_desc_sin_estado = [
            c for c in cols_desc_p
            if c not in ("Estado del indicador", "Reportado")
        ]
        cols_estado = [c for c in ("Estado del indicador", "Reportado") if c in df_p.columns]

        # Orden final: descriptivas (sin estado) → períodos → estado
        cols_finales = cols_desc_sin_estado + cols_periodo + cols_estado
        cols_finales = [c for c in cols_finales if c in df_p.columns]  # solo las que existen

        # Quitar duplicados manteniendo orden
        seen = set()
        cols_finales = [c for c in cols_finales if not (c in seen or seen.add(c))]

        df_tabla_p = df_p[cols_finales].copy()

        # Limpiar celdas con NaN en columnas de período
        for col in cols_periodo:
            if col in df_tabla_p.columns:
                df_tabla_p[col] = df_tabla_p[col].apply(
                    lambda v: "" if pd.isna(v) or str(v).strip() in ("nan", "NaN", "-", "None") else v
                )

        # Formatear Id
        if "Id" in df_tabla_p.columns:
            df_tabla_p["Id"] = df_tabla_p["Id"].apply(
                lambda x: str(x).rstrip(".0") if str(x).endswith(".0") else str(x)
            )

        # Columnas de configuración para st.dataframe
        col_config = {}
        if "Estado del indicador" in df_tabla_p.columns:
            col_config["Estado del indicador"] = st.column_config.TextColumn(
                "Estado", width="medium"
            )
        if "Indicador" in df_tabla_p.columns:
            col_config["Indicador"] = st.column_config.TextColumn("Indicador", width="large")
        for c in cols_periodo:
            col_config[c] = st.column_config.TextColumn(c, width="small")

        styled_p = df_tabla_p.style.apply(_estilo_estado, axis=1)

        event_p = st.dataframe(
            styled_p,
            use_container_width=True,
            hide_index=True,
            column_config=col_config,
            on_select="rerun",
            selection_mode="single-row",
            key=f"tabla_perio_{nombre_perio}",
        )

        # ── Panel de detalle al hacer clic en fila ───────────────────────────
        if event_p and event_p.selection and event_p.selection.get("rows"):
            idx_sel = event_p.selection["rows"][0]
            fila = df_tabla_p.iloc[idx_sel]

            id_ind  = str(fila.get("Id", ""))
            col_nom = _col_nombre_indicador(df_tabla_p)
            nombre  = str(fila.get(col_nom, "")) if col_nom else ""
            proceso = str(fila.get("Proceso", ""))
            tipo    = str(fila.get("Tipo", ""))
            sentido = str(fila.get("Sentido", ""))
            estado  = str(fila.get("Estado del indicador", ""))

            badge_bg = COLOR_ESTADO.get(estado, "#9E9E9E")

            @st.dialog(f"{id_ind} — {nombre[:60]}", width="large")
            def panel_detalle_reporte():
                st.markdown(f"**Proceso:** {proceso} &nbsp;|&nbsp; **Tipo:** {tipo} &nbsp;|&nbsp; **Sentido:** {sentido}")
                st.markdown(
                    f"<span style='background:{badge_bg};padding:4px 14px;"
                    f"border-radius:12px;font-size:0.9rem'><b>Estado: {estado}</b></span>",
                    unsafe_allow_html=True,
                )
                st.markdown("---")
                st.markdown("**Histórico de períodos (desde 2024)**")

                # Tabla de valores por período
                if cols_periodo:
                    periodos_vals = []
                    for col_p in cols_periodo:
                        val = fila.get(col_p, "")
                        periodos_vals.append({"Período": col_p, "Valor": val})
                    df_hist_rep = pd.DataFrame(periodos_vals)
                    st.dataframe(df_hist_rep, use_container_width=True, hide_index=True)
                else:
                    st.info("No hay columnas de período disponibles desde 2024.")

                # Ficha del indicador
                st.markdown("---")
                st.markdown("**Ficha técnica**")
                ficha_cols = [c for c in ["Id", "Indicador", "Proceso", "Subproceso",
                                           "Tipo", "Sentido", "Periodicidad"] if c in fila.index]
                for c in ficha_cols:
                    st.markdown(f"- **{c}:** {fila.get(c, '—')}")

            panel_detalle_reporte()

        # ── Exportar ──────────────────────────────────────────────────────────
        st.download_button(
            label=f"📥 Exportar {nombre_perio}",
            data=exportar_excel(df_tabla_p, nombre_perio[:31]),
            file_name=f"seguimiento_{nombre_perio.lower()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key=f"exp_{nombre_perio}",
        )
