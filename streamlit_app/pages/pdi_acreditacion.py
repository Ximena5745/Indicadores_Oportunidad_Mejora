import pandas as pd
import streamlit as st

from streamlit_app.components.filters import render_filters


def render():
    st.title("PDI / Acreditación")
    st.caption("Seguimiento de evidencias y avances de acreditación por foco estratégico.")

    with st.expander("🔎 Filtros", expanded=False):
        if st.button("Limpiar filtros", key="pdi_clear_filters"):
            for _k in ("pdi_estado", "pdi_macro", "pdi_horizonte"):
                if _k in st.session_state:
                    del st.session_state[_k]
            st.rerun()

        sel = render_filters(
            pd.DataFrame(),
            {
                "estado": {"label": "Estado", "options": ["Al día", "En riesgo", "Vencido"]},
                "macro": {"label": "Macrolinea", "options": ["Docencia", "Investigación", "Extensión", "Gobierno"]},
                "horizonte": {"label": "Horizonte", "options": ["Q2-2026", "Q3-2026", "Q4-2026"], "include_all": False, "default": "Q2-2026"},
            },
            key_prefix="pdi",
            columns_per_row=3,
        )

    activos = []
    if sel.get("estado", "Todos") != "Todos":
        activos.append(f"Estado: {sel['estado']}")
    if sel.get("macro", "Todos") != "Todos":
        activos.append(f"Macrolinea: {sel['macro']}")
    if sel.get("horizonte"):
        activos.append(f"Horizonte: {sel['horizonte']}")
    if activos:
        st.caption("Filtros activos: " + " · ".join(activos))

    data = pd.DataFrame([
        {"Frente": "Autoevaluación institucional", "Estado": "Al día", "Responsable": "Calidad", "Vence": "30/04/2026"},
        {"Frente": "Evidencias por factor", "Estado": "En riesgo", "Responsable": "Decanaturas", "Vence": "15/05/2026"},
        {"Frente": "Plan de cierre hallazgos", "Estado": "Vencido", "Responsable": "Planeación", "Vence": "31/03/2026"},
    ])

    if sel.get("estado", "Todos") != "Todos":
        data = data[data["Estado"] == sel["estado"]]

    st.dataframe(data, use_container_width=True, hide_index=True)
