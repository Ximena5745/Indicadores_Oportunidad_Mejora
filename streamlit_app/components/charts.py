import pandas as pd
import plotly.express as px
import streamlit as st

def deterministic_timeseries():
    # deterministic mock data (fixed values)
    dates = pd.date_range(end=pd.Timestamp("2026-04-07"), periods=12, freq="M")
    values = [72, 74, 73, 75, 77, 78, 80, 79, 81, 82, 83, 85]
    df = pd.DataFrame({"date": dates, "value": values})
    return df

def draw_performance_chart():
    df = deterministic_timeseries()
    fig = px.bar(df, x="date", y="value", labels={"value": "Desempeño"}, title="Curva de desempeño institucional")
    st.plotly_chart(fig, use_container_width=True)

def draw_semaforo():
    sem = {"estado": ["Peligro", "Alerta", "Cumplimiento", "Sobrecumplimiento"], "valor": [20, 24, 85, 115]}
    df = pd.DataFrame(sem)
    fig = px.pie(df, names="estado", values="valor", color_discrete_map={"Peligro": "#ff3b30", "Alerta": "#ffab00", "Cumplimiento": "#00c853", "Sobrecumplimiento": "#00b8d4"}, title="Semáforo global")
    st.plotly_chart(fig, use_container_width=True)
