"""
Sistema de Diseño Unificado - Sistema de Indicadores
Politécnico Grancolombiano

Este módulo define la paleta de colores, tipografía, sombras, iconos y
gradientes para mantener consistencia visual en toda la aplicación.
"""

# =============================================================================
# PALETA DE COLORES INSTITUCIONAL
# =============================================================================

COLORS = {
    # Colores principales
    "primary": "#1A3A5C",           # Azul institucional
    "primary_light": "#2E5C8A",     # Azul claro
    "primary_dark": "#0D1F33",      # Azul oscuro
    
    # Colores de estado
    "success": "#43A047",           # Verde cumplimiento
    "success_light": "#66BB6A",     # Verde claro
    "success_dark": "#2E7D32",      # Verde oscuro
    
    "warning": "#FBAF17",           # Amarillo alerta
    "warning_light": "#FFCC4D",     # Amarillo claro
    "warning_dark": "#F57F17",      # Amarillo oscuro
    
    "danger": "#D32F2F",            # Rojo peligro
    "danger_light": "#EF5350",      # Rojo claro
    "danger_dark": "#B71C1C",       # Rojo oscuro
    
    "info": "#2196F3",              # Azul info
    "info_light": "#64B5F6",        # Azul info claro
    "info_dark": "#1565C0",         # Azul info oscuro
    
    # Colores de cumplimiento específicos
    "cumplimiento": "#43A047",
    "sobrecumplimiento": "#1A3A5C",
    "alerta": "#FBAF17",
    "peligro": "#D32F2F",
    "sin_dato": "#9E9E9E",
    
    # Escala de grises
    "white": "#FFFFFF",
    "gray_50": "#FAFAFA",
    "gray_100": "#F5F5F5",
    "gray_200": "#EEEEEE",
    "gray_300": "#E0E0E0",
    "gray_400": "#BDBDBD",
    "gray_500": "#9E9E9E",
    "gray_600": "#757575",
    "gray_700": "#616161",
    "gray_800": "#424242",
    "gray_900": "#212121",
    "black": "#000000",
    
    # Fondos
    "background": "#F5F7FA",
    "surface": "#FFFFFF",
    "surface_variant": "#F8F9FA",
    
    # Texto
    "text_primary": "#1A1A1A",
    "text_secondary": "#666666",
    "text_disabled": "#9E9E9E",
    "text_on_dark": "#FFFFFF",
}

# =============================================================================
# GRADIENTES

# =============================================================================
# PALETAS POR LÍNEA Y PALETA ALTERNATIVA VIVA
# =============================================================================
LINE_COLOR = {
    # Ejemplos / placeholders — reemplazar por los hex reales del usuario
    "PDI": "#E03A3A",
    "CMI": "#1F6FEB",
    "GESTION": "#8BC34A",
}

# Paleta alternativa vívida para gráficos de no‑cumplimiento y visuales de alta
# atención. Es una lista de colores que se usarán como ciclo para series.
ALT_VIVID_PALETTE = [
    "#FF6B6B",
    "#FFB86B",
    "#FFD56B",
    "#6BFF8A",
    "#6BD2FF",
    "#6B8CFF",
]


def get_line_color(linea):
    """Retorna el color principal para una línea dada.

    Args:
        linea: str o None

    Returns:
        str: hex color
    """
    if not linea:
        return COLORS.get("primary")
    return LINE_COLOR.get(linea.strip().upper(), COLORS.get("primary"))


def get_vivid_palette():
    """Retorna la paleta alternativa vívida."""
    return ALT_VIVID_PALETTE


def get_palette_for_chart(kind="default", linea=None):
    """Selector simple de paleta según el tipo de gráfico y/o la línea.

    Reglas:
    - Si `linea` está presente y mapeada en `LINE_COLOR`, devuelve una paleta
      centrada en ese color.
    - Si `kind=="non_cumplimiento"` devuelve la `ALT_VIVID_PALETTE`.
    - En caso contrario, devuelve una paleta por defecto basada en estados.
    """
    if linea and linea.strip().upper() in LINE_COLOR:
        base = LINE_COLOR[linea.strip().upper()]
        return [base, COLORS["warning"], COLORS["danger"]]

    if kind == "non_cumplimiento":
        return get_vivid_palette()

    return [COLORS["success"], COLORS["warning"], COLORS["danger"]]

