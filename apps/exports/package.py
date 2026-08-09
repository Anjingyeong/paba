"""Assemble per-employee statements + manager summary into a ZIP with a manifest.

Filenames use the opaque employee id only — never a name. The manifest (also
returned as a dict for the DB record) lists the snapshot, version, checksum and
each member file.
"""

from __future__ import annotations

import io
import json
import zipfile
from datetime import date

from openpyxl import Workbook

from .statement import LineItem, StatementData, build_statement
from .summary import build_summary


def _wb_bytes(wb: Workbook) -> bytes:
    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def statement_filename(data: StatementData) -> str:
    return f"pay-statement-{data.employee_id}-{data.attribution_month:%Y-%m}.xlsx"


def statements_from_snapshot(snapshot) -> list[StatementData]:
    """Map a close snapshot's payload into statement data (no PII)."""
    payload = snapshot.payload
    month = snapshot.period.month
    pay_date = date.fromisoformat(payload["pay_date"]) if payload.get("pay_date") else month
    statements: list[StatementData] = []
    for line in payload.get("lines", []):
        statements.append(
            StatementData(
                attribution_month=month,
                employee_id=line["employee_id"],
                department=line.get("department", ""),
                title=line.get("title", ""),
                pay_date=pay_date,
                calc_period=payload.get("calc_period", f"{month:%Y-%m}"),
                earnings=[LineItem(e["label"], int(e["amount"])) for e in line.get("earnings", [])],
                deductions=[
                    LineItem(d["label"], int(d["amount"])) for d in line.get("deductions", [])
                ],
                detail_lines=list(line.get("detail_lines", [])),
                version=snapshot.version,
                checksum=snapshot.checksum,
            )
        )
    return statements


def build_export_zip(
    *, month_label: str, statements: list[StatementData], snapshot_version: int, checksum: str
) -> tuple[bytes, dict]:
    files: list[dict] = []
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for data in statements:
            name = statement_filename(data)
            zf.writestr(name, _wb_bytes(build_statement(data)))
            files.append({"file": name, "employee_id": data.employee_id, "net": data.net_pay})

        summary_name = f"summary-{month_label}.xlsx"
        zf.writestr(summary_name, _wb_bytes(build_summary(month_label, statements)))

        manifest = {
            "month": month_label,
            "snapshot_version": snapshot_version,
            "checksum": checksum,
            "summary_file": summary_name,
            "statements": files,
        }
        zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))

    return buffer.getvalue(), manifest
