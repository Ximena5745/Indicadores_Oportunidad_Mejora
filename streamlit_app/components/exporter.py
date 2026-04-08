import io
import streamlit as st
import pandas as pd
import plotly.io as pio
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, Table
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors


def download_csv(df: pd.DataFrame, filename: str = 'export.csv'):
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(label='Descargar CSV', data=csv, file_name=filename, mime='text/csv')


def download_pdf(figs: list, filename: str = 'reporte.pdf', title: str = 'Reporte', table_df: pd.DataFrame = None, metadata: dict = None):
    """Genera un PDF con portada, figuras y una tabla opcional.

    Args:
        figs: lista de figuras Plotly
        filename: nombre para descarga
        title: título de la portada
        table_df: DataFrame opcional para insertar como tabla
        metadata: dict con claves como 'periodo' o 'unidades' para portada
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4)
    styles = getSampleStyleSheet()
    elems = []

    # Portada
    elems.append(Paragraph(title, styles['Title']))
    elems.append(Spacer(1, 12))
    if metadata:
        for k, v in metadata.items():
            elems.append(Paragraph(f"<b>{k}:</b> {v}", styles['Normal']))
        elems.append(Spacer(1, 12))

    elems.append(Paragraph('Generado por Sistema de Indicadores', styles['Normal']))
    elems.append(Spacer(1, 24))

    # Figuras
    for fig in figs:
        img_bytes = pio.to_image(fig, format='png', engine='kaleido')
        img_buf = io.BytesIO(img_bytes)
        rl_img = RLImage(img_buf, width=450, height=300)
        elems.append(rl_img)
        elems.append(Spacer(1, 12))

    # Tabla opcional
    if table_df is not None and not table_df.empty:
        elems.append(Spacer(1, 12))
        elems.append(Paragraph('Tabla de datos', styles['Heading2']))
        # convertir DF a lista de listas
        data = [table_df.columns.tolist()] + table_df.fillna('').astype(str).values.tolist()
        tbl = Table(data, repeatRows=1)
        tbl.setStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f0f0f0')),
            ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ])
        elems.append(tbl)

    doc.build(elems)
    buf.seek(0)
    st.download_button('Descargar PDF', data=buf, file_name=filename, mime='application/pdf')
