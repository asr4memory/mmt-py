import pytest

from mmt.filesystem.checks import IssueCode
from mmt.projects.use_cases import create_project
from mmt.uploaded_files.models import FileRecordIssueCode, UploadedFile


@pytest.fixture
def make_file(django_user_model):
    user = django_user_model.objects.create_user(
        username='bob_check', password='password', email='bob_check@example.com'
    )
    project = create_project(title='Test project', user=user)
    paths = []

    def make(content: bytes, *, has_file: bool = True) -> UploadedFile:
        uploaded_file = UploadedFile.objects.create(
            filename='test_file.mp4',
            original_filename='test_file.mp4',
            media_type='video/mp4',
            project=project,
            size=len(content),
            has_file=has_file,
        )
        uploaded_file.file_path.write_bytes(content)
        paths.append(uploaded_file.file_path)
        return uploaded_file

    yield make

    for path in paths:
        path.unlink(missing_ok=True)


@pytest.mark.django_db
def test_ok_when_file_matches(make_file):
    """A present, correctly sized file produces no issues."""
    assert make_file(b'hello world').check_file() == []


@pytest.mark.django_db
def test_size_mismatch(make_file):
    """Reports a size mismatch when disk size differs from the database."""
    uploaded_file = make_file(b'hello world')
    uploaded_file.size = 999

    issues = uploaded_file.check_file()

    assert [issue.code for issue in issues] == [IssueCode.SIZE_MISMATCH]


@pytest.mark.django_db
def test_has_file_mismatch(make_file):
    """Reports when a file exists on disk but has_file is False."""
    uploaded_file = make_file(b'hello world', has_file=False)

    issues = uploaded_file.check_file()

    assert [issue.code for issue in issues] == [FileRecordIssueCode.HAS_FILE_MISMATCH]
