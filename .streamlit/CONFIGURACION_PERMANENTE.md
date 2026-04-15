# 🎨 Configuración Permanente — Layout Ancho (Wide)

**Documento:** Referencia de Configuración Streamlit  
**Fecha Actualización:** 15 de abril de 2026  
**Status:** ✅ PERMANENTE — No modificar sin justificación documentada

---

## 🎯 OBJETIVO

Mantener **layout wide** sin espaciado lateral excesivo en TODAS las iteraciones del dashboard.

**Problema Histórico:** La configuración se perdía/se dañaba en iteraciones posteriores, causando desperdicio de espacio horizontal.

---

## 📍 ARCHIVOS CRÍTICOS (NO ELIMINAR)

### 1. `.streamlit/config.toml` ⭐ CRÍTICO

```toml
[client]
toolbarMode = "minimal"        # Barra minimal
showErrorDetails = false       # Menos clutter

[server]
headless = true
enableCORS = false
enableXsrfProtection = false
maxUploadSize = 50
maxMessageSize = 200

[theme]
base = "light"
primaryColor = "#1A3A5C"
backgroundColor = "#F4F6F9"
secondaryBackgroundColor = "#FFFFFF"
textColor = "#212121"
font = "sans serif"
```

**✅ PRESENTE:** Sección `[client]` con `toolbarMode = "minimal"`

**❌ NO DEBE CONTENER:** Márgenes adicionales o restricciones de ancho

---

### 2. `streamlit_app/main.py` ⭐ CRÍTICO

**Línea 6 (inmutable):**
```python
st.set_page_config(page_title="Sistema de Indicadores", layout="wide")
```

**✅ VERIFICAR:** Este código SIEMPRE debe estar en main.py línea 6 (antes de cualquier import de datos)

**❌ NO MOVER:** No debe estar dentro de funciones ni condicionales

---

### 3. `streamlit_app/styles/main.css` ⭐ CRÍTICO

**Secciones Obligatorias:**

```css
/* Contenedor principal - 100% ancho */
[data-testid="stAppViewContainer"] {
    padding-left: 0 !important;
    padding-right: 0 !important;
    max-width: 100% !important;
    width: 100% !important;
}

/* Bloque - márgenes mínimos */
.block-container {
    padding-left: 1rem !important;
    padding-right: 1rem !important;
    max-width: 100% !important;
}
```

**✅ VERIFICAR:** Estos dos selectores DEBEN estar presentes

**❌ NO ANULAR:** No agregar `max-width: 90%` u otras restricciones

---

## 🔧 CHECKLIST DE VALIDACIÓN

Antes de cada release, verificar:

- [ ] `.streamlit/config.toml` existe y contiene `[client]` section
- [ ] `streamlit_app/main.py` línea 6: `st.set_page_config(..., layout="wide")`
- [ ] `streamlit_app/styles/main.css` contiene `[data-testid="stAppViewContainer"]` con `width: 100%`
- [ ] `streamlit_app/styles/main.css` contiene `.block-container` con `max-width: 100%`
- [ ] **SIN overflow horizontal:** Dashboard usa 100% del ancho disponible
- [ ] **Sidebar funcional:** No desaparece ni se colapsa incorrectamente

---

## 🚀 CÓMO APLICAR CAMBIOS

**SI necesitas agregar nuevos estilos:**

1. **Siempre agrega a `main.css`** en la sección apropiada (no en `styles.css`)
2. **Nunca restricciones de ancho** (`max-width: Xpx` está prohibido para contenedor principal)
3. **Documentar cambio** abajo en "HISTORIAL DE CAMBIOS"

**SI necesitas modificar config.toml:**

1. **Mantén `[client]` section intacta**
2. **Documentar razón del cambio**
3. **Validar en desarrollo** antes de commit

---

## 📋 HISTORIAL DE CAMBIOS

| Fecha | Cambio | Responsable | Justificación |
|--|--|--|--|
| 2026-04-15 | ✅ [client] + CSS wide layout | TPM | Eliminar espaciado lateral excesivo |
| | | | |

---

## ⚠️ ADVERTENCIAS

### NO Hacer:
- ❌ Eliminar `[client]` section en config.toml
- ❌ Cambiar `layout="wide"` a `layout="centered"` en main.py
- ❌ Agregar `max-width: 90%` al contenedor principal
- ❌ Modificar este archivo sin incrementar versión

### Hacer:
- ✅ Validar cambios CSS en navegador (DevTools F12)
- ✅ Testear en pantallas 1920x1080 y 3840x2160
- ✅ Documentar TODO cambio aquí
- ✅ Hacer commit con mensaje `[STYLE] Mantenimiento width/layout`

---

## 🔗 REFERENCIAS

- Documentación Oficial: https://docs.streamlit.io/library/advanced-features/configuration
- CSS Selectors Streamlit: https://discuss.streamlit.io/t/css-selectors-for-streamlit-elements
- Issue Original: Dashboard desperdiciaba espacio horizontal

---

**Versión:** 1.0  
**Última Revisión:** 15 de abril de 2026  
**Próxima Revisión:** 30 de abril de 2026 (Fin Fase 2 Semana 3)

---

## CONTACTO / ESCALADA

Si algo se daña relacionado a layout/width:
1. Revisar este documento primero
2. Navegar a `.streamlit/config.toml` y validar presencia de `[client]`
3. Revisar main.py línea 6: `st.set_page_config(..., layout="wide")`
4. Revisar `main.css` líneas de `stAppViewContainer` y `block-container`
5. Si aún falla: Revisar DevTools (F12) > Elements > buscar estilos conflictivos
