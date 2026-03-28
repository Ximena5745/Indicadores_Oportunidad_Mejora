"""
consolidation/core/metrics.py
Sistema de métricas y reporting
"""

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ProcessingMetrics:
    """Métricas detalladas de procesamiento."""
    
    # Tiempos
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    
    # Contadores
    total_records: int = 0
    processed_records: int = 0
    na_records: int = 0
    skipped_records: int = 0
    error_records: int = 0
    
    # Por fuente
    by_source: Dict[str, int] = field(default_factory=dict)
    
    # Por tipo de extracción
    by_extractor: Dict[str, int] = field(default_factory=dict)
    
    # Errores
    errors: List[Dict] = field(default_factory=list)
    
    # Rendimiento
    processing_time_seconds: Optional[float] = None
    records_per_second: Optional[float] = None
    
    def record_processed(self, source: str = 'unknown', extractor: str = 'unknown'):
        """Registra un registro procesado."""
        self.processed_records += 1
        self.by_source[source] = self.by_source.get(source, 0) + 1
        self.by_extractor[extractor] = self.by_extractor.get(extractor, 0) + 1
    
    def record_error(self, record_id: str, error: str, context: Optional[Dict] = None):
        """Registra un error."""
        self.error_records += 1
        self.errors.append({
            'timestamp': datetime.now().isoformat(),
            'record_id': record_id,
            'error': error,
            'context': context or {}
        })
    
    def finalize(self):
        """Finaliza métricas calculando tiempos."""
        self.end_time = datetime.now()
        if self.start_time:
            duration = (self.end_time - self.start_time).total_seconds()
            self.processing_time_seconds = duration
            if duration > 0 and self.processed_records > 0:
                self.records_per_second = self.processed_records / duration
    
    def to_dict(self) -> Dict:
        """Convierte a diccionario."""
        return {
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration_seconds': self.processing_time_seconds,
            'counts': {
                'total': self.total_records,
                'processed': self.processed_records,
                'na': self.na_records,
                'skipped': self.skipped_records,
                'errors': self.error_records
            },
            'performance': {
                'records_per_second': self.records_per_second,
                'success_rate': self._success_rate()
            },
            'by_source': self.by_source,
            'by_extractor': self.by_extractor,
            'errors': self.errors[:10]  # Solo primeros 10 errores
        }
    
    def _success_rate(self) -> float:
        if self.total_records == 0:
            return 100.0
        successful = self.processed_records + self.na_records
        return (successful / self.total_records) * 100


class MetricsCollector:
    """Colector centralizado de métricas."""
    
    def __init__(self):
        self.metrics: Dict[str, ProcessingMetrics] = {}
        self.current_phase: Optional[str] = None
    
    def start_phase(self, phase_name: str):
        """Inicia una nueva fase de procesamiento."""
        self.current_phase = phase_name
        self.metrics[phase_name] = ProcessingMetrics()
        logger.info(f"[METRICS] Iniciando fase: {phase_name}")
    
    def end_phase(self, phase_name: Optional[str] = None):
        """Finaliza la fase actual."""
        name = phase_name or self.current_phase
        if name and name in self.metrics:
            self.metrics[name].finalize()
            duration = self.metrics[name].processing_time_seconds
            logger.info(f"[METRICS] Fase '{name}' completada en {duration:.2f}s")
    
    def get_current(self) -> Optional[ProcessingMetrics]:
        """Obtiene métricas de fase actual."""
        if self.current_phase:
            return self.metrics.get(self.current_phase)
        return None
    
    def generate_report(self, output_path: Optional[Path] = None) -> Dict:
        """Genera reporte completo."""
        report = {
            'generated_at': datetime.now().isoformat(),
            'phases': {name: m.to_dict() for name, m in self.metrics.items()},
            'summary': self._calculate_summary()
        }
        
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            logger.info(f"Reporte guardado: {output_path}")
        
        return report
    
    def _calculate_summary(self) -> Dict:
        """Calcula resumen de todas las fases."""
        total_duration = sum(
            (m.processing_time_seconds or 0) for m in self.metrics.values()
        )
        
        total_records = sum(m.total_records for m in self.metrics.values())
        total_processed = sum(m.processed_records for m in self.metrics.values())
        total_errors = sum(m.error_records for m in self.metrics.values())
        
        return {
            'total_duration_seconds': total_duration,
            'total_records': total_records,
            'total_processed': total_processed,
            'total_errors': total_errors,
            'overall_success_rate': (
                (total_processed / total_records * 100) if total_records > 0 else 0
            )
        }


class ProgressReporter:
    """Reporter de progreso en tiempo real."""
    
    def __init__(self, total: int, description: str = "Procesando"):
        self.total = total
        self.description = description
        self.current = 0
        self.start_time = time.time()
        self.last_update = self.start_time
        self.update_interval = 5  # segundos
    
    def update(self, increment: int = 1):
        """Actualiza progreso."""
        self.current += increment
        now = time.time()
        
        # Reportar cada N segundos o al completar
        if (now - self.last_update >= self.update_interval or 
            self.current >= self.total):
            self._report()
            self.last_update = now
    
    def _report(self):
        """Muestra reporte de progreso."""
        if self.total == 0:
            return
        
        elapsed = time.time() - self.start_time
        pct = (self.current / self.total) * 100
        
        # Estimar tiempo restante
        if self.current > 0:
            rate = self.current / elapsed
            remaining = (self.total - self.current) / rate if rate > 0 else 0
            eta_str = f"ETA: {remaining:.0f}s"
        else:
            eta_str = "ETA: --"
        
        logger.info(
            f"{self.description}: {self.current:,}/{self.total:,} "
            f"({pct:.1f}%) | {elapsed:.1f}s | {eta_str}"
        )
    
    def finish(self):
        """Finaliza reporte."""
        elapsed = time.time() - self.start_time
        logger.info(
            f"{self.description}: Completado {self.current:,} items "
            f"en {elapsed:.1f}s "
            f"({self.current/elapsed:.1f} items/s)"
        )


class PerformanceMonitor:
    """Monitoreo de rendimiento del sistema."""
    
    def __init__(self):
        self.checkpoints: List[Dict] = []
    
    def checkpoint(self, name: str):
        """Registra un checkpoint de tiempo."""
        import psutil
        
        self.checkpoints.append({
            'name': name,
            'timestamp': datetime.now().isoformat(),
            'cpu_percent': psutil.cpu_percent(),
            'memory_percent': psutil.virtual_memory().percent,
            'memory_mb': psutil.Process().memory_info().rss / 1024 / 1024
        })
    
    def report(self) -> Dict:
        """Genera reporte de rendimiento."""
        return {
            'checkpoints': self.checkpoints,
            'peak_memory_mb': max(
                (c['memory_mb'] for c in self.checkpoints), default=0
            )
        }
