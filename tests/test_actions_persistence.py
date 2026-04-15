import pandas as pd
from core import db_manager
from streamlit_app.components import renderers


def main():
    df = pd.DataFrame([
        {"ACCION": "Mejorar X", "RESPONSABLE": "Ana", "ESTADO": "Abierta"},
        {"ACCION": "Corregir Y", "RESPONSABLE": "Luis", "ESTADO": "En progreso"},
    ])

    print("Guardando Excel usando helper...")
    path = renderers._save_actions_to_excel(df, basename="test_acciones")
    print("Archivo guardado en:", path)

    print("Guardando en DB via guardar_acciones_bulk...")
    ok = db_manager.guardar_acciones_bulk(df)
    print("Resultado guardado en DB:", ok)


if __name__ == "__main__":
    main()
