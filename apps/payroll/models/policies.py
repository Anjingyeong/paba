"""Effective-dated compensation & applicability policies.

Each model records how one subject (an employee, or the store) is treated over a
half-open date range. A PostgreSQL exclusion constraint (GiST, needs the
``btree_gist`` extension) forbids two rows for the same subject whose ranges
*overlap*, while allowing *adjacent* ranges to meet exactly — so a wage change on
2026-07-01 is expressed as ``[.., 2026-07-01)`` + ``[2026-07-01, ..)`` with no gap
and no overlap.

Applicability of the weekly holiday allowance (주휴수당) and the four social
insurances is stored as an explicit *decision with a source*. The compensation
profile only seeds the creation default; a manager confirms the real legal
applicability later (Todos 9 & 10). Industrial-accident insurance (산재) is
employer-only and is never an employee-side toggle here.
"""

from __future__ import annotations

from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import ArrayField, RangeOperators
from django.core.validators import MinValueValidator
from django.db import models

from apps.core.models import EffectiveDatedModel, Store
from apps.identity.models import CompensationProfile, Employee


class Weekday(models.IntegerChoices):
    MONDAY = 0, "월"
    TUESDAY = 1, "화"
    WEDNESDAY = 2, "수"
    THURSDAY = 3, "목"
    FRIDAY = 4, "금"
    SATURDAY = 5, "토"
    SUNDAY = 6, "일"


class ApplicabilityDecision(models.TextChoices):
    APPLICABLE = "APPLICABLE", "적용"
    NOT_APPLICABLE = "NOT_APPLICABLE", "미적용"


class HeadcountBracket(models.TextChoices):
    UNDER_5 = "UNDER_5", "5인 미만"
    FROM_5_TO_49 = "FROM_5_TO_49", "5~49인"
    FROM_50_TO_299 = "FROM_50_TO_299", "50~299인"
    OVER_300 = "OVER_300", "300인 이상"


def default_applicability_for(profile: str) -> str:
    """Creation-time default only. GENERAL → off, MANAGER → on.

    This is a convenience seed, NOT a legal determination: a manager may set the
    opposite decision with a recorded source at any time.
    """
    if profile == CompensationProfile.MANAGER:
        return ApplicabilityDecision.APPLICABLE
    return ApplicabilityDecision.NOT_APPLICABLE


class HourlyWage(EffectiveDatedModel):
    """The contractual hourly wage in whole KRW, effective-dated per employee."""

    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name="hourly_wages")
    hourly_wage = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text="Whole KRW per hour.",
    )

    class Meta:
        constraints = [
            ExclusionConstraint(
                name="hourly_wage_no_overlap_per_employee",
                expressions=[
                    ("employee", RangeOperators.EQUAL),
                    ("effective", RangeOperators.OVERLAPS),
                ],
            ),
        ]

    def __str__(self) -> str:
        return f"HourlyWage#{self.pk}: {self.hourly_wage}원 {self.effective}"


class EmploymentTerms(EffectiveDatedModel):
    """Scheduled-work terms used by time calculation and weekly-allowance logic.

    The contract week is Monday-Sunday (fixed). Break minutes here are *scheduled*
    and informational only — unrecorded scheduled breaks are never auto-deducted
    without evidence (that rule lives in the time-calculation engine, Todo 8).
    """

    employee = models.ForeignKey(
        Employee, on_delete=models.PROTECT, related_name="employment_terms"
    )
    week_start_weekday = models.PositiveSmallIntegerField(
        choices=Weekday.choices,
        default=Weekday.MONDAY,
        help_text="Fixed to Monday; the labour week runs Monday-Sunday.",
    )
    weekly_rest_weekday = models.PositiveSmallIntegerField(
        choices=Weekday.choices,
        help_text="The paid weekly rest day (주휴일).",
    )
    work_weekdays = ArrayField(
        models.PositiveSmallIntegerField(choices=Weekday.choices),
        help_text="Weekdays normally worked.",
    )
    daily_scheduled_hours = models.DecimalField(max_digits=5, decimal_places=2)
    scheduled_weekly_hours = models.DecimalField(max_digits=6, decimal_places=2)
    ordinary_worker_reference_days = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        help_text="통상근로자 기준일수 for short-time weekly-allowance proration.",
    )
    scheduled_break_minutes = models.PositiveSmallIntegerField(
        default=0,
        help_text="Informational scheduled break; not auto-deducted without a recorded break.",
    )

    class Meta:
        constraints = [
            ExclusionConstraint(
                name="employment_terms_no_overlap_per_employee",
                expressions=[
                    ("employee", RangeOperators.EQUAL),
                    ("effective", RangeOperators.OVERLAPS),
                ],
            ),
        ]

    def __str__(self) -> str:
        return f"EmploymentTerms#{self.pk} {self.effective}"


class WeeklyAllowanceApplicability(EffectiveDatedModel):
    """Manager-owned decision on whether the weekly holiday allowance applies."""

    employee = models.ForeignKey(
        Employee, on_delete=models.PROTECT, related_name="weekly_allowance_applicability"
    )
    decision = models.CharField(max_length=16, choices=ApplicabilityDecision.choices)
    source = models.CharField(
        max_length=255,
        help_text="Basis for the decision (e.g. contract facts, manager note).",
    )

    class Meta:
        constraints = [
            ExclusionConstraint(
                name="weekly_allowance_no_overlap_per_employee",
                expressions=[
                    ("employee", RangeOperators.EQUAL),
                    ("effective", RangeOperators.OVERLAPS),
                ],
            ),
        ]

    def __str__(self) -> str:
        return f"WeeklyAllowance#{self.pk} {self.decision} {self.effective}"


class InsuranceApplicability(EffectiveDatedModel):
    """Per-employee enrollment decision for the four employee-side insurances.

    National pension, health, long-term care and employment insurance each carry
    an explicit applicability flag with a shared source note. Detailed rates and
    institution reconciliation are added in Todo 10.
    """

    employee = models.ForeignKey(
        Employee, on_delete=models.PROTECT, related_name="insurance_applicability"
    )
    national_pension = models.BooleanField()
    health = models.BooleanField()
    long_term_care = models.BooleanField()
    employment = models.BooleanField()
    source = models.CharField(max_length=255)

    class Meta:
        constraints = [
            ExclusionConstraint(
                name="insurance_applicability_no_overlap_per_employee",
                expressions=[
                    ("employee", RangeOperators.EQUAL),
                    ("effective", RangeOperators.OVERLAPS),
                ],
            ),
        ]

    def __str__(self) -> str:
        return f"InsuranceApplicability#{self.pk} {self.effective}"


class StoreHeadcountBracket(EffectiveDatedModel):
    """The store's regular-worker headcount bracket over time (상시근로자 구간).

    Affects which labour rules apply; recorded with a source and effective-dated.
    """

    store = models.ForeignKey(Store, on_delete=models.PROTECT, related_name="headcount_brackets")
    bracket = models.CharField(max_length=16, choices=HeadcountBracket.choices)
    source = models.CharField(max_length=255)

    class Meta:
        constraints = [
            ExclusionConstraint(
                name="store_headcount_no_overlap",
                expressions=[
                    ("store", RangeOperators.EQUAL),
                    ("effective", RangeOperators.OVERLAPS),
                ],
            ),
        ]

    def __str__(self) -> str:
        return f"store {self.bracket} {self.effective}"
