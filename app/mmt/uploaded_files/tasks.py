from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.translation import gettext_lazy as _, override

from .filesystem import generate_file_md5
from .models import UploadedFile

User = get_user_model()

SUBJECT_PREFIX = "[mmt-py]"


@shared_task
def add(x: int, y: int) -> int:
    return x + y


@shared_task
def calculate_server_checksum(uploaded_file_id: int) -> str:
    uploaded_file = UploadedFile.objects.select_related("upload_job__user").get(
        pk=uploaded_file_id
    )
    upload_job = uploaded_file.upload_job
    user = upload_job.user
    upload_path = settings.BASE_DIR / "user_files" / user.username / "uploads"
    file_path = upload_path / upload_job.directory_name() / uploaded_file.filename

    checksum = generate_file_md5(file_path)
    UploadedFile.objects.filter(pk=uploaded_file_id).update(checksum_server=checksum)
    return checksum


@shared_task
def send_file_uploaded_emails(user_id: int, filename: str) -> None:
    # Send mail to user.
    user = User.objects.select_related("profile").get(pk=user_id)
    with override(user.profile.locale):
        subject = _("File uploaded")
        body = render_to_string(
            "file_uploaded_user.txt", {"username": user.username, "filename": filename}
        )
        send_mail(
            f"{SUBJECT_PREFIX} {subject}",
            body,
            "from@example.com",
            [user.email],
            fail_silently=False,
        )

    # Send mail to admins.
    admins = User.objects.select_related("profile").filter(
        is_superuser=True, is_active=True
    )
    for admin in admins:
        with override(admin.profile.locale):
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
                f"{SUBJECT_PREFIX} {subject}",
                body,
                "from@example.com",
                [admin.email],
                fail_silently=False,
            )
