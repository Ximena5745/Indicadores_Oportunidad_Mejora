import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

try:
    from ..services.data_service import DataService
    from ..styles.design_system import COLORS, get_vivid_palette
except (ImportError, ValueError):
    from services.data_service import DataService
    from styles.design_system import COLORS, get_vivid_palette


class Charts:
    def __init__(self, service: DataService = None):
        self.service = service or DataService()

    def draw_performance_chart(self):
        df = self.service.get_timeseries()
        if df.empty:
            st.info("No hay datos de desempeño disponibles.")
            return

        fig = go.Figure()
        primary = COLORS.get("primary")
        vivid = get_vivid_palette()[0]

        fig.add_trace(
            go.Bar(
                x=df["date"],
                y=df["value"],
                name="Realizado",
                marker_color=primary,
                marker_line_color=primary,
                marker_line_width=1,
                hovertemplate="%{x|%b %Y}<br>Desempeño: %{y}<extra></extra>",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=df["date"],
                y=df["value"],
                name="Tendencia",
                mode="lines+markers",
                line=dict(color=vivid, width=4),
                marker=dict(size=8),
                hovertemplate="%{x|%b %Y}<br>Tendencia: %{y}<extra></extra>",
            )
        )
        fig.update_layout(
            title="Curva de desempeño institucional",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=0, r=0, t=40, b=20),
            xaxis=dict(showgrid=False, tickformat="%b %Y", zeroline=False),
            yaxis=dict(showgrid=True, gridcolor="#e6edf5", zeroline=False),
        )
        st.plotly_chart(fig, use_container_width=True)

    def draw_semaforo(self):
        df = self.service.get_semaforo()
        max_val = df["valor"].max() if not df.empty else 1
        color_map = {
            "Peligro": COLORS.get("danger"),
            "Alerta": COLORS.get("warning"),
            "Cumplimiento": COLORS.get("success"),
            "Sobrecumplimiento": COLORS.get("sobrecumplimiento"),
        }
        html_rows = [
            "<div class='html-bar-chart'>",
            "<div style='font-weight:700;margin-bottom:14px;color:#0f2137;'>Semáforo global</div>",
        ]
        for _, row in df.iterrows():
            estado = str(row["estado"])
            valor = int(row["valor"])
            width = min(max(valor / max_val * 100, 2), 100)
            color = color_map.get(estado, "#7d8be3")
            html_rows.append(
                f"<div class='html-bar-item'>"
                f"<div class='bar-axis'>"
                f"<div class='bar-label'>{estado}</div>"
                f"<div class='bar-track'><div class='bar-fill' style='width:{width}%;background:{color};'></div></div>"
                f"</div>"
                f"<div class='bar-value'>{valor}</div>"
                f"</div>"
            )
        html_rows.append("</div>")
        st.markdown("".join(html_rows), unsafe_allow_html=True)


def deterministic_timeseries():
    return DataService().get_timeseries()


def draw_performance_chart():
    return Charts().draw_performance_chart()


def draw_semaforo():
    return Charts().draw_semaforo()
