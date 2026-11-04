from urllib.parse import urljoin

from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.mail import EmailMultiAlternatives, send_mail
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.utils.translation import override

from mmt.core.tasks import email_task

from mmt.my_account.pdf import generate_dpa_pdf

User = get_user_model()


@email_task
def send_upload_permission_request_email(user_id: int) -> None:
    user = User.objects.get(pk=user_id)
    admins = User.objects.filter(is_superuser=True, is_active=True)

    url = urljoin(
        settings.MMT_SITE_HOST,
        reverse('admin:my_account_user_change', args=[user.id]),
    )

    for admin in admins:
        profile = admin.safe_profile
        with override(profile.locale):
            subject = _('A user has requested upload permission.')
            body = render_to_string(
                'email/upload_permission_request.txt',
                {
                    'addressee': admin.username,
                    'username': user.username,
                    'url': url,
                },
            )
            send_rendered_email.delay(
                subject=f'{settings.MMT_EMAIL_SUBJECT_PREFIX} {subject}',
                body=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[admin.email],
            )


@email_task
def send_upload_permission_granted_email(user_id: int) -> None:
    user = User.objects.get(pk=user_id)
    profile = user.safe_profile

    with override(profile.locale):
        subject = _('Upload permission granted')
        body = render_to_string(
            'email/upload_permission_granted.txt',
            {'addressee': user.username},
        )
        send_mail(
            subject=f'{settings.MMT_EMAIL_SUBJECT_PREFIX} {subject}',
            message=body,
            from_email=None,
            recipient_list=[user.email],
            fail_silently=False,
        )


@shared_task
def create_dpa_pdf(user_id: int) -> None:
    user = User.objects.get(pk=user_id)
    profile = user.safe_profile

    pdf = generate_dpa_pdf(profile.full_name, user.dpa_accepted_at)

    profile.dpa.delete()
    profile.dpa.save(f'dpa_{user.username}.pdf', ContentFile(pdf))

    send_dpa_created_email.delay(user_id)


@email_task
def send_dpa_created_email(user_id: int) -> None:
    user = User.objects.get(pk=user_id)
    profile = user.safe_profile

    url = urljoin(settings.MMT_SITE_HOST, reverse('account:profile'))

    with override(profile.locale):
        subject = _('Data processing agreement provided')
        body = render_to_string(
            'email/dpa_created.txt',
            {'addressee': user.username, 'url': url},
        )
        send_mail(
            subject=f'{settings.MMT_EMAIL_SUBJECT_PREFIX} {subject}',
            message=body,
            from_email=None,
            recipient_list=[user.email],
            fail_silently=False,
        )


@email_task
def send_rendered_email(
    subject: str,
    body: str,
    from_email: str,
    to: list[str],
    html_body: str | None = None,
) -> None:
    """Send an email that has already been rendered."""
    message = EmailMultiAlternatives(subject, body, from_email, to)
    if html_body is not None:
        message.attach_alternative(html_body, 'text/html')
    message.send()
