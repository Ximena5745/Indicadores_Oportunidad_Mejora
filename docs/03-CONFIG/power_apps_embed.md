# Power Apps embed opcional

Este proyecto ya puede arrancar en un modo más limpio para iframe usando `POWER_APPS_EMBEDDED=true`.

## Qué activa

- Oculta la barra lateral y reduce el chrome visual de Streamlit.
- Arranca Streamlit con `CORS` y `XSRF` desactivados, que suele ser necesario detrás de un host embebido.
- Desactiva métricas de uso del navegador y minimiza la barra de herramientas.

## Cómo usarlo

1. Define la variable de entorno `POWER_APPS_EMBEDDED=true` en el entorno de ejecución.
2. Arranca la app con `python scripts/start_streamlit.py`.
3. Usa la URL pública en Power Apps dentro de un iframe o web content control.

## Importante

Streamlit no expone por sí mismo un encabezado configurable de `frame-ancestors`. Si Power Apps bloquea el iframe, el proyecto debe publicarse detrás de un proxy o gateway que permita framing desde los dominios de Power Apps.

## Recomendación de despliegue

- Mantener `POWER_APPS_EMBEDDED=false` para uso normal.
- Activarlo solo en el despliegue pensado para Power Apps.
- Publicar siempre por HTTPS.