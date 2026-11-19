#!/usr/bin/env python3
"""Run the mock drift smoke. No model calls and no weight downloads."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tslit_dspy.cli import main

if __name__ == "__main__":
    raise SystemExit(main(["drift-smoke"]))
