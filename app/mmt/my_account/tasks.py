from urllib.parse import urljoin

from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.utils.translation import override

User = get_user_model()


@shared_task
def send_user_activation_email(user_id: int) -> None:
    user = User.objects.get(pk=user_id)
    profile = user.safe_profile
    with override(profile.locale):
        subject = _("Your account has been activated.")
        body = render_to_string("email/user_activated.txt", {"addressee": user.username})
        send_mail(
            subject=f"{settings.MMT_EMAIL_SUBJECT_PREFIX} {subject}",
            message=body,
            from_email=None,
            recipient_list=[user.email],
            fail_silently=False,
        )


@shared_task
def send_upload_permission_request_email(user_id: int) -> None:
    user = User.objects.get(pk=user_id)
    admins = User.objects.filter(is_superuser=True, is_active=True)

    url = urljoin(
        settings.MMT_SITE_HOST,
        reverse('admin:my_account_user_change', args=[user]),
    )

    for admin in admins:
        profile = admin.safe_profile
        with override(profile.locale):
            subject = _("A user has requested upload permission.")
            body = render_to_string(
                "email/upload_permission_request.txt",
                {
                    "addressee": admin.username,
                    "username": user.username,
                    "url": url,
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
def send_upload_permission_granted_email(user_id: int) -> None:
    user = User.objects.get(pk=user_id)
    profile = user.safe_profile

    with override(profile.locale):
        subject = _("Upload permission granted")
        body = render_to_string(
            "email/upload_permission_granted.txt",
            {"addressee": user.username},
        )
        send_mail(
            subject=f"{settings.MMT_EMAIL_SUBJECT_PREFIX} {subject}",
            message=body,
            from_email=None,
            recipient_list=[user.email],
            fail_silently=False,
        )
