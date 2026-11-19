#!/usr/bin/env python3
"""Print the adversary-drift sample-size plan. No model calls."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tslit_dspy.drift.power import main

if __name__ == "__main__":
    raise SystemExit(main())
