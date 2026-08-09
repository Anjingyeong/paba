"""Earnings engine: base pay, manager-confirmed weekly allowance, manual items.

Only base pay and confirmed weekly allowance are ever *calculated*. All other
positive earnings (bonus/overtime/night/holiday/other) and every deduction-side
adjustment are manager-entered final amounts with an explanation — never derived
by a formula. Monetary rounding (``ROUND_CEILING``) happens once, at the end of the
positive earnings, never mid-calculation.
"""

from __future__ import annotations

from .base import BasePayResult, RatedSegment, calculate_base_pay
from .manual import ALLOWED_MANUAL_KINDS, ManualEarning, validate_manual_earning
from .weekly_allowance import (
    MIN_WEEKLY_HOURS,
    WeeklyAllowanceDecision,
    WeeklyAllowanceFacts,
    is_candidate,
    is_month_boundary_week_complete,
    weekly_allowance_amount,
    weekly_allowance_hours,
)

__all__ = [
    "ALLOWED_MANUAL_KINDS",
    "MIN_WEEKLY_HOURS",
    "BasePayResult",
    "ManualEarning",
    "RatedSegment",
    "WeeklyAllowanceDecision",
    "WeeklyAllowanceFacts",
    "calculate_base_pay",
    "is_candidate",
    "is_month_boundary_week_complete",
    "validate_manual_earning",
    "weekly_allowance_amount",
    "weekly_allowance_hours",
]