# =============================================================================

GRADIENTS = {
    "hero": "linear-gradient(135deg, #1A3A5C 0%, #2E5C8A 100%)",
    "hero_alt": "linear-gradient(135deg, #0D1F33 0%, #1A3A5C 100%)",
    "alert": "linear-gradient(135deg, #D32F2F 0%, #EF5350 100%)",
    "warning": "linear-gradient(135deg, #FBAF17 0%, #FFCC4D 100%)",
    "success": "linear-gradient(135deg, #43A047 0%, #66BB6A 100%)",
    "info": "linear-gradient(135deg, #2196F3 0%, #64B5F6 100%)",
    "glass": "rgba(255, 255, 255, 0.85)",
    "glass_dark": "rgba(26, 58, 92, 0.9)",
    "sidebar": "linear-gradient(180deg, #061a2f 0%, #123a63 100%)",
}

# =============================================================================
# SOMBRAS
# =============================================================================

SHADOWS = {
    "xs": "0 1px 2px rgba(0,0,0,0.05)",
    "sm": "0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.08)",
    "md": "0 4px 6px rgba(0,0,0,0.1), 0 2px 4px rgba(0,0,0,0.06)",
    "lg": "0 10px 15px rgba(0,0,0,0.1), 0 4px 6px rgba(0,0,0,0.05)",
    "xl": "0 20px 25px rgba(0,0,0,0.15), 0 10px 10px rgba(0,0,0,0.04)",
    "2xl": "0 25px 50px rgba(0,0,0,0.25)",
    "inner": "inset 0 2px 4px rgba(0,0,0,0.06)",
    "glow": "0 0 20px rgba(26, 58, 92, 0.3)",
    "glow_success": "0 0 20px rgba(67, 160, 71, 0.3)",
    "glow_warning": "0 0 20px rgba(251, 175, 23, 0.3)",
    "glow_danger": "0 0 20px rgba(211, 47, 47, 0.3)",
}

# =============================================================================
# TIPOGRAFÍA
# =============================================================================

TYPOGRAPHY = {
    "font_family": "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    "font_mono": "'JetBrains Mono', 'Fira Code', monospace",
    
    # Tamaños
    "size_xs": "0.75rem",      # 12px
    "size_sm": "0.875rem",     # 14px
    "size_base": "1rem",       # 16px
    "size_lg": "1.125rem",     # 18px
    "size_xl": "1.25rem",      # 20px
    "size_2xl": "1.5rem",      # 24px
    "size_3xl": "1.875rem",    # 30px
    "size_4xl": "2.25rem",     # 36px
    "size_5xl": "3rem",        # 48px
    "size_6xl": "3.75rem",     # 60px
    
    # Pesos
    "weight_normal": "400",
    "weight_medium": "500",
    "weight_semibold": "600",
    "weight_bold": "700",
    "weight_extrabold": "800",
    
    # Altura de línea
    "leading_tight": "1.25",
    "leading_snug": "1.375",
    "leading_normal": "1.5",
    "leading_relaxed": "1.625",
    "leading_loose": "2",
}

# =============================================================================
# ESPACIADO
# =============================================================================

SPACING = {
    "0": "0",
    "1": "0.25rem",    # 4px
    "2": "0.5rem",     # 8px
    "3": "0.75rem",    # 12px
    "4": "1rem",       # 16px
    "5": "1.25rem",    # 20px
    "6": "1.5rem",     # 24px
    "8": "2rem",       # 32px
    "10": "2.5rem",    # 40px
    "12": "3rem",      # 48px
    "16": "4rem",      # 64px
    "20": "5rem",      # 80px
    "24": "6rem",      # 96px
}

# =============================================================================
# BORDES Y RADIO
# =============================================================================

BORDERS = {
    "width_thin": "1px",
    "width_normal": "2px",
    "width_thick": "4px",
    
    "radius_none": "0",
    "radius_sm": "0.25rem",    # 4px
    "radius_md": "0.5rem",      # 8px
    "radius_lg": "0.75rem",     # 12px
    "radius_xl": "1rem",        # 16px
    "radius_2xl": "1.5rem",     # 24px
    "radius_full": "9999px",
}

# =============================================================================
# ICONOS (FontAwesome classes)
# =============================================================================

