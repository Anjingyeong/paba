"""Pytest bootstrap: ensure the project root is importable so ``config`` and
``apps`` resolve regardless of the invocation directory."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
