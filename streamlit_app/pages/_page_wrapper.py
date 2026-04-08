import importlib.util
import sys
from pathlib import Path


def _ensure_root_path():
    root = Path(__file__).resolve().parents[2]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    return root


def load_disabled_page(page_filename: str):
    root = _ensure_root_path()
    source_path = root / "pages_disabled" / page_filename
    module_name = f"disabled_page_{page_filename.replace('.py', '')}"
    if module_name in sys.modules:
        del sys.modules[module_name]
    spec = importlib.util.spec_from_file_location(module_name, source_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def render_disabled_page(page_filename: str):
    load_disabled_page(page_filename)
