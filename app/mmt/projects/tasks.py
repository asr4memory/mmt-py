from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.translation import gettext_lazy as _
from django.utils.translation import override

from mmt.projects.models import ServiceRequest

User = get_user_model()


@shared_task
def send_new_service_request_email(service_request_id: int) -> None:
    service_request = ServiceRequest.objects.get(pk=service_request_id)
    project = service_request.project
    user = project.user

    admins = User.objects.filter(is_superuser=True, is_active=True)
    for admin in admins:
        profile = admin.safe_profile
        with override(profile.locale):
            subject = _("New service request")
            body = render_to_string(
                "new_service_request.txt",
                {
                    "admin": admin.username,
                    "username": user.username,
                },
            )
            send_mail(
                subject=f"{settings.MMT_EMAIL_SUBJECT_PREFIX} {subject}",
                message=body,
                from_email=None,
                recipient_list=[admin.email],
                fail_silently=False,
            )


@shared_task
def send_new_file_email(user_id: int, filename: str) -> None:
    User = get_user_model()
    user = User.objects.get(pk=user_id)
    profile = user.safe_profile
    with override(profile.locale):
        subject = _("New file ready for download")
        body = render_to_string(
            "new_downloadable_file.txt",
            {"username": user.username, "filename": filename},
        )
        send_mail(
            subject=f"{settings.MMT_EMAIL_SUBJECT_PREFIX} {subject}",
            message=body,
            from_email=None,
            recipient_list=[user.email],
            fail_silently=False,
        )
