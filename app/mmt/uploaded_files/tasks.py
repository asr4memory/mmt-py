from celery import shared_task
from django.utils.translation import gettext_lazy as _

from mmt.uploaded_files.ffmpeg import extract_waveform_data
from mmt.uploaded_files.models import UploadedFile
from mmt.uploaded_files.utils import generate_file_md5

SAMPLING_RATE = 10


@shared_task
def calculate_server_checksum(uploaded_file_id: int) -> None:
    """
    Calculates an MD5 checksum for the uploaded file and saves it

    :param uploaded_file_id: id of uploaded file record
    :type uploaded_file_id: int
    """
    uploaded_file = UploadedFile.objects.get(pk=uploaded_file_id)
    checksum = generate_file_md5(uploaded_file.file_path)
    UploadedFile.objects.filter(pk=uploaded_file_id).update(checksum_server=checksum)


@shared_task
def create_waveform_data(uploaded_file_id: int) -> None:
    """
    Generates waveform data and calculates duration and saves both

    :param uploaded_file_id: id of uploaded file record
    :type uploaded_file_id: int
    """
    uploaded_file = UploadedFile.objects.get(pk=uploaded_file_id)
    waveform = extract_waveform_data(
        media_file=uploaded_file.file_path, sampling_rate=SAMPLING_RATE
    )
    duration = len(waveform) / SAMPLING_RATE
    UploadedFile.objects.filter(pk=uploaded_file_id).update(
        waveform=waveform, duration=duration
    )
