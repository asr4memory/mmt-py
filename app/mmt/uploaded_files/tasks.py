from celery import shared_task
from django.utils.translation import gettext_lazy as _

from mmt.uploaded_files.media import (
    detect_media_type,
    extract_duration,
    extract_waveform_data,
    generate_file_md5,
)
from mmt.uploaded_files.models import UploadedFile, Waveform


@shared_task
def task_assemble_chunks(uploaded_file_id: int) -> None:
    uploaded_file = UploadedFile.objects.get(pk=uploaded_file_id)
    try:
        uploaded_file.assemble_chunks()
    except Exception:
        # Reset the flag so the file drops back to 'incomplete' and the final
        # chunk can be re-sent to retry assembly.
        UploadedFile.objects.filter(pk=uploaded_file_id).update(assembling=False)
        raise
    calculate_duration.delay(uploaded_file_id)
    calculate_server_checksum.delay(uploaded_file_id)
    task_update_media_type.delay(uploaded_file_id)


@shared_task
def calculate_server_checksum(uploaded_file_id: int) -> None:
    uploaded_file = UploadedFile.objects.get(pk=uploaded_file_id)
    checksum = generate_file_md5(uploaded_file.file_path)
    UploadedFile.objects.filter(pk=uploaded_file_id).update(checksum_server=checksum)
    uploaded_file.refresh_from_db()
    uploaded_file.log_if_corrupt()


@shared_task
def task_update_media_type(uploaded_file_id: int) -> None:
    uploaded_file = UploadedFile.objects.get(pk=uploaded_file_id)
    media_type = detect_media_type(uploaded_file.file_path)
    if media_type:
        UploadedFile.objects.filter(pk=uploaded_file_id).update(media_type=media_type)


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
