#!/usr/bin/env python3
"""Compatibility alias for the canonical shared task route."""
from importlib import import_module
from pathlib import Path
import sys

_ROOT = str(Path(__file__).resolve().parents[1])
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
_core = import_module("one_c_harness.shared_task_route")
main = _core.main
if __name__ == "__main__":
    raise SystemExit(main())
