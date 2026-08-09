"""Per-employee, per-month insurance reconciliation records.

Each of the four employee insurances carries a lifecycle status. A close is only
permitted once every insurance has a manager-final status (RECONCILED or
NOT_APPLICABLE); an ESTIMATED-only insurance blocks the close.
"""

from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.identity.models import Employee


class InsuranceKindChoices(models.TextChoices):
    NATIONAL_PENSION = "NATIONAL_PENSION", "국민연금"
    HEALTH = "HEALTH", "건강보험"
    LONG_TERM_CARE = "LONG_TERM_CARE", "장기요양"
    EMPLOYMENT = "EMPLOYMENT", "고용보험"


class InsuranceStatus(models.TextChoices):
    NOT_APPLICABLE = "NOT_APPLICABLE", "미가입"
    ESTIMATED = "ESTIMATED", "예상"
    RECONCILED = "RECONCILED", "대사완료"


class InsuranceReconciliation(models.Model):
    employee = models.ForeignKey(
        Employee, on_delete=models.PROTECT, related_name="insurance_reconciliations"
    )
    period_month = models.DateField(help_text="First day of the pay month (Asia/Seoul).")
    insurance = models.CharField(max_length=20, choices=InsuranceKindChoices.choices)

    status = models.CharField(max_length=16, choices=InsuranceStatus.choices)
    rate_version = models.CharField(max_length=16, blank=True)
    source_url = models.URLField(blank=True)
    monthly_base = models.PositiveIntegerField(default=0)
    estimated_amount = models.PositiveIntegerField(default=0)
    final_amount = models.IntegerField(null=True, blank=True)
    variance = models.IntegerField(null=True, blank=True)
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    reason = models.CharField(max_length=255, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["employee", "period_month", "insurance"],
                name="one_reconciliation_per_employee_month_insurance",
            ),
        ]

    def __str__(self) -> str:
        return f"InsuranceReconciliation#{self.pk} {self.insurance} {self.status}"
