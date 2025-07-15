from celery import shared_task
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.translation import gettext_lazy as _
from django.utils.translation import override

User = get_user_model()

SUBJECT_PREFIX = "[mmt-py]"


@shared_task
def send_new_user_email(user_id: int) -> None:
    user = User.objects.get(pk=user_id)
    admins = User.objects.filter(is_superuser=True, is_active=True)
    for admin in admins:
        profile = admin.safe_profile
        with override(profile.locale):
            subject = _("A new user has registered.")
            body = render_to_string(
                "new_user.txt",
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


@shared_task
def send_user_activation_email(user_id: int) -> None:
    user = User.objects.get(pk=user_id)
    profile = user.safe_profile
    with override(profile.locale):
        subject = _("Your account has been activated.")
        body = render_to_string("user_activated.txt", {"username": user.username})
        send_mail(
            f"{SUBJECT_PREFIX} {subject}",
            body,
            "from@example.com",
            [user.email],
            fail_silently=False,
        )
