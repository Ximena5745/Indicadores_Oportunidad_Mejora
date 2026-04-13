import streamlit as st


def render_filters(data, config, key_prefix="filter", columns_per_row=3, collapsible: bool = False, collapsed_by_default: bool = True, compact: bool = True):
    """Renderiza filtros reutilizables.

    Args:
        data: no usado, mantenido para compatibilidad.
        config: dict con definición de filtros (label, options, default, include_all).
        key_prefix: prefijo para keys de Streamlit.
        columns_per_row: cuántos filtros mostrar por fila.
        collapsible: si True muestra los primeros `columns_per_row` filtros en línea y el resto dentro de un `st.expander`.
        collapsed_by_default: si el expander inicia colapsado cuando `collapsible=True`.

    Devuelve: dict con las selecciones.
    """
    del data

    selections = {}
    items = list(config.items())

    if collapsible and len(items) > columns_per_row:
        # Mostrar primeros N filtros en línea, el resto en un expander
        primary = items[:columns_per_row]
        secondary = items[columns_per_row:]

        # Render primary inline
        cols = st.columns(len(primary))
        for col, (key, conf) in zip(cols, primary):
            with col:
                selections[key] = _render_single_filter(conf, key_prefix, key, compact=compact)

        # Render secondary inside expander
        # Persistir preferencia de colapso en st.session_state
        persist_key = f"{key_prefix}_filters_collapsed"
        if persist_key not in st.session_state:
            st.session_state[persist_key] = collapsed_by_default

        # Checkbox para que el usuario fije la preferencia (visible siempre)
        c1, c2 = st.columns([1, 9])
        with c1:
            st.checkbox("Mantener filtros cerrados", value=st.session_state[persist_key], key=persist_key)

        expanded = not st.session_state[persist_key]
        with st.expander("🔎 Filtros avanzados", expanded=expanded):
            for start in range(0, len(secondary), columns_per_row):
                row_items = secondary[start:start + columns_per_row]
                cols = st.columns(min(columns_per_row, len(row_items)))
                for col, (key, conf) in zip(cols, row_items):
                    with col:
                        selections[key] = _render_single_filter(conf, key_prefix, key, compact=compact)

    else:
        # Render all inline in rows
        for start in range(0, len(items), columns_per_row):
            cols = st.columns(min(columns_per_row, len(items) - start))
            row_items = items[start:start + columns_per_row]

            for col, (key, conf) in zip(cols, row_items):
                with col:
                    selections[key] = _render_single_filter(conf, key_prefix, key, compact=compact)

    return selections


def _render_single_filter(conf: dict, key_prefix: str, key: str, compact: bool = True):
    """Helper: renderiza un solo filtro y devuelve el valor seleccionado."""
    raw_options = list(conf.get("options", []))
    include_all = conf.get("include_all", True)
    all_label = conf.get("all_label", "Todos")
    options = ([all_label] if include_all else []) + raw_options

    label = conf.get("label", key)
    if compact and conf.get("short_label"):
        label = conf.get("short_label")

    if not options:
        st.selectbox(label, ["Sin opciones"], disabled=True, key=f"{key_prefix}_{key}")
        return None

    default_value = conf.get("default", options[0])
    if default_value not in options:
        default_value = options[0]

    return st.selectbox(
        label,
        options,
        index=options.index(default_value),
        key=f"{key_prefix}_{key}",
        format_func=lambda x, ia=include_all, al=all_label, conf=conf: str(conf.get("all_display", "— Todos —")) if ia and x == al else str(x),
    )
