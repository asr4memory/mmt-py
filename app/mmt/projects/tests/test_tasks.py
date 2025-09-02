from django.contrib.auth import get_user_model
from django.test import TestCase
from django.core import mail

from mmt.projects.tasks import send_new_processing_request_email
from mmt.projects.models import Project, ProcessingRequest
from mmt.uploaded_files.models import UploadedFile
from mmt.my_account.models import Profile

User = get_user_model()


class ProjectsTaskTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.alice = User.objects.create_superuser(
            username="alice", password="password", email="alice@example.com"
        )
        cls.bob = User.objects.create_user(
            username="bob", password="password", email="bob@example.com"
        )
        cls.project = Project.objects.create(user=cls.alice, name="Test project")
        cls.uploaded_file = UploadedFile.objects.create(
            project=cls.project,
            filename="test_file.mp4",
            size=20000,
            transferred=20000,
            media_type="video/mp4",
            status=UploadedFile.UploadStatus.COMPLETE,
        )
        cls.processing_request = ProcessingRequest.objects.create(
            project=cls.project, description="Put on platform."
        )

    def test_send_new_processing_request_email(self):
        processing_request = self.processing_request

        send_new_processing_request_email(processing_request.id)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "[mmt-py] New processing request")

    def test_send_new_processing_request_email_german(self):
        processing_request = self.processing_request
        profile = self.alice.safe_profile
        profile.locale = Profile.LOCALE_GERMAN
        profile.save()

        send_new_processing_request_email(processing_request.id)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "[mmt-py] Neue Verarbeitungsanfrage")
