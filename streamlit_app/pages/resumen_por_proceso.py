import unicodedata
import pandas as pd
import streamlit as st
import plotly.express as px
from streamlit_app.components import KPIRow
from streamlit_app.services.data_service import DataService
from streamlit_app.components.filters import render_filters
from core.config import VICERRECTORIA_COLORS, COLORES
from components.charts import exportar_excel, panel_detalle_indicador

# Constantes y helpers replicados de Direccionamiento Estratégico
_PROCESOS_DIR = {
    "Planeación Estratégica",
    "Desempeño Institucional",
    "Gestión de Proyectos",
}
_IDS_EXCLUIR_PLAN = {
    "373", "390", "414", "415", "416", "417", "418", "420", "469", "470", "471"
}
_COLOR_PROC = {
    "Planeación Estratégica":  "#1A3A5C",
    "Desempeño Institucional": "#1565C0",
    "Gestión de Proyectos":    "#2E7D32",
}


def _ultimo_por_anio(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "Id" not in df.columns:
        return df
    col = "Fecha" if "Fecha" in df.columns else "Periodo"
    return (df.sort_values(col)
              .drop_duplicates(subset="Id", keep="last")
              .reset_index(drop=True))


def _kpis(df: pd.DataFrame):
    total = len(df)
    cats = {
        cat: {"n": int((df.get("Categoria") == cat).sum()) if "Categoria" in df.columns else 0}
        for cat in (globals().get("ORDEN_CATEGORIAS") or ["Peligro", "Alerta", "Cumplimiento", "Sobrecumplimiento", "Sin dato"]) 
    }
    for cat in cats:
        cats[cat]["pct"] = round(cats[cat]["n"] / total * 100, 1) if total else 0
    return total, cats


def _render_kpis(total: int, cats: dict):
    from core.config import COLORES as _COLORES
    definiciones = [
        ("Total",             total,                         _COLORES["primario"],          None),
        ("🔴 Peligro",        cats["Peligro"]["n"],        _COLORES["peligro"],           f'{cats["Peligro"]["pct"]}%'),
        ("🟡 Alerta",         cats["Alerta"]["n"],         _COLORES["alerta"],            f'{cats["Alerta"]["pct"]}%'),
        ("🟢 Cumplimiento",   cats["Cumplimiento"]["n"],   _COLORES["cumplimiento"],      f'{cats["Cumplimiento"]["pct"]}%'),
        ("🔵 Sobrecumpl.",    cats["Sobrecumplimiento"]["n"],_COLORES["sobrecumplimiento"], f'{cats["Sobrecumplimiento"]["pct"]}%'),
    ]
    cols = st.columns(len(definiciones))
    for col, (label, val, color, delta) in zip(cols, definiciones):
        with col:
            st.metric(label, val, delta=delta,
                      delta_color="off" if label == "Total" else
                      ("inverse" if "Peligro" in label or "Alerta" in label else "normal"))


def _tabla_display(df: pd.DataFrame) -> pd.DataFrame:
    cols = [c for c in ["Id", "Indicador", "Subproceso", "Periodo", "Meta", "Ejecucion", "Cumplimiento_norm", "Categoria", "Sentido"] if c in df.columns]
    df = df[cols].copy()
    if "Cumplimiento_norm" in df.columns:
        df["Cumplimiento_norm"] = (df["Cumplimiento_norm"] * 100).round(1).astype(str) + "%"
    return df.rename(columns={"Cumplimiento_norm": "Cumpl.%", "Ejecucion": "Ejecución"})


def _estilo_cat(row):
    from core.config import COLOR_CATEGORIA_CLARO
    bg = COLOR_CATEGORIA_CLARO.get(row.get("Categoria", ""), "")
    return [f"background-color:{bg}" if bg else "" for _ in row]


def _render_proceso(df_proc: pd.DataFrame, nombre: str, prefix: str, anio: int):
    if df_proc.empty:
        st.info(f"Sin indicadores para **{nombre}**.")
        return

    if "Anio" in df_proc.columns:
        df_anio = df_proc[df_proc["Anio"] == anio]
    else:
        df_anio = df_proc

    df_ult = _ultimo_por_anio(df_anio)

    if df_ult.empty:
        st.warning(f"Sin datos para **{nombre}** en {anio}.")
        return

    total, cats = _kpis(df_ult)
    _render_kpis(total, cats)

    st.markdown("---")

    st.caption(
        f"**{total}** indicadores · año **{anio}** · "
        "Haz clic en una fila para ver la ficha histórica completa."
    )
    df_show = _tabla_display(df_ult)

    col_cfg = {}
    if "Indicador" in df_show.columns: col_cfg["Indicador"] = st.column_config.TextColumn("Indicador", width="large")
    if "Cumpl.%"   in df_show.columns: col_cfg["Cumpl.%"]   = st.column_config.TextColumn("Cumpl.%",   width="small")
    if "Meta"      in df_show.columns: col_cfg["Meta"]      = st.column_config.NumberColumn("Meta",      format="%.2f")
    if "Ejecución" in df_show.columns: col_cfg["Ejecución"] = st.column_config.NumberColumn("Ejecución", format="%.2f")

    event = st.dataframe(
        df_show.style.apply(_estilo_cat, axis=1),
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key=f"tbl_{prefix}",
        column_config=col_cfg if col_cfg else None,
    )

    curr_rows = event.selection.get("rows", []) if (event and event.selection) else []
    prev_key  = f"_dir_prev_{prefix}"
    if curr_rows != st.session_state.get(prev_key, []):
        st.session_state[prev_key] = curr_rows
        if curr_rows:
            idx = curr_rows[0]
            st.session_state["_dir_ficha_id"]  = str(df_ult.iloc[idx]["Id"])
            st.session_state["_dir_ficha_nom"] = str(df_ult.iloc[idx].get("Indicador", ""))

    st.download_button(
        "📥 Exportar",
        data=exportar_excel(df_show, nombre[:31]),
        file_name=f"{prefix}_{anio}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key=f"exp_{prefix}",
    )


# Meses en español para selección
MESES_OPCIONES = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
]

