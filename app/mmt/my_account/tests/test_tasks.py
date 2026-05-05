from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase
from django.urls import reverse

from mmt.my_account.models import Profile
from mmt.my_account.tasks import (
    send_agreed_to_dpa_email,
    send_dpa_created_email,
    send_upload_permission_granted_email,
    send_upload_permission_request_email,
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

    def test_send_agreed_to_dpa_email(self):
        send_agreed_to_dpa_email(self.bob.id)

        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(
            email.subject, '[mmt] A user has agreed to the data processing agreement.'
        )
        self.assertTrue(
            email.body_contains(
                reverse('admin:my_account_user_change', args=[self.bob.id])
            )
        )

    def test_send_agreed_to_dpa_email_german(self):
        profile = self.alice.safe_profile
        profile.locale = Profile.LOCALE_GERMAN
        profile.save()

        send_agreed_to_dpa_email(self.bob.id)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(
            mail.outbox[0].subject,
            '[mmt] Ein Nutzer hat dem Auftragsverarbeitungsvertrag zugestimmt.',
        )

    def test_send_dpa_created_email(self):
        send_dpa_created_email(self.bob.id)

        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.subject, '[mmt] Data processing agreement provided')
        self.assertTrue(email.body_contains(reverse('account:profile')))

    def test_send_dpa_created_email_german(self):
        profile = self.bob.safe_profile
        profile.locale = Profile.LOCALE_GERMAN
        profile.save()

        send_dpa_created_email(self.bob.id)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(
            mail.outbox[0].subject, '[mmt] Auftragsverarbeitungsvertrag bereitgestellt'
        )
