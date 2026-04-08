"""
Panel de monitoreo de cargas - Fase 1: Gobierno y calidad de datos.
Sistema de Indicadores SGIND.

Este módulo proporciona un dashboard Streamlit para visualizar:
- Estado de las cargas de archivos
- Resultados de validaciones
- Alertas y errores
"""

import streamlit as st
import pandas as pd
import json
from pathlib import Path
from datetime import datetime

# =============================================================================
# CONFIGURACIÓN
# =============================================================================

ARTIFACTS_PATH = Path("data/output/artifacts")
OUTPUT_PATH = Path("data/output")
LOGS_PATH = Path("data/output/logs")

# =============================================================================
# FUNCIONES DE CARGA DE DATOS
# =============================================================================

def cargar_ultimo_artefacto() -> dict:
    """Carga el artefacto de ingesta más reciente."""
    if not ARTIFACTS_PATH.exists():
        return None
    
    archivos = list(ARTIFACTS_PATH.glob("ingesta_*.json"))
    if not archivos:
        return None
    
    # Obtener el más reciente
    ultimo = sorted(archivos)[-1]
    with open(ultimo, "r", encoding="utf-8") as f:
        return json.load(f)

def cargar_reporte_qa() -> str:
    """Carga el reporte QA más reciente."""
    if not LOGS_PATH.exists():
        return None
    
    reportes = list(LOGS_PATH.glob("reporte_qa_*.txt"))
    if not reportes:
        return None
    
    ultimo = sorted(reportes)[-1]
    with open(ultimo, "r", encoding="utf-8") as f:
        return f.read()

def cargar_historico() -> pd.DataFrame:
    """Carga el histórico de ejecuciones."""
    if not ARTIFACTS_PATH.exists():
        return pd.DataFrame()
    
    archivos = list(ARTIFACTS_PATH.glob("ingesta_*.json"))
    datos = []
    
    for archivo in archivos:
        with open(archivo, "r", encoding="utf-8") as f:
            data = json.load(f)
            datos.append({
                "fecha": data["resumen"]["fecha"],
                "total_archivos": data["resumen"]["total_archivos"],
                "exitosos": data["resumen"]["exitosos"],
                "fallidos": data["resumen"]["fallidos"],
                "total_registros": data["resumen"]["total_registros"]
            })
    
    return pd.DataFrame(datos)

# =============================================================================
# PÁGINA PRINCIPAL
# =============================================================================

