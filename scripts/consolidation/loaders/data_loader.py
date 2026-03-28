"""
consolidation/loaders/data_loader.py
Carga de fuentes de datos consolidadas
"""

import logging
from pathlib import Path
from typing import Dict, Optional, Set, Tuple

import pandas as pd

from ..core.constants import get_project_paths
from ..core.utils import id_str, limpiar_clasificacion, limpiar_html, make_llave

logger = logging.getLogger(__name__)


class DataLoader:
    """
    Cargador de fuentes de datos para consolidación.
    """
    
    def __init__(self):
        self.paths = get_project_paths()
        self._cache = {}
    
    def load_api_consolidated(self, use_cache: bool = True) -> pd.DataFrame:
        """
        Carga Consolidado_API_Kawak.xlsx
        
        Returns:
            DataFrame con datos API consolidados
        """
        cache_key = 'api_consolidated'
        
        if use_cache and cache_key in self._cache:
            return self._cache[cache_key]
        
        path = self.paths['CONSOLIDADO_API_KW']
        
        if not path.exists():
            raise FileNotFoundError(
                f"No se encontró {path}. "
                f"Ejecutar primero: python scripts/consolidar_api.py"
            )
        
        logger.info(f"Cargando API consolidada: {path}")
        df = pd.read_excel(path)
        df = df.dropna(subset=['fecha'])
        df['fecha'] = pd.to_datetime(df['fecha'])
        
        if 'clasificacion' in df.columns:
            df['clasificacion'] = df['clasificacion'].apply(limpiar_clasificacion)
        
        df = df.rename(columns={
            'ID': 'Id', 'nombre': 'Indicador', 'proceso': 'Proceso',
            'frecuencia': 'Periodicidad', 'sentido': 'Sentido',
        })
        
        # Vectorizado: generar llaves
        df['LLAVE'] = (
            df['Id'].astype(str).str.replace(r'\.0$', '', regex=True) + '-' +
            df['fecha'].dt.year.astype(str) + '-' +
            df['fecha'].dt.month.astype(str).str.zfill(2) + '-' +
            df['fecha'].dt.day.astype(str).str.zfill(2)
        )
        
        if use_cache:
            self._cache[cache_key] = df
        
        logger.info(f"  API consolidada: {len(df):,} registros")
        return df
    
    def load_kawak_2025(self) -> pd.DataFrame:
        """
        Carga Kawak 2025 si existe.
        
        Returns:
            DataFrame o vacío si no existe
        """
        path = self.paths['BASE_PATH'] / "Kawak" / "2025.xlsx"
        
        if not path.exists():
            logger.info("  Kawak 2025: no encontrado")
            return pd.DataFrame()
        
        logger.info(f"Cargando Kawak 2025: {path}")
        df = pd.read_excel(path)
        df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce')
        df = df.dropna(subset=['fecha'])
        df['LLAVE'] = df.apply(
            lambda r: make_llave(r['Id'], r['fecha']), axis=1
        )
        
        logger.info(f"  Kawak 2025: {len(df):,} registros")
        return df
    
    def load_historical_consolidated(self) -> Dict[str, pd.DataFrame]:
        """
        Carga hojas históricas existentes.
        
        Returns:
            Dict con DataFrames por hoja
        """
        input_file = self.paths['INPUT_FILE']
        
        if not input_file.exists():
            raise FileNotFoundError(f"No se encontró archivo base: {input_file}")
        
        logger.info(f"Cargando consolidado existente: {input_file}")
        
        sheets = {
            'Consolidado Historico': 'historico',
            'Consolidado Semestral': 'semestral',
            'Consolidado Cierres': 'cierres'
        }
        
        result = {}
        for sheet_name, key in sheets.items():
            try:
                df = pd.read_excel(input_file, sheet_name=sheet_name)
                df['Fecha'] = pd.to_datetime(df['Fecha'])
                result[key] = df
                logger.info(f"  {sheet_name}: {len(df):,} filas")
            except Exception as e:
                logger.warning(f"  Error cargando {sheet_name}: {e}")
                result[key] = pd.DataFrame()
        
        return result
    
    def load_kawak_valid_ids(self) -> Optional[Set[Tuple[str, int]]]:
        """
        Carga IDs válidos desde catálogo Kawak.
        
        Returns:
            Set de tuplas (id, año) o None si no existe
        """
        path = self.paths['KAWAK_CAT_FILE']
        
        if not path.exists():
            logger.info("  Catálogo Kawak no encontrado, filtro desactivado")
            return None
        
        try:
            df = pd.read_excel(path)
            df.columns = [str(c).strip() for c in df.columns]
            
            col_id = next(
                (c for c in df.columns if c.lower() == 'id'), None
            )
            col_año = next(
                (c for c in df.columns 
                 if c.lower() in ('año', 'anio', 'year')), None
            )
            
            if not col_id or not col_año:
                logger.warning("  Columnas Id/Año no encontradas")
                return None
            
            validos = set()
            for _, row in df.iterrows():
                id_s = id_str(row[col_id])
                try:
                    año = int(float(row[col_año]))
                    if id_s:
                        validos.add((id_s, año))
                except (TypeError, ValueError):
                    continue
            
            logger.info(f"  IDs válidos: {len(validos):,}")
            return validos
            
        except Exception as e:
            logger.warning(f"  Error leyendo catálogo: {e}")
            return None
    
    def load_lmi_metric_ids(self) -> Set[str]:
        """
        Carga IDs de tipo Métrica desde LMI.
        
        Returns:
            Set de IDs string
        """
        path = self.paths['BASE_PATH'] / "lmi_reporte.xlsx"
        
        if not path.exists():
            logger.info("  LMI reporte no encontrado")
            return set()
        
        try:
            df = pd.read_excel(path)
            df.columns = [str(c).strip() for c in df.columns]
            
            col_tipo = next(
                (c for c in df.columns 
                 if c.lower().startswith('tipo')
                 and 'variable' not in c.lower()), None
            )
            col_ind = next(
                (c for c in df.columns 
                 if c.lower().startswith('indicador')), None
            )
            col_id = next(
                (c for c in df.columns if c.lower() == 'id'), 'Id'
            )
            
            mask = pd.Series(False, index=df.index)
            
            if col_tipo:
                mask |= df[col_tipo].astype(str).str.strip().str.lower() == 'metrica'
            
            if col_ind:
                mask |= df[col_ind].astype(str).str.lower().str.contains(
                    'metrica', na=False
                )
            
            ids = set()
            for val in df.loc[mask, col_id].dropna():
                s = str(val).strip()
                ids.add(s[:-2] if s.endswith('.0') else s)
            
            logger.info(f"  IDs Métrica: {len(ids)}")
            return ids
            
        except Exception as e:
            logger.warning(f"  Error leyendo LMI: {e}")
            return set()
    
    def clear_cache(self):
        """Limpia caché de datos cargados."""
        self._cache.clear()
