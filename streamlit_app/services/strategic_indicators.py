# streamlit_app/services/strategic_indicators.py -- re-export para compatibilidad legacy.
# Ubicacion canonica: services/strategic_indicators.py
try:
    from services.strategic_indicators import *  # noqa: F401, F403
except ImportError:
    # Si falla, intentar desde la raíz del proyecto
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from services.strategic_indicators import *  # noqa: F401, F403

