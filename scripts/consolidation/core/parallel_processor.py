"""
consolidation/core/parallel_processor.py
Procesamiento paralelo con multiprocessing
"""

import logging
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from typing import Any, Callable, Dict, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)


class ParallelProcessor:
    """
    Procesador paralelo para operaciones intensivas.
    """
    
    def __init__(self, max_workers: Optional[int] = None):
        self.max_workers = max_workers or max(1, mp.cpu_count() - 1)
        self.chunk_size = 5000
    
    def process_dataframe(
        self,
        df: pd.DataFrame,
        func: Callable[[pd.DataFrame], pd.DataFrame]
    ) -> pd.DataFrame:
        """
        Procesa DataFrame en paralelo por chunks.
        
        Args:
            df: DataFrame a procesar
            func: Función a aplicar por chunk
        
        Returns:
            DataFrame procesado
        """
        if len(df) < self.chunk_size:
            return func(df)
        
        # Dividir en chunks
        n_chunks = max(1, len(df) // self.chunk_size)
        chunks = np.array_split(df, n_chunks)
        
        logger.info(f"Procesando {len(df):,} filas en {len(chunks)} chunks con {self.max_workers} workers")
        
        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            results = list(executor.map(func, chunks))
        
        return pd.concat(results, ignore_index=True)
    
    def parallel_apply(
        self,
        df: pd.DataFrame,
        func: Callable,
        axis: int = 1
    ) -> pd.Series:
        """
        Aplica función en paralelo (reemplazo de apply).
        
        Args:
            df: DataFrame
            func: Función a aplicar
            axis: Eje (1=por fila)
        
        Returns:
            Series con resultados
        """
        from joblib import Parallel, delayed
        
        def process_chunk(chunk):
            return chunk.apply(func, axis=axis)
        
        chunks = np.array_split(df, self.max_workers)
        
        results = Parallel(n_jobs=self.max_workers)(
            delayed(process_chunk)(chunk) for chunk in chunks
        )
        
        return pd.concat(results)
    
    def parallel_file_read(self, file_paths: List[str]) -> Dict[str, Any]:
        """
        Lee múltiples archivos en paralelo.
        
        Args:
            file_paths: Lista de rutas de archivos
        
        Returns:
            Dict {ruta: contenido}
        """
        def read_single(path: str):
            try:
                return path, pd.read_excel(path)
            except Exception as e:
                logger.error(f"Error leyendo {path}: {e}")
                return path, None
        
        with ThreadPoolExecutor(max_workers=min(4, len(file_paths))) as executor:
            results = list(executor.map(read_single, file_paths))
        
        return {path: df for path, df in results if df is not None}
    
    def parallel_extraction(
        self,
        rows: List[Dict],
        extractors: Dict[str, Any]
    ) -> List[Dict]:
        """
        Extrae datos de múltiples filas en paralelo.
        
        Args:
            rows: Lista de filas (dicts)
            extractors: Dict de extractores pre-configurados
        
        Returns:
            Lista de resultados
        """
        def process_batch(batch):
            results = []
            for row in batch:
                row_id = str(row.get('Id', ''))
                extractor = extractors.get(row_id, extractors.get('default'))
                if extractor:
                    result = extractor.extract(row)
                    results.append({
                        'row': row,
                        'extraction': result
                    })
            return results
        
        # Dividir en batches
        n_batches = max(1, len(rows) // self.chunk_size)
        batches = [rows[i::n_batches] for i in range(n_batches)]
        
        logger.info(f"Extrayendo {len(rows):,} registros en {n_batches} batches")
        
        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            batch_results = list(executor.map(process_batch, batches))
        
        # Aplanar resultados
        all_results = []
        for batch in batch_results:
            all_results.extend(batch)
        
        return all_results


class BatchProcessor:
    """
    Procesador por lotes con progreso.
    """
    
    def __init__(self, batch_size: int = 1000, show_progress: bool = True):
        self.batch_size = batch_size
        self.show_progress = show_progress
    
    def process_with_progress(
        self,
        items: List[Any],
        process_func: Callable[[Any], Any]
    ) -> List[Any]:
        """
        Procesa items mostrando progreso.
        
        Args:
            items: Lista de items a procesar
            process_func: Función de procesamiento
        
        Returns:
            Lista de resultados
        """
        from tqdm import tqdm
        
        results = []
        
        iterator = tqdm(
            items,
            desc="Procesando",
            total=len(items),
            disable=not self.show_progress
        ) if self.show_progress else items
        
        for item in iterator:
            try:
                result = process_func(item)
                results.append(result)
            except Exception as e:
                logger.error(f"Error procesando item: {e}")
                results.append(None)
        
        return results
    
    def process_batches(
        self,
        df: pd.DataFrame,
        batch_func: Callable[[pd.DataFrame], pd.DataFrame]
    ) -> pd.DataFrame:
        """
        Procesa DataFrame por batches con checkpointing.
        
        Args:
            df: DataFrame
            batch_func: Función a aplicar por batch
        
        Returns:
            DataFrame procesado
        """
        total_rows = len(df)
        processed = 0
        results = []
        
        for start in range(0, total_rows, self.batch_size):
            end = min(start + self.batch_size, total_rows)
            batch = df.iloc[start:end]
            
            try:
                processed_batch = batch_func(batch)
                results.append(processed_batch)
                processed += len(batch)
                
                if self.show_progress:
                    pct = (processed / total_rows) * 100
                    logger.info(f"Progreso: {processed:,}/{total_rows:,} ({pct:.1f}%)")
                
            except Exception as e:
                logger.error(f"Error en batch {start}-{end}: {e}")
                # Continuar con siguiente batch
                continue
        
        return pd.concat(results, ignore_index=True) if results else pd.DataFrame()
