import gc
import json
import logging
import os
import sys
import types as _types
from collections import OrderedDict
from importlib.machinery import ModuleSpec
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock

logger = logging.getLogger(__name__)

# Cache loaded notebook modules to prevent multiple executions.
#
# Bounded, not unbounded. Each executed notebook keeps its own merged frames
# alive in its module namespace — roughly 25-45 MB apiece — so holding all
# sixteen resident grew the process past 1.8 GB and got it OOM-killed on a
# 512 MiB host. An LRU keeps the working set flat: the notebooks a visitor is
# actually clicking through stay warm and the rest are dropped.
#
# The cost of a miss is real (re-executing a notebook takes seconds), so this
# is sized as large as the memory budget allows rather than as small as
# possible. Override with CALRETAIL_NOTEBOOK_CACHE.
_CACHE_SIZE = max(1, int(os.environ.get("CALRETAIL_NOTEBOOK_CACHE", "3")))

_loaded_notebooks: "OrderedDict[str, ModuleType]" = OrderedDict()


def cache_info() -> dict:
    return {"warm": list(_loaded_notebooks), "limit": _CACHE_SIZE}


def _remember(name: str, mod: ModuleType) -> None:
    _loaded_notebooks[name] = mod
    while len(_loaded_notebooks) > _CACHE_SIZE:
        evicted, victim = _loaded_notebooks.popitem(last=False)
        # Drop the module's namespace explicitly. Without this the frames it
        # built stay reachable from any closure the notebook left behind and
        # the eviction frees nothing.
        victim.__dict__.clear()
        sys.modules.pop(evicted.split(".")[0], None)
        gc.collect()
        logger.info(f"Evicted notebook from cache: {evicted}")


def get_notebook_module(notebook_name: str) -> ModuleType:
    """
    Dynamically loads and evaluates Jupyter notebook code cells in order,
    returning a Python module namespace. Saves state variables and functions.
    """
    if notebook_name in _loaded_notebooks:
        _loaded_notebooks.move_to_end(notebook_name)   # most recently used
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

    _remember(notebook_name, mod)
    return mod
