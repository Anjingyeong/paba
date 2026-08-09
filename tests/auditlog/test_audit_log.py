"""The audit log is append-only at both the model and database layers."""

from __future__ import annotations

import pytest
from django.db import InternalError, ProgrammingError, transaction

from apps.auditlog import services
from apps.auditlog.models import AuditImmutableError, AuditLogEntry

pytestmark = pytest.mark.django_db


def _entry() -> AuditLogEntry:
    return services.record(
        actor_type="MANAGER",
        actor_id="u1",
        action="UPDATE",
        subject_type="Employee",
        subject_id="EMP-001",
        result="SUCCESS",
        before={"wage": 10000},
        after={"wage": 11000},
    )


def test_record_writes_entry_with_digests() -> None:
    entry = _entry()
    assert entry.pk is not None
    assert entry.before_digest and entry.after_digest
    assert entry.before_digest != entry.after_digest


def test_digest_of_none_is_empty() -> None:
    assert services.digest_state(None) == ""


def test_model_save_blocks_update() -> None:
    entry = _entry()
    entry.result = "DENIED"
    with pytest.raises(AuditImmutableError):
        entry.save()


def test_model_delete_blocked() -> None:
    entry = _entry()
    with pytest.raises(AuditImmutableError):
        entry.delete()


def test_db_trigger_blocks_queryset_update() -> None:
    entry = _entry()
    with pytest.raises((InternalError, ProgrammingError)), transaction.atomic():
        AuditLogEntry.objects.filter(pk=entry.pk).update(result="TAMPERED")


def test_db_trigger_blocks_queryset_delete() -> None:
    entry = _entry()
    with pytest.raises((InternalError, ProgrammingError)), transaction.atomic():
        AuditLogEntry.objects.filter(pk=entry.pk).delete()
