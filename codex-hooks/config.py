from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _as_bool(value: str | None, *, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


@dataclass(frozen=True, slots=True)
class HookConfig:
    enabled: bool
    redaction_enabled: bool
    database_path: Path
    project_database_path: Path
    log_path: Path
    sqlite_timeout_seconds: float = 0.2

    @classmethod
    def load(cls) -> HookConfig:
        repository_root = Path(__file__).resolve().parent.parent
        return cls(
            enabled=_as_bool(os.getenv("PROMPT_HOOK_ENABLED"), default=True),
            redaction_enabled=_as_bool(os.getenv("PROMPT_REDACTION_ENABLED"), default=False),
            database_path=Path(
                os.getenv(
                    "PROMPT_HISTORY_DB",
                    str(repository_root / "backend" / "prompt_history.db"),
                )
            ).expanduser(),
            project_database_path=Path(
                os.getenv(
                    "CALLSCOPE_PROJECT_DB",
                    str(repository_root / "backend" / "callscope.db"),
                )
            ).expanduser(),
            log_path=Path(
                os.getenv(
                    "PROMPT_HOOK_LOG",
                    str(repository_root / "logs" / "prompt-hook.log"),
                )
            ).expanduser(),
        )
