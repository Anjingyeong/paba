"""Purge personal data past its retention window.

Defaults to a dry run (reports candidates, writes nothing). Pass ``--confirm`` to
actually destroy the data and record the completion audit entries.
"""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand

from apps.auditlog.retention import purge_expired


class Command(BaseCommand):
    help = "Report (default) or perform destruction of personal data past retention."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--confirm",
            action="store_true",
            help="Actually purge. Without this flag the command only reports candidates.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        report = purge_expired(dry_run=not options["confirm"])
        if report.dry_run:
            self.stdout.write(
                f"[dry-run] {len(report.candidates)} candidate(s): "
                f"{', '.join(report.candidates) or '(none)'}. No data written."
            )
        else:
            self.stdout.write(f"Purged {report.purged} subject(s) past retention.")
