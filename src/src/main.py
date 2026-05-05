"""Compatibility wrapper for running from the src working directory."""

from __future__ import annotations

import runpy
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.modules.pop("src", None)
runpy.run_path(str(REPO_ROOT / "src" / "main.py"), run_name="__main__")
