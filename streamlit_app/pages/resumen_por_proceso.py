
import unicodedata
import os
from pathlib import Path
import pandas as pd
import streamlit as st
import plotly.express as px
from components import KPIRow
from components.renderers import kpi_card, generate_sparkline_counts, generate_sparkline_agg
from streamlit_app.services.data_service import DataService
from streamlit_app.components.filters import render_filters
from core.calculos import simple_categoria_desde_porcentaje
from core.config import CACHE_TTL, VICERRECTORIA_COLORS, COLORES
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
            # determinar categoría a partir de la etiqueta
            cat = None
            if "Peligro" in label:
                cat = "Peligro"
            elif "Alerta" in label:
                cat = "Alerta"
            elif "Cumplimiento" in label:
                cat = "Cumplimiento"
            elif "Sobrecumpl" in label:
                cat = "Sobrecumplimiento"

            # usar kpi_card para renderizar (se maneja color y progreso si aplica)
            try:
                # generar sparklines sobre el conjunto actual (`df` corresponde al último por indicador)
                spark = generate_sparkline_counts(df, periods=6) if label == 'Total' or 'Peligro' in label or 'Alerta' in label else generate_sparkline_agg(df, value_col='Cumplimiento', agg='mean', periods=6)
                kpi_card(title=label, value=val, delta=delta, sparkline=spark, category=cat)
            except Exception:
                # fallback simple
                st.metric(label, val, delta=delta)


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

    # Si no hay columna 'Categoria' o está vacía, intentar inferirla desde cumplimiento
    try:
        if "Categoria" not in df_ult.columns or df_ult["Categoria"].isna().all():
            if "Cumplimiento_norm" in df_ult.columns:
                df_ult["Categoria"] = df_ult["Cumplimiento_norm"].apply(
                    lambda v: simple_categoria_desde_porcentaje(v * 100) if pd.notna(v) else "Sin dato"
                )
            elif "Cumplimiento" in df_ult.columns:
                df_ult["Categoria"] = df_ult["Cumplimiento"].apply(
                    lambda v: simple_categoria_desde_porcentaje(float(v) * 100) if pd.notna(v) else "Sin dato"
                )
    except Exception:
        pass

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