ICONS = {
    # Navegación
    "dashboard": "fa-solid fa-chart-line",
    "home": "fa-solid fa-house",
    "menu": "fa-solid fa-bars",
    "close": "fa-solid fa-xmark",
    "back": "fa-solid fa-arrow-left",
    "forward": "fa-solid fa-arrow-right",
    "search": "fa-solid fa-magnifying-glass",
    "filter": "fa-solid fa-filter",
    "settings": "fa-solid fa-gear",
    "user": "fa-solid fa-user",
    "logout": "fa-solid fa-right-from-bracket",
    
    # Indicadores
    "indicador": "fa-solid fa-bullseye",
    "meta": "fa-solid fa-flag-checkered",
    "ejecucion": "fa-solid fa-person-running",
    "cumplimiento": "fa-solid fa-check-circle",
    "tendencia_up": "fa-solid fa-arrow-trend-up",
    "tendencia_down": "fa-solid fa-arrow-trend-down",
    "tendencia_flat": "fa-solid fa-minus",
    
    # Estados
    "peligro": "fa-solid fa-circle-exclamation",
    "alerta": "fa-solid fa-triangle-exclamation",
    "sobrecumplimiento": "fa-solid fa-star",
    "sin_dato": "fa-solid fa-circle-question",
    "success": "fa-solid fa-check",
    "error": "fa-solid fa-xmark",
    "warning": "fa-solid fa-exclamation",
    "info": "fa-solid fa-circle-info",
    
    # Procesos y Organización
    "proceso": "fa-solid fa-sitemap",
    "subproceso": "fa-solid fa-diagram-project",
    "area": "fa-solid fa-building",
    "unidad": "fa-solid fa-users",
    "departamento": "fa-solid fa-building-user",
    
    # Acciones
    "accion": "fa-solid fa-clipboard-check",
    "accion_mejora": "fa-solid fa-wrench",
    "om": "fa-solid fa-lightbulb",
    "plan": "fa-solid fa-map",
    "estrategia": "fa-solid fa-chess",
    
    # Reportes y Documentos
    "reporte": "fa-solid fa-file-lines",
    "excel": "fa-solid fa-file-excel",
    "pdf": "fa-solid fa-file-pdf",
    "download": "fa-solid fa-download",
    "upload": "fa-solid fa-upload",
    "export": "fa-solid fa-file-export",
    "print": "fa-solid fa-print",
    "share": "fa-solid fa-share-nodes",
    "copy": "fa-solid fa-copy",
    
    # Análisis
    "analisis": "fa-solid fa-magnifying-glass-chart",
    "chart": "fa-solid fa-chart-pie",
    "chart_bar": "fa-solid fa-chart-simple",
    "chart_line": "fa-solid fa-chart-line",
    "chart_area": "fa-solid fa-chart-area",
    "table": "fa-solid fa-table",
    "data": "fa-solid fa-database",
    "stats": "fa-solid fa-calculator",
    
    # IA y Tecnología
    "ia": "fa-solid fa-robot",
    "ai": "fa-solid fa-brain",
    "magic": "fa-solid fa-wand-magic-sparkles",
    "automation": "fa-solid fa-gears",
    "predict": "fa-solid fa-crystal-ball",
    
    # Tiempo
    "calendar": "fa-solid fa-calendar",
    "calendar_check": "fa-solid fa-calendar-check",
    "clock": "fa-solid fa-clock",
    "history": "fa-solid fa-clock-rotate-left",
    "time": "fa-solid fa-hourglass",
    "deadline": "fa-solid fa-stopwatch",
    "vencido": "fa-solid fa-calendar-xmark",
    "proximo": "fa-solid fa-calendar-day",
    
    # Calidad
    "quality": "fa-solid fa-award",
    "certificate": "fa-solid fa-certificate",
    "verified": "fa-solid fa-badge-check",
    "acreditacion": "fa-solid fa-graduation-cap",
    "cna": "fa-solid fa-building-columns",
    
    # Comunicación
    "comment": "fa-solid fa-comment",
    "comments": "fa-solid fa-comments",
    "notification": "fa-solid fa-bell",
    "email": "fa-solid fa-envelope",
    "phone": "fa-solid fa-phone",
    "message": "fa-solid fa-message",
    "alert_bell": "fa-solid fa-bell-exclamation",
    
    # Misceláneos
    "eye": "fa-solid fa-eye",
    "eye_slash": "fa-solid fa-eye-slash",
    "edit": "fa-solid fa-pen-to-square",
    "delete": "fa-solid fa-trash",
    "add": "fa-solid fa-plus",
    "remove": "fa-solid fa-minus",
    "save": "fa-solid fa-floppy-disk",
    "refresh": "fa-solid fa-rotate",
    "sync": "fa-solid fa-rotate",
    "expand": "fa-solid fa-expand",
    "collapse": "fa-solid fa-compress",
    "fullscreen": "fa-solid fa-maximize",
    "external": "fa-solid fa-arrow-up-right-from-square",
    "link": "fa-solid fa-link",
    "bookmark": "fa-solid fa-bookmark",
    "star": "fa-solid fa-star",
    "heart": "fa-solid fa-heart",
    "flag": "fa-solid fa-flag",
    "pin": "fa-solid fa-thumbtack",
    "tag": "fa-solid fa-tag",
    "folder": "fa-solid fa-folder",
    "file": "fa-solid fa-file",
    "image": "fa-solid fa-image",
    "video": "fa-solid fa-video",
    "help": "fa-solid fa-circle-question",
    "support": "fa-solid fa-headset",
    "info_circle": "fa-solid fa-circle-info",
    "lightbulb": "fa-solid fa-lightbulb",
    "fire": "fa-solid fa-fire",
    "bolt": "fa-solid fa-bolt",
    "sun": "fa-solid fa-sun",
    "moon": "fa-solid fa-moon",
    "globe": "fa-solid fa-globe",
    "map": "fa-solid fa-map-location-dot",
    "location": "fa-solid fa-location-dot",
    "marker": "fa-solid fa-map-pin",
}

