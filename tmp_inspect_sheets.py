import pandas as pd
from pathlib import Path
path = Path('data/output/Resultados Consolidados.xlsx')
print('exists', path.exists())
with pd.ExcelFile(path, engine='openpyxl') as xls:
    print('sheets', xls.sheet_names)
    for sheet in ['Consolidado Historico', 'Consolidado Semestral']:
        if sheet in xls.sheet_names:
            df = pd.read_excel(xls, sheet_name=sheet, nrows=2)
            print('sheet:', sheet)
            print('columns:', df.columns.tolist())
            print('sample:', df.to_dict(orient='records'))
        else:
            print('missing:', sheet)
