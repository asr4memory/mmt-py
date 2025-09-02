from django.test import TestCase
from mmt.core.tasks import add


class TaskTests(TestCase):
    def test_add_direct(self):
        result = add(2, 3)
        self.assertEqual(result, 5)
