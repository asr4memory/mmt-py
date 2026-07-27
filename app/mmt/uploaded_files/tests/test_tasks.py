from unittest import mock

import pytest
from django.contrib.auth import get_user_model

from mmt.projects.use_cases import create_project
from mmt.uploaded_files.models import UploadedFile
from mmt.uploaded_files.models import Waveform
from mmt.uploaded_files.tasks import (
    calculate_duration,
    calculate_server_checksum,
    task_assemble_chunks,
    task_extract_waveform_data,
    task_generate_web_video,
)

User = get_user_model()


@pytest.fixture
def uploaded_file(db):
    user = User.objects.create_user(
        username='bob', password='password', email='bob@example.com'
    )
    project = create_project(title='Test project', user=user)
    return UploadedFile.objects.create(
        filename='test_file.mp4', media_type='video/mp4', project=project
    )


@pytest.fixture
def audio_file(db):
    user = User.objects.create_user(
        username='carol', password='password', email='carol@example.com'
    )
    project = create_project(title='Audio project', user=user)
    return UploadedFile.objects.create(
        filename='test_file.wav', media_type='audio/wav', project=project
    )


@pytest.mark.django_db
def test_task_assemble_chunks_assembles_and_enqueues_followups(uploaded_file):
    with (
        mock.patch.object(UploadedFile, 'assemble_chunks') as mock_assemble,
        mock.patch(
            'mmt.uploaded_files.tasks.detect_media_type', return_value='video/quicktime'
        ),
        mock.patch('mmt.uploaded_files.tasks.calculate_duration') as mock_duration,
        mock.patch(
            'mmt.uploaded_files.tasks.calculate_server_checksum'
        ) as mock_checksum,
        mock.patch(
            'mmt.uploaded_files.tasks.task_generate_web_video'
        ) as mock_web_video,
    ):
        task_assemble_chunks(uploaded_file.pk)

    mock_assemble.assert_called_once()
    mock_duration.delay.assert_called_once_with(uploaded_file.pk)
    mock_checksum.delay.assert_called_once_with(uploaded_file.pk)
    mock_web_video.delay.assert_called_once_with(uploaded_file.pk)
    uploaded_file.refresh_from_db()
    assert uploaded_file.media_type == 'video/quicktime'


@pytest.mark.django_db
def test_task_assemble_chunks_does_not_enqueue_web_video_for_audio(audio_file):
    with (
        mock.patch.object(UploadedFile, 'assemble_chunks'),
        mock.patch(
            'mmt.uploaded_files.tasks.detect_media_type', return_value='audio/wav'
        ),
        mock.patch('mmt.uploaded_files.tasks.calculate_duration') as mock_duration,
        mock.patch(
            'mmt.uploaded_files.tasks.calculate_server_checksum'
        ) as mock_checksum,
        mock.patch(
            'mmt.uploaded_files.tasks.task_generate_web_video'
        ) as mock_web_video,
    ):
        task_assemble_chunks(audio_file.pk)

    mock_duration.delay.assert_called_once_with(audio_file.pk)
    mock_checksum.delay.assert_called_once_with(audio_file.pk)
    mock_web_video.delay.assert_not_called()


@pytest.mark.django_db
def test_task_assemble_chunks_keeps_media_type_when_detection_returns_none(
    uploaded_file,
):
    with (
        mock.patch.object(UploadedFile, 'assemble_chunks'),
        mock.patch('mmt.uploaded_files.tasks.detect_media_type', return_value=None),
        mock.patch('mmt.uploaded_files.tasks.calculate_duration'),
        mock.patch('mmt.uploaded_files.tasks.calculate_server_checksum'),
        mock.patch('mmt.uploaded_files.tasks.task_generate_web_video'),
    ):
        task_assemble_chunks(uploaded_file.pk)

    uploaded_file.refresh_from_db()
    assert uploaded_file.media_type == 'video/mp4'  # unchanged


