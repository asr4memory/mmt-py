from celery import shared_task
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.translation import gettext_lazy as _
from django.utils.translation import override

from .models import ServiceRequest

User = get_user_model()

SUBJECT_PREFIX = "[mmt-py]"


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
                subject=f"{SUBJECT_PREFIX} {subject}",
                message=body,
                from_email=None,
                recipient_list=[admin.email],
                fail_silently=False,
            )
