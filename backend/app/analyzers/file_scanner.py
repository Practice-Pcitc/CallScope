from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path


class ScanLimitError(Exception):
    """目录规模超过配置限制。"""


@dataclass(frozen=True, slots=True)
class ScanFileError:
    path: str
    code: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return {"path": self.path, "code": self.code, "message": self.message}


@dataclass(slots=True)
class ScanDiscoveryResult:
    files: list[str] = field(default_factory=list)
    skipped_files: int = 0
    failed_files: int = 0
    errors: list[ScanFileError] = field(default_factory=list)
    visited_entries: int = 0


ProgressCallback = Callable[[str, int], None]


class FileScanner:
    """只发现安全范围内的 Python 文件，不读取或执行项目源码。"""

    def __init__(
        self,
        *,
        ignored_directories: set[str],
        max_files: int,
        max_file_size_bytes: int,
        max_directory_entries: int,
        error_limit: int,
        supported_extensions: set[str] | None = None,
    ) -> None:
        self.ignored_directories = {name.casefold() for name in ignored_directories}
        self.max_files = max_files
        self.max_file_size_bytes = max_file_size_bytes
        self.max_directory_entries = max_directory_entries
        self.error_limit = error_limit
        self.supported_extensions = {
            extension.casefold() if extension.startswith(".") else f".{extension.casefold()}"
            for extension in (supported_extensions or {".py", ".java"})
        }

    def discover(
        self,
        root: Path,
        *,
        on_progress: ProgressCallback | None = None,
    ) -> ScanDiscoveryResult:
        root = root.resolve(strict=True)
        result = ScanDiscoveryResult()
        pending_directories = [root]

        while pending_directories:
            directory = pending_directories.pop()
            try:
                entries = os.scandir(directory)
            except OSError as exc:
                result.failed_files += 1
                self._record_error(
                    result,
                    path=self._relative_path(root, directory),
                    code="DIRECTORY_UNREADABLE",
                    message=f"文件处理失败（{type(exc).__name__}），请检查文件格式和读取权限",
                )
                continue

            for entry in entries:
                result.visited_entries += 1
                if result.visited_entries > self.max_directory_entries:
                    raise ScanLimitError(f"目录项数量超过限制 {self.max_directory_entries}")

                entry_path = Path(entry.path)
                relative_path = self._relative_path(root, entry_path)
                if on_progress and result.visited_entries % 50 == 0:
                    on_progress(relative_path, result.visited_entries)

                try:
                    if entry.is_symlink():
                        if entry_path.suffix.casefold() in self.supported_extensions:
                            result.skipped_files += 1
                            self._record_error(
                                result,
                                path=relative_path,
                                code="SYMLINK_SKIPPED",
                                message="为防止越出项目根目录，已跳过符号链接",
                            )
                        continue

                    if entry.is_dir(follow_symlinks=False):
                        if entry.name.casefold() in self.ignored_directories:
                            continue
                        pending_directories.append(entry_path)
                        continue

                    if not entry.is_file(follow_symlinks=False):
                        continue
                    if entry_path.suffix.casefold() not in self.supported_extensions:
                        continue

                    resolved_file = entry_path.resolve(strict=True)
                    if not resolved_file.is_relative_to(root):
                        result.skipped_files += 1
                        self._record_error(
                            result,
                            path=relative_path,
                            code="PATH_OUTSIDE_ROOT",
                            message="文件规范化后位于项目根目录之外",
                        )
                        continue

                    size = entry.stat(follow_symlinks=False).st_size
                    if size > self.max_file_size_bytes:
                        result.skipped_files += 1
                        self._record_error(
                            result,
                            path=relative_path,
                            code="FILE_TOO_LARGE",
                            message=f"文件大小超过限制 {self.max_file_size_bytes} 字节",
                        )
                        continue

                    if len(result.files) >= self.max_files:
                        raise ScanLimitError(f"Python 文件数量超过限制 {self.max_files}")

                    result.files.append(relative_path)
                except ScanLimitError:
                    raise
                except OSError as exc:
                    result.failed_files += 1
                    self._record_error(
                        result,
                        path=relative_path,
                        code="FILE_UNREADABLE",
                        message=f"文件处理失败（{type(exc).__name__}），请检查文件格式和读取权限",
                    )

        result.files.sort()
        return result

    def _record_error(
        self,
        result: ScanDiscoveryResult,
        *,
        path: str,
        code: str,
        message: str,
    ) -> None:
        if len(result.errors) < self.error_limit:
            result.errors.append(ScanFileError(path=path, code=code, message=message))

    @staticmethod
    def _relative_path(root: Path, path: Path) -> str:
        try:
            relative = path.relative_to(root)
        except ValueError:
            return path.name
        value = relative.as_posix()
        return value if value != "." else ""
