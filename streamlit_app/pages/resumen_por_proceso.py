import unicodedata
import pandas as pd
import streamlit as st
from streamlit_app.components import KPIRow
from streamlit_app.services.data_service import DataService
from streamlit_app.components.filters import render_filters

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
        if unidad != "Todas" and "Unidad" in proc_df.columns:
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

    tabs = st.tabs(["📊 Indicadores", "📋 Resumen", "✅ Calidad", "🔍 Auditoría", "💡 Propuestos", "🤖 Análisis IA"])

    with tabs[0]:
        st.markdown(f"### Indicadores — {selected_process}")
        st.caption(f"Corte consultado: {periodo_info}")
        if proc_df.empty:
            st.info("No hay datos disponibles para el proceso seleccionado.")
        else:
            total = len(proc_df)
            reportado = int((proc_df["Estado"] == "Reportado").sum()) if "Estado" in proc_df.columns else 0
            pendiente = int((proc_df["Estado"] == "Pendiente").sum()) if "Estado" in proc_df.columns else 0
            no_aplica = int((proc_df["Estado"] == "No aplica").sum()) if "Estado" in proc_df.columns else 0

            cols = st.columns([1, 1, 1, 1])
            cols[0].metric("Total indicadores", total)
            cols[1].metric("Reportado", reportado)
            cols[2].metric("Pendiente", pendiente, delta=f"{round(pendiente/total*100,1)}%" if total else None)
            cols[3].metric("No aplica", no_aplica)

            st.markdown("#### Indicadores clave")
            breakdown = proc_df["Estado"].value_counts().to_dict() if "Estado" in proc_df.columns else {}
            st.markdown(
                _render_html_bars(
                    breakdown,
                    ["Reportado", "Pendiente", "No aplica"],
                    {
                        "Reportado": "#0f3a6d",
                        "Pendiente": "#ffab00",
                        "No aplica": "#9e9e9e",
                    },
                    max(breakdown.values()) if breakdown else 1,
                ),
                unsafe_allow_html=True,
            )

            st.markdown("#### Distribución por periodicidad")
            periodo_counts = proc_df["Periodicidad"].value_counts().to_dict() if "Periodicidad" in proc_df.columns else {}
            st.markdown(
                _render_html_bars(
                    periodo_counts,
                    sorted(periodo_counts.keys()),
                    {
                        "Anual": "#0f3a6d",
                        "Bimestral": "#00b8d4",
                        "Mensual": "#1d4a86",
                        "Semestral": "#1d9c60",
                        "Trimestral": "#ffab00",
                    },
                    max(periodo_counts.values()) if periodo_counts else 1,
                ),
                unsafe_allow_html=True,
            )

    with tabs[1]:
        st.markdown(f"#### Resumen — {selected_process}")
        st.caption(f"Corte consultado: {periodo_info}")
        st.write("Resumen agregado de indicadores filtrados por proceso. Aquí se prioriza el análisis por estado y periodicidad.")
        if proc_df.empty:
            st.info("No hay datos disponibles para el proceso seleccionado.")
        else:
            periodo_counts = proc_df["Periodicidad"].value_counts().to_dict() if "Periodicidad" in proc_df.columns else {}
            st.write("**Periodicidad dentro del proceso seleccionado**")
            st.markdown(
                _render_html_bars(
                    periodo_counts,
                    sorted(periodo_counts.keys()),
                    {
                        "Anual": "#0f3a6d",
                        "Bimestral": "#00b8d4",
                        "Mensual": "#1d4a86",
                        "Semestral": "#1d9c60",
                        "Trimestral": "#ffab00",
                    },
                    max(periodo_counts.values()) if periodo_counts else 1,
                ),
                unsafe_allow_html=True,
            )

            status_summary = (
                proc_df["Estado"]
                .value_counts(dropna=True)
                .rename_axis("Estado")
                .reset_index(name="Indicadores")
            ) if "Estado" in proc_df.columns else pd.DataFrame()
            if not status_summary.empty:
                st.markdown("**Indicadores por estado**")
                st.dataframe(status_summary, use_container_width=True, hide_index=True)

            breakdown_df = (
                proc_df[["Periodicidad", "Estado"]]
                .dropna(subset=["Periodicidad", "Estado"])
                .groupby(["Periodicidad", "Estado"], as_index=False)
                .size()
                .rename(columns={"size": "Indicadores"})
            )
            if not breakdown_df.empty:
                st.markdown("**Indicadores por periodicidad y estado**")
                st.dataframe(breakdown_df, use_container_width=True)

            top_processes = (
                proc_df["Proceso"]
                .value_counts()
                .rename_axis("Proceso")
                .reset_index(name="Indicadores")
                .head(8)
            )
            if not top_processes.empty:
                st.markdown("**Procesos con más indicadores en la selección**")
                st.dataframe(top_processes, use_container_width=True, hide_index=True)

    with tabs[2]:
        st.markdown(f"### Calidad — {selected_process}")
        st.write("Métrica de calidad basada en el estado de reporte para el proceso seleccionado.")

    with tabs[3]:
        st.markdown(f"### Auditoría — {selected_process}")
        st.write("Los datos están filtrados por proceso y listos para análisis de auditoría.")

    with tabs[4]:
        st.markdown(f"### Propuestos — {selected_process}")
        st.write("Indicadores propuestos y notas relacionadas con el proceso seleccionado.")

    with tabs[5]:
        st.markdown(f"### Análisis IA — {selected_process}")
        st.write("Análisis IA (mock) para el proceso seleccionado.")
