import pandas as pd
import streamlit as st

from streamlit_app.components.filters import render_filters


def render():
    st.title("Plan de Mejoramiento")
    st.caption("Seguimiento de acciones, responsables y compromisos con vista operativa compacta.")

    with st.expander("🔎 Filtros", expanded=False):
        if st.button("Limpiar filtros", key="pm_clear_filters"):
            for _k in ("pm_prioridad", "pm_estado", "pm_responsable"):
                if _k in st.session_state:
                    del st.session_state[_k]
            st.rerun()

        sel = render_filters(
            pd.DataFrame(),
            {
                "prioridad": {"label": "Prioridad", "options": ["Alta", "Media", "Baja"]},
                "estado": {"label": "Estado", "options": ["En curso", "Bloqueada", "Cerrada"]},
                "responsable": {"label": "Responsable", "options": ["Calidad", "Planeación", "Académica", "Financiera"]},
            },
            key_prefix="pm",
            columns_per_row=3,
        )

    activos = []
    if sel.get("prioridad", "Todos") != "Todos":
        activos.append(f"Prioridad: {sel['prioridad']}")
    if sel.get("estado", "Todos") != "Todos":
        activos.append(f"Estado: {sel['estado']}")
    if sel.get("responsable", "Todos") != "Todos":
        activos.append(f"Responsable: {sel['responsable']}")
    if activos:
        st.caption("Filtros activos: " + " · ".join(activos))

    data = pd.DataFrame([
        {"OM": "OM-101", "Acción": "Actualizar evidencia de cierre", "Prioridad": "Alta", "Estado": "En curso", "Responsable": "Calidad", "Vence": "28/04/2026"},
        {"OM": "OM-087", "Acción": "Ajustar plan docente", "Prioridad": "Media", "Estado": "Bloqueada", "Responsable": "Académica", "Vence": "12/05/2026"},
        {"OM": "OM-075", "Acción": "Cerrar hallazgo financiero", "Prioridad": "Alta", "Estado": "Cerrada", "Responsable": "Financiera", "Vence": "20/03/2026"},
    ])

    for _col, _val in (("Prioridad", sel.get("prioridad", "Todos")), ("Estado", sel.get("estado", "Todos")), ("Responsable", sel.get("responsable", "Todos"))):
        if _val != "Todos":
            data = data[data[_col] == _val]

    k1, k2, k3 = st.columns(3)
    k1.metric("OM visibles", len(data))
    k2.metric("OM alta prioridad", int((data["Prioridad"] == "Alta").sum()))
    k3.metric("OM bloqueadas", int((data["Estado"] == "Bloqueada").sum()))
    st.dataframe(data, use_container_width=True, hide_index=True)
