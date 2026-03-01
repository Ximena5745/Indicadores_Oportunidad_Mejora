"""
pages/5_Reporte_Seguimiento.py — Indicadores con Reporte de Seguimiento.

Fuente: data/raw/Seguimiento_Reporte.xlsx (generado por generar_reporte.py).
Solo muestra indicadores con Revisar == 1 (indicador único/primero).
Página autocontenida: no depende de funciones externas de data_loader.

Mapeo de procesos:
  "Proceso" en LMI/Seguimiento == "Subproceso" en Subproceso-Proceso-Area.xlsx
  El archivo de mapeo agrega: Proceso (padre) y Unidad (Área).
"""
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.charts import exportar_excel

# ── Rutas ─────────────────────────────────────────────────────────────────────
_DATA_RAW   = Path(__file__).parent.parent / "data" / "raw"
_RUTA_XLSX  = _DATA_RAW / "Seguimiento_Reporte.xlsx"
_RUTA_MAPA  = _DATA_RAW / "Subproceso-Proceso-Area.xlsx"
_CORTE      = datetime(2024, 1, 1)

# ── Paleta corporativa ────────────────────────────────────────────────────────
CORP = {
    "reportado":  "#A6CE38",
    "pendiente":  "#EC0677",
    "primario":   "#0F385A",
    "secundario": "#1FB2DE",
    "acento":     "#42F2F2",
    "alerta":     "#FBAF17",
}

# ── Colores de celda ──────────────────────────────────────────────────────────
COLOR_ESTADO    = {"Reportado": "#EDF7D6", "Pendiente de reporte": "#FDE8F3"}
COLOR_REPORTADO = {"Si": "#EDF7D6", "Sí": "#EDF7D6", "No": "#FDE8F3"}

# ── Columnas descriptivas ─────────────────────────────────────────────────────
# Tabla consolidada: Estado y Reportado después de Id e Indicador
COLS_DESC_CON = ["Id", "Indicador", "Estado del indicador", "Reportado",
                 "Unidad", "Proceso", "Subproceso", "Tipo", "Sentido", "Periodicidad"]

# Tabla de periodicidad: Estado y Reportado al final
COLS_DESC = ["Id", "Indicador", "Unidad", "Proceso", "Subproceso", "Tipo", "Sentido",
             "Periodicidad", "Estado del indicador", "Reportado"]


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


def _aplicar_filtros_tabla(df: pd.DataFrame, txt_id: str, txt_nombre: str,
                           sel_proc: str, sel_sub: str, sel_estado: str) -> pd.DataFrame:
    """Aplica los 5 filtros estándar sobre df."""
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


def _filtros_cascada(df: pd.DataFrame, prefix: str):
    """
    Renderiza filtros: ID (texto), Nombre (texto), Proceso (dropdown),
    Subproceso (dropdown dinámico según Proceso), Estado (dropdown).
    Retorna (txt_id, txt_nom, sel_proc, sel_sub, sel_estado).
    """
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
            # Subproceso filtrado según Proceso seleccionado
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


# ── Carga de mapeo Subproceso → Proceso → Unidad ─────────────────────────────

@st.cache_data(ttl=600, show_spinner=False)
def _cargar_mapa_procesos() -> pd.DataFrame:
    """
    Retorna DataFrame con columnas: Subproceso, Proceso, Unidad.
    La columna 'Subproceso' del mapeo = la columna 'Proceso' de LMI/Seguimiento.
    """
    if not _RUTA_MAPA.exists():
        return pd.DataFrame()
    df = pd.read_excel(str(_RUTA_MAPA), engine="openpyxl")
    df.columns = [str(c).strip() for c in df.columns]
    # Detectar columnas por contenido (tolera problemas de encoding en el nombre)
    col_sub  = next((c for c in df.columns if c.lower() == "subproceso"), None)
    col_proc = next((c for c in df.columns if c.lower() == "proceso"), None)
    col_area = next((c for c in df.columns if "rea" in c.lower()), None)  # Área / Area
    if not col_sub or not col_proc:
        return pd.DataFrame()
    rename = {col_sub: "Subproceso", col_proc: "Proceso"}
    if col_area:
        rename[col_area] = "Unidad"
    df = df.rename(columns=rename)
    cols_keep = [c for c in ["Subproceso", "Proceso", "Unidad"] if c in df.columns]
    return (df[cols_keep]
            .dropna(subset=["Subproceso"])
            .drop_duplicates(subset=["Subproceso"])
            .reset_index(drop=True))