@st.cache_data(ttl=300, show_spinner=False)
def _obtener_anios_disponibles(df: pd.DataFrame) -> list:
    """Retorna lista de años disponibles en el dataset."""
    if df.empty or "Año" not in df.columns:
        return []
    anios = sorted(df["Año"].dropna().unique().tolist())
    return [int(a) for a in anios if not pd.isna(a)]


def _obtener_periodo_default(df: pd.DataFrame):
    if df.empty or "Año" not in df.columns or "Mes" not in df.columns:
        return None, None

    periodos = df[["Año", "Mes"]].dropna().copy()
    if periodos.empty:
        return None, None

    periodos["Año"] = pd.to_numeric(periodos["Año"], errors="coerce")
    periodos["Mes"] = pd.to_numeric(periodos["Mes"], errors="coerce")
    periodos = periodos.dropna().astype(int)
    if periodos.empty:
        return None, None

    ultimo = periodos.sort_values(["Año", "Mes"]).iloc[-1]
    anio = int(ultimo["Año"])
    mes_idx = int(ultimo["Mes"])
    if mes_idx < 1 or mes_idx > len(MESES_OPCIONES):
        return anio, None
    return anio, MESES_OPCIONES[mes_idx - 1]

def _normalize_text(value):
# ... (el resto del archivo permanece igual)

    if value is None:
        return ""
    text = str(value).strip()
    text = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in text if not unicodedata.combining(ch)).upper()


def _indicator_modal(ind_name="Indicador ejemplo"):
    if st.button(f"Abrir detalle: {ind_name}", key=f"modal_btn_{ind_name}"):
        with st.modal("Detalle indicador"):
            st.header(ind_name)
            tabs = st.tabs(["IRIP", "DAD", "Coherencia", "Eficiencia OM"])
            with tabs[0]:
                st.write("Contenido IRIP (mock)")
            with tabs[1]:
                st.write("Contenido DAD (mock)")
            with tabs[2]:
                st.write("Contenido Coherencia (mock)")
            with tabs[3]:
                st.write("Contenido Eficiencia OM (mock)")


