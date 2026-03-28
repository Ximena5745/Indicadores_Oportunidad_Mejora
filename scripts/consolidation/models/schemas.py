"""
consolidation/models/schemas.py
Validación de datos con Pydantic
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validator


class InputConfig(BaseModel):
    """Configuración de archivos de entrada."""
    input_file: str = Field(..., description="Archivo base de entrada")
    api_consolidated: str = Field(..., description="API Kawak consolidada")
    kawak_catalog: str = Field(..., description="Catálogo de indicadores Kawak")
    lmi_report: Optional[str] = Field(None, description="Reporte LMI (opcional)")
    
    @validator('input_file', 'api_consolidated', 'kawak_catalog')
    def path_must_exist(cls, v):
        from pathlib import Path
        if not Path(v).exists():
            raise ValueError(f"Archivo no existe: {v}")
        return v


class ExtractionConfig(BaseModel):
    """Configuración de extracción para un indicador."""
    id: str = Field(..., description="ID del indicador")
    patron: str = Field(default='LAST', regex='^(LAST|VARIABLES|SUM_SER|AVG|SUM)$')
    simbolo_ejec: Optional[str] = Field(None, description="Símbolo de ejecución")
    simbolo_meta: Optional[str] = Field(None, description="Símbolo de meta")
    
    class Config:
        extra = 'allow'


class ProcessingConfig(BaseModel):
    """Configuración del procesamiento."""
    año_cierre: int = Field(default=2025, ge=2020, le=2030)
    batch_size: int = Field(default=1000, ge=100, le=10000)
    max_workers: Optional[int] = Field(None, ge=1, le=8)
    use_cache: bool = Field(default=True)
    validate_output: bool = Field(default=True)


class SourceRow(BaseModel):
    """Validación de fila de fuente de datos."""
    Id: str
    Indicador: Optional[str] = None
    Proceso: Optional[str] = None
    Periodicidad: str = Field(default='Mensual')
    Sentido: str = Field(default='Positivo', regex='^(Positivo|Negativo)$')
    fecha: datetime
    resultado: Optional[float] = None
    meta: Optional[float] = None
    variables: Optional[str] = None
    series: Optional[str] = None
    analisis: Optional[str] = None
    LLAVE: Optional[str] = None


class ProcessedRecord(BaseModel):
    """Registro procesado validado."""
    Id: str
    Fecha: datetime
    Meta: Optional[float] = None
    Ejecucion: Optional[float] = None
    Cumplimiento: Optional[float] = Field(None, ge=0, le=1.3)
    LLAVE: str
    fuente: str = Field(..., regex='^(api_directo|variables|variables_simbolo|series_sum|na_record|skip|sin_resultado)$')
    es_na: bool = False


class ConsolidationMetrics(BaseModel):
    """Métricas del proceso de consolidación."""
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    records_processed: int = 0
    records_na: int = 0
    records_skipped: int = 0
    errors: List[str] = []
    
    def calculate_duration(self):
        if self.end_time:
            self.duration_seconds = (self.end_time - self.start_time).total_seconds()


class OutputSummary(BaseModel):
    """Resumen de output generado."""
    output_file: str
    sheets_created: List[str] = []
    records_by_sheet: Dict[str, int] = {}
    file_size_bytes: Optional[int] = None
    checksum: Optional[str] = None
