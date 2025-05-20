from datetime import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import UploadJob


User = get_user_model()


class UploadJobTestCase(TestCase):
    def setUp(self):
        User.objects.create_user(username="alice", password="password")

    def test_normal_directory_name(self):
        """Directory names are created from title and creation date"""
        user = User.objects.get(username="alice")
        date_now = datetime.now()
        job = UploadJob.objects.create(title="Test upload job", user=user)

        actual = job.directory_name()
        expected = "Test upload job" + date_now.strftime(".%Y-%m-%dT%H%M%SZ")

        self.assertEqual(actual, expected)

    def test_unsafe_directory_name(self):
        """Directory names are made safe"""
        user = User.objects.get(username="alice")
        date_now = datetime.now()
        job = UploadJob.objects.create(title="ä/#*hello", user=user)

        actual = job.directory_name()
        expected = "ähello" + date_now.strftime(".%Y-%m-%dT%H%M%SZ")

        self.assertEqual(actual, expected)
