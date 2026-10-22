"""Pytest bootstrap: src-layout — tests import packages (agent, core, ...) from src/."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
