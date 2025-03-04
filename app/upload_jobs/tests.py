from django.contrib.auth import get_user_model
from django.test import TestCase

from upload_jobs.models import UploadJob


User = get_user_model()


class UploadJobTestCase(TestCase):
    def setUp(self):
        user = User.objects.create_user(username="alice", password="password")
        UploadJob.objects.create(title="Test upload job", user=user)

    def test_upload_jobs_can(self):
        """Directory names are created correctly"""
        job = UploadJob.objects.get(title="Test upload job")

        actual = job.directory_name()
        expected = "Test upload job"

        len_expected = len(expected)
        len_date = 18

        self.assertEqual(actual[:len_expected], expected)
        self.assertEqual(len(actual), len_expected + 1 + len_date)