# =============================================================================
# TRANSICIONES Y ANIMACIONES
# =============================================================================

TRANSITIONS = {
    "fast": "150ms ease",
    "normal": "300ms ease",
    "slow": "500ms ease",
    "bounce": "500ms cubic-bezier(0.68, -0.55, 0.265, 1.55)",
    "spring": "400ms cubic-bezier(0.175, 0.885, 0.32, 1.275)",
}

# =============================================================================
# Z-INDEX
# =============================================================================

Z_INDEX = {
    "dropdown": 100,
    "sticky": 200,
    "fixed": 300,
    "modal_backdrop": 400,
    "modal": 500,
    "popover": 600,
    "tooltip": 700,
    "toast": 800,
    "loading": 900,
}

# =============================================================================
# BREAKPOINTS (para responsive)
# =============================================================================

BREAKPOINTS = {
    "sm": "640px",
    "md": "768px",
    "lg": "1024px",
    "xl": "1280px",
    "2xl": "1536px",
}

# =============================================================================
# FUNCIONES AUXILIARES
# =============================================================================

def get_color_for_cumplimiento(valor):
    """
    Retorna el color correspondiente según el valor de cumplimiento.
    
    Args:
        valor: Porcentaje de cumplimiento (0-100)
    
    Returns:
        str: Código hexadecimal del color
    """
    if valor >= 100:
        return COLORS["sobrecumplimiento"]
    elif valor >= 80:
        return COLORS["cumplimiento"]
    elif valor >= 60:
        return COLORS["alerta"]
    else:
        return COLORS["peligro"]


def get_icon_for_estado(estado):
    """
    Retorna el icono FontAwesome correspondiente al estado.
    
    Args:
        estado: str - Estado del indicador
    
    Returns:
        str: Clase del icono FontAwesome
    """
    estado = estado.lower() if estado else ""
    
    mapping = {
        "cumplimiento": ICONS["cumplimiento"],
        "sobrecumplimiento": ICONS["sobrecumplimiento"],
        "alerta": ICONS["alerta"],
        "peligro": ICONS["peligro"],
        "sin dato": ICONS["sin_dato"],
        "success": ICONS["success"],
        "warning": ICONS["warning"],
        "danger": ICONS["peligro"],
        "info": ICONS["info"],
    }
    
    return mapping.get(estado, ICONS["sin_dato"])


