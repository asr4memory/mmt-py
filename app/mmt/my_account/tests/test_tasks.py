import shutil
import tempfile
from datetime import datetime, UTC
from unittest import mock

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

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
        self.assertEqual(email.to, ['alice@example.com'])
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
        self.assertEqual(email.to, ['bob@example.com'])
        self.assertTrue(email.body_contains('bob'))

    def test_send_dpa_created_email(self):
        send_dpa_created_email(self.bob.id)

        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.subject, '[mmt] Data processing agreement provided')
        self.assertEqual(email.to, ['bob@example.com'])
        self.assertTrue(email.body_contains('bob'))
        self.assertTrue(email.body_contains(reverse('account:profile')))

    @mock.patch('mmt.my_account.tasks.generate_dpa_pdf', return_value=b'%PDF')
    @mock.patch('mmt.my_account.tasks.send_dpa_created_email.delay')
    def test_create_dpa_pdf(self, send_email_mock, generate_mock):
        self.bob.dpa_accepted_at = datetime(2026, 5, 7, 10, 0, 0, tzinfo=UTC)
        self.bob.save()

        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp)

        with override_settings(MEDIA_ROOT=tmp):
            create_dpa_pdf(self.bob.id)

        generate_mock.assert_called_once_with(
            self.bob.safe_profile.full_name, self.bob.dpa_accepted_at
        )
        profile = self.bob.safe_profile
        self.assertTrue(profile.dpa.name.endswith('dpa_bob.pdf'))
        send_email_mock.assert_called_once_with(self.bob.id)
