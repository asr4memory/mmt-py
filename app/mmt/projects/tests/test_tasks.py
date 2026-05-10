from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase
from django.urls import reverse

from mmt.my_account.models import Profile
from mmt.projects.models import ProcessingRequest, Project
from mmt.projects.tasks import (
    send_new_processing_request_email,
    send_processing_request_updated_email,
)
from mmt.uploaded_files.models import UploadedFile

User = get_user_model()


class ProjectsTaskTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.alice = User.objects.create_superuser(
            username='alice', password='password', email='alice@example.com'
        )
        cls.bob = User.objects.create_user(
            username='bob', password='password', email='bob@example.com'
        )
        cls.project = Project.objects.create(user=cls.alice, title='Test project')
        cls.uploaded_file = UploadedFile.objects.create(
            project=cls.project,
            filename='test_file.mp4',
            original_filename='test_file.mp4',
            has_file=True,
            size=20000,
            media_type='video/mp4',
        )
        cls.processing_request = ProcessingRequest.objects.create(
            project=cls.project,
            description='Put on platform.',
            make_available_on_platform=True,
        )

    def test_send_new_processing_request_email(self):
        processing_request = self.processing_request

        send_new_processing_request_email(processing_request.id)

        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.subject, '[mmt] New processing request')
        self.assertTrue(
            email.body_contains(
                reverse(
                    'admin:projects_processingrequest_change',
                    args=[processing_request.id],
                )
            )
        )

    def test_send_new_processing_request_email_german(self):
        processing_request = self.processing_request
        profile = self.alice.safe_profile
        profile.locale = Profile.LOCALE_GERMAN
        profile.save()

        send_new_processing_request_email(processing_request.id)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, '[mmt] Neue Bearbeitungsanfrage')

    def test_send_processing_request_updated_email(self):
        processing_request = self.processing_request

        send_processing_request_updated_email(processing_request.id)

        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.subject, '[mmt] Processing request updated')
        self.assertTrue(
            email.body_contains(
                reverse(
                    'projects:processing-request',
                    args=[self.project.id, processing_request.id],
                )
            )
        )
