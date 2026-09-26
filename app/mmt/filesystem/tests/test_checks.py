import os

import pytest

from mmt.filesystem.checks import IssueCode, check_directory, check_file

requires_non_root = pytest.mark.skipif(
    os.geteuid() == 0, reason='running as root bypasses permission checks'
)


def codes(issues):
    return [issue.code for issue in issues]


def test_check_directory_ok(tmp_path):
    assert check_directory(tmp_path) == []


def test_check_directory_missing(tmp_path):
    path = tmp_path / 'missing'

    issues = check_directory(path)

    assert codes(issues) == [IssueCode.MISSING]
    assert issues[0].path == path


def test_check_directory_not_a_directory(tmp_path):
    path = tmp_path / 'file'
    path.write_bytes(b'not a dir')

    assert codes(check_directory(path)) == [IssueCode.NOT_A_DIRECTORY]


@requires_non_root
def test_check_directory_reports_each_missing_permission(tmp_path):
    path = tmp_path / 'locked'
    path.mkdir(mode=0o000)
    try:
        issues = check_directory(path)
    finally:
        path.chmod(0o700)

    assert codes(issues) == [
        IssueCode.NOT_READABLE,
        IssueCode.NOT_WRITABLE,
        IssueCode.NOT_EXECUTABLE,
    ]


def test_check_file_ok(tmp_path):
    path = tmp_path / 'file'
    path.write_bytes(b'hello')

    assert check_file(path, expected_size=5) == []


def test_check_file_missing(tmp_path):
    assert codes(check_file(tmp_path / 'missing')) == [IssueCode.MISSING]


def test_check_file_not_a_regular_file(tmp_path):
    assert codes(check_file(tmp_path)) == [IssueCode.NOT_A_REGULAR_FILE]


def test_check_file_size_mismatch(tmp_path):
    path = tmp_path / 'file'
    path.write_bytes(b'hello')

    assert codes(check_file(path, expected_size=999)) == [IssueCode.SIZE_MISMATCH]


@requires_non_root
def test_check_file_not_readable(tmp_path):
    path = tmp_path / 'file'
    path.write_bytes(b'hello')
    path.chmod(0o000)

    assert codes(check_file(path)) == [IssueCode.NOT_READABLE]
