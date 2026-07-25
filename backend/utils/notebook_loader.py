import json
import logging
import sys
import types as _types
from importlib.machinery import ModuleSpec
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock

logger = logging.getLogger(__name__)

# Cache loaded notebook modules to prevent multiple executions
_loaded_notebooks = {}

def get_notebook_module(notebook_name: str) -> ModuleType:
    """
    Dynamically loads and evaluates Jupyter notebook code cells in order,
    returning a Python module namespace. Saves state variables and functions.
    """
    if notebook_name in _loaded_notebooks:
        return _loaded_notebooks[notebook_name]

    base_dir = Path(__file__).resolve().parent.parent.parent
    nb_path = base_dir / "notebooks" / "capabilities" / notebook_name

    if not nb_path.exists():
        raise FileNotFoundError(f"Notebook {notebook_name} not found at {nb_path}")

    logger.info(f"Loading notebook capability: {notebook_name}")

    with open(nb_path, "r", encoding="utf-8") as f:
        nb_data = json.load(f)

    # Instantiate custom module
    mod = ModuleType(notebook_name.split(".")[0])
    mod.__file__ = str(nb_path)

    # Ensure matplotlib is importable inside notebooks.
    # Use a real Agg backend if installed; otherwise inject a spec-compliant
    # MagicMock so that `import matplotlib.pyplot` inside notebooks doesn't
    # raise "ValueError: matplotlib.__spec__ is not set".
    try:
        import matplotlib
        import matplotlib.pyplot as _mpl_plt
        matplotlib.use("Agg")
    except Exception:
        _loader = _types.ModuleType.__class__  # any hashable non-None object
        _mock_mpl = MagicMock(spec=_types.ModuleType("matplotlib"))
        _mock_mpl.__spec__    = ModuleSpec("matplotlib", None)
        _mock_mpl.__path__    = []
        _mock_mpl.__package__ = "matplotlib"
        _mock_mpl.__loader__  = None
        _mock_mpl.use         = MagicMock()

        _mock_plt = MagicMock(spec=_types.ModuleType("matplotlib.pyplot"))
        _mock_plt.__spec__    = ModuleSpec("matplotlib.pyplot", None)
        _mock_plt.__package__ = "matplotlib"
        _mock_plt.__loader__  = None
        _mock_fig = MagicMock()
        _mock_ax  = MagicMock()
        _mock_plt.subplots.return_value = (_mock_fig, _mock_ax)

        sys.modules.setdefault("matplotlib",        _mock_mpl)
        sys.modules.setdefault("matplotlib.pyplot", _mock_plt)


    # Extract and run code cells sequentially
    for idx, cell in enumerate(nb_data.get("cells", [])):
        if cell.get("cell_type") == "code":
            source_code = "".join(cell.get("source", []))
            if not source_code.strip():
                continue
            try:
                # Execute in module namespace definition dict
                exec(source_code, mod.__dict__, mod.__dict__)
            except Exception as e:
                logger.error(f"Error executing cell #{idx} in {notebook_name}: {e}")
                continue

    _loaded_notebooks[notebook_name] = mod
    return mod