def get_gradient_for_estado(estado):
    """
    Retorna el gradiente correspondiente al estado.
    
    Args:
        estado: str - Estado del indicador
    
    Returns:
        str: CSS gradient
    """
    estado = estado.lower() if estado else ""
    
    mapping = {
        "cumplimiento": GRADIENTS["success"],
        "sobrecumplimiento": GRADIENTS["hero"],
        "alerta": GRADIENTS["warning"],
        "peligro": GRADIENTS["alert"],
        "success": GRADIENTS["success"],
        "warning": GRADIENTS["warning"],
        "danger": GRADIENTS["alert"],
    }
    
    return mapping.get(estado, GRADIENTS["glass"])


def get_shadow_for_depth(depth):
    """
    Retorna la sombra correspondiente a la profundidad.
    
    Args:
        depth: str - Nivel de profundidad (xs, sm, md, lg, xl, 2xl)
    
    Returns:
        str: CSS box-shadow
    """
    return SHADOWS.get(depth, SHADOWS["md"])


# =============================================================================
# CSS GENERATOR
# =============================================================================

def generate_css_variables():
    """
    Genera las variables CSS para usar en toda la aplicación.
    
    Returns:
        str: Bloque CSS con variables
    """
    css = """
    :root {
        /* Colores */
        --color-primary: {primary};
        --color-primary-light: {primary_light};
        --color-primary-dark: {primary_dark};
        
        --color-success: {success};
        --color-success-light: {success_light};
        --color-success-dark: {success_dark};
        
        --color-warning: {warning};
        --color-warning-light: {warning_light};
        --color-warning-dark: {warning_dark};
        
        --color-danger: {danger};
        --color-danger-light: {danger_light};
        --color-danger-dark: {danger_dark};
        
        --color-info: {info};
        --color-info-light: {info_light};
        --color-info-dark: {info_dark};
        
        --color-background: {background};
        --color-surface: {surface};
        --color-text-primary: {text_primary};
        --color-text-secondary: {text_secondary};
        
        /* Sombras */
        --shadow-sm: {shadow_sm};
        --shadow-md: {shadow_md};
        --shadow-lg: {shadow_lg};
        --shadow-xl: {shadow_xl};
        
        /* Bordes */
        --radius-sm: {radius_sm};
        --radius-md: {radius_md};
        --radius-lg: {radius_lg};
        --radius-xl: {radius_xl};
        
        /* Tipografía */
        --font-family: {font_family};
    }
    """.format(
        primary=COLORS["primary"],
        primary_light=COLORS["primary_light"],
        primary_dark=COLORS["primary_dark"],
        success=COLORS["success"],
        success_light=COLORS["success_light"],
        success_dark=COLORS["success_dark"],
        warning=COLORS["warning"],
        warning_light=COLORS["warning_light"],
        warning_dark=COLORS["warning_dark"],
        danger=COLORS["danger"],
        danger_light=COLORS["danger_light"],
        danger_dark=COLORS["danger_dark"],
        info=COLORS["info"],
        info_light=COLORS["info_light"],
        info_dark=COLORS["info_dark"],
        background=COLORS["background"],
        surface=COLORS["surface"],
        text_primary=COLORS["text_primary"],
        text_secondary=COLORS["text_secondary"],
        shadow_sm=SHADOWS["sm"],
        shadow_md=SHADOWS["md"],
        shadow_lg=SHADOWS["lg"],
        shadow_xl=SHADOWS["xl"],
        radius_sm=BORDERS["radius_sm"],
        radius_md=BORDERS["radius_md"],
        radius_lg=BORDERS["radius_lg"],
        radius_xl=BORDERS["radius_xl"],
        font_family=TYPOGRAPHY["font_family"],
    )
    
    return css


# Exportar todo
__all__ = [
    "COLORS",
    "GRADIENTS",
    "SHADOWS",
    "TYPOGRAPHY",
    "SPACING",
    "BORDERS",
    "ICONS",
    "TRANSITIONS",
    "Z_INDEX",
    "BREAKPOINTS",
    "get_color_for_cumplimiento",
    "get_icon_for_estado",
    "get_gradient_for_estado",
    "get_shadow_for_depth",
    "generate_css_variables",
    "LINE_COLOR",
    "ALT_VIVID_PALETTE",
    "get_line_color",
    "get_vivid_palette",
    "get_palette_for_chart",
]
