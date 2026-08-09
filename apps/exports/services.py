"""Generate a payroll export and record its manifest.

Produces the ZIP bytes (per-employee statements + manager summary + manifest.json)
from the latest snapshot payload and stores an :class:`ExportManifest` with a
5-minute expiry. Downloads are served from private storage (Todo 16); this layer
owns the authoritative metadata and the audit trail.
"""

from __future__ import annotations

from apps.auditlog import services as audit

from .models import ExportManifest
from .package import build_export_zip, statements_from_snapshot


def create_export(*, snapshot, requester=None) -> tuple[ExportManifest, bytes]:
    statements = statements_from_snapshot(snapshot)
    month_label = f"{snapshot.period.month:%Y-%m}"
    zip_bytes, manifest_dict = build_export_zip(
        month_label=month_label,
        statements=statements,
        snapshot_version=snapshot.version,
        checksum=snapshot.checksum,
    )
    manifest = ExportManifest.objects.create(
        snapshot=snapshot,
        version=snapshot.version,
        checksum=snapshot.checksum,
        requested_by=requester,
        manifest=manifest_dict,
    )
    audit.record(
        actor_type="MANAGER",
        actor_id=str(getattr(requester, "pk", "")),
        action="EXPORT",
        subject_type="PayrollPeriod",
        subject_id=month_label,
        result="SUCCESS",
        after={"version": snapshot.version, "checksum": snapshot.checksum},
    )
    return manifest, zip_bytes
