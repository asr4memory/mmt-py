from datetime import datetime, timezone

from django.test import TestCase

from mmt.projects.utils import get_dir_contents, get_filename_suffix


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
            tzinfo=timezone.utc,
        )
        actual = get_filename_suffix(date)
        expected = '20001010083000'
        self.assertEqual(actual, expected)
