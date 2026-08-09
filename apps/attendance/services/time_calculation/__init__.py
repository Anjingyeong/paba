"""Payable-time calculation.

Turns a shift's (possibly corrected) punch sequence into deterministic payable
segments, split at day/rate/employment boundaries, using exact Decimal arithmetic.
See :mod:`.core`.
"""

from __future__ import annotations

from .core import PayableSegment, TimeResult, calculate

__all__ = ["PayableSegment", "TimeResult", "calculate"]