@pytest.mark.django_db
def test_task_assemble_chunks_resets_flag_and_skips_followups_on_failure(uploaded_file):
    uploaded_file.assembling = True
    uploaded_file.save(update_fields=['assembling'])

    with (
        mock.patch.object(
            UploadedFile, 'assemble_chunks', side_effect=ValueError('boom')
        ),
        mock.patch('mmt.uploaded_files.tasks.calculate_duration') as mock_duration,
        mock.patch(
            'mmt.uploaded_files.tasks.calculate_server_checksum'
        ) as mock_checksum,
    ):
        with pytest.raises(ValueError):
            task_assemble_chunks(uploaded_file.pk)

    uploaded_file.refresh_from_db()
    assert uploaded_file.assembling is False
    mock_duration.delay.assert_not_called()
    mock_checksum.delay.assert_not_called()


@pytest.mark.django_db
def test_task_generate_web_video_transcodes_and_sets_flag(uploaded_file):
    with mock.patch(
        'mmt.uploaded_files.tasks.transcode_to_web_video', return_value=True
    ) as mock_transcode:
        task_generate_web_video(uploaded_file.pk)

    mock_transcode.assert_called_once_with(
        uploaded_file.file_path, uploaded_file.web_video_path
    )
    uploaded_file.refresh_from_db()
    assert uploaded_file.has_web_video is True


@pytest.mark.django_db
def test_task_generate_web_video_leaves_flag_unset_when_transcode_fails(uploaded_file):
    with mock.patch(
        'mmt.uploaded_files.tasks.transcode_to_web_video', return_value=False
    ):
        task_generate_web_video(uploaded_file.pk)

    uploaded_file.refresh_from_db()
    assert uploaded_file.has_web_video is False


@pytest.mark.django_db
def test_task_generate_web_video_skips_non_video(audio_file):
    with mock.patch(
        'mmt.uploaded_files.tasks.transcode_to_web_video'
    ) as mock_transcode:
        task_generate_web_video(audio_file.pk)

    mock_transcode.assert_not_called()
    audio_file.refresh_from_db()
    assert audio_file.has_web_video is False


@pytest.mark.django_db
def test_calculate_duration_updates_duration(uploaded_file):
    with mock.patch('mmt.uploaded_files.tasks.extract_duration', return_value=42.7):
        calculate_duration(uploaded_file.pk)

    uploaded_file.refresh_from_db()
    assert uploaded_file.duration == 42


@pytest.mark.django_db
def test_calculate_duration_skips_update_when_none(uploaded_file):
    with mock.patch('mmt.uploaded_files.tasks.extract_duration', return_value=None):
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
    project = create_project(title='Test project', user=user)
    pdf_file = UploadedFile.objects.create(
        filename='document.pdf', media_type='application/pdf', project=project
    )

    task_extract_waveform_data(pdf_file.pk)

    assert not Waveform.objects.filter(uploaded_file=pdf_file).exists()


@pytest.mark.django_db
def test_task_extract_waveform_data_updates_existing_waveform(uploaded_file):
    Waveform.objects.create(uploaded_file=uploaded_file, data=[9, 9, 9])
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


@pytest.mark.django_db
def test_calculate_server_checksum_logs_on_mismatch(uploaded_file, caplog):
    uploaded_file.checksum_client = 'client-sum'
    uploaded_file.save()

    with mock.patch(
        'mmt.uploaded_files.tasks.generate_file_md5', return_value='server-sum'
    ):
        with caplog.at_level('WARNING', logger='mmt.uploaded_files.models'):
            calculate_server_checksum(uploaded_file.pk)

    assert 'Checksum mismatch' in caplog.text


@pytest.mark.django_db
def test_calculate_server_checksum_no_log_when_matching(uploaded_file, caplog):
    uploaded_file.checksum_client = 'same-sum'
    uploaded_file.save()

    with mock.patch(
        'mmt.uploaded_files.tasks.generate_file_md5', return_value='same-sum'
    ):
        with caplog.at_level('WARNING', logger='mmt.uploaded_files.models'):
            calculate_server_checksum(uploaded_file.pk)

    assert 'Checksum mismatch' not in caplog.text
