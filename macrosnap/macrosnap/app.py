"""
MacroSnap Root Forwarder
This file ensures backward compatibility if launched from the legacy nested path.
The active codebase is maintained at the project root: /app.py
"""
from pathlib import Path
import runpy
import sys

root_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(root_dir))
runpy.run_path(str(root_dir / "app.py"), run_name="__main__")
