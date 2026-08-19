from __future__ import annotations

from datetime import date

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.core.models import Store
from apps.payroll.models import PeriodStatus
from apps.payroll.services.close import CloseBlocked, close_period, latest_snapshot, prepare_period
from apps.payroll.services.month_close import PayrollBuildBlocked, build_month_payload


def previous_month(today: date) -> date:
    first = today.replace(day=1)
    if first.month == 1:
        return date(first.year - 1, 12, 1)
    return date(first.year, first.month - 1, 1)


def pay_date_for_month(month: date, pay_day: int) -> date:
    if month.month == 12:
        return date(month.year + 1, 1, pay_day)
    return date(month.year, month.month + 1, pay_day)


class Command(BaseCommand):
    help = "Safely finalize the previous month's payroll when every close gate is ready."

    def handle(self, *args, **options) -> None:
        today = timezone.localdate()
        month = previous_month(today)
        store = Store.get()

        if not store.auto_payroll_close_enabled:
            self.stdout.write("Automatic payroll close is disabled; nothing to do.")
            return
        if store.payroll_pay_day is None:
            self.stderr.write(self.style.WARNING("Payroll pay day is not configured; skipping."))
            return

        period = prepare_period(month)
        snapshot = latest_snapshot(period)
        if period.status == PeriodStatus.CLOSED and snapshot is not None:
            self.stdout.write(
                f"{month:%Y-%m} already closed at v{snapshot.version}; nothing to do."
            )
            return
        if snapshot is not None:
            self.stderr.write(
                self.style.WARNING(
                    f"{month:%Y-%m} was reopened after v{snapshot.version}; "
                    "manual reclose required."
                )
            )
            return

        pay_date = pay_date_for_month(month, store.payroll_pay_day)
        try:
            payload = build_month_payload(month, pay_date=pay_date)
            snapshot = close_period(
                period=period,
                payload=payload,
                reason="automatic previous-month close",
            )
        except PayrollBuildBlocked as exc:
            self.stderr.write(
                self.style.WARNING(
                    f"{month:%Y-%m} payroll build blocked: {', '.join(exc.blockers)}"
                )
            )
            return
        except CloseBlocked as exc:
            self.stderr.write(
                self.style.WARNING(f"{month:%Y-%m} close blocked: {', '.join(exc.blockers)}")
            )
            return

        self.stdout.write(
            self.style.SUCCESS(
                f"Closed {month:%Y-%m} payroll at v{snapshot.version}; statements are ready."
            )
        )