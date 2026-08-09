"""Idempotently prepare the previous month's DRAFT payroll period.

Intended to run on the 1st of each month (Asia/Seoul) via the scheduler. Running
it repeatedly, or concurrently, still yields exactly one period per month.
"""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand
from django.db import IntegrityError
from django.utils import timezone

from apps.payroll.services.close import prepare_previous_month


class Command(BaseCommand):
    help = "Prepare the previous month's DRAFT payroll period (idempotent)."

    def handle(self, *args: Any, **options: Any) -> None:
        try:
            period = prepare_previous_month(timezone.localdate())
        except IntegrityError:
            self.stdout.write("Period already prepared.")
            return
        self.stdout.write(f"Prepared {period.month:%Y-%m} ({period.status}).")
