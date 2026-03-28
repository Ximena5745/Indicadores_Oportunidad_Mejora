"""
consolidation/core/logging_config.py
Configuración centralizada de logging
"""

import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logging(
    level: int = logging.INFO,
    log_file: Optional[Path] = None,
    console: bool = True
):
    """
    Configura logging estructurado.
    
    Args:
        level: Nivel de logging
        log_file: Path opcional para archivo de log
        console: Si incluir handler de consola
    """
    handlers = []
    
    formatter = logging.Formatter(
        '%(asctime)s | %(name)-30s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)
    
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        handlers.append(console_handler)
    
    logging.basicConfig(
        level=level,
        handlers=handlers,
        force=True
    )
    
    logging.getLogger('openpyxl').setLevel(logging.WARNING)
    logging.getLogger('pandas').setLevel(logging.WARNING)
