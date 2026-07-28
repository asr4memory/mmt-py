from django.contrib.auth import get_user_model
from django.test import TestCase

from mmt.projects.use_cases import create_project
from mmt.uploaded_files.models import UploadedFile

User = get_user_model()


class ChecksumTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.bob = User.objects.create_user(
            username='bob', password='password', email='bob@example.com'
        )

        cls.project = create_project(title='Test project', user=cls.bob)

        cls.uploaded_file = UploadedFile.objects.create(
            filename='test_file.mp4',
            original_filename='test_file.mp4',
            media_type='video/mp4',
            project=cls.project,
        )

    def test_is_corrupt_none_when_checksum_missing(self):
        self.assertIsNone(self.uploaded_file.is_corrupt)

    def test_is_corrupt_true_when_checksums_differ(self):
        self.uploaded_file.checksum_client = 'aaa'
        self.uploaded_file.checksum_server = 'bbb'
        self.assertTrue(self.uploaded_file.is_corrupt)

    def test_is_corrupt_false_when_checksums_match(self):
        self.uploaded_file.checksum_client = 'aaa'
        self.uploaded_file.checksum_server = 'aaa'
        self.assertFalse(self.uploaded_file.is_corrupt)

    def test_log_if_corrupt_logs_warning_on_mismatch(self):
        self.uploaded_file.checksum_client = 'aaa'
        self.uploaded_file.checksum_server = 'bbb'
        with self.assertLogs('mmt.uploaded_files.models', level='WARNING') as cm:
            self.uploaded_file.log_if_corrupt()
        self.assertTrue(any('Checksum mismatch' in line for line in cm.output))

    def test_log_if_corrupt_silent_when_matching(self):
        self.uploaded_file.checksum_client = 'aaa'
        self.uploaded_file.checksum_server = 'aaa'
        with self.assertNoLogs('mmt.uploaded_files.models', level='WARNING'):
            self.uploaded_file.log_if_corrupt()

    def test_log_if_corrupt_silent_when_checksum_missing(self):
        with self.assertNoLogs('mmt.uploaded_files.models', level='WARNING'):
            self.uploaded_file.log_if_corrupt()

    def test_queryset_corrupt_returns_only_mismatched_with_both_checksums(self):
        self.uploaded_file.checksum_client = 'aaa'
        self.uploaded_file.checksum_server = 'bbb'
        self.uploaded_file.save()
        matching = UploadedFile.objects.create(
            filename='ok.mp4',
            media_type='video/mp4',
            project=self.project,
            checksum_client='ccc',
            checksum_server='ccc',
        )
        unverified = UploadedFile.objects.create(
            filename='pending.mp4',
            media_type='video/mp4',
            project=self.project,
            checksum_client='ddd',
        )

        corrupt = UploadedFile.objects.corrupt()

        self.assertIn(self.uploaded_file, corrupt)
        self.assertNotIn(matching, corrupt)
        self.assertNotIn(unverified, corrupt)

    def test_queryset_checksum_ok_returns_only_matching_with_both_checksums(self):
        self.uploaded_file.checksum_client = 'aaa'
        self.uploaded_file.checksum_server = 'bbb'
        self.uploaded_file.save()
        matching = UploadedFile.objects.create(
            filename='ok.mp4',
            media_type='video/mp4',
            project=self.project,
            checksum_client='ccc',
            checksum_server='ccc',
        )
        unverified = UploadedFile.objects.create(
            filename='pending.mp4',
            media_type='video/mp4',
            project=self.project,
            checksum_client='ddd',
        )

        ok = UploadedFile.objects.checksum_ok()

        self.assertIn(matching, ok)
        self.assertNotIn(self.uploaded_file, ok)
        self.assertNotIn(unverified, ok)

    def test_queryset_unverified_returns_files_missing_a_checksum(self):
        self.uploaded_file.checksum_client = 'aaa'
        self.uploaded_file.checksum_server = 'bbb'
        self.uploaded_file.save()
        matching = UploadedFile.objects.create(
            filename='ok.mp4',
            media_type='video/mp4',
            project=self.project,
            checksum_client='ccc',
            checksum_server='ccc',
        )
        unverified = UploadedFile.objects.create(
            filename='pending.mp4',
            media_type='video/mp4',
            project=self.project,
            checksum_client='ddd',
        )

        result = UploadedFile.objects.unverified()

        self.assertIn(unverified, result)
        self.assertNotIn(self.uploaded_file, result)
        self.assertNotIn(matching, result)
