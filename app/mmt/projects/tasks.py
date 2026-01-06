from urllib.parse import urljoin

from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.utils.translation import override

from mmt.projects.models import ProcessingRequest

User = get_user_model()


@shared_task
def send_new_processing_request_email(processing_request_id: int) -> None:
    processing_request = ProcessingRequest.objects.get(pk=processing_request_id)
    project = processing_request.project
    user = project.user

    url = urljoin(
        settings.MMT_SITE_HOST,
        reverse(
            'admin:projects_processingrequest_change', args=[processing_request_id]
        ),
    )

    admins = User.objects.filter(is_superuser=True, is_active=True)
    for admin in admins:
        profile = admin.safe_profile
        with override(profile.locale):
            subject = _('New processing request')
            body = render_to_string(
                'email/new_processing_request.txt',
                {
                    'addressee': admin.username,
                    'username': user.username,
                    'url': url,
                },
            )
            send_mail(
                subject=f'{settings.MMT_EMAIL_SUBJECT_PREFIX} {subject}',
                message=body,
                from_email=None,
                recipient_list=[admin.email],
                fail_silently=False,
            )


@shared_task
def send_processing_request_updated_email(processing_request_id: int) -> None:
    processing_request = ProcessingRequest.objects.get(pk=processing_request_id)
    project = processing_request.project
    user = project.user
    profile = user.safe_profile

    url = urljoin(
        settings.MMT_SITE_HOST,
        reverse(
            'projects:processing-request', args=[project.id, processing_request_id]
        ),
    )

    with override(profile.locale):
        subject = _('Processing request updated')
        body = render_to_string(
            'email/processing_request_updated.txt',
            {
                'addressee': user.username,
                'processing_request_id': processing_request_id,
                'url': url,
            },
        )
        send_mail(
            subject=f'{settings.MMT_EMAIL_SUBJECT_PREFIX} {subject}',
            message=body,
            from_email=None,
            recipient_list=[user.email],
            fail_silently=False,
        )
