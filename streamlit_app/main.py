from pathlib import Path
import sys

import streamlit as st
from streamlit_option_menu import option_menu

# Agregar streamlit_app al path de imports
sys.path.insert(0, str(Path(__file__).parent))

st.set_page_config(page_title="Sistema de Indicadores", layout="wide")


def load_css(file_path):
    """Carga un archivo CSS y lo retorna como una cadena."""
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()

def _inject_styles():
    """Inyecta estilos locales con ruta robusta para local y cloud."""
    base = Path(__file__).resolve().parent / "styles"
    css_files = ["styles.css", "main.css"]
    for css_name in css_files:
        css_path = base / css_name
        if not css_path.exists():
            css_path = Path(f"streamlit_app/styles/{css_name}")
        if css_path.exists():
            styles = load_css(str(css_path))
            st.markdown(f"<style>{styles}</style>", unsafe_allow_html=True)


def _load_sidebar_logo_html():
    from base64 import b64encode
    from pathlib import Path

    base = Path(__file__).parent / "assets"
    logo_candidates = [
        base / "Wallpaper-POLI.jpg.webp",
        base / "Wallpaper-POLI.webp",
        base / "Wallpaper-POLI.jpg",
        base / "Wallpaper-POLI.png",
    ]
    logo_path = next((p for p in logo_candidates if p.exists()), None)
    if logo_path is None:
        return None
    mime = "image/webp" if logo_path.suffix.lower() == ".webp" else "image/png"
    try:
        encoded = b64encode(logo_path.read_bytes()).decode("ascii")
        return f"<img src='data:{mime};base64,{encoded}' alt='Logo' class='sidebar-logo-img'/>"
    except Exception:
        return None


def _get_git_commit_short():
    import subprocess, os
    try:
        p = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, check=True)
        return p.stdout.strip()
    except Exception:
        return os.getenv("GIT_COMMIT", "unknown")


def main():
    _inject_styles()

    # Importar páginas bajo demanda para evitar circular imports durante la carga
    from streamlit_app.pages import (
        cmi_estrategico,
        gestion_om,
        plan_mejoramiento,
        resumen_general,
        resumen_por_proceso,
        seguimiento_reportes,
        tablero_operativo,
        pdi_acreditacion,
    )

    # Configuración del sidebar
    with st.sidebar:
        logo_html = _load_sidebar_logo_html()
        if logo_html:
            logo_block = f"<div class='sidebar-logo'>{logo_html}</div>"
        else:
            logo_block = """
    <div class='sidebar-logo'>
      <svg width='28' height='28' viewBox='0 0 24 24' fill='none' xmlns='http://www.w3.org/2000/svg'>
        <rect width='24' height='24' rx='4' fill='#ffffff22'/>
        <text x='12' y='16' font-size='10' text-anchor='middle' fill='white' font-family='Arial' font-weight='700'>PG</text>
      </svg>
    </div>
"""

        header_html = f"""
<div class='sidebar-header'>
  {logo_block}
  <div>
    <div class='sidebar-title'>Sistema de Indicadores</div>
        <div class='sidebar-subtitle'>Politécnico Grancolombiano</div>
  </div>
</div>
"""
        st.markdown(header_html, unsafe_allow_html=True)
        st.markdown("<div class='sidebar-divider'></div>", unsafe_allow_html=True)
        st.markdown("<div class='sidebar-section-title'>Navegación</div>", unsafe_allow_html=True)

        menu = option_menu(
            menu_title=None,
            options=["Resumen general", "Resumen Estratégico", "Resumen por procesos", "Seguimiento operativo"],
            icons=["file-text", "house", "layers", "clipboard-check"],
            menu_icon="cast",
            default_index=0,
        )

        # Mantener sidebar limpio: el foco es la navegación y el encabezado.
        st.markdown("<style>.sidebar-status-card{display:none!important;}.version-box{display:none!important;}</style>", unsafe_allow_html=True)

    # Routing simple a páginas
    if menu == "Resumen Estratégico":
        # Resumen estratégico: cada pestaña tiene su propio resumen ejecutivo.
        tab_cmi, tab_plan, tab_acred = st.tabs(["CMI Estratégico", "Plan de Mejoramiento", "Gestión y Acreditación"])
        with tab_cmi:
            cmi_estrategico.render()
        with tab_plan:
            plan_mejoramiento.render()
        with tab_acred:
            pdi_acreditacion.render()

    elif menu == "Resumen general":
        resumen_general.render()

    elif menu == "Resumen por procesos":
        # Resumen por procesos se renderiza como una vista con sus propias pestañas (ya implementado en el módulo)
        resumen_por_proceso.render()

    elif menu == "Seguimiento operativo":
        # Agrupar vistas operativas en pestañas internas
        tab_a, tab_b, tab_c = st.tabs(
            ["Tablero Operativo", "Seguimiento reportes", "Gestión de OM"]
        )
        with tab_a:
            tablero_operativo.render()
        with tab_b:
            seguimiento_reportes.render()
        with tab_c:
            gestion_om.render()


if __name__ == "__main__":
    main()
