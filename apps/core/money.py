"""Money policy helpers.

Every monetary amount stored in the system is an integer number of Korean won
(KRW). Intermediate arithmetic uses :class:`decimal.Decimal`; only the final,
end-of-earnings amount is quantized to an integer, and positive earnings round
*up* (``ROUND_CEILING``) so employees are never shortchanged by fractions.

This module holds the shared primitives; the payroll engine (Todo 9) composes
them into full calculations.
"""

from __future__ import annotations

from decimal import ROUND_CEILING, Decimal

from django.core.exceptions import ValidationError

# One won is the smallest representable unit; there are no sub-won amounts.
WON = Decimal("1")


def ceil_won(amount: Decimal) -> int:
    """Round a Decimal amount up to whole won. Used for positive earnings only."""
    return int(amount.quantize(WON, rounding=ROUND_CEILING))


def validate_non_negative_krw(value: int) -> None:
    """Model-field validator: stored KRW amounts are whole, non-negative won."""
    if not isinstance(value, int):  # pragma: no cover - defensive
        raise ValidationError("KRW amounts must be integers (whole won).")
    if value < 0:
        raise ValidationError("KRW amounts must not be negative.")
