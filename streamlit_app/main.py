import streamlit as st

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

    pages = {
        "Resumen estrategico": [
            st.Page("pages/cmi_estrategico.py", title="CMI Estrategico", icon="📈"),
            st.Page("pages/pdi_acreditacion.py", title="PDI / Acreditacion", icon="🏛️"),
            st.Page("pages/plan_mejoramiento.py", title="Plan de Mejoramiento", icon="📋"),
        ],
        "Resumen por procesos": [
            st.Page("pages/resumen_por_proceso.py", title="Mapa de procesos", icon="🗺️"),
        ],
        "Seguimiento operativo": [
            st.Page("pages/5_Seguimiento_de_reportes.py", title="Seguimiento reportes", icon="📊"),
            st.Page("pages/2_Gestion_OM.py", title="Gestion de OM", icon="⚠️"),
            st.Page("pages/4_Registro_OM.py", title="Registro OM", icon="📝"),
        ],
    }
    pg = st.navigation(pages)
    pg.run()


if __name__ == "__main__":
    main()
