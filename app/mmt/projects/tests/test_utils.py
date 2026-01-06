from datetime import datetime, timezone

from django.test import TestCase

from mmt.projects.utils import get_filename_suffix


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
