"""Insurance reconciliation lifecycle: estimate → reconcile / not-applicable.

A close requires every employee insurance to reach a manager-final status. This
module never touches industrial-accident insurance (employer-only).
"""

from __future__ import annotations

from datetime import date

from django.core.exceptions import ValidationError

from apps.payroll.models.deductions import (
    InsuranceReconciliation,
    InsuranceStatus,
)

from .estimate import EMPLOYEE_INSURANCES, estimate_premium, load_rates

FINAL_STATUSES = frozenset({InsuranceStatus.RECONCILED, InsuranceStatus.NOT_APPLICABLE})


def set_estimate(*, employee, period_month: date, insurance: str, monthly_base: int, version: str):
    entry = load_rates(version)["insurances"][insurance]
    amount = estimate_premium(insurance, monthly_base, version)
    obj, _ = InsuranceReconciliation.objects.update_or_create(
        employee=employee,
        period_month=period_month,
        insurance=insurance,
        defaults={
            "status": InsuranceStatus.ESTIMATED,
            "rate_version": version,
            "source_url": entry["source_url"],
            "monthly_base": monthly_base,
            "estimated_amount": amount,
            "final_amount": None,
            "variance": None,
        },
    )
    return obj


def reconcile(
    *, employee, period_month: date, insurance: str, final_amount: int, manager, reason: str
):
    if not reason.strip():
        raise ValidationError("Reconciliation requires a reason.")
    obj = InsuranceReconciliation.objects.get(
        employee=employee, period_month=period_month, insurance=insurance
    )
    obj.status = InsuranceStatus.RECONCILED
    obj.final_amount = final_amount
    obj.variance = final_amount - obj.estimated_amount
    obj.manager = manager
    obj.reason = reason
    obj.save()
    return obj


def set_not_applicable(*, employee, period_month: date, insurance: str, manager, reason: str):
    if not reason.strip():
        raise ValidationError("Marking NOT_APPLICABLE requires a reason.")
    obj, _ = InsuranceReconciliation.objects.update_or_create(
        employee=employee,
        period_month=period_month,
        insurance=insurance,
        defaults={
            "status": InsuranceStatus.NOT_APPLICABLE,
            "final_amount": 0,
            "variance": None,
            "manager": manager,
            "reason": reason,
        },
    )
    return obj


def all_insurances_final(*, employee, period_month: date) -> bool:
    """True iff all four employee insurances have a manager-final status."""
    rows = InsuranceReconciliation.objects.filter(employee=employee, period_month=period_month)
    by_insurance = {r.insurance: r.status for r in rows}
    return all(
        by_insurance.get(kind) in FINAL_STATUSES for kind in EMPLOYEE_INSURANCES
    )
