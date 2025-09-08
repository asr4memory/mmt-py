from celery import shared_task
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.translation import gettext_lazy as _
from django.utils.translation import override

# TODO: Put into settings.
SUBJECT_PREFIX = "[mmt-py]"


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
            subject=f"{SUBJECT_PREFIX} {subject}",
            message=body,
            recipient_list=[user.email],
            fail_silently=False,
        )
