import shutil
import tempfile
from datetime import datetime, UTC
from unittest import mock

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from mmt.my_account.pdf import generate_dpa_pdf
from mmt.my_account.tasks import (
    create_dpa_pdf,
    send_upload_permission_granted_email,
    send_upload_permission_request_email,
    send_dpa_created_email,
)

User = get_user_model()


class MyAccountTaskTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.alice = User.objects.create_superuser(
            username='alice', password='password', email='alice@example.com'
        )
        cls.bob = User.objects.create_user(
            username='bob', password='password', email='bob@example.com'
        )

    def test_send_upload_permission_request_email(self):
        send_upload_permission_request_email(self.bob.id)

        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.subject, '[mmt] A user has requested upload permission.')
        self.assertTrue(
            email.body_contains(
                reverse(
                    'admin:my_account_user_change',
                    args=[self.bob.id],
                )
            )
        )

    def test_send_upload_permission_granted_email(self):
        send_upload_permission_granted_email(self.bob.id)

        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.subject, '[mmt] Upload permission granted')

    def test_send_dpa_created_email(self):
        send_dpa_created_email(self.bob.id)

        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.subject, '[mmt] Data processing agreement provided')

    @mock.patch('weasyprint.HTML')
    def test_generate_dpa_pdf(self, html_mock):
        html_mock.return_value.write_pdf.return_value = b'%PDF'

        result = generate_dpa_pdf('Bob Smith', '07.05.2026, 10:00:00 Uhr (CEST)')

        self.assertEqual(result, b'%PDF')
        rendered = html_mock.call_args.kwargs['string']
        self.assertIn('Bob Smith', rendered)
        self.assertIn('07.05.2026', rendered)
        self.assertIn('Vertrag zur Auftragsverarbeitung gemäß Art. 28 DSGVO', rendered)

    @mock.patch('mmt.my_account.tasks.generate_dpa_pdf', return_value=b'%PDF')
    @mock.patch('mmt.my_account.tasks.send_dpa_created_email.delay')
    def test_create_dpa_pdf(self, send_email_mock, generate_mock):
        self.bob.terms_accepted_at = datetime(2026, 5, 7, 10, 0, 0, tzinfo=UTC)
        self.bob.save()

        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp)

        with override_settings(MEDIA_ROOT=tmp):
            create_dpa_pdf(self.bob.id)

        generate_mock.assert_called_once()
        profile = self.bob.safe_profile
        self.assertTrue(profile.dpa.name.endswith('dpa_bob.pdf'))
        send_email_mock.assert_called_once_with(self.bob.id)
