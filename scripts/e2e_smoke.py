"""End-to-end integration smoke: drive the whole business flow with synthetic data
and produce a real export ZIP, then roll everything back so the dev DB stays clean.

Run:  uv run python scripts/e2e_smoke.py
Chains: employee + effective policies -> kiosk pairing -> punches -> approval ->
payable-time -> base pay -> weekly allowance -> insurance reconcile -> prepare
period -> close (immutable snapshot) -> XLSX/ZIP export (verified in-memory).
"""

from __future__ import annotations

import datetime as dt
import io
import os
import sys
import zipfile
from decimal import Decimal
from pathlib import Path

import django

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()

from django.contrib.auth.models import User  # noqa: E402
from django.db import transaction  # noqa: E402
from django.db.backends.postgresql.psycopg_any import DateRange  # noqa: E402

from apps.attendance.models import PunchKind  # noqa: E402
from apps.attendance.services import approvals, corrections  # noqa: E402
from apps.attendance.services.punches import record_punch  # noqa: E402
from apps.attendance.services.time_calculation import calculate  # noqa: E402
from apps.core.models import Store  # noqa: E402
from apps.devices.services import activate_device, create_pairing_code  # noqa: E402
from apps.exports.services import create_export  # noqa: E402
from apps.identity.models import CompensationProfile, Employee  # noqa: E402
from apps.payroll.models import EmploymentTerms, HourlyWage  # noqa: E402
from apps.payroll.models.policies import Weekday  # noqa: E402
from apps.payroll.services.close import close_period, prepare_period  # noqa: E402
from apps.payroll.services.deductions import EMPLOYEE_INSURANCES, reconciliation  # noqa: E402
from apps.payroll.services.earnings import (  # noqa: E402
    RatedSegment,
    WeeklyAllowanceDecision,
    WeeklyAllowanceFacts,
    calculate_base_pay,
    weekly_allowance_amount,
)
from apps.payroll.services.earnings.weekly_allowance import APPLICABLE  # noqa: E402


def main() -> None:
    sid = transaction.savepoint()
    try:
        Store.get()
        manager = User.objects.create_user("smoke-mgr", password="pw-123456-strong", is_staff=True)
        emp = Employee.objects.create(
            employee_code="EMP-SMOKE1", display_name="합성직원",
            hire_date=dt.date(2026, 1, 1), compensation_profile=CompensationProfile.GENERAL,
        )
        HourlyWage.objects.create(
            employee=emp, hourly_wage=12000, effective=DateRange(dt.date(2026, 1, 1), None)
        )
        EmploymentTerms.objects.create(
            employee=emp, effective=DateRange(dt.date(2026, 1, 1), None),
            weekly_rest_weekday=Weekday.SUNDAY, work_weekdays=[0, 1, 2, 3, 4],
            daily_scheduled_hours=Decimal("8"), scheduled_weekly_hours=Decimal("40"),
            ordinary_worker_reference_days=Decimal("20"),
        )

        # Kiosk pairing + a full punch cycle.
        result = activate_device(create_pairing_code(manager), "매장 태블릿")
        assert result is not None
        dev = result.device
        ci = record_punch(employee=emp, kind=PunchKind.CLOCK_IN, idempotency_key="s-in", device=dev)
        record_punch(employee=emp, kind=PunchKind.CLOCK_OUT, idempotency_key="s-out", device=dev)
        approvals.approve_shift(manager=manager, shift=ci.shift)

        # Payable time -> base pay (rate the segments at the effective wage).
        events = corrections.effective_events(ci.shift)
        time_result = calculate(events)
        assert time_result.ok, time_result.blockers
        segments = [RatedSegment(s.hours, 12000) for s in time_result.segments]
        base = calculate_base_pay(segments)

        # Weekly allowance (manager-confirmed) — synthetic facts.
        facts = WeeklyAllowanceFacts(
            avg_weekly_scheduled_hours=Decimal("40"), full_attendance=True, employed=True,
            is_short_time=False, daily_scheduled_hours=Decimal("8"),
            four_week_scheduled_hours=Decimal("160"), ordinary_reference_days=Decimal("20"),
            ordinary_hourly_wage=12000,
        )
        weekly = weekly_allowance_amount(facts, WeeklyAllowanceDecision(APPLICABLE, "주15h+ 개근"))

        # Insurance: estimate + reconcile all four.
        period_month = dt.date(2026, 7, 1)
        for ins in EMPLOYEE_INSURANCES:
            reconciliation.set_estimate(
                employee=emp, period_month=period_month, insurance=ins,
                monthly_base=base.amount_krw + weekly, version="2026.1",
            )
            reconciliation.reconcile(
                employee=emp, period_month=period_month, insurance=ins,
                final_amount=1000, manager=manager, reason="기관 고지액",
            )
        assert reconciliation.all_insurances_final(employee=emp, period_month=period_month)

        total_deduction = 4000
        net = base.amount_krw + weekly - total_deduction

        # Close -> immutable snapshot.
        payload = {
            "pay_date": "2026-08-05", "calc_period": "2026-07",
            "lines": [{
                "employee_id": emp.employee_code, "department": "베이커리", "title": "사원",
                "net": net, "insurance_final": True,
                "earnings": [
                    {"label": "기본급", "amount": base.amount_krw},
                    {"label": "주휴수당", "amount": weekly},
                ],
                "deductions": [{"label": "4대보험", "amount": total_deduction}],
                "detail_lines": [f"지급시간 {time_result.total_hours}h × 12,000"],
            }],
        }
        period = prepare_period(period_month)
        snapshot = close_period(period=period, payload=payload)

        # Export -> ZIP (verified in-memory).
        _manifest, zip_bytes = create_export(snapshot=snapshot, requester=manager)
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            names = zf.namelist()

        out_dir = ".omo/evidence"
        os.makedirs(out_dir, exist_ok=True)
        with open(f"{out_dir}/e2e-smoke-export.zip", "wb") as fh:
            fh.write(zip_bytes)

        print("END-TO-END SMOKE OK")
        print(f"  payable hours   : {time_result.total_hours}")
        print(f"  base pay        : {base.amount_krw:,} KRW")
        print(f"  weekly allowance: {weekly:,} KRW")
        print(f"  net pay         : {net:,} KRW")
        print(f"  snapshot        : v{snapshot.version} checksum={snapshot.checksum[:12]}…")
        print(f"  export files    : {names}")
        print(f"  saved artifact  : {out_dir}/e2e-smoke-export.zip ({len(zip_bytes):,} bytes)")
    finally:
        transaction.savepoint_rollback(sid)
        print("  (dev DB rolled back — no synthetic data persisted)")


if __name__ == "__main__":
    with transaction.atomic():
        main()
