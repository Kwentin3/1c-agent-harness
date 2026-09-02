#!/usr/bin/env python3
"""Compatibility alias for the single shared native task route.

Issue #38 no longer owns preparation, native lifecycle, receipt collection or
cleanup. Use `scripts/shared_task_route.py run`; this filename forwards to that
same command so old automation cannot enter a parallel lifecycle.
"""

from shared_task_route import main


if __name__ == "__main__":
    raise SystemExit(main())
