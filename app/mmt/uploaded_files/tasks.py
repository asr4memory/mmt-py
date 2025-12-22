from celery import shared_task
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from .models import UploadedFile
from .utils import generate_file_md5

User = get_user_model()


@shared_task
def calculate_server_checksum(uploaded_file_id: int) -> str:
    uploaded_file = UploadedFile.objects.select_related('project__user').get(
        pk=uploaded_file_id
    )
    file_path = uploaded_file.file_path
    checksum = generate_file_md5(file_path)
    UploadedFile.objects.filter(pk=uploaded_file_id).update(checksum_server=checksum)
    return checksum
