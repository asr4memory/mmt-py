from unittest import mock

import pytest
from django.contrib.auth import get_user_model

from mmt.projects.use_cases import create_project
from mmt.uploaded_files.models import UploadedFile
from mmt.uploaded_files.models import Waveform
from mmt.uploaded_files.tasks import (
    calculate_duration,
    calculate_server_checksum,
    task_extract_waveform_data,
)

User = get_user_model()


@pytest.fixture
def uploaded_file(db):
    user = User.objects.create_user(
        username='bob', password='password', email='bob@example.com'
    )
    _, project = create_project(title='Test project', user=user)
    return UploadedFile.objects.create(
        filename='test_file.mp4', media_type='video/mp4', project=project
    )


@pytest.mark.django_db
def test_calculate_duration_updates_duration(uploaded_file):
    with mock.patch(
        'mmt.uploaded_files.tasks.extract_duration', return_value=42.7
    ):
        calculate_duration(uploaded_file.pk)

    uploaded_file.refresh_from_db()
    assert uploaded_file.duration == 42


@pytest.mark.django_db
def test_calculate_duration_skips_update_when_none(uploaded_file):
    with mock.patch(
        'mmt.uploaded_files.tasks.extract_duration', return_value=None
    ):
        calculate_duration(uploaded_file.pk)

    uploaded_file.refresh_from_db()
    assert uploaded_file.duration == 0  # unchanged default


@pytest.mark.django_db
def test_task_extract_waveform_data_creates_waveform(uploaded_file):
    fake_data = [1, 2, 3]
    with mock.patch(
        'mmt.uploaded_files.tasks.extract_waveform_data', return_value=fake_data
    ):
        task_extract_waveform_data(uploaded_file.pk)

    waveform = Waveform.objects.get(uploaded_file=uploaded_file)
    assert waveform.data == fake_data


@pytest.mark.django_db
def test_task_extract_waveform_data_skips_when_none(uploaded_file):
    with mock.patch(
        'mmt.uploaded_files.tasks.extract_waveform_data', return_value=None
    ):
        task_extract_waveform_data(uploaded_file.pk)

    assert not Waveform.objects.filter(uploaded_file=uploaded_file).exists()


@pytest.mark.django_db
def test_task_extract_waveform_data_skips_non_av():
    user = User.objects.create_user(
        username='alice', password='password', email='alice@example.com'
    )
    _, project = create_project(title='Test project', user=user)
    pdf_file = UploadedFile.objects.create(
        filename='document.pdf', media_type='application/pdf', project=project
    )

    task_extract_waveform_data(pdf_file.pk)

    assert not Waveform.objects.filter(uploaded_file=pdf_file).exists()


@pytest.mark.django_db
def test_task_extract_waveform_data_updates_existing_waveform(uploaded_file):
    Waveform.objects.create(
        uploaded_file=uploaded_file, data=[9, 9, 9]
    )
    new_data = [1, 2, 3]
    with mock.patch(
        'mmt.uploaded_files.tasks.extract_waveform_data', return_value=new_data
    ):
        task_extract_waveform_data(uploaded_file.pk)

    assert Waveform.objects.filter(uploaded_file=uploaded_file).count() == 1
    assert Waveform.objects.get(uploaded_file=uploaded_file).data == new_data


@pytest.mark.django_db
def test_calculate_server_checksum(uploaded_file):
    fake_checksum = 'abc123'

    with mock.patch(
        'mmt.uploaded_files.tasks.generate_file_md5', return_value=fake_checksum
    ):
        calculate_server_checksum(uploaded_file.pk)

    uploaded_file.refresh_from_db()
    assert uploaded_file.checksum_server == fake_checksum
