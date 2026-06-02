from celery import shared_task
from django.utils.translation import gettext_lazy as _

from mmt.uploaded_files.analysis import (
    extract_duration,
    extract_waveform_data,
    generate_file_md5,
)
from mmt.uploaded_files.models import UploadedFile, Waveform


@shared_task
def calculate_server_checksum(uploaded_file_id: int) -> None:
    uploaded_file = UploadedFile.objects.get(pk=uploaded_file_id)
    checksum = generate_file_md5(uploaded_file.file_path)
    UploadedFile.objects.filter(pk=uploaded_file_id).update(checksum_server=checksum)


@shared_task
def calculate_duration(uploaded_file_id: int) -> None:
    uploaded_file = UploadedFile.objects.get(pk=uploaded_file_id)
    duration = extract_duration(uploaded_file.file_path)
    if duration is not None:
        UploadedFile.objects.filter(pk=uploaded_file_id).update(duration=duration)


@shared_task
def task_extract_waveform_data(uploaded_file_id: int) -> None:
    uploaded_file = UploadedFile.objects.get(pk=uploaded_file_id)
    if not uploaded_file.is_av_media():
        return

    data = extract_waveform_data(media_file=uploaded_file.file_path)
    if data is None:
        return
    Waveform.objects.update_or_create(
        uploaded_file=uploaded_file,
        defaults={'data': data},
    )