# ── Carga de datos (caché local, no depende de data_loader) ──────────────────

@st.cache_data(ttl=300, show_spinner="Cargando Seguimiento_Reporte.xlsx...")
def _cargar_datos() -> dict:
    """
    Retorna dict:
      consolidado   : DataFrame combinado de todas las periodicidades,
                      con Subproceso (original "Proceso"), Proceso y Unidad del mapeo.
      resumen       : DataFrame hoja Resumen
      periodicidades: list de dict {nombre, df, cols_periodo}
    """
    if not _RUTA_XLSX.exists():
        return {}

    xl    = pd.ExcelFile(str(_RUTA_XLSX), engine="openpyxl")
    hojas = xl.sheet_names
    out   = {"consolidado": pd.DataFrame(), "resumen": pd.DataFrame(), "periodicidades": []}

    mapa = _cargar_mapa_procesos()   # Subproceso → Proceso, Unidad

    COLS_MANTENER = ["Id", "Indicador", "Unidad", "Proceso", "Subproceso",
                     "Tipo", "Sentido", "Periodicidad",
                     "Estado del indicador", "Reportado", "Revisar"]

    if "Resumen" in hojas:
        df = xl.parse("Resumen")
        df.columns = [str(c).strip() for c in df.columns]
        out["resumen"] = df

    trozos_consolidado = []
    for hoja in hojas:
        if hoja in ("Seguimiento", "Resumen"):
            continue

        df = xl.parse(hoja)
        df.columns = [str(c).strip() for c in df.columns]

        # Filtrar Revisar == 1 y deduplicar por Id
        if "Revisar" in df.columns:
            revisar = pd.to_numeric(df["Revisar"], errors="coerce").fillna(0)
            df = df[revisar == 1].copy()
        if "Id" in df.columns:
            df["Id"] = df["Id"].apply(_id_limpio)
            df = df.drop_duplicates(subset="Id", keep="first").reset_index(drop=True)

        # Renombrar "Proceso" → "Subproceso" (es el subproceso en el mapeo)
        if "Proceso" in df.columns:
            df = df.rename(columns={"Proceso": "Subproceso"})

        # Unir mapeo para obtener Proceso (padre) y Unidad
        if not mapa.empty and "Subproceso" in df.columns:
            df = df.merge(mapa, on="Subproceso", how="left")

        cols_p = _cols_periodo_desde_2024(df.columns)
        out["periodicidades"].append({"nombre": hoja, "df": df, "cols_periodo": cols_p})

        cols_desc = [c for c in COLS_MANTENER if c in df.columns]
        trozos_consolidado.append(df[cols_desc].copy())

    if trozos_consolidado:
        df_con = pd.concat(trozos_consolidado, ignore_index=True)
        if "Id" in df_con.columns:
            df_con = df_con.drop_duplicates(subset="Id", keep="first").reset_index(drop=True)
        out["consolidado"] = df_con

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

df_con = datos["consolidado"]
df_res = datos["resumen"]
perios = datos["periodicidades"]

if df_con.empty and not perios:
    st.error("No se encontraron hojas de periodicidad con indicadores (Revisar = 1).")
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
nombres_tabs = ["📋 Resumen", "📊 Consolidado"] + [f"📅 {p['nombre']}" for p in perios]
tabs = st.tabs(nombres_tabs)

