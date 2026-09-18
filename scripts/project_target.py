#!/usr/bin/env python3
"""Compatibility wrapper for :mod:`one_c_harness.project_target`."""
from importlib import import_module
from pathlib import Path
import sys

_ROOT = str(Path(__file__).resolve().parents[1])
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
_core = import_module("one_c_harness.project_target")
for _name, _value in vars(_core).items():
    if _name not in {"__name__", "__file__", "__package__", "__loader__", "__spec__"}:
        globals()[_name] = _value
if __name__ == "__main__":
    raise SystemExit(_core.main())
