from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.translation import gettext_lazy as _
from django.utils.translation import override

from .models import UploadedFile
from .utils import generate_file_md5

User = get_user_model()

SUBJECT_PREFIX = "[mmt-py]"


@shared_task
def add(x: int, y: int) -> int:
    return x + y


@shared_task
def calculate_server_checksum(uploaded_file_id: int) -> str:
    uploaded_file = UploadedFile.objects.select_related("project__user").get(
        pk=uploaded_file_id
    )
    project = uploaded_file.project

    file_path = project.directory_path / uploaded_file.filename
    checksum = generate_file_md5(file_path)
    UploadedFile.objects.filter(pk=uploaded_file_id).update(checksum_server=checksum)
    return checksum


@shared_task
def send_file_uploaded_emails(user_id: int, filename: str) -> None:
    # Send mail to user.
    user = User.objects.get(pk=user_id)
    profile = user.safe_profile
    with override(profile.locale):
        subject = _("File uploaded")
        body = render_to_string(
            "file_uploaded_user.txt", {"username": user.username, "filename": filename}
        )
        send_mail(
            subject=f"{SUBJECT_PREFIX} {subject}",
            message=body,
            from_email=None,
            recipient_list=[user.email],
            fail_silently=False,
        )

    # Send mail to admins.
    admins = User.objects.filter(is_superuser=True, is_active=True)
    for admin in admins:
        profile = admin.safe_profile
        with override(profile.locale):
            subject = _("File uploaded")
            body = render_to_string(
                "file_uploaded_admin.txt",
                {
                    "admin": admin.username,
                    "username": user.username,
                    "filename": filename,
                },
            )
            send_mail(
                subject=f"{SUBJECT_PREFIX} {subject}",
                message=body,
                from_email=None,
                recipient_list=[admin.email],
                fail_silently=False,
            )
