from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from models import GitMetadata, ProjectMatch


def _normalized(path: str) -> str:
    return os.path.normcase(os.path.normpath(str(Path(path).resolve(strict=False))))


def _contains(root: str, candidate: str) -> bool:
    try:
        return os.path.commonpath([root, candidate]) == root
    except (OSError, ValueError):
        return False


def resolve_project(
    *,
    working_directory: str,
    project_database_path: Path,
    git: GitMetadata,
) -> ProjectMatch:
    candidate = _normalized(working_directory)
    best: tuple[int, str, str] | None = None

    if project_database_path.is_file():
        try:
            with sqlite3.connect(project_database_path, timeout=0.1) as connection:
                rows = connection.execute("SELECT id, name, root_path FROM projects").fetchall()
            for project_id, project_name, root_path in rows:
                normalized_root = _normalized(str(root_path))
                if _contains(normalized_root, candidate):
                    match = (len(normalized_root), str(project_id), str(project_name))
                    if best is None or match[0] > best[0]:
                        best = match
        except (OSError, sqlite3.Error):
            best = None

    if best:
        return ProjectMatch(project_id=best[1], project_name=best[2])

    fallback_path = git.repository_path or working_directory
    fallback_name = Path(fallback_path).name or fallback_path
    return ProjectMatch(project_id=None, project_name=fallback_name)
