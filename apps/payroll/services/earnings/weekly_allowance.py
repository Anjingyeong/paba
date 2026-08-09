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

from calendar import monthrange
from dataclasses import dataclass
from datetime import date, timedelta
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


def is_month_boundary_week_complete(
    month: date, weekly_rest_weekday: int, as_of: date
) -> bool:
    """Whether every labour week whose paid rest day falls in ``month`` has fully
    elapsed as of ``as_of``.

    Weekly allowance is attributed to the month containing the paid weekly rest day
    (주휴일). A labour week runs Monday-Sunday. When a week's rest day is in ``month``
    but the week extends into the next month, that week is a *month-boundary week*;
    it is only complete once its Sunday has elapsed (``<= as_of``). An incomplete
    boundary week must block the close because its allowance cannot yet be finalized.

    Determined purely from the calendar — deterministic and independent of data
    volume. Affects only *whether* a close is allowed, never any pay amount.
    """
    last_day = date(month.year, month.month, monthrange(month.year, month.month)[1])
    day = month.replace(day=1)
    while day <= last_day:
        if day.weekday() == weekly_rest_weekday:
            monday = day - timedelta(days=day.weekday())
            sunday = monday + timedelta(days=6)
            if sunday > last_day and sunday > as_of:
                return False
        day += timedelta(days=1)
    return True


def weekly_allowance_amount(
    facts: WeeklyAllowanceFacts, decision: WeeklyAllowanceDecision
) -> int:
    """KRW for one week's allowance. Zero unless the manager confirmed APPLICABLE."""
    if not decision.reason.strip():
        raise ValueError("A reason is required for the weekly-allowance decision.")
    if decision.decision != APPLICABLE:
        return 0
    return ceil_won(weekly_allowance_hours(facts) * facts.ordinary_hourly_wage)
