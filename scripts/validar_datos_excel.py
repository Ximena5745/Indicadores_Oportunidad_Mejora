import pandas as pd
from pathlib import Path

# Ruta del archivo Excel
DATA_ROOT = Path(__file__).resolve().parents[2]
PATH_CONSOLIDADO = Path(r"c:/Users/lxisilva/OneDrive - Politécnico Grancolombiano/Documentos/Proyectos/Sistema_Indicadores_Poli/data/output/Resultados Consolidados.xlsx")

# Cargar datos del archivo Excel
def cargar_datos():
    if not PATH_CONSOLIDADO.exists():
        print("El archivo no existe en la ruta especificada.")
        return

    print(f"Directorio actual: {Path.cwd()}")
    print(f"Ruta absoluta del archivo: {PATH_CONSOLIDADO}")
    try:
        df = pd.read_excel(PATH_CONSOLIDADO, sheet_name="Consolidado Cierres", engine="openpyxl")
        print("Primeras filas del DataFrame:")
        print(df.head())
        print("\nColumnas del DataFrame:")
        print(df.columns)
        print("\nInformación del DataFrame:")
        print(df.info())
    except Exception as e:
        print(f"Error al cargar el archivo Excel: {e}")

if __name__ == "__main__":
    cargar_datos()