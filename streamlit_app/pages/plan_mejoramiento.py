"""
Plan de Mejoramiento — stub de implementación.
Muestra avance por línea estratégica, indicadores pendientes y estado general.
"""
import streamlit as st
import pandas as pd
import numpy as np


def run():
    st.title("Plan de Mejoramiento")
    st.info("Módulo en construcción. Aquí se mostrará el avance del plan institucional.")

    np.random.seed(77)
    lineas = ["Formación", "Investigación", "Extensión", "Internacionalización", "Gestión"]
    data = []
    for l in lineas:
        data.append({
            "Línea estratégica": l,
            "Indicadores planeados": np.random.randint(10, 30),
            "Indicadores en curso": np.random.randint(5, 15),
            "Indicadores cumplidos": np.random.randint(3, 12),
            "Avance (%)": round(np.random.uniform(30, 90), 1),
            "Estado": "🟢 En curso" if np.random.random() > 0.3 else "🟡 En riesgo"
        })
    df = pd.DataFrame(data)

    st.dataframe(df, use_container_width=True)

    st.markdown("---")
    st.subheader("Indicadores pendientes")
    pendientes = df[df["Estado"].str.contains("riesgo")]
    st.dataframe(pendientes, use_container_width=True)