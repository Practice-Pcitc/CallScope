from __future__ import annotations

import re

_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._~+/=-]+"),
    re.compile(
        r"(?i)((?:api[_-]?key|password|secret|token)\s*[:=]\s*)"
        r"([^\s,;\"']+)"
    ),
    re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b"),
)


def redact_prompt(prompt: str) -> str:
    redacted = prompt
    for pattern in _PATTERNS:
        if pattern.groups:
            redacted = pattern.sub(lambda match: f"{match.group(1)}[REDACTED]", redacted)
        else:
            redacted = pattern.sub("[REDACTED]", redacted)
    return redacted