# ─────────────────────────────────────────────────────────────────────────────
# TAB 0 — RESUMEN
# ─────────────────────────────────────────────────────────────────────────────
with tabs[0]:
    COL_ESTADO = "Estado del indicador"
    COL_REP    = "Reportado"

    total        = len(df_con)
    n_reportados = int((df_con[COL_ESTADO] == "Reportado").sum())            if COL_ESTADO in df_con.columns else 0
    n_pendientes = int((df_con[COL_ESTADO] == "Pendiente de reporte").sum()) if COL_ESTADO in df_con.columns else 0
    n_rep_hoy    = int((df_con[COL_REP].isin(["Sí", "Si"])).sum())           if COL_REP    in df_con.columns else 0
    pct_rep      = round(n_rep_hoy / total * 100, 1) if total else 0

    # ── KPIs ──────────────────────────────────────────────────────────────────
    st.markdown("### Vista Resumen")
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

    # ── Gráfica circular + Por Periodicidad ───────────────────────────────────
    if not df_res.empty:
        col_per = df_res.columns[0]
        col_rpt = next((c for c in df_res.columns if "reportad" in c.lower()), None)
        col_pen = next((c for c in df_res.columns if "pendiente" in c.lower()), None)

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
                    textinfo="label+percent",
                    textfont=dict(size=13),
                    hovertemplate="<b>%{label}</b><br>%{value} indicadores (%{percent})<extra></extra>",
                ))
                fig_pie.update_layout(
                    height=280, showlegend=False,
                    margin=dict(t=10, b=10, l=10, r=10),
                    paper_bgcolor="white",
                    annotations=[dict(
                        text=f"<b>{total}</b><br>total",
                        x=0.5, y=0.5, font_size=16, showarrow=False,
                    )],
                )
                st.plotly_chart(fig_pie, use_container_width=True)

        with gc2:
            st.markdown("#### Por Periodicidad")
            if col_rpt:
                fig_per = go.Figure()
                fig_per.add_trace(go.Bar(
                    x=df_res[col_per], y=df_res[col_rpt],
                    name="Reportados", marker_color=CORP["reportado"],
                    text=df_res[col_rpt], textposition="outside",
                ))
                if col_pen:
                    fig_per.add_trace(go.Bar(
                        x=df_res[col_per], y=df_res[col_pen],
                        name="Pendientes", marker_color=CORP["pendiente"],
                        text=df_res[col_pen], textposition="outside",
                    ))
                fig_per.update_layout(
                    barmode="group", height=280,
                    xaxis_title="Periodicidad", yaxis_title="Indicadores",
                    plot_bgcolor="white", paper_bgcolor="white",
                    legend=dict(orientation="h", y=-0.35),
                    margin=dict(t=15, b=80),
                )
                st.plotly_chart(fig_per, use_container_width=True)
        st.dataframe(df_res, use_container_width=True, hide_index=True)
        st.markdown("")

    # ── Por Unidad ────────────────────────────────────────────────────────────
    if "Unidad" in df_con.columns and COL_ESTADO in df_con.columns:
        st.markdown("#### Por Unidad")
        unidad_stats = (
            df_con.groupby("Unidad")[COL_ESTADO]
            .value_counts().unstack(fill_value=0).reset_index()
        )
        unidad_stats["_t"] = unidad_stats.drop(columns=["Unidad"]).sum(axis=1)
        unidad_stats = unidad_stats.sort_values("_t", ascending=False).drop(columns="_t")

        col_rep_u = "Reportado"            if "Reportado"            in unidad_stats.columns else None
        col_pen_u = "Pendiente de reporte" if "Pendiente de reporte" in unidad_stats.columns else None

        ug1, ug2 = st.columns([3, 2])
        with ug1:
            fig_uni = go.Figure()
            if col_rep_u:
                fig_uni.add_trace(go.Bar(
                    y=unidad_stats["Unidad"], x=unidad_stats[col_rep_u],
                    orientation="h", name="Reportado", marker_color=CORP["reportado"],
                    text=unidad_stats[col_rep_u], textposition="outside",
                ))
            if col_pen_u:
                fig_uni.add_trace(go.Bar(
                    y=unidad_stats["Unidad"], x=unidad_stats[col_pen_u],
                    orientation="h", name="Pendiente", marker_color=CORP["pendiente"],
                    text=unidad_stats[col_pen_u], textposition="outside",
                ))
            fig_uni.update_layout(
                barmode="stack",
                height=max(300, len(unidad_stats) * 38 + 60),
                xaxis_title="Indicadores", yaxis_title="",
                yaxis=dict(autorange="reversed"),
                plot_bgcolor="white", paper_bgcolor="white",
                legend=dict(orientation="h", y=-0.15),
                margin=dict(t=15, b=50, l=10, r=10),
            )
            st.plotly_chart(fig_uni, use_container_width=True)
        with ug2:
            total_uni = unidad_stats.drop(columns=["Unidad"]).sum(axis=1)
            df_uni_t = unidad_stats[["Unidad"]].copy()
            if col_rep_u:
                df_uni_t["Reportados"] = unidad_stats[col_rep_u]
                df_uni_t["% Reporte"]  = (unidad_stats[col_rep_u] / total_uni * 100).round(1).astype(str) + "%"
            df_uni_t["Total"] = total_uni
            st.dataframe(df_uni_t, use_container_width=True, hide_index=True)

        # ── Detalle de subprocesos al seleccionar una Unidad ──────────────────
        opts_unidad = [""] + unidad_stats["Unidad"].tolist()
        sel_uni_det = st.selectbox(
            "Ver subprocesos de la Unidad:",
            opts_unidad,
            key="res_uni_det",
            format_func=lambda x: "— Seleccionar —" if x == "" else x,
        )
        if sel_uni_det:
            df_sub_uni = df_con[df_con["Unidad"] == sel_uni_det]
            if not df_sub_uni.empty and "Proceso" in df_sub_uni.columns and COL_ESTADO in df_sub_uni.columns:
                proc_sub = (
                    df_sub_uni.groupby(["Proceso", "Subproceso"] if "Subproceso" in df_sub_uni.columns else ["Proceso"])[COL_ESTADO]
                    .value_counts().unstack(fill_value=0).reset_index()
                )
                cols_show = ["Proceso"] + (["Subproceso"] if "Subproceso" in proc_sub.columns else [])
                for est in ["Reportado", "Pendiente de reporte"]:
                    if est in proc_sub.columns:
                        cols_show.append(est)
                st.dataframe(proc_sub[cols_show], use_container_width=True, hide_index=True)

        st.markdown("")

    # ── Por Proceso (padre, del mapeo) ────────────────────────────────────────
    col_proc_res = "Proceso" if "Proceso" in df_con.columns else None
    if col_proc_res and COL_ESTADO in df_con.columns:
        st.markdown("#### Por Proceso")
        proc_stats = (
            df_con.groupby(col_proc_res)[COL_ESTADO]
            .value_counts().unstack(fill_value=0).reset_index()
        )
        proc_stats["_t"] = proc_stats.drop(columns=[col_proc_res]).sum(axis=1)
        proc_stats = proc_stats.sort_values("_t", ascending=False).drop(columns="_t")

        col_rep_p = "Reportado"            if "Reportado"            in proc_stats.columns else None
        col_pen_p = "Pendiente de reporte" if "Pendiente de reporte" in proc_stats.columns else None

        cg1, cg2 = st.columns([3, 2])
        with cg1:
            fig_proc = go.Figure()
            if col_rep_p:
                fig_proc.add_trace(go.Bar(
                    y=proc_stats[col_proc_res], x=proc_stats[col_rep_p],
                    orientation="h", name="Reportado", marker_color=CORP["reportado"],
                    text=proc_stats[col_rep_p], textposition="outside",
                ))
            if col_pen_p:
                fig_proc.add_trace(go.Bar(
                    y=proc_stats[col_proc_res], x=proc_stats[col_pen_p],
                    orientation="h", name="Pendiente", marker_color=CORP["pendiente"],
                    text=proc_stats[col_pen_p], textposition="outside",
                ))
            fig_proc.update_layout(
                barmode="stack",
                height=max(300, len(proc_stats) * 35 + 60),
                xaxis_title="Indicadores", yaxis_title="",
                yaxis=dict(autorange="reversed"),
                plot_bgcolor="white", paper_bgcolor="white",
                legend=dict(orientation="h", y=-0.15),
                margin=dict(t=15, b=50, l=10, r=10),
            )
            st.plotly_chart(fig_proc, use_container_width=True)
        with cg2:
            total_proc = proc_stats.drop(columns=[col_proc_res]).sum(axis=1)
            df_pct = proc_stats[[col_proc_res]].copy()
            if col_rep_p:
                df_pct["Reportados"] = proc_stats[col_rep_p]
                df_pct["% Reporte"]  = (proc_stats[col_rep_p] / total_proc * 100).round(1).astype(str) + "%"
            df_pct["Total"] = total_proc
            st.dataframe(df_pct, use_container_width=True, hide_index=True)

        # ── Subprocesos del proceso seleccionado ──────────────────────────────
        if "Subproceso" in df_con.columns:
            opts_proc_det = [""] + proc_stats[col_proc_res].tolist()
            sel_proc_det = st.selectbox(
                "Ver subprocesos del Proceso:",
                opts_proc_det,
                key="res_proc_det",
                format_func=lambda x: "— Seleccionar —" if x == "" else x,
            )
            if sel_proc_det:
                df_sub_det = df_con[df_con[col_proc_res] == sel_proc_det]
                if not df_sub_det.empty and COL_ESTADO in df_sub_det.columns:
                    sub_det = (
                        df_sub_det.groupby("Subproceso")[COL_ESTADO]
                        .value_counts().unstack(fill_value=0).reset_index()
                    )
                    sub_det["Total"] = sub_det.drop(columns=["Subproceso"]).sum(axis=1)
                    if "Reportado" in sub_det.columns:
                        sub_det["% Reporte"] = (sub_det["Reportado"] / sub_det["Total"] * 100).round(1).astype(str) + "%"
                    st.dataframe(sub_det, use_container_width=True, hide_index=True)

    st.markdown("---")

    # ── 🚨 Ranking procesos sin reporte ───────────────────────────────────────
    if col_proc_res and COL_ESTADO in df_con.columns:
        df_pen = df_con[df_con[COL_ESTADO] == "Pendiente de reporte"]

        if not df_pen.empty:
            st.markdown("#### 🚨 Procesos con más indicadores sin reporte")
            ranking = (
                df_pen.groupby(col_proc_res).size()
                .reset_index(name="Sin reporte")
                .sort_values("Sin reporte", ascending=False)
            )
            tot_p   = df_con.groupby(col_proc_res).size().reset_index(name="Total")
            ranking = ranking.merge(tot_p, on=col_proc_res, how="left")
            ranking["% Sin reporte"] = (ranking["Sin reporte"] / ranking["Total"] * 100).round(1)

            cr1, cr2 = st.columns([3, 2])
            with cr1:
                fig_rank = go.Figure(go.Bar(
                    x=ranking["Sin reporte"],
                    y=ranking[col_proc_res],
                    orientation="h",
                    marker=dict(
                        color=ranking["% Sin reporte"],
                        colorscale=[
                            [0,   CORP["reportado"]],
                            [0.5, CORP["alerta"]],
                            [1,   CORP["pendiente"]],
                        ],
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
                df_rk = ranking.rename(columns={col_proc_res: "Proceso"}).copy()
                df_rk["% Sin reporte"] = df_rk["% Sin reporte"].astype(str) + "%"

                def _color_rank(row):
                    try:
                        pct = float(str(row["% Sin reporte"]).replace("%", ""))
                    except ValueError:
                        pct = 0
                    bg = "#FDE8F3" if pct >= 80 else "#FEF3D0" if pct >= 50 else "#EDF7D6"
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

# ─────────────────────────────────────────────────────────────────────────────
# TAB 1 — CONSOLIDADO
# ─────────────────────────────────────────────────────────────────────────────
with tabs[1]:
    COL_ESTADO = "Estado del indicador"

    st.markdown("### Tabla Consolidada")

    # Filtros con cascada Proceso → Subproceso
    f_id_con, f_nom_con, f_proc_con, f_sub_con, f_est_con = _filtros_cascada(df_con, "con")

    df_filtrado = _aplicar_filtros_tabla(df_con, f_id_con, f_nom_con,
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

        # Gráfico por Proceso (padre, ordenado descendente)
        col_proc_p = "Proceso" if "Proceso" in df_p.columns else None
        if col_proc_p and COL_E in df_p.columns:
            proc_p = (
                df_p.groupby(col_proc_p)[COL_E]
                .value_counts().unstack(fill_value=0).reset_index()
            )
            proc_p["_t"] = proc_p.drop(columns=[col_proc_p]).sum(axis=1)
            proc_p = proc_p.sort_values("_t", ascending=False).drop(columns="_t")

            fig_pg = go.Figure()
            for est, color in [("Reportado", CORP["reportado"]),
                                ("Pendiente de reporte", CORP["pendiente"])]:
                if est in proc_p.columns:
                    fig_pg.add_trace(go.Bar(
                        x=proc_p[col_proc_p], y=proc_p[est],
                        name=est, marker_color=color,
                        text=proc_p[est], textposition="outside",
                    ))
            fig_pg.update_layout(
                barmode="stack", height=280,
                xaxis=dict(title="Proceso", tickangle=-30,
                           categoryorder="array",
                           categoryarray=proc_p[col_proc_p].tolist()),
                yaxis_title="Indicadores",
                plot_bgcolor="white", paper_bgcolor="white",
                legend=dict(orientation="h", y=-0.35),
                margin=dict(t=10, b=80),
            )
            st.plotly_chart(fig_pg, use_container_width=True)

        st.markdown("---")
        st.markdown("#### Detalle de Indicadores")

        # Filtros con cascada Proceso → Subproceso
        f_id_p, f_nom_p, f_proc_p, f_sub_p, f_est_p = _filtros_cascada(df_p, f"p_{nombre_p}")

        df_p_fil = _aplicar_filtros_tabla(df_p, f_id_p, f_nom_p, f_proc_p, f_sub_p, f_est_p)
        st.caption(f"Mostrando **{len(df_p_fil)}** de **{len(df_p)}** indicadores")

        cols_desc_p   = [c for c in COLS_DESC if c in df_p_fil.columns and c not in (COL_E, COL_R)]
        cols_estado_p = [c for c in (COL_E, COL_R) if c in df_p_fil.columns]
        cols_finales  = cols_desc_p + cols_p + cols_estado_p
        seen = set()
        cols_finales = [c for c in cols_finales
                        if c in df_p_fil.columns and not (c in seen or seen.add(c))]

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
            proceso_i  = str(fila.get("Proceso", ""))
            subproc_i  = str(fila.get("Subproceso", ""))
            unidad_i   = str(fila.get("Unidad", ""))
            tipo_i     = str(fila.get("Tipo", ""))
            sentido_i  = str(fila.get("Sentido", ""))
            estado_i   = str(fila.get(COL_E, ""))
            badge_c    = COLOR_ESTADO.get(estado_i, "#9E9E9E")

            @st.dialog(f"{id_ind} — {nombre_ind[:60]}", width="large")
            def _panel_detalle():
                st.markdown(
                    f"**Unidad:** {unidad_i}  \n"
                    f"**Proceso:** {proceso_i}  \n"
                    f"**Subproceso:** {subproc_i}"
                )
                st.markdown(
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
                for fc in ["Id", "Indicador", "Unidad", "Proceso", "Subproceso",
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
