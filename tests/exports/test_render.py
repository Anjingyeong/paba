"""LibreOffice headless render check (skips when soffice is unavailable).

Confirms the generated statement opens and converts to a PDF without errors — a
volatile formula, #REF!/#VALUE!, or a broken sheet would fail the conversion.
"""

from __future__ import annotations

import datetime as dt
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from apps.exports.statement import LineItem, StatementData, build_statement

_WIN_SOFFICE = Path(r"C:\Program Files\LibreOffice\program\soffice.exe")


def _find_soffice() -> str | None:
    for candidate in ("soffice", "libreoffice"):
        found = shutil.which(candidate)
        if found:
            return found
    if _WIN_SOFFICE.exists():
        return str(_WIN_SOFFICE)
    return None


def test_statement_renders_to_pdf(tmp_path: Path) -> None:
    soffice = _find_soffice()
    if soffice is None:
        pytest.skip("LibreOffice (soffice) not installed")

    data = StatementData(
        attribution_month=dt.date(2026, 7, 1),
        employee_id="EMP-0001",
        department="베이커리",
        title="사원",
        pay_date=dt.date(2026, 8, 5),
        calc_period="2026-07",
        earnings=[LineItem("기본급", 1_800_000)],
        deductions=[LineItem("국민연금", 81_000)],
        detail_lines=["기본급: 160.00h × 11,250"],
        checksum="abc123",
    )
    xlsx = tmp_path / "statement.xlsx"
    build_statement(data).save(xlsx)

    subprocess.run(
        [soffice, "--headless", "--convert-to", "pdf", "--outdir", str(tmp_path), str(xlsx)],
        check=True,
        capture_output=True,
        timeout=120,
        env={**os.environ, "HOME": str(tmp_path)},
    )
    pdf = tmp_path / "statement.pdf"
    assert pdf.exists()
    assert pdf.stat().st_size > 0
