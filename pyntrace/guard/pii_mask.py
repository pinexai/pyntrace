"""Regex-based PII masking for scan storage and log sanitization."""
from __future__ import annotations

import os
import re

# ── Compiled patterns (label, regex, replacement) ────────────────────────────
_PATTERNS: list[tuple[str, re.Pattern, str]] = [
    # Secrets / API keys
    ("openai_key",   re.compile(r"\bsk-[a-zA-Z0-9]{32,}"), "[API_KEY]"),
    ("anthropic_key",re.compile(r"\bsk-ant-[a-zA-Z0-9\-]{20,}"), "[API_KEY]"),
    ("aws_key",      re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "[AWS_KEY]"),
    ("aws_secret",   re.compile(r"(?i)aws.{0,20}secret.{0,20}['\"]([a-zA-Z0-9/+]{40})['\"]"), "[AWS_SECRET]"),
    ("gh_token",     re.compile(r"\b(ghp|gho|ghu|ghs|ghr)_[a-zA-Z0-9]{36,}\b"), "[GH_TOKEN]"),
    ("bearer_token", re.compile(r"(?i)(bearer\s+)[a-zA-Z0-9\-._~+/]+=*"), r"\1[TOKEN]"),
    ("generic_key",  re.compile(r"(?i)(api[_\-]?key|secret[_\-]?key|private[_\-]?key)\s*[=:]\s*\S+"), r"\1=[REDACTED]"),

    # Personal identifiers
    ("email",        re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"), "[EMAIL]"),
    ("ssn",          re.compile(r"\b(?!000|666|9\d{2})\d{3}-(?!00)\d{2}-(?!0000)\d{4}\b"), "[SSN]"),
    ("phone_us",     re.compile(r"\b(\+1[-.\s]?)?\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}\b"), "[PHONE]"),
    ("phone_intl",   re.compile(r"\+(?:[1-9]\d{1,2}[-.\s]?)(?:\d[-.\s]?){6,14}\d"), "[PHONE]"),
    ("dob",          re.compile(r"\b(?:0?[1-9]|1[0-2])[-/](?:0?[1-9]|[12]\d|3[01])[-/](?:19|20)\d{2}\b"), "[DOB]"),

    # Financial
    ("credit_card",  re.compile(
        r"\b(?:4[0-9]{12}(?:[0-9]{3})?|"  # Visa
        r"5[1-5][0-9]{14}|"               # Mastercard
        r"3[47][0-9]{13}|"                # Amex
        r"3(?:0[0-5]|[68][0-9])[0-9]{11}|"  # Diners
        r"6(?:011|5[0-9]{2})[0-9]{12}|"  # Discover
        r"(?:2131|1800|35\d{3})\d{11})\b"  # JCB
    ), "[CC]"),
    ("iban",         re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{1,30}\b"), "[IBAN]"),

    # Network / infrastructure
    ("ipv4",         re.compile(r"\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b"), "[IPv4]"),
    ("ipv6",         re.compile(r"\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b"), "[IPv6]"),
    ("mac_addr",     re.compile(r"\b(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}\b"), "[MAC]"),

    # Passwords in context
    ("password",     re.compile(r"(?i)(password|passwd|pwd)\s*[=:]\s*\S+"), r"\1=[REDACTED]"),
]

# Flat list for callers that don't need labels
_PATTERN_LIST: list[tuple[re.Pattern, str]] = [(p, r) for _, p, r in _PATTERNS]


def mask_pii(text: str) -> str:
    """Return *text* with PII replaced by placeholders.

    No-op unless ``PYNTRACE_MASK_PII=1`` environment variable is set.
    """
    if not os.getenv("PYNTRACE_MASK_PII"):
        return text
    for pattern, replacement in _PATTERN_LIST:
        text = pattern.sub(replacement, text)
    return text


def mask_pii_always(text: str) -> str:
    """Like :func:`mask_pii` but always active regardless of env var."""
    for pattern, replacement in _PATTERN_LIST:
        text = pattern.sub(replacement, text)
    return text


def detect_pii(text: str) -> list[dict]:
    """Return a list of detected PII matches with label and position.

    Each entry: ``{"label": str, "start": int, "end": int, "value": str}``.
    Useful for reporting which PII types were found without redacting.
    """
    findings: list[dict] = []
    for label, pattern, _ in _PATTERNS:
        for m in pattern.finditer(text):
            findings.append({
                "label": label,
                "start": m.start(),
                "end": m.end(),
                "value": m.group(),
            })
    # Sort by position
    findings.sort(key=lambda x: x["start"])
    return findings


def sanitize_for_log(text: str, max_len: int = 200) -> str:
    """Truncate and redact PII/secrets for safe log output.

    Always active — does not require ``PYNTRACE_MASK_PII``.
    """
    if len(text) > max_len:
        text = text[:max_len] + "...[truncated]"
    for pattern, replacement in _PATTERN_LIST:
        text = pattern.sub(replacement, text)
    return text
