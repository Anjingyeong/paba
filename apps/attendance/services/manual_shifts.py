from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from django.db import transaction
from django.db.models import Q
from django.http import QueryDict
from django.utils import timezone

from apps.attendance.models import PunchEvent, PunchKind, Shift
from apps.auditlog import services as audit
from apps.identity.models import Employee


@dataclass(frozen=True, slots=True)
class ManualShiftInput:
    employee_code: str
    started_at: datetime
    ended_at: datetime
    note: str
    idempotency_key: UUID


@dataclass(frozen=True, slots=True)
class ManualShiftInputError(Exception):
    code: str

    def __str__(self) -> str:
        return self.code


@dataclass(frozen=True, slots=True)
class ManualShiftConflict(Exception):
    code: str = "OVERLAPPING_SHIFT"

    def __str__(self) -> str:
        return self.code


def _parse_datetime(raw: str) -> datetime:
    parsed = datetime.fromisoformat(raw)
    if timezone.is_naive(parsed):
        return timezone.make_aware(parsed)
    return timezone.localtime(parsed)


def parse_manual_shift_input(raw: QueryDict) -> ManualShiftInput:
    """Parse one manager-submitted local work interval."""
    employee_code = raw.get("employee_code", "").strip()
    try:
        started_at = _parse_datetime(raw.get("started_at", ""))
        ended_at = _parse_datetime(raw.get("ended_at", ""))
        idempotency_key = UUID(raw.get("idempotency_key", ""))
    except ValueError as exc:
        raise ManualShiftInputError("INVALID_INPUT") from exc
    if not employee_code:
        raise ManualShiftInputError("EMPLOYEE_REQUIRED")
    if ended_at <= started_at:
        raise ManualShiftInputError("END_MUST_FOLLOW_START")
    return ManualShiftInput(
        employee_code=employee_code,
        started_at=started_at,
        ended_at=ended_at,
        note=raw.get("note", "").strip(),
        idempotency_key=idempotency_key,
    )


def record_manual_shift(*, employee: Employee, entry: ManualShiftInput, actor_id: str) -> Shift:
    """Append a closed work interval without mutating existing punches."""
    key_root = f"manual:{entry.idempotency_key}"
    clock_in_key = f"{key_root}:in"
    clock_out_key = f"{key_root}:out"

    with transaction.atomic():
        existing = (
            PunchEvent.objects.select_related("shift")
            .filter(idempotency_key=clock_in_key)
            .first()
        )
        if existing is not None:
            return existing.shift

        Employee.objects.select_for_update().get(pk=employee.pk)
        overlaps = Shift.objects.filter(
            employee=employee,
            opened_at__lt=entry.ended_at,
        ).filter(Q(closed_at__isnull=True) | Q(closed_at__gt=entry.started_at))
        if overlaps.exists():
            raise ManualShiftConflict()

        shift = Shift.objects.create(employee=employee, closed_at=entry.ended_at)
        Shift.objects.filter(pk=shift.pk).update(opened_at=entry.started_at)
        shift.opened_at = entry.started_at
        PunchEvent.objects.bulk_create(
            [
                PunchEvent(
                    shift=shift,
                    kind=PunchKind.CLOCK_IN,
                    occurred_at=entry.started_at,
                    idempotency_key=clock_in_key,
                ),
                PunchEvent(
                    shift=shift,
                    kind=PunchKind.CLOCK_OUT,
                    occurred_at=entry.ended_at,
                    idempotency_key=clock_out_key,
                ),
            ]
        )
        audit.record(
            actor_type="MANAGER",
            actor_id=actor_id,
            action="CREATE_MANUAL_SHIFT",
            subject_type="Shift",
            subject_id=str(shift.pk),
            result="SUCCESS",
            after={
                "employee_code": employee.employee_code,
                "started_at": entry.started_at,
                "ended_at": entry.ended_at,
                "note": entry.note,
            },
        )
        return shift
