import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from streamlit_app.components.filters import render_filters
from streamlit_app.services.data_service import DataService


def render():
    st.title("CMI Estratégico")
    st.caption("Monitoreo por perspectiva con vista compacta para seguimiento ejecutivo.")

    service = DataService()
    ts = service.get_timeseries().copy()
    sem = service.get_semaforo().copy()
    periodos = ts["date"].dt.strftime("%b %Y").tolist() if not ts.empty else []

    with st.expander("🔎 Filtros", expanded=False):
        if st.button("Limpiar filtros", key="cmi_clear_filters"):
            for _k in ("cmi_perspectiva", "cmi_horizonte", "cmi_corte"):
                if _k in st.session_state:
                    del st.session_state[_k]
            st.rerun()

        cfg = {
            "perspectiva": {
                "label": "Perspectiva",
                "options": ["Financiera", "Clientes", "Procesos", "Aprendizaje"],
                "all_display": "— Todas —",
            },
            "horizonte": {
                "label": "Horizonte",
                "options": ["Mensual", "Trimestral", "Semestral"],
            },
            "corte": {
                "label": "Corte",
                "options": periodos,
                "include_all": False,
                "default": periodos[-1] if periodos else None,
            },
        }
        sel = render_filters(pd.DataFrame(), cfg, key_prefix="cmi", columns_per_row=3)

    activos = []
    if sel.get("perspectiva", "Todos") != "Todos":
        activos.append(f"Perspectiva: {sel['perspectiva']}")
    if sel.get("horizonte", "Todos") != "Todos":
        activos.append(f"Horizonte: {sel['horizonte']}")
    if sel.get("corte"):
        activos.append(f"Corte: {sel['corte']}")
    if activos:
        st.caption("Filtros activos: " + " · ".join(activos))

    if ts.empty or sem.empty:
        st.info("No hay datos disponibles para CMI estratégico.")
        return

    cols_kpi = st.columns(3)
    ultimo = float(ts["value"].iloc[-1])
    previo = float(ts["value"].iloc[-2]) if len(ts) > 1 else ultimo
    delta = ultimo - previo
    cols_kpi[0].metric("Desempeño último corte", f"{ultimo:.1f}", f"{delta:+.1f}")
    cols_kpi[1].metric("Promedio 12 cortes", f"{ts['value'].mean():.1f}")
    cols_kpi[2].metric("Máximo histórico", f"{ts['value'].max():.1f}")

    c1, c2 = st.columns([2, 1])
    with c1:
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=ts["date"],
            y=ts["value"],
            name="Resultado",
            marker_color="#1f4e79",
            hovertemplate="%{x|%b %Y}<br>%{y:.1f}<extra></extra>",
        ))
        fig.add_trace(go.Scatter(
            x=ts["date"],
            y=ts["value"].rolling(3, min_periods=1).mean(),
            mode="lines+markers",
            name="Tendencia 3M",
            line=dict(color="#00a3a3", width=3),
            marker=dict(size=6),
        ))
        fig.update_layout(
            title="Desempeño estratégico",
            margin=dict(l=10, r=10, t=45, b=10),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            legend=dict(orientation="h", y=1.02, x=1, xanchor="right"),
        )
        st.plotly_chart(fig, use_container_width=True, key="cmi_desempeno")

    with c2:
        st.markdown("### Semáforo CMI")
        total = max(int(sem["valor"].sum()), 1)
        for _, row in sem.iterrows():
            estado = str(row["estado"])
            valor = int(row["valor"])
            pct = valor / total * 100
            st.markdown(
                f"<div style='margin:6px 0;'>"
                f"<div style='display:flex;justify-content:space-between;font-size:12px;'>"
                f"<span>{estado}</span><span>{valor}</span></div>"
                f"<div style='height:8px;background:#e5e7eb;border-radius:999px;'>"
                f"<div style='width:{pct:.1f}%;height:8px;background:#1f4e79;border-radius:999px;'></div>"
                f"</div></div>",
                unsafe_allow_html=True,
            )
