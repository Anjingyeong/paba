"""Core building blocks shared across domain apps.

- :class:`Store` is a hard singleton: this product serves exactly one store, so
  there is no tenant key anywhere in the schema.
- :class:`EffectiveDatedModel` is the abstract base for every policy that changes
  over time (wages, terms, applicability decisions). Each row carries a half-open
  ``effective`` date range ``[start, end)``; subclasses add a PostgreSQL exclusion
  constraint so two rows for the same subject can never overlap, while adjacent
  ranges (touching endpoints) are allowed.
"""

from __future__ import annotations

from datetime import date

from django.contrib.postgres.fields import DateRangeField
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Store(TimeStampedModel):
    """The single store. Enforced to a single row (pk=1)."""

    SINGLETON_PK = 1

    name = models.CharField(max_length=120)
    payroll_pay_day = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(28)],
        help_text="Day of the following month used as the payroll payment date.",
    )
    auto_payroll_close_enabled = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(pk=1),
                name="store_is_singleton",
            ),
        ]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs) -> None:
        self.pk = self.SINGLETON_PK
        super().save(*args, **kwargs)

    @classmethod
    def get(cls) -> Store:
        obj, _ = cls.objects.get_or_create(pk=cls.SINGLETON_PK, defaults={"name": "매장"})
        return obj


class EffectiveDatedModel(TimeStampedModel):
    """Abstract base for effective-dated policy rows.

    ``effective`` is a half-open ``[lower, upper)`` date range. ``upper`` may be
    unbounded (``None``) for the currently-in-force row. Subclasses MUST declare
    an ``ExclusionConstraint`` over their subject FK + ``effective`` to forbid
    overlapping periods at the database level.
    """

    effective = DateRangeField(
        help_text="Half-open [start, end) date range this row is in force.",
    )

    class Meta:
        abstract = True

    @property
    def effective_start(self) -> date | None:
        return self.effective.lower if self.effective else None

    @property
    def effective_end(self) -> date | None:
        return self.effective.upper if self.effective else None

    def clean(self) -> None:
        super().clean()
        rng = self.effective
        if rng is None or rng.lower is None:
            raise ValidationError({"effective": "An effective start date is required."})
        if rng.upper is not None and rng.upper <= rng.lower:
            raise ValidationError({"effective": "Effective end must be after the start date."})
