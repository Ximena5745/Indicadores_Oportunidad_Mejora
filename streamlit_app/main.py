import streamlit as st
from streamlit_extras.switch_page_button import switch_page

st.set_page_config(page_title="Sistema de Indicadores", layout="wide")

CSS = """
<style>
[data-testid="stSidebar"] { background-color: #1A3A5C; }
[data-testid="stSidebar"] * { color: white !important; }
[data-testid="stSidebar"] label { color: #B3D9FF !important; font-weight: 500; }
.stApp { background-color: #F4F6F9; }
h1 { color: #1A3A5C; }
h2, h3 { color: #1565C0; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

def main():
    with st.sidebar:
        st.markdown("---")
        if st.button("Actualizar datos", use_container_width=True):
            st.cache_data.clear()
            st.success("Datos actualizados.")
        st.markdown("---")

        # Sidebar navigation
        section = st.radio("Navegación", ["Resumen estratégico", "Resumen por procesos", "Seguimiento operativo"], index=0)

    # Main content based on selected section
    if section == "Resumen estratégico":
        tab = st.tabs(["CMI Estratégico", "PDI / Acreditación", "Plan de Mejoramiento"])
        with tab[0]:
            switch_page("pages/cmi_estrategico.py")
        with tab[1]:
            switch_page("pages/pdi_acreditacion.py")
        with tab[2]:
            switch_page("pages/plan_mejoramiento.py")

    elif section == "Resumen por procesos":
        tab = st.tabs(["Mapa de procesos"])
        with tab[0]:
            switch_page("pages/resumen_por_proceso.py")

    elif section == "Seguimiento operativo":
        tab = st.tabs(["Seguimiento reportes", "Gestión de OM", "Registro OM"])
        with tab[0]:
            switch_page("pages/5_Seguimiento_de_reportes.py")
        with tab[1]:
            switch_page("pages/2_Gestion_OM.py")
        with tab[2]:
            switch_page("pages/4_Registro_OM.py")

if __name__ == "__main__":
    main()
