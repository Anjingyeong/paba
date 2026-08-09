"""Writing audit entries and computing state digests.

``record`` is the single entry point for appending to the audit log. Before/after
states are passed as plain dicts; they are redacted and hashed to a SHA-256 digest
so the log proves a change occurred without persisting the sensitive values.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from .models import AuditLogEntry
from .redaction import redact


def digest_state(state: dict[str, Any] | None) -> str:
    """Stable SHA-256 of a redacted, canonicalized state dict (or "" for None)."""
    if state is None:
        return ""
    canonical = json.dumps(state, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(redact(canonical).encode("utf-8")).hexdigest()


def record(
    *,
    actor_type: str,
    actor_id: str,
    action: str,
    subject_type: str,
    subject_id: str,
    result: str,
    request_id: str = "",
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
) -> AuditLogEntry:
    return AuditLogEntry.objects.create(
        actor_type=actor_type,
        actor_id=actor_id,
        action=action,
        subject_type=subject_type,
        subject_id=subject_id,
        result=result,
        request_id=request_id,
        before_digest=digest_state(before),
        after_digest=digest_state(after),
    )
