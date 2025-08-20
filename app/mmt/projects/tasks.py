from celery import shared_task
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.translation import gettext_lazy as _
from django.utils.translation import override

from .models import ProcessingRequest
User = get_user_model()

SUBJECT_PREFIX = "[mmt-py]"


@shared_task
def send_new_processing_request_email(processing_request_id: int) -> None:
    processing_request = ProcessingRequest.objects.get(pk=processing_request_id)
    project = processing_request.project
    user = project.user

    admins = User.objects.filter(is_superuser=True, is_active=True)
    for admin in admins:
        profile = admin.safe_profile
        with override(profile.locale):
            subject = _("New processing request.")
            body = render_to_string(
                "new_processing_request.txt",
                {
                    "admin": admin.username,
                    "username": user.username,
                },
            )
            send_mail(
                f"{SUBJECT_PREFIX} {subject}",
                body,
                "from@example.com",
                [admin.email],
                fail_silently=False,
            )