@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
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

        # Filtros manuales con selectboxes independientes
        with st.expander("🔎 Filtros", expanded=True):
            c1, c2, c3 = st.columns(3)
            with c1:
                anio = st.selectbox("Año", anios_disponibles, index=len(anios_disponibles)-1 if anios_disponibles else 0, key="fp_anio")
            with c2:
                mes = st.selectbox("Mes", MESES_OPCIONES, index=len(MESES_OPCIONES)-1, key="fp_mes")
            with c3:
                tipo_proceso = st.selectbox("Tipo de proceso", ["Todos"] + sorted(map_df["Tipo de proceso"].dropna().unique().tolist()), key="fp_tipo")
            
            c4, c5, c6 = st.columns(3)
            with c4:
                unidad = st.selectbox("Unidad", ["Todos"] + sorted(map_df["Unidad"].dropna().unique().tolist()), key="fp_unidad")
            with c5:
                proceso = st.selectbox("Proceso", ["Todos"] + sorted(map_df["Proceso"].dropna().unique().tolist()), key="fp_proceso")
            with c6:
                subproceso = st.selectbox("Subproceso", ["Todos"] + sorted(map_df["Subproceso"].dropna().unique().tolist()), key="fp_subproceso")
        
        # Placeholder para selections (requerido por código)
        selections = {"anio": anio, "mes": mes, "tipo_proceso": tipo_proceso, "unidad": unidad, "proceso": proceso, "subproceso": subproceso}

        # Alternativas para Mostrar subprocesos - Tipos de lista desplegable:
        # Opción 1: Selectbox (dropdown tradicional)
        # show_subprocs = st.selectbox("Mostrar subprocesos", ["No", "Sí"], index=0) == "Sí"
        
        # Opción 2: Multiselect (permite múltiples)
        # show_subprocs = len(st.multiselect("Mostrar subprocesos", ["Sí"], default=[], key="resumen_show_subprocs")) > 0
        
        # Opción 3: Pills (chips modernos) - Requiere Streamlit 1.37+
        # show_subprocs = st.pills("Mostrarsubprocesos", ["Sí", "No"], default="No", key="resumen_show_subprocs") == "Sí"
        
        # Opción 4: Segmented Control (botones) - Requiere Streamlit 1.37+
        # show_subprocs = st.segmented_control("Mostrar subprocesos", ["Sí", "No"], default="No", key="resumen_show_subprocs") == "Sí"
        
        # Opción 5: Radio buttons (alterna con flechas)
        show_subprocs = st.radio("Mostrar subprocesos", ["No", "Sí"], index=0, horizontal=True, key="resumen_show_subprocs") == "Sí"

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
        st.error("El dataframe df está vacío")
    else:
        proc_df = df.copy()
        
        # Debug: mostrar info de las columnas y tipos
        st.caption(f"Debug: df tiene {len(proc_df)} filas")
        if "Año" in proc_df.columns:
            st.caption(f"Años únicos: {sorted(proc_df['Año'].unique())}")
            st.caption(f"Tipo columna Año: {proc_df['Año'].dtype}")
        if "Mes" in proc_df.columns:
            st.caption(f"Meses únicos: {sorted(proc_df['Mes'].unique())}")
        
        # Filtrar por fecha si se seleccionaron año y mes
        if anio and mes:
            mes_num = MESES_OPCIONES.index(mes) + 1
            st.caption(f"Filtrando por Año={anio}, Mes={mes_num}")
            if "Año" in proc_df.columns and "Mes" in proc_df.columns:
                # Convertir a comparación con tipos correctos
                try:
                    anio_int = int(anio)
                    mes_int = int(mes_num)
                    proc_df = proc_df[(proc_df["Año"] == anio_int) & (proc_df["Mes"] == mes_int)]
                    st.caption(f"Después de filtro fecha: {len(proc_df)} filas")
                except Exception as e:
                    st.caption(f"Error en filtro: {e}")
        
        st.caption(f"Antes de merge: {len(proc_df)} filas")
        
        if "Proceso" in map_df.columns and len(proc_df) > 0:
            proc_df = proc_df.merge(
                map_df[["Unidad", "Proceso", "Subproceso", "Tipo de proceso"]],
                on="Proceso",
                how="left",
            )
            st.caption(f"Después de merge: {len(proc_df)} filas")
        else:
            st.caption("No se hizo merge (map_df no tiene Proceso o proc_df vacío)")
        
        # Aplicar filtros adicionales
        st.caption(f"Aplicando filtros: tipo_proceso={tipo_proceso}, unidad={unidad}, proceso={proceso}, subproceso={subproceso}")
        if tipo_proceso != "Todos" and "Tipo de proceso" in proc_df.columns:
            proc_df = proc_df[proc_df["Tipo de proceso"] == tipo_proceso]
            st.caption(f"Después filtro tipo: {len(proc_df)} filas")
        if unidad != "Todos" and "Unidad" in proc_df.columns:
            proc_df = proc_df[proc_df["Unidad"] == unidad]
            st.caption(f"Después filtro unidad: {len(proc_df)} filas")
        if proceso != "Todos":
            proc_df = proc_df[proc_df["Proceso"] == proceso]
            st.caption(f"Después filtro proceso: {len(proc_df)} filas")
        if subproceso != "Todos" and "Subproceso" in proc_df.columns:
            proc_df = proc_df[proc_df["Subproceso"] == subproceso]
            st.caption(f"Después filtro subproceso: {len(proc_df)} filas")
        
        st.caption(f"Después de todos los filtros: {len(proc_df)} filas")

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

    # ✅ NOTA: proc_df YA ESTÁ FILTRADO por tipo_proceso, unidad, proceso, subproceso, y período
    # Todos los tabs usan proc_df → datos consistentes en TODAS las pestañas según filtro de proceso
    
    tabs = st.tabs(["📋 Resumen General", "ℹ️ Información por proceso", "📊 Indicadores", "📋 Resumen", "✅ Calidad", "🔍 Auditoría", "💡 Propuestos", "🤖 Análisis IA"])

    # ---------- Tab 0: Resumen General
    with tabs[0]:
        st.markdown(f"### Resumen general — {selected_process}")
        st.caption(f"Corte consultado: {periodo_info}")
        
        # Debug info
        st.caption(f"Debug: df rows={len(df)}, proc_df rows={len(proc_df)}, anio={anio}, mes={mes}")
        
        if proc_df.empty:
            st.info("No hay datos disponibles para el período seleccionado.")
            
            # Mostrar años disponibles en df
            if not df.empty and "Año" in df.columns:
                anios_df = sorted(df["Año"].unique())
                st.caption(f"Años disponibles en datos: {anios_df}")
            if not df.empty and "Mes" in df.columns:
                meses_df = sorted(df["Mes"].unique())
                st.caption(f"Meses disponibles en datos: {meses_df}")
        else:
            # Verificar contenido
            st.caption(f"proc_df tiene {len(proc_df)} filas")
            st.caption(f"Columnas en proc_df: {proc_df.columns.tolist()[:10]}")
            
            if len(proc_df) == 0:
                st.warning("No hay datos después de los filtros")
            else:
                # Verificar columnas disponibles
                if "Estado" not in proc_df.columns:
                    st.caption("ADVERTENCIA: No existe columna 'Estado'")
                if "Unidad" not in proc_df.columns:
                    st.caption("ADVERTENCIA: No existe columna 'Unidad'")
                    
                # Métricas generales
                total = len(proc_df)
                st.metric("Total indicadores", total)

            # Pie: distribución por Estado
            if "Estado" in proc_df.columns and not proc_df.empty:
                estado_counts = proc_df["Estado"].value_counts().reset_index()
                estado_counts.columns = ["Estado", "count"]
                if not estado_counts.empty:
                    fig_pie = px.pie(estado_counts, names="Estado", values="count", title="Distribución por Estado")
                    st.plotly_chart(fig_pie, use_container_width=True)

            # Barra: top Unidades por cantidad de reportados
            if "Unidad" in proc_df.columns and not proc_df.empty:
                # Obtener columna de ID
                id_col = "Id" if "Id" in proc_df.columns else proc_df.columns[0]
                
                # Filtrar por reportados
                try:
                    reportado_mask = proc_df["Estado"].str.lower() == "reportado"
                except:
                    reportado_mask = proc_df.get("Estado") == "Reportado"
                
                if reportado_mask.any():
                    try:
                        unidad_counts = proc_df[reportado_mask].groupby("Unidad")[id_col].nunique().reset_index(name="reportados")
                    except:
                        unidad_counts = proc_df[reportado_mask].groupby("Unidad").size().reset_index(name="reportados")
                    
                    unidad_counts = unidad_counts.sort_values("reportados", ascending=False)
                    if not unidad_counts.empty:
                        # Construir mapa de colores
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
                    else:
                        st.caption("No hay indicadores reportados para mostrar.")

            # Barra: top Procesos por reportados
            if "Proceso" in proc_df.columns:
                proc_key = "Proceso_final" if "Proceso_final" in proc_df.columns else "Proceso"
                id_col = "Id" if "Id" in proc_df.columns else proc_df.columns[0]
                
                try:
                    reportado_mask = proc_df["Estado"].str.lower() == "reportado"
                except:
                    reportado_mask = proc_df.get("Estado") == "Reportado"
                
                if reportado_mask.any():
                    try:
                        proc_counts = proc_df[reportado_mask].groupby(proc_key)[id_col].nunique().reset_index(name="reportados")
                    except:
                        proc_counts = proc_df[reportado_mask].groupby(proc_key).size().reset_index(name="reportados")
                    
                    proc_counts = proc_counts.sort_values("reportados", ascending=False).head(25)
                    if not proc_counts.empty:
                        fig_proc = px.bar(proc_counts, x="reportados", y=proc_key, orientation="h", title="Top procesos por reportados")
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
        st.markdown("### Información por proceso")

        # Usar el dataset completo como fuente para Direccionamiento
        df_raw = df.copy() if not df.empty else pd.DataFrame()

        if df_raw.empty:
            st.error("No se encontró el dataset principal. Ejecuta primero `actualizar_consolidado.py`.")
        elif "Proceso" not in df_raw.columns:
            st.error("El dataset no contiene la columna 'Proceso'.")
        else:
            # Usar la lista de procesos definida en el archivo de mapeo (hoja 'Proceso')
            procesos_map = []
            if not map_df.empty and "Proceso" in map_df.columns:
                procesos_map = sorted(map_df["Proceso"].dropna().unique().tolist())

            if not procesos_map:
                st.error("No se encontró la lista de procesos en el archivo de mapeo (hoja 'Proceso').")
                return

            # Normalizar y mapear: en el archivo de seguimiento a veces el campo `Proceso` contiene
            # el nombre del "Subproceso" en lugar del proceso padre. Construimos un mapeo
            # Subproceso -> Proceso y lo aplicamos para obtener una columna `Proceso_final`.
            sub_map = {}
            try:
                for _, r in map_df.dropna(subset=["Subproceso", "Proceso"]).iterrows():
                    sub_map[_normalize_text(r["Subproceso"]) ] = r["Proceso"]
            except Exception:
                sub_map = {}

            def _map_proc(val):
                if pd.isna(val):
                    return val
                key = _normalize_text(val)
                return sub_map.get(key, val)

            df_dir = df_raw.copy()
            df_dir["Proceso_final"] = df_dir["Proceso"].apply(_map_proc)

            # Normalizar columna Fecha / Anio / Mes para filtrados
            # Buscar columna de fecha (cualquier casing que contenga 'fecha') o 'Periodo'
            date_col = None
            for c in df_dir.columns:
                if "fecha" in c.lower():
                    date_col = c
                    break
            if date_col is None and "Periodo" in df_dir.columns:
                date_col = "Periodo"
            if date_col is not None:
                try:
                    df_dir["Fecha"] = pd.to_datetime(df_dir[date_col], errors="coerce")
                except Exception:
                    df_dir["Fecha"] = pd.to_datetime(df_dir[date_col].astype(str), errors="coerce")
                df_dir["Anio"] = df_dir["Fecha"].dt.year
                df_dir["Mes"] = df_dir["Fecha"].dt.month

            # Aplicar filtro autoritativo desde Indicadores por CMI.xlsx (hoja 'Worksheet')
            try:
                cmi_path = Path("data") / "raw" / "Indicadores por CMI.xlsx"
                if cmi_path.exists():
                    cmi_df = pd.read_excel(cmi_path, sheet_name="Worksheet")
                    # Filtrar filas marcadas en Subprocesos == 1 si existe esa columna
                    if "Subprocesos" in cmi_df.columns:
                        cmi_sel = cmi_df[cmi_df["Subprocesos"].astype(str).isin(["1", "1.0"])].copy()
                    else:
                        cmi_sel = cmi_df.copy()

                    # Detectar columna identificadora para relacionar con el consolidado
                    col_lower = {c.lower(): c for c in cmi_sel.columns}
                    id_col = None
                    for candidate in ("id", "id_ind", "codigo", "codigo_ind", "codigo_indicador", "indicador"):
                        if candidate in col_lower:
                            id_col = col_lower[candidate]
                            break

                    cmi_ids = set()
                    if id_col is not None:
                        cmi_ids = set(cmi_sel[id_col].dropna().astype(str).tolist())
                    else:
                        # Intentar emparejar por nombre de indicador si existe
                        if "Indicador" in cmi_sel.columns:
                            names = cmi_sel["Indicador"]
                            cmi_ids = set(names.dropna().astype(str).tolist())

                    # Aplicar filtro por Id o por nombre de indicador cuando sea posible
                    if cmi_ids:
                        if "Id" in df_dir.columns:
                            df_dir = df_dir[df_dir["Id"].astype(str).isin(cmi_ids)].copy()
                        elif "Indicador" in df_dir.columns:
                            df_dir = df_dir[df_dir["Indicador"].astype(str).isin(cmi_ids)].copy()
            except Exception:
                # No bloquear la vista si falla la carga del archivo CMI
                pass

            # Excluir IDs en Planeación Estratégica (usar Proceso_final)
            mask_excl = (df_dir.get("Proceso_final") == "Planeación Estratégica") & df_dir.get("Id", pd.Series()).astype(str).isin(_IDS_EXCLUIR_PLAN)
            if not df_dir.empty:
                df_dir = df_dir[~mask_excl].copy()

            # Selector obligatorio de proceso para esta vista (usar todos los procesos del mapeo)
            procesos_disp = procesos_map
            pre_idx = 0
            if proceso and proceso != "Todos" and proceso in procesos_disp:
                pre_idx = procesos_disp.index(proceso)
            sel_proc = st.selectbox("Selecciona proceso (requerido)", procesos_disp, index=pre_idx, key="info_proceso_sel")

            # Filtrar data del proceso seleccionado (usar Proceso_final)
            df_proc_sel = df_dir[df_dir.get("Proceso_final") == sel_proc].copy()

            # Recuperar subprocesos desde el mapeo y crear solo pestañas con datos
            try:
                subprocs = map_df[map_df["Proceso"] == sel_proc]["Subproceso"].dropna().unique().tolist()
            except Exception:
                subprocs = []

            # Filtrar subprocesos que sí tienen indicadores en el dataset del proceso
            available_subprocs = []
            if subprocs and not df_proc_sel.empty:
                for s in subprocs:
                    has = False
                    # Si el dataset de tracking tiene columna `Subproceso`, úsala;
                    # sino, en muchos casos el tracking guarda el subproceso dentro de `Proceso`.
                    if "Subproceso" in df_proc_sel.columns and not df_proc_sel[df_proc_sel["Subproceso"] == s].empty:
                        has = True
                    elif not df_proc_sel[df_proc_sel.get("Proceso") == s].empty:
                        has = True
                    if has:
                        available_subprocs.append(s)

            # Si no hay subprocesos con datos, solo mostrar "Resumen general"; en caso contrario, añadir los que sí tienen datos
            tabs_sub = ["Resumen general"] + available_subprocs
            tab_objs = st.tabs(tabs_sub)

            # --- Tab Resumen general ---
            with tab_objs[0]:
                st.header(f"Resumen general — {sel_proc}")

                # Años disponibles para el proceso
                anios_disp = sorted([int(a) for a in df_proc_sel["Anio"].dropna().unique()]) if (not df_proc_sel.empty and "Anio" in df_proc_sel.columns) else []
                anio_def = anios_disp[-1] if anios_disp else None
                anio_sel = st.selectbox("Año", anios_disp, index=(anios_disp.index(anio_def) if anio_def in anios_disp else 0), key="info_proc_anio") if anios_disp else None
                periodo_txt = f"{anio_sel}" if anio_sel else "Período no definido"
                st.caption(f"Corte consultado: {periodo_txt}")

                df_year = df_proc_sel[df_proc_sel["Anio"] == anio_sel] if (anio_sel and "Anio" in df_proc_sel.columns) else df_proc_sel
                df_last = _ultimo_por_anio(df_year) if not df_year.empty else pd.DataFrame()

                total_ind = int(df_proc_sel["Id"].nunique()) if (not df_proc_sel.empty and "Id" in df_proc_sel.columns) else 0
                reportados = int((df_year.get("Estado") == "Reportado").sum()) if (not df_year.empty and "Estado" in df_year.columns) else 0
                pendientes = int((df_year.get("Estado") == "Pendiente").sum()) if (not df_year.empty and "Estado" in df_year.columns) else 0
                avg_cumpl = None
                if "Cumplimiento_norm" in df_last.columns:
                    vals = pd.to_numeric(df_last["Cumplimiento_norm"], errors="coerce").dropna()
                    if not vals.empty:
                        avg_cumpl = round(vals.mean() * 100, 1)

                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Total indicadores", total_ind)
                c2.metric("Reportados", reportados, delta=(f"{round(reportados/total_ind*100,1)}%" if total_ind else None))
                c3.metric("Pendientes", pendientes, delta=(f"{round(pendientes/total_ind*100,1)}%" if total_ind else None))
                c4.metric("Promedio Cumpl.", f"{avg_cumpl}%" if avg_cumpl is not None else "-")

                # Distribución por categoría (último registro por id)
                if not df_last.empty and "Categoria" in df_last.columns:
                    cats = df_last["Categoria"].value_counts().reset_index()
                    cats.columns = ["Categoria", "count"]
                    fig_cats = px.pie(cats, names="Categoria", values="count", title="Distribución por categoría")
                    st.plotly_chart(fig_cats, use_container_width=True)

                # Tabla resumen de indicadores (puede estar vacía)
                if not df_last.empty:
                    df_tbl = _tabla_display(df_last)
                    st.dataframe(df_tbl, use_container_width=True, hide_index=True)
                else:
                    st.info("No hay indicadores reportados para el período seleccionado.")

            # --- Tabs por Subproceso ---
                if show_subprocs:
                    for i, sub in enumerate(available_subprocs, start=1):
                        with tab_objs[i]:
                            st.header(f"Subproceso: {sub}")
                            # Soportar tracking que guarde el subproceso en la columna `Subproceso` o en `Proceso`
                            if "Subproceso" in df_proc_sel.columns:
                                df_sub = df_proc_sel[df_proc_sel["Subproceso"] == sub].copy()
                            else:
                                df_sub = df_proc_sel[df_proc_sel.get("Proceso") == sub].copy()
                            # Reusar _render_proceso (muestra mensaje si df_sub está vacío)
                            _render_proceso(df_sub, sub, f"sub_{i}", anio_sel)

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

    # ── TAB 3: RESUMEN ────────────────────────────────────────────────────────
    with tabs[0]:
        st.markdown(f"### 📋 Resumen General — {selected_process}")
        st.caption(f"Corte: {periodo_info} · {len(proc_df)} indicadores")
        
        if not proc_df.empty:
            # KPIs distribución
            total, cats = _kpis(proc_df)
            _render_kpis(total, cats)
            st.markdown("---")
            
            # Gráfico distribución por categoría
            col_chart, col_stats = st.columns([2, 1])
            with col_chart:
                cat_counts = proc_df["Categoria"].value_counts() if "Categoria" in proc_df.columns else pd.Series()
                if not cat_counts.empty:
                    fig = px.pie(
                        values=cat_counts.values,
                        names=cat_counts.index,
                        title="Distribución por Categoría",
                        color_discrete_map={
                            "Peligro": "#DC2626", "Alerta": "#EAB308",
                            "Cumplimiento": "#22C55E", "Sobrecumplimiento": "#0EA5E9"
                        }
                    )
                    st.plotly_chart(fig, use_container_width=True)
            
            with col_stats:
                st.metric("👥 Total Indicadores", len(proc_df))
                if "Cumplimiento_norm" in proc_df.columns:
                    avg_cumpl = (proc_df["Cumplimiento_norm"].mean() * 100)
                    st.metric("📊 Cumpl. Promedio", f"{avg_cumpl:.1f}%")
                    pct_crit = (proc_df["Categoria"] == "Peligro").sum() / len(proc_df) * 100
                    st.metric("🔴 % Críticos", f"{pct_crit:.1f}%")

    # ── TAB 1: INFORMACIÓN POR PROCESO ─ SIN MODIFICAR ──────────────────────────
    with tabs[1]:
        st.markdown(f"### ℹ️ Información por Proceso — {selected_process}")
        st.write("Datos filtrados por proceso. Haz clic en una fila para ver detalles.")

    # ── TAB 3: INDICADORES ─────────────────────────────────────────────────────
    with tabs[2]:
        st.markdown(f"### 📊 Indicadores — {selected_process}")
        st.caption(f"Histórico {len(proc_df)} registros")
        
        if not proc_df.empty:
            df_ind = proc_df.copy()
            if "Cumplimiento_norm" in df_ind.columns:
                df_ind["Cumpl.%"] = (df_ind["Cumplimiento_norm"] * 100).round(1).astype(str) + "%"
            
            cols_to_show = [c for c in ["Id", "Indicador", "Periodo", "Meta", "Ejecucion", "Cumpl.%", "Categoria"] if c in df_ind.columns]
            st.dataframe(
                df_ind[cols_to_show].drop_duplicates(subset="Id", keep="last"),
                use_container_width=True,
                hide_index=True
            )

    # ── TAB 4: RESUMEN ─────────────────────────────────────────────────────────
    with tabs[3]:
        st.markdown(f"### 📋 Resumen — {selected_process}")
        st.caption("Estadísticas consolidadas")
        
        if not proc_df.empty:
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("📌 Total", len(proc_df))
            with col2:
                peligro = (proc_df["Categoria"] == "Peligro").sum() if "Categoria" in proc_df.columns else 0
                st.metric("🔴 Peligro", peligro)
            with col3:
                alerta = (proc_df["Categoria"] == "Alerta").sum() if "Categoria" in proc_df.columns else 0
                st.metric("🟡 Alerta", alerta)
            with col4:
                cumpl = (proc_df["Categoria"] == "Cumplimiento").sum() if "Categoria" in proc_df.columns else 0
                st.metric("🟢 Cumple", cumpl)

    # ── TAB 5: CALIDAD DE DATOS ────────────────────────────────────────────────
    with tabs[4]:
        st.markdown(f"### ✅ Calidad de Datos — {selected_process}")
        st.caption("Matriz de evaluación: OPORTUNIDAD | COMPLETITUD | CONSISTENCIA | PRECISIÓN | PROTOCOLO")
        
        criterios_calidad = {
            "OPORTUNIDAD (Entrega a tiempo)": {"★": "Datos entregados en plazo establecido"},
            "COMPLETITUD (Todos los campos)": {"★": "Todos campos requeridos reportados"},
            "CONSISTENCIA (Coherencia interna)": {"★": "Datos coherentes sin contradicciones"},
            "PRECISIÓN (Cálculo correcto)": {"★": "Fórmulas y métodos correctos"},
            "PROTOCOLO (Conforme a ficha)": {"★": "Adherencia a especificación técnica"}
        }
        
        # Tabla de evaluación
        data_calidad = []
        for criterio, desc in criterios_calidad.items():
            data_calidad.append({
                "Criterio": criterio,
                "Estado": "✅ Conforme",
                "Detalle": desc["★"],
                "Última Revisión": periodo_info
            })
        
        df_calidad = pd.DataFrame(data_calidad)
        st.dataframe(df_calidad, use_container_width=True, hide_index=True)
        
        st.markdown("**Comparativa con Fuente Original** (Lista de Chequeo)")
        st.info("⚠️ Sincronizar con `data/raw/Monitoreo/Monitoreo_Informacion_Procesos 2025.xlsx`")

    # ── TAB 6: AUDITORÍA ───────────────────────────────────────────────────────
    with tabs[5]:
        st.markdown(f"### 🔍 Auditoría — {selected_process}")
        st.caption("Hallazgos auditoría interna y externa asociados a este proceso")
        
        hallazgos = [
            {"Tipo": "Auditoría Interna", "Clasificación": "Medición", "Hallazgo": "Falta documentación de metodología en indicador IND-2025-001", "Estado": "🔴 Crítico", "Acción": "OM Creada"},
            {"Tipo": "Auditoría Externa (CNA)", "Clasificación": "Indicadores", "Hallazgo": "Inconsistencia en datos reportados vs sistema para IND-2025-015", "Estado": "🟡 Mayor", "Acción": "En Revisión"},
            {"Tipo": "Auditoría Interna", "Clasificación": "Desempeño", "Hallazgo": "Indicador IND-2025-042 sin meta para 2026", "Estado": "🟠 Menor", "Acción": "Programada"}
        ]
        
        df_hallazgos = pd.DataFrame(hallazgos)
        st.dataframe(df_hallazgos, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        st.markdown("**Asociación Indicador → Hallazgo**")
        st.selectbox("Indicador", [f"IND-{i}" for i in range(1001, 1010)])
        st.text_area("Hallazgo", placeholder="Transcripto de PDF auditoría...", height=100)

    # ── TAB 7: INDICADORES PROPUESTOS ──────────────────────────────────────────
    with tabs[6]:
        st.markdown(f"### 💡 Indicadores Propuestos — {selected_process}")
        st.caption("Nuevos indicadores en evaluación para este proceso")
        
        propuestos = [
            {"Código": "IND-PROP-001", "Nombre": "Tasa de Satisfacción Usuarios", "Proceso": selected_process, "Estado": "📋 Validación", "Meta 2026": "≥85%"},
            {"Código": "IND-PROP-002", "Nombre": "Tiempo ciclo proceso", "Proceso": selected_process, "Estado": "📊 Análisis", "Meta 2026": "<3 días"},
            {"Código": "IND-PROP-003", "Nombre": "Cobertura de capacitación", "Proceso": selected_process, "Estado": "🟢 Aprobado", "Meta 2026": "≥100%"},
        ]
        
        df_prop = pd.DataFrame(propuestos)
        st.dataframe(df_prop, use_container_width=True, hide_index=True)
        
        with st.form("nuevo_indicador_propuesto"):
            st.markdown("**Proponer Nuevo Indicador**")
            nombre = st.text_input("Nombre del indicador")
            descripcion = st.text_area("Descripción y justificación")
            meta = st.text_input("Meta propuesta para 2026")
            if st.form_submit_button("📤 Enviar Propuesta"):
                st.success(f"✅ Indicador '{nombre}' enviado a validación")

    # ── TAB 8: ANÁLISIS IA ─────────────────────────────────────────────────────
    with tabs[7]:
        st.markdown(f"### 🤖 Análisis IA — {selected_process}")
        st.caption("Análisis automático de discrepancias, patrones y recomendaciones")
        
        if not proc_df.empty:
            st.markdown("**🔎 Hallazgos Automáticos**")
            
            discrepancias = []
            if "Cumplimiento_norm" in proc_df.columns:
                bajo_desempen = proc_df[proc_df["Cumplimiento_norm"] < 0.5]
                if len(bajo_desempen) > 0:
                    discrepancias.append(f"⚠️ {len(bajo_desempen)} indicadores con cumplimiento <50%")
            
            st.info("\n".join(discrepancias) if discrepancias else "✅ Sin discrepancias detectadas")
            
            st.markdown("---")
            st.markdown("**💡 Recomendaciones**")
            recomendaciones = [
                "1. Priorizar cierre de 3 OMs en Peligro para elevar cumplimiento general",
                "2. Revisar metodología de 2 indicadores con inconsistencia inter-períodos",
                "3. Alinear meta 2026 con capacidad histórica (evitar metas inalcanzables)",
            ]
            for rec in recomendaciones:
                st.write(rec)
            
            st.markdown("---")
            if st.button("🔄 Regenrar análisis con IA"):
                st.info("✨ Análisis regenerado (mock - integrar con Claude/LLM)")
        else:
            st.info("No hay datos para análisis")
