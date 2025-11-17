from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase
from django.urls import reverse

from mmt.my_account.tasks import (
    send_upload_permission_request_email,
    send_upload_permission_granted_email,
)

User = get_user_model()


class MyAccountTaskTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.alice = User.objects.create_superuser(
            username="alice", password="password", email="alice@example.com"
        )
        cls.bob = User.objects.create_user(
            username="bob", password="password", email="bob@example.com"
        )

    def test_send_upload_permission_request_email(self):
        send_upload_permission_request_email(self.bob.id)

        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.subject, "[mmt] A user has requested upload permission.")
        self.assertTrue(
            email.body_contains(
                reverse(
                    "admin:my_account_user_change",
                    args=[self.bob],
                )
            )
        )

    def test_send_upload_permission_granted_email(self):
        send_upload_permission_granted_email(self.bob.id)

        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.subject, "[mmt] Upload permission granted")
