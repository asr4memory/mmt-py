from datetime import timedelta
from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from mmt.projects.use_cases import create_project
from mmt.uploaded_files.models import FileChunk, UploadedFile

User = get_user_model()


class RemovePartialUploadsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.bob = User.objects.create_user(
            username='bob', password='password', email='bob@example.com'
        )
        cls.project = create_project(title='Test project', user=cls.bob)

    def _make_partial(self, filename, *, age_hours=48, assembling=False):
        uploaded_file = UploadedFile.objects.create(
            filename=filename,
            original_filename=filename,
            media_type='video/mp4',
            project=self.project,
            assembling=assembling,
        )
        chunk = FileChunk.objects.create(uploaded_file=uploaded_file, index=0)
        chunk.chunk_path.parent.mkdir(exist_ok=True)
        chunk.chunk_path.write_bytes(b'part0')
        self.addCleanup(chunk.chunk_path.unlink, missing_ok=True)
        # updated_at uses auto_now, so override it directly to simulate age.
        UploadedFile.objects.filter(pk=uploaded_file.pk).update(
            updated_at=timezone.now() - timedelta(hours=age_hours)
        )
        return uploaded_file, chunk

    def test_removes_stale_partial_upload(self):
        """Deletes the record and its chunk files from disk."""
        uploaded_file, chunk = self._make_partial('stale.mp4')

        call_command('remove_partial_uploads', stdout=StringIO())

        self.assertFalse(UploadedFile.objects.filter(pk=uploaded_file.pk).exists())
        self.assertFalse(chunk.chunk_path.exists())

    def test_keeps_recent_partial_upload(self):
        """Uploads younger than the min age are left untouched."""
        uploaded_file, chunk = self._make_partial('recent.mp4', age_hours=1)

        call_command('remove_partial_uploads', stdout=StringIO())

        self.assertTrue(UploadedFile.objects.filter(pk=uploaded_file.pk).exists())
        self.assertTrue(chunk.chunk_path.exists())

    def test_keeps_complete_file(self):
        """Files with has_file set are not partial and are kept."""
        uploaded_file = UploadedFile.objects.create(
            filename='complete.mp4',
            original_filename='complete.mp4',
            media_type='video/mp4',
            project=self.project,
            has_file=True,
        )
        UploadedFile.objects.filter(pk=uploaded_file.pk).update(
            updated_at=timezone.now() - timedelta(hours=48)
        )

        call_command('remove_partial_uploads', stdout=StringIO())

        self.assertTrue(UploadedFile.objects.filter(pk=uploaded_file.pk).exists())

    def test_keeps_assembling_file(self):
        """Files currently being assembled are kept."""
        uploaded_file, chunk = self._make_partial('assembling.mp4', assembling=True)

        call_command('remove_partial_uploads', stdout=StringIO())

        self.assertTrue(UploadedFile.objects.filter(pk=uploaded_file.pk).exists())
        self.assertTrue(chunk.chunk_path.exists())

    def test_dry_run_deletes_nothing(self):
        """--dry-run reports but leaves records and files in place."""
        uploaded_file, chunk = self._make_partial('stale.mp4')

        call_command('remove_partial_uploads', '--dry-run', stdout=StringIO())

        self.assertTrue(UploadedFile.objects.filter(pk=uploaded_file.pk).exists())
        self.assertTrue(chunk.chunk_path.exists())

    def test_min_age_override(self):
        """A lower --min-age makes more uploads eligible for removal."""
        uploaded_file, chunk = self._make_partial('recent.mp4', age_hours=2)

        call_command('remove_partial_uploads', '--min-age', '1', stdout=StringIO())

        self.assertFalse(UploadedFile.objects.filter(pk=uploaded_file.pk).exists())
        self.assertFalse(chunk.chunk_path.exists())


@pytest.fixture
def project(db):
    user = User.objects.create_user(
        username='carol', password='password', email='carol@example.com'
    )
    return create_project(title='Backfill project', user=user)


@pytest.fixture
def file_on_disk(project):
    """An uploaded file present on disk but not marked as present."""
    uploaded_file = UploadedFile.objects.create(
        project=project, filename='on_disk.mp4', has_file=False
    )
    uploaded_file.file_path.parent.mkdir(parents=True, exist_ok=True)
    uploaded_file.file_path.write_bytes(b'bytes')
    yield uploaded_file
    uploaded_file.file_path.unlink(missing_ok=True)


def test_backfill_has_file_marks_a_file_on_disk_as_present(file_on_disk):
    call_command('backfill_has_file', stdout=StringIO())

    file_on_disk.refresh_from_db()
    assert file_on_disk.has_file


def test_backfill_has_file_marks_a_missing_file_as_absent(project):
    uploaded_file = UploadedFile.objects.create(
        project=project, filename='missing.mp4', has_file=True
    )

    call_command('backfill_has_file', stdout=StringIO())

    uploaded_file.refresh_from_db()
    assert not uploaded_file.has_file


def test_backfill_has_file_dry_run_reports_the_count_and_changes_nothing(
    file_on_disk, project
):
    UploadedFile.objects.create(project=project, filename='absent.mp4', has_file=False)
    stdout = StringIO()

    call_command('backfill_has_file', '--dry-run', stdout=stdout)

    file_on_disk.refresh_from_db()
    assert not file_on_disk.has_file
    assert '1 file(s) would be updated.' in stdout.getvalue()
