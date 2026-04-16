import pandas as pd
import os

paths = [os.path.join('data','raw','Plan de accion','PA_1.xlsx'), os.path.join('data','raw','Plan de accion','PA_2.xlsx')]
dfs = []
for p in paths:
    if not os.path.exists(p):
        continue
    df = pd.read_excel(p, dtype=str, na_filter=False)
    cols = df.columns.tolist()
    avance_col = next((c for c in cols if 'Avance' in c and '%' in c), None)
    id_om_col = next((c for c in cols if 'Id Oportunidad de mejora' in c), None)
    if not id_om_col:
        id_om_col = next((c for c in cols if c.startswith('Id ') and 'Oportunidad' in c), None)
    if id_om_col and avance_col:
        sub = df[[id_om_col, avance_col]].copy()
        sub.columns = ['Id_OM','Avance']
        dfs.append(sub)

if not dfs:
    print('NO DATA')
    exit(0)

df_all = pd.concat(dfs, ignore_index=True)
df_all['Avance'] = pd.to_numeric(df_all['Avance'], errors='coerce')
df_all['Id_OM'] = df_all['Id_OM'].astype(str).str.strip()
df_all = df_all.dropna(subset=['Id_OM','Avance'])

max_av = df_all['Avance'].max()
if max_av <= 1:
    df_all['Avance'] = df_all['Avance'] * 100

df_all['Avance'] = df_all['Avance'].astype(float).round(1)
resultado = df_all.groupby('Id_OM')['Avance'].mean().to_dict()
print('RESULTADOS', resultado)
print('440', resultado.get('440'))
