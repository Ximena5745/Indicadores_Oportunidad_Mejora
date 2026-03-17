"""
services/ai_analysis.py — Análisis de texto con Claude (Anthropic).

Extrae insights y oportunidades de mejora del análisis registrado por el usuario.
Requiere ANTHROPIC_API_KEY en st.secrets o variable de entorno.
"""
import hashlib
import streamlit as st


_MODEL = "claude-haiku-4-5-20251001"

_PROMPT_TEMPLATE = """Eres un analista institucional experto en mejora continua y gestión por indicadores.

A continuación se presenta el análisis registrado por el responsable del indicador:

Indicador: {nombre}
Proceso: {proceso}
Categoría actual: {categoria}
Cumplimiento actual: {cumplimiento}

Análisis del responsable:
\"\"\"{analisis}\"\"\"

Tu tarea:
1. Identifica los principales insights del análisis (máximo 3 puntos concisos).
2. Si el análisis menciona causas, brechas o situaciones que lo justifiquen, propón oportunidades de mejora concretas y accionables (máximo 3).
3. Si el análisis es muy breve o no contiene información suficiente para extraer oportunidades, indícalo brevemente.

Responde en español, en formato de listas cortas y directas. No repitas el análisis original."""


def _get_client():
    """Retorna cliente Anthropic o None si la key no está configurada."""
    try:
        import anthropic
        key = st.secrets.get("ANTHROPIC_API_KEY", "")
        if not key:
            import os
            key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not key:
            return None
        return anthropic.Anthropic(api_key=key)
    except Exception:
        return None


def analizar_texto_indicador(
    id_ind: str,
    nombre: str,
    proceso: str,
    categoria: str,
    cumplimiento: str,
    texto_analisis: str,
) -> str | None:
    """
    Llama a Claude para extraer insights y oportunidades de mejora.
    Usa st.session_state como caché para no repetir llamadas en el mismo indicador.
    Retorna el texto generado, o None si no hay API key o falla la llamada.
    """
    client = _get_client()
    if client is None:
        return None

    # Caché por hash del texto para no rellamar si no cambió
    cache_key = "_ai_" + hashlib.md5(f"{id_ind}{texto_analisis}".encode()).hexdigest()
    if cache_key in st.session_state:
        return st.session_state[cache_key]

    prompt = _PROMPT_TEMPLATE.format(
        nombre=nombre,
        proceso=proceso,
        categoria=categoria,
        cumplimiento=cumplimiento,
        analisis=texto_analisis,
    )

    try:
        message = client.messages.create(
            model=_MODEL,
            max_tokens=600,
            messages=[{"role": "user", "content": prompt}],
        )
        resultado = message.content[0].text.strip()
        st.session_state[cache_key] = resultado
        return resultado
    except Exception:
        return None
