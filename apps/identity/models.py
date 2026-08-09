"""Employees, login roles, and compensation profiles.

Two orthogonal axes are modelled separately and must never be conflated:

- :class:`AccountRole` — *what someone can log in and do* (punch as an EMPLOYEE
  on the kiosk, or operate the MANAGER console).
- :class:`CompensationProfile` — *how someone is paid by default* (a GENERAL
  hourly worker vs. a salaried-style MANAGER profile).

Every combination is representable: a MANAGER-role person can carry a GENERAL
profile, and an EMPLOYEE-role person can carry a MANAGER profile. The profile
only seeds *default* weekly-allowance / insurance toggles; it never determines
legal eligibility, which a manager confirms explicitly (Todos 9 & 10).

No resident-registration number, address, or health information is stored — only
an opaque employee code and a display name.
"""

from __future__ import annotations

from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models

from apps.core.models import TimeStampedModel


class AccountRole(models.TextChoices):
    EMPLOYEE = "EMPLOYEE", "직원"
    MANAGER = "MANAGER", "점장"


class CompensationProfile(models.TextChoices):
    GENERAL = "GENERAL", "일반"
    MANAGER = "MANAGER", "매니저"


# Employee codes are opaque identifiers, never a person's name. Enforced shape:
# 3-20 chars of uppercase letters, digits, dash or underscore.
employee_code_validator = RegexValidator(
    regex=r"^[A-Z0-9][A-Z0-9_-]{2,19}$",
    message="Employee code must be 3-20 chars of A-Z, 0-9, '-' or '_' and is not a name.",
)


class Employee(TimeStampedModel):
    employee_code = models.CharField(
        max_length=20,
        unique=True,
        validators=[employee_code_validator],
    )
    display_name = models.CharField(max_length=60)
    hire_date = models.DateField()
    leave_date = models.DateField(null=True, blank=True)
    is_minor = models.BooleanField(default=False)

    account_role = models.CharField(
        max_length=16,
        choices=AccountRole.choices,
        default=AccountRole.EMPLOYEE,
    )
    compensation_profile = models.CharField(
        max_length=16,
        choices=CompensationProfile.choices,
        default=CompensationProfile.GENERAL,
    )

    # Managers authenticate through a Django account (wired up in Todo 4).
    # Nullable here so employees without a login are representable.
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="employee",
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(leave_date__isnull=True)
                | models.Q(leave_date__gte=models.F("hire_date")),
                name="employee_leave_not_before_hire",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.display_name} ({self.employee_code})"


# Authentication-secret models live in the auth submodule but belong to this app.
# Imported here (after Employee) so Django discovers them and there is no cycle.
from apps.identity.auth.models import (  # noqa: E402,F401
    EmployeePin,
    ManagerMfaThrottle,
    ManagerTOTP,
    RecoveryCode,
)
