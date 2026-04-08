"""
Resumen por proceso — Mapa de procesos con análisis integrado.

Estructura de tabs:
  1. Indicadores (nivel de cumplimiento)
  2. Reporte de indicadores
  3. Calidad de información
  4. Resultados de auditoría
  5. Indicadores propuestos
  6. Análisis IA (histórico)

Cada tab recibe el proceso (o procesos) seleccionado(s).
Al hacer clic en una fila de indicador se abre la ficha emergente
(con tabs: IRIP / DAD / Coherencia / Eficiencia OM).

Este módulo integra la lógica formerly de Direccionamiento Estratégico
y Auditorías como tabs dentro del mismo flujo.
"""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.data_mocks import get_irip_data, get_dad_data, get_cmi_data


# ── Helpers de visualización ───────────────────────────────────────────────────

def _render_kpis_proceso(df: pd.DataFrame, columns_fn):
    """Renderiza 5 KPI cards (total, peligro, alerta, cumplimiento, sobrecumpl)."""
    total = len(df)
    semaforo = {"Peligro": 0, "Alerta": 0, "Cumplimiento": 0, "Sobrecumplimiento": 0}
    if "Categoria" in df.columns:
        for cat in semaforo:
            semaforo[cat] = int((df["Categoria"] == cat).sum())
    colores = {"Peligro": "#ff3b30", "Alerta": "#ffab00",
               "Cumplimiento": "#00c853", "Sobrecumplimiento": "#00b8d4"}
    definiciones = [
        ("Total", total, "#1A3A5C", None),
        ("🔴 Peligro", semaforo["Peligro"], colores["Peligro"], f"{semaforo['Peligro']/total*100:.1f}%" if total else "0%"),
        ("🟡 Alerta", semaforo["Alerta"], colores["Alerta"], f"{semaforo['Alerta']/total*100:.1f}%" if total else "0%"),
        ("🟢 Cumplimiento", semaforo["Cumplimiento"], colores["Cumplimiento"], f"{semaforo['Cumplimiento']/total*100:.1f}%" if total else "0%"),
        ("🔵 Sobrecumpl.", semaforo["Sobrecumplimiento"], colores["Sobrecumplimiento"], f"{semaforo['Sobrecumplimiento']/total*100:.1f}%" if total else "0%"),
    ]
    for col, (label, val, color, delta) in zip(columns_fn(), definiciones):
        with col:
            st.markdown(
                f"<div style='background:#fff;border-radius:8px;padding:16px;border-left:4px solid {color};'>"
                f"<div style='font-size:12px;color:#666'>{label}</div>"
                f"<div style='font-size:22px;font-weight:700;color:{color}'>{val}</div>"
                f"<div style='font-size:11px;color:#999'>{delta or ''}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )


def _render_tabla_con_ficha(df: pd.DataFrame, key_prefix: str, proceso_nombre: str):
    """Tabla de indicadores con selección que abre ficha emergente."""
    if df.empty:
        st.info(f"Sin indicadores para **{proceso_nombre}**.")
        return

    cols_show = [c for c in ["Id", "Indicador", "Subproceso", "Meta",
                              "Ejecucion", "Cumplimiento_norm", "Categoria", "Sentido"]
                 if c in df.columns]
    df_show = df[cols_show].copy()
    if "Cumplimiento_norm" in df_show.columns:
        df_show["Cumplimiento_norm"] = (df_show["Cumplimiento_norm"] * 100).round(1).astype(str) + "%"
    df_show = df_show.rename(columns={"Cumplimiento_norm": "Cumpl.%", "Ejecucion": "Ejecución"})

    col_cfg = {
        "Indicador": st.column_config.TextColumn("Indicador", width="large"),
        "Cumpl.%":   st.column_config.TextColumn("Cumpl.%",   width="small"),
    }
    if "Meta" in df_show.columns:
        col_cfg["Meta"] = st.column_config.NumberColumn("Meta", format="%.2f")
    if "Ejecución" in df_show.columns:
        col_cfg["Ejecución"] = st.column_config.NumberColumn("Ejecución", format="%.2f")

    event = st.dataframe(
        df_show, use_container_width=True, hide_index=True,
        on_select="rerun", selection_mode="single-row", key=f"tbl_{key_prefix}",
        column_config=col_cfg,
    )

    curr_rows = event.selection.get("rows", []) if (event and event.selection) else []
    prev_key = f"_rp_prev_{key_prefix}"
    if curr_rows != st.session_state.get(prev_key, []):
        st.session_state[prev_key] = curr_rows
        if curr_rows:
            idx = curr_rows[0]
            st.session_state["_rp_ficha_id"] = str(df_show.iloc[idx]["Id"])
            st.session_state["_rp_ficha_nom"] = str(df_show.iloc[idx].get("Indicador", ""))

    st.download_button(
        f"📥 Exportar {proceso_nombre[:20]}",
        data=df_show.to_csv(index=False).encode("utf-8"),
        file_name=f"{key_prefix}.csv",
        mime="text/csv",
        key=f"exp_{key_prefix}",
    )


def _render_indicadores_tab(df: pd.DataFrame, proceso_nombre: str):
    """Tab 1: KPIs + tabla de indicadores con ficha."""
    cols = st.columns(5)
    _render_kpis_proceso(df, lambda: cols)
    st.markdown("---")
    st.caption(f"Haz clic en una fila para abrir la ficha del indicador.")
    _render_tabla_con_ficha(df, proceso_nombre.replace(" ", "_").lower()[:20], proceso_nombre)


def _render_reporte_tab(df: pd.DataFrame, proceso_nombre: str):
    """Tab 2: Reporte de indicadores (resumen ejecutivo por proceso)."""
    st.subheader(f"Reporte — {proceso_nombre}")
    if df.empty:
        st.info("Sin datos.")
        return
    # Gráfico de cumplimiento por período
    if "Periodo" in df.columns and "Cumplimiento_norm" in df.columns:
        df_plot = df.dropna(subset=["Cumplimiento_norm"]).copy()
        df_plot["Cumplimiento_norm"] = df_plot["Cumplimiento_norm"] * 100
        agg = df_plot.groupby("Periodo")["Cumplimiento_norm"].mean().reset_index()
        fig = go.Figure(go.Bar(x=agg["Periodo"], y=agg["Cumplimiento_norm"],
                               marker_color="#1A3A5C", text=agg["Cumplimiento_norm"].round(1)))
        fig.update_layout(margin=dict(l=10, r=10, t=30, b=10), height=300)
        st.plotly_chart(fig, use_container_width=True)
    st.dataframe(df.head(20), use_container_width=True, hide_index=True)


def _render_calidad_tab(df: pd.DataFrame, proceso_nombre: str):
    """Tab 3: Calidad de información — flags de QA."""
    st.subheader(f"Calidad de información — {proceso_nombre}")
    # Simular métricas de calidad con datos mock
    total = len(df)
    calidad = [
        {"métrica": "Registros completos", "valor": f"{int(total * 0.92)}/{total}", "pct": 92},
        {"métrica": "Fuentes validadas", "valor": f"{int(total * 0.88)}/{total}", "pct": 88},
        {"métrica": "Consistencia histórica", "valor": f"{int(total * 0.95)}/{total}", "pct": 95},
        {"métrica": "Indicadores actualizados", "valor": f"{int(total * 0.90)}/{total}", "pct": 90},
    ]
    st.table(pd.DataFrame(calidad))
    # Heatmap de calidad por mes (mock)
    import numpy as np
    meses = ["Ene", "Feb", "Mar", "Abr", "May", "Jun"]
    matrix = np.random.uniform(0.75, 0.99, size=(4, 6)).round(2)
    fig = go.Figure(go.Heatmap(z=matrix, x=meses,
                                y=["Complitud", "Validación", "Consistencia", "Actualización"],
                                colorscale="RdYlGn", text=matrix, texttemplate="%{z:.0%}"))
    fig.update_layout(margin=dict(l=10, r=10, t=30, b=10), height=250)
    st.plotly_chart(fig, use_container_width=True)


def _render_auditoria_tab(df: pd.DataFrame, proceso_nombre: str):
    """Tab 4: Resultados de auditoría — hallazgos por proceso."""
    st.subheader(f"Resultados de auditoría — {proceso_nombre}")
    # Mock de hallazgos
    hallazgos = [
        {"severidad": "🔴 Alta", "descripcion": "Indicador sin medición en los últimos 3 períodos", "indicador": "Tasa retención 2do año", "estado": "Abierta"},
        {"severidad": "🟡 Media", "descripcion": "Meta desactualizada vs comportamiento histórico", "indicador": "Cobertura banda ancha", "estado": "En revisión"},
        {"severidad": "🔵 Baja", "descripcion": "Fuente de dato no vinculada a sistema oficial", "indicador": "Publicaciones indexadas", "estado": "Cerrada"},
    ]
    st.table(pd.DataFrame(hallazgos))
    st.markdown("**Detalle de auditoría**")
    st.info("Los hallazgos de auditoría se integran aquí. Cada hallazgo incluye severidad, descripción, indicador asociado y estado.")


def _render_propuestos_tab(df: pd.DataFrame, proceso_nombre: str):
    """Tab 5: Indicadores propuestos para el proceso."""
    st.subheader(f"Indicadores propuestos — {proceso_nombre}")
    propuestos = [
        {"indicador": "Tasa de participación en actividades de extensión", "tipo": "Nuevo", "justificación": "Mide impacto social de la institución"},
        {"indicador": "Ingresos por proyectos de investigación financiados", "tipo": "Propuesto", "justificación": "Complementa el indicador de eficiencia financiera"},
        {"indicador": "Satisfacción del estudiante con servicios de apoyo académico", "tipo": "En validación", "justificación": "Requerido para acreditación CNA"},
    ]
    st.table(pd.DataFrame(propuestos))
    st.button("➕ Agregar indicador propuesto", key=f"add_prop_{proceso_nombre[:10]}")


def _render_analisis_ia_tab(df: pd.DataFrame, proceso_nombre: str):
    """Tab 6: Análisis IA de histórico + acceso a ficha de indicador."""
    st.subheader(f"Análisis IA — {proceso_nombre}")

    irip = get_irip_data(30)
    dad = get_dad_data(30)
    cmi = get_cmi_data(30)

    tabs_ia = st.tabs(["Tendencia IRIP", "DAD — Anomalías", "CMI Score", "Recomendaciones"])

    with tabs_ia[0]:
        st.write("**Tendencia IRIP**")
        fig = go.Figure(go.Scatter(x=list(range(len(irip))), y=irip["cumplimiento"],
                                    mode="lines+markers", line=dict(color="#6200ea")))
        fig.update_layout(margin=dict(l=10, r=10, t=20, b=10), height=250)
        st.plotly_chart(fig, use_container_width=True)

    with tabs_ia[1]:
        st.write("**Detector de anomalías**")
        fig2 = go.Figure(go.Scatter(x=list(range(len(dad))), y=dad["avance"],
                                     mode="lines+markers", line=dict(color="#00b8d4")))
        # marcar outliers mock (z > 2)
        outlier_idx = [5, 12, 22]
        outlier_vals = [dad["avance"].iloc[i] for i in outlier_idx]
        fig2.add_trace(go.Scatter(x=outlier_idx, y=outlier_vals, mode="markers",
                                  marker=dict(color="#ff3b30", size=10), name="Anomalía"))
        fig2.update_layout(margin=dict(l=10, r=10, t=20, b=10), height=250)
        st.plotly_chart(fig2, use_container_width=True)

    with tabs_ia[2]:
        st.write("**CMI Score**")
        fig3 = go.Figure(go.Scatter(x=list(range(len(cmi))), y=cmi["score"],
                                     mode="lines+markers", line=dict(color="#00c853")))
        fig3.update_layout(margin=dict(l=10, r=10, t=20, b=10), height=250)
        st.plotly_chart(fig3, use_container_width=True)

    with tabs_ia[3]:
        st.write("**Recomendaciones IA**")
        recomendaciones = [
            {"prioridad": "🔴 Alta", "recomendación": "Revisar indicadores con IRIP > 70% — riesgo de incumplimiento en 30 días"},
            {"prioridad": "🟡 Media", "recomendación": "Ajustar meta del indicador 'Cobertura banda ancha' — comportamiento histórico supera la meta en 12%"},
            {"prioridad": "🔵 Baja", "recomendación": "Consolidar fuentes de datos para 'Publicaciones indexadas' — inconsistencia detectada en DAD"},
        ]
        st.table(pd.DataFrame(recomendaciones))


def _ficha_indicador(df_source: pd.DataFrame):
    """Ficha emergente con tabs: IRIP / DAD / Coherencia / Eficiencia OM."""
    fid = st.session_state.get("_rp_ficha_id")
    fnom = st.session_state.get("_rp_ficha_nom", "")

    @st.dialog(f"📊 {fid} — {fnom[:65]}", width="large")
    def _render_ficha():
        col1, col2 = st.columns([1, 4])
        with col1:
            st.metric("ID", fid)
            st.metric("Indicador", fnom[:40])
        with col2:
            st.write("Resumen histórico del indicador.")

        tabs_ficha = st.tabs(["🔮 IRIP Predictivo", "🧭 DAD — Anomalías", "📏 Coherencia metas", "⚠️ Eficiencia OM"])

        irip = get_irip_data(30)
        dad = get_dad_data(30)
        cmi = get_cmi_data(30)

        with tabs_ficha[0]:
            st.write("**Score de riesgo de incumplimiento**")
            fig = go.Figure(go.Bar(x=list(range(len(irip))), y=irip["cumplimiento"],
                                   marker_color=["#ff3b30" if v < 70 else "#00c853" for v in irip["cumplimiento"]]))
            fig.update_layout(margin=dict(l=10, r=10, t=20, b=10), height=220)
            st.plotly_chart(fig, use_container_width=True)

        with tabs_ficha[1]:
            st.write("**Puntos anómalos detectados**")
            fig2 = go.Figure(go.Scatter(x=list(range(len(dad))), y=dad["avance"],
                                        mode="lines+markers", line=dict(color="#00b8d4")))
            fig2.update_layout(margin=dict(l=10, r=10, t=20, b=10), height=220)
            st.plotly_chart(fig2, use_container_width=True)

        with tabs_ficha[2]:
            st.write("**Coherencia meta vs comportamiento**")
            fig3 = go.Figure(go.Scatter(x=list(range(len(cmi))), y=cmi["score"],
                                        mode="lines+markers", line=dict(color="#8a82e9")))
            fig3.update_layout(margin=dict(l=10, r=10, t=20, b=10), height=220)
            st.plotly_chart(fig3, use_container_width=True)

        with tabs_ficha[3]:
            st.write("**Eficiencia OM (SEAC)**")
            om_data = pd.DataFrame({
                "OM": ["OM-001", "OM-002", "OM-003"],
                "Estado": ["Cerrada", "En curso", "Abierta"],
                "Días": [15, 45, 90],
                "Efectividad": ["Alta", "Media", "Baja"],
            })
            st.table(om_data)

        if st.button("✖ Cerrar ficha"):
            st.session_state["_rp_ficha_id"] = None
            st.rerun()

    if fid:
        _render_ficha()


def run():
    st.title("🗺️ Mapa de procesos")
    st.markdown("Selecciona uno o varios procesos para ver su análisis integrado.")

    # Selector de proceso(s) — multi-select
    procesos_opciones = [
        "Planeación Estratégica",
        "Desempeño Institucional",
        "Gestión de Proyectos",
        "Gestión del Talento Humano",
        "Infraestructura y Recursos",
        "Admisiones y Registro",
    ]
    procesos_sel = st.multiselect(
        "Procesos a analizar",
        procesos_opciones,
        default=["Planeación Estratégica"],
        help="Selecciona uno o varios procesos. Cada uno mostrará tabs de análisis integrado."
    )

    if not procesos_sel:
        st.info("Selecciona al menos un proceso para continuar.")
        return

    # Selector de año
    anio_sel = st.selectbox("Año", [2025, 2024, 2023], index=0)

    # Para cada proceso seleccionado renderizamos las tabs
    # Si hay varios, usamos tabs; si es uno, tabs igualmente
    tabs_procesos = st.tabs(procesos_sel)

    # Generar datos mock por proceso
    for idx_proc, proc in enumerate(procesos_sel):
        with tabs_procesos[idx_proc]:
            # Crear dataset mock para el proceso
            irip = get_irip_data(30)
            df_proc = pd.DataFrame({
                "Id":           [f"IND-{i:03d}" for i in range(1, 21)],
                "Indicador":    [f"Indicador {i} — {proc[:20]}" for i in range(1, 21)],
                "Subproceso":   [proc.split()[0]] * 20,
                "Proceso":      [proc] * 20,
                "Meta":         [round(v, 2) for v in irip["cumplimiento"].values[:20]],
                "Ejecucion":    [round(v * 0.95, 2) for v in irip["cumplimiento"].values[:20]],
                "Cumplimiento_norm": irip["cumplimiento"].values[:20] / 100,
                "Categoria":    ["Peligro" if v < 70 else "Alerta" if v < 80 else "Cumplimiento" if v < 100 else "Sobrecumplimiento"
                                 for v in irip["cumplimiento"].values[:20]],
                "Periodo":      ["Dic 2025"] * 20,
                "Sentido":      ["Ascendente"] * 20,
            })

            inner_tabs = st.tabs([
                "📊 Indicadores",
                "📋 Reporte",
                "✅ Calidad información",
                "🔍 Resultados auditoría",
                "💡 Propuestos",
                "🤖 Análisis IA",
            ])

            with inner_tabs[0]:
                _render_indicadores_tab(df_proc, proc)
            with inner_tabs[1]:
                _render_reporte_tab(df_proc, proc)
            with inner_tabs[2]:
                _render_calidad_tab(df_proc, proc)
            with inner_tabs[3]:
                _render_auditoria_tab(df_proc, proc)
            with inner_tabs[4]:
                _render_propuestos_tab(df_proc, proc)
            with inner_tabs[5]:
                _render_analisis_ia_tab(df_proc, proc)

    # Ficha emergente (se renderiza si hay selección activa)
    _ficha_indicador(None)
