import streamlit as st
from streamlit_option_menu import option_menu

st.set_page_config(page_title="Sistema de Indicadores", layout="wide")

def main():
    # Configuración del sidebar
    with st.sidebar:
        st.title("Sistema de Indicadores")
        st.markdown("Politécnico Grancolombiano · v2.0 Estratégico")
        st.markdown("---")

        # Menú principal
        menu = option_menu(
            menu_title="Navegación",
            options=["Inicio estratégico", "Resumen por procesos", "Seguimiento operativo"],
            icons=["house", "bar-chart", "clipboard-check"],
            menu_icon="cast",
            default_index=0,
        )

    # Lógica de navegación
    if menu == "Inicio estratégico":
        st.title("Inicio estratégico")
        tab1, tab2, tab3 = st.tabs(["CMI Estratégico", "PDI / Acreditación", "Plan de Mejoramiento"])
        with tab1:
            st.write("Contenido de CMI Estratégico")
        with tab2:
            st.write("Contenido de PDI / Acreditación")
        with tab3:
            st.write("Contenido de Plan de Mejoramiento")

    elif menu == "Resumen por procesos":
        st.title("Resumen por procesos")
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
            "📊 Indicadores",
            "📋 Reporte de indicadores",
            "✅ Calidad de información",
            "🔍 Resultados de auditoría",
            "💡 Propuestos",
            "🤖 Análisis IA",
        ])
        with tab1:
            st.write("Contenido de Indicadores")
        with tab2:
            st.write("Contenido de Reporte de indicadores")
        with tab3:
            st.write("Contenido de Calidad de información")
        with tab4:
            st.write("Contenido de Resultados de auditoría")
        with tab5:
            st.write("Contenido de Propuestos")
        with tab6:
            st.write("Contenido de Análisis IA")

    elif menu == "Seguimiento operativo":
        st.title("Seguimiento operativo")
        tab1, tab2, tab3 = st.tabs([
            "Seguimiento reportes",
            "Gestión de OM",
            "Registro OM",
        ])

        # Seguimiento reportes
        with tab1:
            st.subheader("Seguimiento de reportes")
            st.write("Esta sección permite visualizar el estado de los reportes generados.")
            st.write("""
                - Reportes pendientes
                - Reportes en proceso
                - Reportes completados
            """)
            # Ejemplo de tabla
            data = {
                "Reporte": ["Reporte 1", "Reporte 2", "Reporte 3"],
                "Estado": ["Pendiente", "En proceso", "Completado"],
                "Fecha": ["2026-04-01", "2026-04-02", "2026-04-03"]
            }
            st.table(data)

        # Gestión de OM
        with tab2:
            st.subheader("Gestión de OM")
            st.write("Esta sección permite gestionar las órdenes de mejora (OM).")
            st.write("""
                - Crear nuevas OM
                - Actualizar estado de OM existentes
                - Consultar historial de OM
            """)
            # Ejemplo de formulario
            with st.form("form_gestion_om"):
                om_name = st.text_input("Nombre de la OM")
                om_status = st.selectbox("Estado", ["Pendiente", "En proceso", "Completado"])
                submitted = st.form_submit_button("Guardar")
                if submitted:
                    st.success(f"OM '{om_name}' guardada con estado '{om_status}'.")

        # Registro OM
        with tab3:
            st.subheader("Registro de OM")
            st.write("Esta sección permite registrar nuevas órdenes de mejora.")
            st.write("""
                - Ingresar detalles de la OM
                - Asignar responsables
                - Establecer fechas de seguimiento
            """)
            # Ejemplo de entrada de datos
            om_details = st.text_area("Detalles de la OM")
            om_responsible = st.text_input("Responsable")
            om_date = st.date_input("Fecha de seguimiento")
            if st.button("Registrar OM"):
                st.success("OM registrada exitosamente.")

if __name__ == "__main__":
    main()
