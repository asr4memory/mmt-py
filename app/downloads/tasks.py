from celery import shared_task
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.translation import gettext_lazy as _, override


# TODO: Put into settings.
SUBJECT_PREFIX = "[mmt-py]"


@shared_task
def send_new_file_email(user_id: int, filename: str) -> None:
    User = get_user_model()
    user = User.objects.select_related("profile").get(pk=user_id)
    with override(user.profile.locale):
        subject = _("New file ready for downloaded")
        body = render_to_string(
            "new_downloadable_file.txt",
            {"username": user.username, "filename": filename},
        )
        send_mail(
            f"{SUBJECT_PREFIX} {subject}",
            body,
            "from@example.com",
            [user.email],
            fail_silently=False,
        )
