"""Checks that a path on disk exists and is usable.

Issue messages are admin-facing plain English and are not translated.
"""

import os
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from stat import S_ISDIR, S_ISREG


class IssueCode(StrEnum):
    MISSING = 'missing'
    STAT_ERROR = 'stat_error'
    NOT_A_DIRECTORY = 'not_a_directory'
    NOT_A_REGULAR_FILE = 'not_a_regular_file'
    NOT_READABLE = 'not_readable'
    NOT_WRITABLE = 'not_writable'
    NOT_EXECUTABLE = 'not_executable'
    SIZE_MISMATCH = 'size_mismatch'


@dataclass(frozen=True)
class Issue:
    """A single problem found at a path."""

    path: Path
    code: str
    message: str


def check_directory(path: Path) -> list[Issue]:
    """Return the problems that prevent using path as a read-write directory."""
    stat = _stat(path)
    if isinstance(stat, Issue):
        return [stat]
    issues = []

    if not S_ISDIR(stat.st_mode):
        return [
            Issue(path, IssueCode.NOT_A_DIRECTORY, f'Path is not a directory: {path}')
        ]

    if not os.access(path, os.R_OK):
        issues.append(
            Issue(path, IssueCode.NOT_READABLE, f'Directory is not readable: {path}')
        )
    if not os.access(path, os.W_OK):
        issues.append(
            Issue(path, IssueCode.NOT_WRITABLE, f'Directory is not writable: {path}')
        )
    if not os.access(path, os.X_OK):
        issues.append(
            Issue(
                path, IssueCode.NOT_EXECUTABLE, f'Directory is not traversable: {path}'
            )
        )
    return issues


def check_file(path: Path, expected_size: int | None = None) -> list[Issue]:
    """Return the problems that prevent reading path as a regular file.

    A size different from expected_size is reported, unless it is None.
    """
    stat = _stat(path)
    if isinstance(stat, Issue):
        return [stat]
    issues = []

    if not S_ISREG(stat.st_mode):
        issues.append(
            Issue(
                path,
                IssueCode.NOT_A_REGULAR_FILE,
                f'Path is not a regular file: {path}',
            )
        )
    if expected_size is not None and stat.st_size != expected_size:
        issues.append(
            Issue(
                path,
                IssueCode.SIZE_MISMATCH,
                f'File size on disk ({stat.st_size} bytes) differs from the '
                f'expected size ({expected_size} bytes): {path}',
            )
        )
    if not os.access(path, os.R_OK):
        issues.append(
            Issue(path, IssueCode.NOT_READABLE, f'File is not readable: {path}')
        )
    return issues


def _stat(path: Path) -> os.stat_result | Issue:
    """Return the stat result of path, or the issue that prevented reading it."""
    try:
        return path.stat()
    except FileNotFoundError:
        return Issue(path, IssueCode.MISSING, f'Path does not exist: {path}')
    except OSError as exc:
        return Issue(path, IssueCode.STAT_ERROR, f'Could not read metadata: {exc}')
