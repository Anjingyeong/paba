"""Effective-dated policy models: overlap prevention, adjacency, and reads."""

from __future__ import annotations

import datetime as dt

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.backends.postgresql.psycopg_any import DateRange

from apps.core.models import Store
from apps.identity.models import CompensationProfile, Employee
from apps.payroll.models import (
    ApplicabilityDecision,
    EmploymentTerms,
    HeadcountBracket,
    HourlyWage,
    StoreHeadcountBracket,
    default_applicability_for,
)

pytestmark = pytest.mark.django_db


def _employee(code: str = "EMP-001") -> Employee:
    return Employee.objects.create(
        employee_code=code, display_name="합성직원", hire_date=dt.date(2026, 1, 1)
    )


# --- HourlyWage overlap / adjacency -----------------------------------------
def test_adjacent_wage_periods_are_allowed() -> None:
    emp = _employee()
    HourlyWage.objects.create(
        employee=emp, hourly_wage=10000,
        effective=DateRange(dt.date(2026, 1, 1), dt.date(2026, 7, 1)),
    )
    # Touching endpoint, no overlap thanks to half-open [start, end).
    HourlyWage.objects.create(
        employee=emp, hourly_wage=11000,
        effective=DateRange(dt.date(2026, 7, 1), None),
    )
    assert HourlyWage.objects.filter(employee=emp).count() == 2


def test_overlapping_wage_periods_are_rejected() -> None:
    emp = _employee()
    HourlyWage.objects.create(
        employee=emp, hourly_wage=10000,
        effective=DateRange(dt.date(2026, 1, 1), dt.date(2026, 7, 1)),
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        HourlyWage.objects.create(
            employee=emp, hourly_wage=11000,
            effective=DateRange(dt.date(2026, 6, 1), None),  # 1-month overlap
        )


def test_single_day_overlap_is_rejected() -> None:
    emp = _employee()
    HourlyWage.objects.create(
        employee=emp, hourly_wage=10000,
        effective=DateRange(dt.date(2026, 1, 1), dt.date(2026, 7, 2)),
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        HourlyWage.objects.create(
            employee=emp, hourly_wage=11000,
            effective=DateRange(dt.date(2026, 7, 1), None),  # overlaps on 2026-07-01
        )


def test_two_employees_do_not_collide() -> None:
    a, b = _employee("EMP-A"), _employee("EMP-B")
    rng = DateRange(dt.date(2026, 1, 1), None)
    HourlyWage.objects.create(employee=a, hourly_wage=10000, effective=rng)
    HourlyWage.objects.create(employee=b, hourly_wage=12000, effective=rng)
    assert HourlyWage.objects.count() == 2


def test_wage_reads_by_effective_date() -> None:
    emp = _employee()
    HourlyWage.objects.create(
        employee=emp, hourly_wage=10000,
        effective=DateRange(dt.date(2026, 1, 1), dt.date(2026, 7, 1)),
    )
    HourlyWage.objects.create(
        employee=emp, hourly_wage=11000,
        effective=DateRange(dt.date(2026, 7, 1), None),
    )
    jan = HourlyWage.objects.get(employee=emp, effective__contains=dt.date(2026, 1, 15))
    jul = HourlyWage.objects.get(employee=emp, effective__contains=dt.date(2026, 7, 15))
    assert jan.hourly_wage == 10000
    assert jul.hourly_wage == 11000


# --- Effective range validation ---------------------------------------------
def test_effective_end_before_start_is_invalid() -> None:
    emp = _employee()
    wage = HourlyWage(
        employee=emp, hourly_wage=10000,
        effective=DateRange(dt.date(2026, 7, 1), dt.date(2026, 6, 1)),
    )
    with pytest.raises(ValidationError):
        wage.full_clean()


def test_missing_effective_start_is_invalid() -> None:
    emp = _employee()
    wage = HourlyWage(employee=emp, hourly_wage=10000, effective=DateRange(None, None))
    with pytest.raises(ValidationError):
        wage.full_clean()


# --- Required contract facts -------------------------------------------------
def test_employment_terms_require_core_facts() -> None:
    emp = _employee()
    terms = EmploymentTerms(
        employee=emp,
        effective=DateRange(dt.date(2026, 1, 1), None),
        # weekly_rest_weekday, work_weekdays, hours intentionally omitted
    )
    with pytest.raises(ValidationError):
        terms.full_clean()


# --- Applicability defaults --------------------------------------------------
def test_applicability_defaults_follow_profile_but_are_only_seeds() -> None:
    assert default_applicability_for(CompensationProfile.GENERAL) == (
        ApplicabilityDecision.NOT_APPLICABLE
    )
    assert default_applicability_for(CompensationProfile.MANAGER) == (
        ApplicabilityDecision.APPLICABLE
    )


# --- Store headcount bracket overlap ----------------------------------------
def test_store_headcount_bracket_overlap_rejected() -> None:
    store = Store.get()
    StoreHeadcountBracket.objects.create(
        store=store, bracket=HeadcountBracket.UNDER_5, source="초기",
        effective=DateRange(dt.date(2026, 1, 1), None),
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        StoreHeadcountBracket.objects.create(
            store=store, bracket=HeadcountBracket.FROM_5_TO_49, source="변경",
            effective=DateRange(dt.date(2026, 6, 1), None),
        )
