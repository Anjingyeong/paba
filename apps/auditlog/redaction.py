"""Structural redaction of sensitive values from application logs.

The filter rewrites each log record's rendered message so that PINs, TOTP codes,
session/token/secret values and KRW pay amounts never reach a log sink. Employee
*names* should never be logged in the first place — code refers to subjects by
opaque id — but as defence in depth the redactor also masks values passed under
sensitive keys (``name``, ``pin``, ``token`` …).
"""

from __future__ import annotations

import logging
import re

# key=value / key: value where the key is sensitive → mask the value, keep the key.
_KEY_VALUE = re.compile(
    r"(?i)\b(pin|totp|otp|token|secret|password|passwd|session(?:id)?|name|display_name)"
    r"(\s*[:=]\s*)"
    r"([^\s,;]+)"
)
# Standalone 6-digit sequences (PINs / TOTP codes).
_SIX_DIGITS = re.compile(r"(?<!\d)\d{6}(?!\d)")
# KRW amounts like 1,234,000원 or 1234000원.
_KRW = re.compile(r"[0-9][0-9,]*\s*원")

_MASK = "[REDACTED]"


def redact(text: str) -> str:
    text = _KEY_VALUE.sub(lambda m: f"{m.group(1)}{m.group(2)}{_MASK}", text)
    text = _SIX_DIGITS.sub(_MASK, text)
    text = _KRW.sub(f"{_MASK}원", text)
    return text


class SensitiveDataFilter(logging.Filter):
    """Logging filter that redacts sensitive values from every record."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            message = record.getMessage()
        except Exception:  # pragma: no cover - never let logging raise
            return True
        record.msg = redact(message)
        record.args = ()
        return True
