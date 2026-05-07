import io
from urllib.parse import urljoin
import zoneinfo

from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _, override

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
def send_agreed_to_dpa_email(user_id: int) -> None:
    user = User.objects.get(pk=user_id)
    admins = User.objects.filter(is_superuser=True, is_active=True)

    url = urljoin(
        settings.MMT_SITE_HOST,
        reverse('admin:my_account_user_change', args=[user.id]),
    )

    for admin in admins:
        profile = admin.safe_profile
        with override(profile.locale):
            subject = _('A user has agreed to the data processing agreement.')
            body = render_to_string(
                'email/agreed_to_dpa.txt',
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


@shared_task
def create_dpa_pdf(user_id: int) -> None:
    from weasyprint import HTML

    user = User.objects.get(pk=user_id)
    profile = user.safe_profile

    dt_berlin = timezone.localtime(
        user.terms_accepted_at, timezone=zoneinfo.ZoneInfo('Europe/Berlin')
    )
    accepted_at_str = dt_berlin.strftime('%d.%m.%Y, %H:%M:%S Uhr (%Z)')

    context = dict(full_name=profile.full_name, dpa_accepted_at=accepted_at_str)
    html_template = render_to_string('pdfs/dpa.html', context)

    html = HTML(string=html_template)
    pdf = html.write_pdf()

    profile.dpa.delete()
    profile.dpa.save(f'dpa_{user.username}.pdf', ContentFile(pdf))