def main():
    # Deshabilitando configuración de página para evitar interferencias
    # st.set_page_config(
    #     page_title="Monitoreo de Cargas - SGIND",
    #     page_icon="📊",
    #     layout="wide"
    # )
    
    st.title("📊 Panel de Monitoreo de Cargas")
    st.markdown("---")
    
    # Cargar datos
    artefacto = cargar_ultimo_artefacto()
    reporte_qa = cargar_reporte_qa()
    historico = cargar_historico()
    
    # =================================================================
    # MÉTRICAS PRINCIPALES
    # =================================================================
    if artefacto:
        resumen = artefacto["resumen"]
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Total Archivos",
                resumen["total_archivos"],
                help="Total de archivos procesados en la última ejecución"
            )
        
        with col2:
            exitosos = resumen["exitosos"]
            color = "normal" if exitosos == resumen["total_archivos"] else "off"
            st.metric(
                "✅ Exitosos",
                exitosos,
                delta=None,
                delta_color=color
            )
        
        with col3:
            fallidos = resumen["fallidos"]
            st.metric(
                "❌ Fallidos",
                fallidos,
                delta=-fallidos if fallidos > 0 else None,
                delta_color="inverse"
            )
        
        with col4:
            st.metric(
                "📋 Total Registros",
                f"{resumen['total_registros']:,}",
                help="Total de registros procesados"
            )
        
        st.markdown("---")
        
        # =================================================================
        # HISTÓRICO DE EJECUCIONES
        # =================================================================
        if not historico.empty:
            st.subheader("📈 Histórico de Ejecuciones")
            
            # Convertir fechas
            historico["fecha"] = pd.to_datetime(historico["fecha"])
            historico = historico.sort_values("fecha", ascending=False)
            
            # Gráfico de líneas
            st.line_chart(
                historico.set_index("fecha")[["exitosos", "fallidos"]],
                height=250
            )
            
            st.markdown("---")
        
        # =================================================================
        # DETALLE POR ARCHIVO
        # =================================================================
        st.subheader("📁 Detalle por Archivo")
        
        detalle_df = pd.DataFrame(artefacto["detalle"])
        detalle_df = detalle_df.sort_values("exitosa", ascending=True)
        
        # Aplicar formato condicional
        def formatear_estado(exitosa):
            return "✅ Exitoso" if exitosa else "❌ Fallido"
        
        detalle_df["Estado"] = detalle_df["exitosa"].apply(formatear_estado)
        
        # Filtrar por estado
        col_filtro1, col_filtro2 = st.columns(2)
        with col_filtro1:
            filtro_estado = st.multiselect(
                "Filtrar por estado",
                options=["✅ Exitoso", "❌ Fallido"],
                default=["✅ Exitoso", "❌ Fallido"]
            )
        
        # Filtrar dataframe
        filtro_map = {"✅ Exitoso": True, "❌ Fallido": False}
        filtro_booleano = [filtro_map[f] for f in filtro_estado]
        detalle_filtrado = detalle_df[detalle_df["exitosa"].isin(filtro_booleano)]
        
        # Mostrar tabla
        if not detalle_filtrado.empty:
            display_df = detalle_filtrado[[
                "archivo", "plantilla", "Estado",
                "registros_leidos", "registros_validos"
            ]].copy()
            display_df.columns = ["Archivo", "Plantilla", "Estado", "Leídos", "Válidos"]
            
            st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No hay archivos que coincidan con el filtro.")
        
        # =================================================================
        # ALERTAS Y ERRORES
        # =================================================================
        st.subheader("🚨 Alertas y Validaciones")
        
        # Recopilar todas las validaciones
        todas_validaciones = []
        for item in artefacto["detalle"]:
            for validacion in item.get("validaciones", []):
                validacion["archivo"] = item["archivo"]
                todas_validaciones.append(validacion)
        
        if todas_validaciones:
            validaciones_df = pd.DataFrame(todas_validaciones)
            
            # Filtrar por tipo
            col_filtro3, col_filtro4 = st.columns(2)
            with col_filtro3:
                filtro_tipo = st.multiselect(
                    "Tipo de validación",
                    options=validaciones_df["estado"].unique().tolist(),
                    default=validaciones_df["estado"].unique().tolist()
                )
            
            validaciones_filtradas = validaciones_df[
                validaciones_df["estado"].isin(filtro_tipo)
            ]
            
            # Agrupar por estado
            conteo_estado = validaciones_df["estado"].value_counts()
            
            col_alerta1, col_alerta2 = st.columns(2)
            with col_alerta1:
                if "ERROR" in conteo_estado.index:
                    st.error(f"⚠️ {conteo_estado.get('ERROR', 0)} Errores detectados")
                else:
                    st.success("✅ Sin errores")
            
            with col_alerta2:
                st.warning(f"⚠️ {conteo_estado.get('WARNING', 0)} Advertencias")
            
            if not validaciones_filtradas.empty:
                st.dataframe(
                    validaciones_filtradas[["archivo", "campo", "estado", "mensaje"]],
                    use_container_width=True,
                    hide_index=True
                )
        else:
            st.success("✅ No se detectaron alertas o validaciones")
        
        # =================================================================
        # REPORTE QA COMPLETO
        # =================================================================
        with st.expander("📄 Ver Reporte QA Completo"):
            if reporte_qa:
                st.text(reporte_qa)
            else:
                st.info("No hay reporte QA disponible")
        
        # =================================================================
        # ÚLTIMA ACTUALIZACIÓN
        # =================================================================
        st.markdown("---")
        st.caption(
            f"Última actualización: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
    else:
        st.warning("⚠️ No hay datos de ingesta disponibles. Ejecute primero el script de ingesta.")
        
        st.code(
            "python scripts/ingesta_plantillas.py",
            language="bash"
        )

# =============================================================================
# EJECUCIÓN
# =============================================================================

if __name__ == "__main__":
    main()
