from urllib.parse import urljoin

from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.translation import gettext_lazy as _, override

from mmt.my_account.pdf import generate_dpa_pdf

User = get_user_model()


@shared_task
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
            send_mail(
                subject=f'{settings.MMT_EMAIL_SUBJECT_PREFIX} {subject}',
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

    pdf = generate_dpa_pdf(profile.full_name, user.terms_accepted_at)

    profile.dpa.delete()
    profile.dpa.save(f'dpa_{user.username}.pdf', ContentFile(pdf))

    send_dpa_created_email.delay(user_id)


@shared_task
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
