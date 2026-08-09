"""Weekly holiday allowance (주휴수당): a manager-confirmed decision, not an
automatic rule.

The engine only produces a *warning candidate* from explicit facts — a 4-week
average of ≥ 15 scheduled weekly hours, full attendance of scheduled days, and an
ongoing employment relationship. The manager then confirms ``APPLICABLE`` or
``NOT_APPLICABLE`` with a reason; role/profile defaults are only seeds and never
decide legal eligibility.

Weekly allowance hours are the ordinary daily scheduled hours for a normal worker,
or, for a short-time worker, ``4-week scheduled hours ÷ ordinary-worker total
scheduled days`` over the same period. The amount is those hours × the ordinary
hourly wage, rounded up once. There is no ``base × 20%`` shortcut anywhere.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from apps.core.money import ceil_won

APPLICABLE = "APPLICABLE"
NOT_APPLICABLE = "NOT_APPLICABLE"
MIN_WEEKLY_HOURS = Decimal("15")


@dataclass(frozen=True)
class WeeklyAllowanceFacts:
    avg_weekly_scheduled_hours: Decimal
    full_attendance: bool
    employed: bool
    is_short_time: bool
    daily_scheduled_hours: Decimal
    four_week_scheduled_hours: Decimal
    ordinary_reference_days: Decimal
    ordinary_hourly_wage: int


@dataclass(frozen=True)
class WeeklyAllowanceDecision:
    decision: str  # APPLICABLE | NOT_APPLICABLE
    reason: str


def is_candidate(facts: WeeklyAllowanceFacts) -> bool:
    """Whether the facts warrant a weekly-allowance warning for the manager."""
    return (
        facts.avg_weekly_scheduled_hours >= MIN_WEEKLY_HOURS
        and facts.full_attendance
        and facts.employed
    )


def weekly_allowance_hours(facts: WeeklyAllowanceFacts) -> Decimal:
    if facts.is_short_time:
        if facts.ordinary_reference_days <= 0:
            raise ValueError("ordinary_reference_days must be positive for short-time workers.")
        return facts.four_week_scheduled_hours / facts.ordinary_reference_days
    return facts.daily_scheduled_hours


def weekly_allowance_amount(
    facts: WeeklyAllowanceFacts, decision: WeeklyAllowanceDecision
) -> int:
    """KRW for one week's allowance. Zero unless the manager confirmed APPLICABLE."""
    if not decision.reason.strip():
        raise ValueError("A reason is required for the weekly-allowance decision.")
    if decision.decision != APPLICABLE:
        return 0
    return ceil_won(weekly_allowance_hours(facts) * facts.ordinary_hourly_wage)
