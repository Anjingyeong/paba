"""Sensitive values are structurally redacted from log output."""

from __future__ import annotations

import logging

from apps.auditlog.redaction import SensitiveDataFilter, redact


def test_redacts_six_digit_pin_and_totp() -> None:
    assert "123456" not in redact("employee PIN 123456 entered")
    assert "654321" not in redact("totp code 654321")


def test_redacts_key_value_secrets() -> None:
    out = redact("token=abc123def session=zzz name=홍길동")
    assert "abc123def" not in out
    assert "zzz" not in out
    assert "홍길동" not in out


def test_redacts_krw_amounts() -> None:
    out = redact("net pay 1,234,000원 paid")
    assert "1,234,000" not in out
    assert "원" in out


def test_filter_mutates_log_record() -> None:
    f = SensitiveDataFilter()
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname=__file__, lineno=1,
        msg="PIN %s for token=%s", args=("123456", "supersecret"), exc_info=None,
    )
    assert f.filter(record) is True
    rendered = record.getMessage()
    assert "123456" not in rendered
    assert "supersecret" not in rendered