def _render_html_bars(counts, labels, color_map=None, max_value=None):
    html = ["<div class='html-bar-chart'>"]
    color_map = color_map or {}
    if max_value is None:
        max_value = max(counts.values()) if counts else 1
    for label in labels:
        value = int(counts.get(label, 0))
        width = int(max(3, min(100, (value / max_value * 100) if max_value else 5)))
        color = color_map.get(label, "#7d8be3")
        html.append(
            f"<div class='html-bar-item'>"
            f"<div class='bar-axis'>"
            f"<div class='bar-label'>{label}</div>"
            f"<div class='bar-track'><div class='bar-fill' style='width:{width}%;background:{color};'></div></div>"
            f"</div>"
            f"<div class='bar-value'>{value}</div>"
            f"</div>"
        )
    html.append("</div>")
    return "".join(html)


def render():
    st.title("Resumen por procesos")
    st.write("Seleccione un proceso para ver detalle. Esta vista contiene 6 tabs por proceso.")

    ds = DataService()
    df = ds.get_tracking_data()
    map_df = ds.get_process_map()

    if map_df.empty:
        st.warning(
            "No se encontró la fuente de mapeo `Subproceso-Proceso-Area.xlsx` en `data/raw`. "
            "Revisa que el archivo exista y contenga la hoja 'Proceso'."
        )

    elif df.empty:
        st.warning(
            "No se encontró la fuente de datos `Tracking Mensual` en `data/output/Seguimiento_Reporte.xlsx`. "
            "Revisa que el archivo exista y la hoja `Tracking Mensual` esté disponible."
        )

    map_df = map_df.rename(columns={
        c: c.strip() for c in map_df.columns
    })
    if "Unidad" not in map_df.columns or "Proceso" not in map_df.columns or "Subproceso" not in map_df.columns:
        st.error("La hoja 'Proceso' del archivo de mapeo no contiene las columnas esperadas: Unidad, Proceso, Subproceso.")
        return

    map_df = map_df.dropna(subset=["Proceso"]).reset_index(drop=True)
    map_df["Tipo de proceso"] = map_df.get("Tipo de proceso", "").astype(str)

    # Obtener años disponibles
    anios_disponibles = _obtener_anios_disponibles(df)
    anio_default, mes_default = _obtener_periodo_default(df)

    with st.expander("🔎 Filtros", expanded=False):
        _rp_keys = [
            "resumen_proceso_anio", "resumen_proceso_mes", "resumen_proceso_tipo_proceso",
            "resumen_proceso_unidad", "resumen_proceso_proceso", "resumen_proceso_subproceso",
        ]
        if st.button("Limpiar filtros", key="resumen_proceso_clear"):
            for _k in _rp_keys:
                if _k in st.session_state:
                    del st.session_state[_k]
            st.rerun()

        filter_config = {
            "anio": {
                "label": "Año",
                "options": anios_disponibles,
                "include_all": False,
                "default": anio_default or (anios_disponibles[-1] if anios_disponibles else None),
            },
            "mes": {
                "label": "Mes",
                "options": MESES_OPCIONES,
                "include_all": False,
                "default": mes_default or "Diciembre",
            },
            "tipo_proceso": {"label": "Tipo de proceso", "options": sorted(map_df["Tipo de proceso"].dropna().unique().tolist())},
            "unidad": {"label": "Unidad", "options": sorted(map_df["Unidad"].dropna().unique().tolist())},
            "proceso": {"label": "Proceso", "options": sorted(map_df["Proceso"].dropna().unique().tolist())},
            "subproceso": {"label": "Subproceso", "options": sorted(map_df["Subproceso"].dropna().unique().tolist())}
        }

        selections = render_filters(
            df if not df.empty else map_df,
            filter_config,
            key_prefix="resumen_proceso",
            columns_per_row=3,
        )

        anio = selections.get("anio")
        mes = selections.get("mes")
        tipo_proceso = selections.get("tipo_proceso", "Todos")
        unidad = selections.get("unidad", "Todos")
        proceso = selections.get("proceso", "Todos")
        subproceso = selections.get("subproceso", "Todos")

    _activos = []
    if anio:
        _activos.append(f"Año: {anio}")
    if mes:
        _activos.append(f"Mes: {mes}")
    if tipo_proceso != "Todos":
        _activos.append(f"Tipo: {tipo_proceso}")
    if unidad != "Todos":
        _activos.append(f"Unidad: {unidad}")
    if proceso != "Todos":
        _activos.append(f"Proceso: {proceso}")
    if subproceso != "Todos":
        _activos.append(f"Subproceso: {subproceso}")
    if _activos:
        st.caption("Filtros activos: " + " · ".join(_activos))

    if df.empty:
        proc_df = pd.DataFrame()
    else:
        proc_df = df.copy()
        
        # Filtrar por fecha si se seleccionaron año y mes
        if anio and mes:
            mes_num = MESES_OPCIONES.index(mes) + 1
            if "Año" in proc_df.columns and "Mes" in proc_df.columns:
                proc_df = proc_df[(proc_df["Año"] == anio) & (proc_df["Mes"] == mes_num)]
        
        if "Proceso" in map_df.columns:
            proc_df = proc_df.merge(
                map_df[["Unidad", "Proceso", "Subproceso", "Tipo de proceso"]],
                on="Proceso",
                how="left",
            )

        if tipo_proceso != "Todos" and "Tipo de proceso" in proc_df.columns:
            proc_df = proc_df[proc_df["Tipo de proceso"] == tipo_proceso]
        if unidad != "Todos" and "Unidad" in proc_df.columns:
            proc_df = proc_df[proc_df["Unidad"] == unidad]
        if proceso != "Todos":
            proc_df = proc_df[proc_df["Proceso"] == proceso]
        if subproceso != "Todos" and "Subproceso" in proc_df.columns:
            proc_df = proc_df[proc_df["Subproceso"] == subproceso]

    selected_process = (
        proceso
        if proceso != "Todos"
        else subproceso
        if subproceso != "Todos"
        else unidad
        if unidad != "Todos"
        else "Todos los procesos"
    )

    periodo_info = f"{mes} {anio}" if anio and mes else "Período no definido"

    tabs = st.tabs(["📋 Resumen General", "ℹ️ Información por proceso", "📊 Indicadores", "📋 Resumen", "✅ Calidad", "🔍 Auditoría", "💡 Propuestos", "🤖 Análisis IA"])

    # ---------- Tab 0: Resumen General
    with tabs[0]:
        st.markdown(f"### Resumen general — {selected_process}")
        st.caption(f"Corte consultado: {periodo_info}")
        if proc_df.empty:
            st.info("No hay datos disponibles para el período seleccionado.")
        else:
            # Métricas generales
            total = len(proc_df)
            reportado = int((proc_df.get("Estado") == "Reportado").sum()) if "Estado" in proc_df.columns else 0
            pendiente = int((proc_df.get("Estado") == "Pendiente").sum()) if "Estado" in proc_df.columns else 0
            no_aplica = int((proc_df.get("Estado") == "No aplica").sum()) if "Estado" in proc_df.columns else 0

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total indicadores", total)
            c2.metric("Reportados", reportado, delta=f"{round(reportado/total*100,1)}%" if total else None)
            c3.metric("Pendientes", pendiente, delta=f"{round(pendiente/total*100,1)}%" if total else None)
            c4.metric("No aplica", no_aplica)

            # Pie: distribución por Estado (si existe)
            if "Estado" in proc_df.columns:
                estado_counts = proc_df["Estado"].value_counts().reset_index()
                estado_counts.columns = ["Estado", "count"]
                fig_pie = px.pie(estado_counts, names="Estado", values="count", title="Distribución por Estado")
                st.plotly_chart(fig_pie, use_container_width=True)

            # Barra: top Unidades por cantidad de reportados (colores por vicerrectoría)
            if "Unidad" in proc_df.columns:
                unidad_counts = proc_df[proc_df.get("Estado") == "Reportado"].groupby("Unidad")["Id"].nunique().reset_index(name="reportados") if "Id" in proc_df.columns else proc_df[proc_df.get("Estado") == "Reportado"].groupby("Unidad").size().reset_index(name="reportados")
                unidad_counts = unidad_counts.sort_values("reportados", ascending=False)
                if not unidad_counts.empty:
                    # Construir mapa de colores: usar mapeo fijo y una paleta para los restantes
                    # Paleta institucional como fallback
                    palette = [
                        COLORES.get("primario"),
                        COLORES.get("secundario"),
                        COLORES.get("cumplimiento"),
                        COLORES.get("alerta"),
                        COLORES.get("peligro"),
                        COLORES.get("sin_dato"),
                    ]
                    unique_unidades = unidad_counts["Unidad"].tolist()
                    color_map = {}
                    idx = 0
                    for u in unique_unidades:
                        if u in VICERRECTORIA_COLORS:
                            color_map[u] = VICERRECTORIA_COLORS[u]
                        else:
                            color_map[u] = palette[idx % len(palette)] or "#7d8be3"
                            idx += 1

                    fig_un = px.bar(
                        unidad_counts,
                        x="reportados",
                        y="Unidad",
                        orientation="h",
                        title="Reportados por Unidad",
                        color="Unidad",
                        color_discrete_map=color_map,
                    )
                    st.plotly_chart(fig_un, use_container_width=True)

            # Barra: top Procesos por reportados
            if "Proceso" in proc_df.columns:
                proc_counts = proc_df[proc_df.get("Estado") == "Reportado"].groupby("Proceso")["Id"].nunique().reset_index(name="reportados") if "Id" in proc_df.columns else proc_df[proc_df.get("Estado") == "Reportado"].groupby("Proceso").size().reset_index(name="reportados")
                proc_counts = proc_counts.sort_values("reportados", ascending=False).head(25)
                if not proc_counts.empty:
                    fig_proc = px.bar(proc_counts, x="reportados", y="Proceso", orientation="h", title="Top procesos por reportados")
                    st.plotly_chart(fig_proc, use_container_width=True)

            # Cumplimiento: si existe columna Cumplimiento o Nivel, mostrar distribución
            if "Cumplimiento" in proc_df.columns or "Nivel de cumplimiento" in proc_df.columns:
                if "Nivel de cumplimiento" in proc_df.columns:
                    niv_counts = proc_df["Nivel de cumplimiento"].value_counts().reset_index()
                    niv_counts.columns = ["Nivel", "count"]
                    fig_niv = px.bar(niv_counts, x="Nivel", y="count", title="Distribución por Nivel de cumplimiento")
                    st.plotly_chart(fig_niv, use_container_width=True)
                else:
                    # Cumplimiento numérico: mostrar histograma
                    fig_c = px.histogram(proc_df, x="Cumplimiento", nbins=20, title="Histograma de Cumplimiento")
                    st.plotly_chart(fig_c, use_container_width=True)

    # ---------- Tab 1: Información por proceso (replica Direccionamiento Estratégico)
    with tabs[1]:
        st.markdown("# 🏛️ Direccionamiento Estratégico — Información por proceso")

        # Usar el dataset completo como fuente para Direccionamiento
        df_raw = df.copy() if not df.empty else pd.DataFrame()

        if df_raw.empty:
            st.error("No se encontró el dataset principal. Ejecuta primero `actualizar_consolidado.py`.")
        elif "Proceso" not in df_raw.columns:
            st.error("El dataset no contiene la columna 'Proceso'.")
        else:
            df_dir = df_raw[df_raw["Proceso"].isin(_PROCESOS_DIR)].copy()
            if df_dir.empty:
                st.error("No se encontraron indicadores para los procesos de Direccionamiento Estratégico.")
            else:
                # Excluir IDs en Planeación Estratégica
                mask_excl = (df_dir["Proceso"] == "Planeación Estratégica") & df_dir["Id"].astype(str).isin(_IDS_EXCLUIR_PLAN)
                df_dir = df_dir[~mask_excl].copy()

                df_plan   = df_dir[df_dir["Proceso"] == "Planeación Estratégica"].copy()
                df_desemp = df_dir[df_dir["Proceso"] == "Desempeño Institucional"].copy()
                df_gest   = df_dir[df_dir["Proceso"] == "Gestión de Proyectos"].copy()

                # Selector de año (por defecto 2025 si existe)
                anios_disp = sorted([int(a) for a in df_dir["Anio"].dropna().unique()]) if "Anio" in df_dir.columns else [2025]
                anio_def   = 2025 if 2025 in anios_disp else (anios_disp[-1] if anios_disp else 2025)
                anio_sel   = st.selectbox("Año", anios_disp, index=anios_disp.index(anio_def) if anios_disp else 0, key="dir_anio_proc")

                st.markdown("---")
                tab_plan, tab_desemp, tab_gest = st.tabs([
                    "📋 Planeación Estratégica",
                    "📊 Desempeño Institucional",
                    "🗂️ Gestión de Proyectos",
                ])

                with tab_plan:
                    _render_proceso(df_plan, "Planeación Estratégica", "plan", anio_sel)

                with tab_desemp:
                    _render_proceso(df_desemp, "Desempeño Institucional", "desemp", anio_sel)

                with tab_gest:
                    _render_proceso(df_gest, "Gestión de Proyectos", "gest", anio_sel)

    # ── Diálogo de ficha histórica (único, fuera de tabs) ───────────────────────
    id_ficha = st.session_state.get("_dir_ficha_id")
    if id_ficha:
        nom_ficha = st.session_state.get("_dir_ficha_nom", "")
        df_hist   = df[df["Id"].astype(str) == id_ficha].copy() if not df.empty else pd.DataFrame()

        @st.dialog(f"📊 {id_ficha} — {nom_ficha[:65]}", width="large")
        def _ficha():
            if st.button("✖ Cerrar"):
                st.session_state["_dir_ficha_id"] = None
                st.rerun()
            panel_detalle_indicador(df_hist, id_ficha, df)

        _ficha()

    with tabs[3]:
        st.markdown(f"### Calidad — {selected_process}")
        st.write("Métrica de calidad basada en el estado de reporte para el proceso seleccionado.")

    with tabs[4]:
        st.markdown(f"### Auditoría — {selected_process}")
        st.write("Los datos están filtrados por proceso y listos para análisis de auditoría.")

    with tabs[5]:
        st.markdown(f"### Propuestos — {selected_process}")
        st.write("Indicadores propuestos y notas relacionadas con el proceso seleccionado.")

    with tabs[6]:
        st.markdown(f"### Análisis IA — {selected_process}")
        st.write("Análisis IA (mock) para el proceso seleccionado.")

    # ---------- Tab 2: Información por proceso (detalle por indicador)
    with tabs[2]:
        st.markdown(f"### Información por proceso — {selected_process}")
        st.caption(f"Corte consultado: {periodo_info}")
        if proc_df.empty:
            st.info("No hay datos disponibles para el proceso seleccionado.")
        else:
            df_for_table = proc_df.copy()
            # Tomar último registro por indicador (por Fecha o Periodo si existe)
            if "Fecha" in df_for_table.columns:
                col_fecha = "Fecha"
            elif "Periodo" in df_for_table.columns:
                col_fecha = "Periodo"
            else:
                col_fecha = None

            if col_fecha:
                df_last = df_for_table.sort_values(col_fecha).drop_duplicates(subset="Id", keep="last")
            else:
                df_last = df_for_table.drop_duplicates(subset="Id", keep="last")

            cols_display = [c for c in ["Id", "Indicador", "Proceso", "Subproceso", "Periodo", "Meta", "Ejecucion", "Cumplimiento_norm", "Categoria"] if c in df_last.columns]
            df_show = df_last[cols_display].copy()
            if "Cumplimiento_norm" in df_show.columns:
                df_show["Cumplimiento_norm"] = (df_show["Cumplimiento_norm"] * 100).round(1).astype(str) + "%"
                df_show = df_show.rename(columns={"Cumplimiento_norm": "Cumpl.%", "Ejecucion": "Ejecución"})

            event = st.dataframe(
                df_show,
                use_container_width=True,
                hide_index=True,
                on_select="rerun",
                selection_mode="single-row",
                key="info_proc_tbl",
            )

            curr_rows = event.selection.get("rows", []) if (event and event.selection) else []
            prev_key = "_info_prev"
            if curr_rows != st.session_state.get(prev_key, []):
                st.session_state[prev_key] = curr_rows
                if curr_rows:
                    idx = curr_rows[0]
                    st.session_state["_info_ficha_id"] = str(df_show.iloc[idx]["Id"])
                    st.session_state["_info_ficha_nom"] = str(df_show.iloc[idx].get("Indicador", ""))

            id_ficha = st.session_state.get("_info_ficha_id")
            if id_ficha:
                nom_ficha = st.session_state.get("_info_ficha_nom", "")
                df_hist = proc_df[proc_df["Id"].astype(str) == id_ficha].copy()

                @st.dialog(f"📊 {id_ficha} — {nom_ficha[:65]}", width="large")
                def _ficha():
                    if st.button("✖ Cerrar"):
                        st.session_state["_info_ficha_id"] = None
                        st.rerun()
                    panel_detalle_indicador(df_hist, id_ficha, proc_df)

                _ficha()
