import smtplib
from unittest import mock

import pytest
from django.contrib.auth.models import AnonymousUser
from allauth.account.adapter import get_adapter
from allauth.core import context as allauth_context
from celery.exceptions import Retry
from django.core import mail
from django.test import RequestFactory

from mmt.my_account.tasks import send_rendered_email


@pytest.fixture
def request_obj():
    request = RequestFactory().get('/')
    request.user = AnonymousUser()
    return request


def test_adapter_enqueues_rendered_email(settings, request_obj):
    adapter = get_adapter()
    with (
        allauth_context.request_context(request_obj),
        mock.patch('mmt.my_account.adapter.send_rendered_email.delay') as delay,
    ):
        adapter.send_mail(
            'account/email/email_confirmation',
            'bob@example.com',
            {'user': mock.Mock(), 'activate_url': 'http://testserver/activate/'},
        )

    assert mail.outbox == []
    delay.assert_called_once()
    kwargs = delay.call_args.kwargs
    assert kwargs['to'] == ['bob@example.com']
    assert kwargs['subject'].startswith(settings.ACCOUNT_EMAIL_SUBJECT_PREFIX)
    assert 'http://testserver/activate/' in kwargs['body']


def test_send_rendered_email_sends_message():
    send_rendered_email(
        subject='Subject',
        body='Body',
        from_email='from@example.com',
        to=['bob@example.com'],
        html_body=None,
    )

    assert len(mail.outbox) == 1
    assert mail.outbox[0].subject == 'Subject'
    assert mail.outbox[0].to == ['bob@example.com']


def test_send_rendered_email_retries_on_smtp_error():
    error = smtplib.SMTPRecipientsRefused({'bob@example.com': (451, b'try later')})
    with mock.patch('django.core.mail.EmailMessage.send', side_effect=error):
        with pytest.raises(Retry):
            send_rendered_email.apply(
                kwargs={
                    'subject': 'Subject',
                    'body': 'Body',
                    'from_email': 'from@example.com',
                    'to': ['bob@example.com'],
                    'html_body': None,
                },
                throw=True,
            ).get()
