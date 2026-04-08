"""
Coherencia de metas (ICM) — stub de implementación.
Accede a datos de indicadores y muestra comparativo meta vs comportamiento histórico.
"""
import streamlit as st
import pandas as pd
import numpy as np


def run():
    st.title("Coherencia de metas (ICM)")
    st.info("Módulo en construcción. Aquí se mostrarán indicadores con distancia meta/comportamiento > 20%.")

    # Datos mock de ejemplo
    np.random.seed(33)
    procesos = ["Admisión", "Formación", "Investigación", "Extensión", "Gestión"]
    datos = []
    for p in procesos:
        for i in range(1, 6):
            meta = np.random.uniform(70, 100)
            actual = meta + np.random.uniform(-25, 25)
            distancia = (actual - meta) / meta * 100
            datos.append({
                "Proceso": p,
                "Indicador": f"{p[:3].upper()}-{i:02d}",
                "Meta (%)": round(meta, 1),
                "Valor real (%)": round(actual, 1),
                "Distancia (%)": round(distancia, 1),
                "Estado": "🔴 Crítico" if abs(distancia) > 20 else ("🟡 Alerta" if abs(distancia) > 10 else "🟢 Normal")
            })
    df = pd.DataFrame(datos)

    st.dataframe(df, use_container_width=True)

    st.markdown("---")
    st.subheader("Indicadores fuera de rango")
    fuera = df[df["Distancia (%)"].abs() > 20]
    st.dataframe(fuera, use_container_width=True)