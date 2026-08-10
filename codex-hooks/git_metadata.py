from __future__ import annotations

import os
import subprocess
from pathlib import Path

from models import GitMetadata


def _run_git(cwd: Path, *arguments: str) -> str | None:
    startupinfo = None
    creationflags = 0
    if os.name == "nt":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        creationflags = subprocess.CREATE_NO_WINDOW
    try:
        result = subprocess.run(
            ["git", *arguments],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=0.4,
            check=False,
            startupinfo=startupinfo,
            creationflags=creationflags,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    value = result.stdout.strip()
    return value or None


def read_git_metadata(working_directory: str) -> GitMetadata:
    cwd = Path(working_directory)
    raw = _run_git(
        cwd,
        "rev-parse",
        "--show-toplevel",
        "--abbrev-ref",
        "HEAD",
        "HEAD",
    )
    if not raw:
        return GitMetadata()
    values = raw.splitlines()
    if len(values) < 3:
        return GitMetadata(repository_path=values[0] if values else None)
    return GitMetadata(
        repository_path=values[0],
        branch=values[1] if values[1] != "HEAD" else None,
        commit=values[2],
    )
