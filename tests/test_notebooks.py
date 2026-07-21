import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock
import pytest

# Mock matplotlib to prevent ModuleNotFoundError during headless testing
mock_matplotlib = MagicMock()
mock_plt = MagicMock()
mock_fig = MagicMock()
mock_ax = MagicMock()
mock_plt.subplots.return_value = (mock_fig, mock_ax)
mock_matplotlib.pyplot = mock_plt
sys.modules['matplotlib'] = mock_matplotlib
sys.modules['matplotlib.pyplot'] = mock_plt
sys.modules['matplotlib.pyplot.subplots'] = mock_plt.subplots


def get_notebook_paths():
    base_path = Path(__file__).resolve().parent.parent
    caps_dir = base_path / "notebooks" / "capabilities"
    paths = sorted(list(caps_dir.glob("*.ipynb")))
    return paths

@pytest.mark.parametrize("nb_path", get_notebook_paths(), ids=lambda p: p.name)
def test_notebook_execution(nb_path):
    print(f"\nExecuting notebook: {nb_path.name}")
    
    with open(nb_path, "r", encoding="utf-8") as f:
        nb_data = json.load(f)
        
    namespace = {
        "__file__": str(nb_path),
        # mock matplotlib show to avoid blocking tests
        "plt": type("MockPlt", (), {"show": lambda: None, "subplots": lambda *a, **k: (type("MockFig", (), {})(), type("MockAx", (), {"bar": lambda *a, **k: None, "set_title": lambda *a, **k: None, "set_xlabel": lambda *a, **k: None, "set_ylabel": lambda *a, **k: None})())})
    }
    
    for idx, cell in enumerate(nb_data.get("cells", [])):
        if cell.get("cell_type") == "code":
            source_lines = cell.get("source", [])
            source_code = "".join(source_lines)
            
            # Skip empty cells
            if not source_code.strip():
                continue
                
            try:
                # Execute the cell within the shared namespace
                exec(source_code, namespace, namespace)
            except Exception as e:
                # Provide rich debug info
                pytest.fail(f"Cell #{idx} in {nb_path.name} failed execution.\nError: {e}\nCell Code:\n{source_code}")
