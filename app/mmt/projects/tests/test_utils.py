from datetime import UTC, datetime

from django.test import TestCase

from mmt.core.tests.test_media_types import PNG_BYTES
from mmt.projects.utils import FileInfo, get_dir_contents, get_filename_suffix


def test_file_info_detects_type_from_contents(tmp_path):
    path = tmp_path / 'still.mp4'
    path.write_bytes(PNG_BYTES)

    file_info = FileInfo(path)

    assert file_info.type == 'image/png'
    assert not file_info.is_video


def test_get_dir_contents_sorted_by_name(tmp_path):
    for name in ['C.txt', 'a.txt', 'B.txt']:
        (tmp_path / name).write_text('')

    contents = get_dir_contents(tmp_path)

    assert [path.name for path in contents] == ['a.txt', 'B.txt', 'C.txt']


class ProjectsUtilTests(TestCase):
    def test_(self):
        date = datetime(
            year=2000,
            month=10,
            day=10,
            hour=8,
            minute=30,
            second=0,
            tzinfo=UTC,
        )
        actual = get_filename_suffix(date)
        expected = '20001010083000'
        self.assertEqual(actual, expected)
