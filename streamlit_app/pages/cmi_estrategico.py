import streamlit as st

def render():
    st.title("CMI Estratégico")
    st.write("Vista de indicadores estratégicos por perspectiva (CMI). Aquí irá radar, scorecards y brechas.")
    cols = st.columns([2, 1])
    with cols[0]:
        st.markdown("### Radar por perspectivas (mock)")
        st.write("(Gráfica Plotly - por implementar con datos reales)")
    with cols[1]:
        st.markdown("### Brechas y hallazgos")
        st.write("Listado de brechas detectadas (mock)")
