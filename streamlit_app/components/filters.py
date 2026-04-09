import streamlit as st


def render_filters(data, config, key_prefix="filter", columns_per_row=3):
    """Renderiza filtros reutilizables con soporte de defaults y varias filas."""
    del data

    selections = {}
    items = list(config.items())

    for start in range(0, len(items), columns_per_row):
        cols = st.columns(min(columns_per_row, len(items) - start))
        row_items = items[start:start + columns_per_row]

        for col, (key, conf) in zip(cols, row_items):
            with col:
                raw_options = list(conf.get("options", []))
                include_all = conf.get("include_all", True)
                all_label = conf.get("all_label", "Todos")
                options = ([all_label] if include_all else []) + raw_options

                if not options:
                    selections[key] = None
                    st.selectbox(conf["label"], ["Sin opciones"], disabled=True, key=f"{key_prefix}_{key}")
                    continue

                default_value = conf.get("default", options[0])
                if default_value not in options:
                    default_value = options[0]

                selections[key] = st.selectbox(
                    conf["label"],
                    options,
                    index=options.index(default_value),
                    key=f"{key_prefix}_{key}",
                    format_func=lambda x, ia=include_all, al=all_label, conf=conf: conf.get("all_display", "— Todos —") if ia and x == al else x,
                )

    return selections
