from __future__ import annotations

from datetime import date

from apps.payroll.services.preview import monthly_payroll_lines


class PayrollBuildBlocked(Exception):
    def __init__(self, blockers: list[str]):
        super().__init__(", ".join(blockers))
        self.blockers = blockers


def build_month_payload(month: date, *, pay_date: date) -> dict:
    """Build the immutable close payload from the live monthly attendance preview.

    The current single-store workflow pays hourly base wages from approved attendance.
    Statutory/manager adjustments can be added as explicit earnings/deductions later
    without changing the snapshot/export contract.
    """
    lines = monthly_payroll_lines(month)
    blockers: set[str] = set()
    for line in lines:
        blockers.update(line.blockers)
    if not lines:
        blockers.add("NO_PAYROLL_LINES")
    if blockers:
        raise PayrollBuildBlocked(sorted(blockers))

    return {
        "pay_date": pay_date.isoformat(),
        "calc_period": f"{month:%Y-%m}",
        "lines": [
            {
                "employee_id": line.employee_code,
                "department": "매장",
                "title": "직원",
                "hours": str(line.total_hours),
                "gross": line.gross_pay,
                "net": line.gross_pay,
                "earnings": [{"label": "기본급", "amount": line.gross_pay}],
                "deductions": [],
                "detail_lines": [
                    f"기본급: {line.total_hours:.2f}시간 × 해당 근무일 적용 시급"
                ],
                "time_blockers": list(line.blockers),
            }
            for line in lines
        ],
    }