"""Server-authoritative, idempotent punch recording.

``record_punch`` is the single way punches enter the system. It:

- is **idempotent** on ``idempotency_key`` — a resent or double-tapped request
  returns the already-recorded event instead of creating a second one;
- is **server-authoritative** on time — the caller's clock is ignored; the event
  timestamp is ``timezone.now()`` (Asia/Seoul);
- enforces the **state machine** CLOCK_IN → (BREAK_START ↔ BREAK_END)* → CLOCK_OUT
  under a row lock, so concurrent punches cannot interleave illegally; and
- guarantees **one open shift per employee** via a partial unique constraint, so
  two concurrent CLOCK_INs cannot both open a shift.

Invalid transitions raise :class:`InvalidPunch` with a stable ``code``.
"""

from __future__ import annotations

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.attendance.models import PunchEvent, PunchKind, Shift
from apps.devices.models import KioskDevice
from apps.identity.models import Employee

# Shift states derived from the last event of the open shift.
IDLE = "IDLE"
WORKING = "WORKING"
ON_BREAK = "ON_BREAK"

# Which punch kind is allowed from each state.
_ALLOWED_NEXT = {
    IDLE: {PunchKind.CLOCK_IN},
    WORKING: {PunchKind.BREAK_START, PunchKind.CLOCK_OUT},
    ON_BREAK: {PunchKind.BREAK_END},
}


class InvalidPunch(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _state_of_open_shift(shift: Shift | None) -> str:
    if shift is None:
        return IDLE
    last = PunchEvent.objects.filter(shift=shift).order_by("-occurred_at", "-id").first()
    if last is None or last.kind in (PunchKind.CLOCK_IN, PunchKind.BREAK_END):
        return WORKING
    if last.kind == PunchKind.BREAK_START:
        return ON_BREAK
    return IDLE  # CLOCK_OUT — the shift is already closed


def current_shift_state(employee: Employee) -> str:
    """Return the employee's server-authoritative attendance state."""
    shift = Shift.objects.filter(employee=employee, closed_at__isnull=True).first()
    return _state_of_open_shift(shift)


def record_punch(
    *,
    employee: Employee,
    kind: str,
    idempotency_key: str,
    device: KioskDevice | None = None,
    now=None,
) -> PunchEvent:
    now = now or timezone.now()

    with transaction.atomic():
        # Idempotency: an identical key means "same action" — return what exists.
        existing = PunchEvent.objects.filter(idempotency_key=idempotency_key).first()
        if existing is not None:
            return existing

        if kind == PunchKind.CLOCK_IN:
            return _clock_in(employee, idempotency_key, device, now)

        open_shift = (
            Shift.objects.select_for_update()
            .filter(employee=employee, closed_at__isnull=True)
            .first()
        )
        # Re-check the key once the shift row is locked: a concurrent duplicate with
        # the same key may have committed (and possibly closed the shift) while we
        # waited on the lock. If so, this *is* that action — return it idempotently
        # instead of erroring.
        if open_shift is None:
            return _existing_or(idempotency_key, InvalidPunch("NO_OPEN_SHIFT"))

        state = _state_of_open_shift(open_shift)
        if kind not in _ALLOWED_NEXT[state]:
            return _existing_or(
                idempotency_key, InvalidPunch(f"ILLEGAL_TRANSITION_{state}_{kind}")
            )

        try:
            event = PunchEvent.objects.create(
                shift=open_shift, kind=kind, occurred_at=now,
                device=device, idempotency_key=idempotency_key,
            )
        except IntegrityError:
            return _existing_or(idempotency_key, InvalidPunch("DUPLICATE"))
        if kind == PunchKind.CLOCK_OUT:
            open_shift.closed_at = now
            open_shift.save(update_fields=["closed_at"])
        return event


def _existing_or(key: str, error: InvalidPunch) -> PunchEvent:
    """Return the event already recorded under ``key`` (idempotent), else raise."""
    existing = PunchEvent.objects.filter(idempotency_key=key).first()
    if existing is not None:
        return existing
    raise error


def _clock_in(employee: Employee, key: str, device: KioskDevice | None, now) -> PunchEvent:
    try:
        with transaction.atomic():
            shift = Shift.objects.create(employee=employee)
            return PunchEvent.objects.create(
                shift=shift, kind=PunchKind.CLOCK_IN, occurred_at=now,
                device=device, idempotency_key=key,
            )
    except IntegrityError:
        # Either the same key won a concurrent race (return that event, idempotent),
        # or another shift is already open for this employee (genuine conflict).
        existing = PunchEvent.objects.filter(idempotency_key=key).first()
        if existing is not None:
            return existing
        raise InvalidPunch("SHIFT_ALREADY_OPEN") from None
