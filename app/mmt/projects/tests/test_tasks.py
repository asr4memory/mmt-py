from django.contrib.auth import get_user_model
from django.test import TestCase
from django.core import mail

from mmt.projects.tasks import send_new_service_request_email
from mmt.projects.models import Project, ServiceRequest
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
        cls.project = Project.objects.create(user=cls.alice, title="Test project")
        cls.uploaded_file = UploadedFile.objects.create(
            project=cls.project,
            filename="test_file.mp4",
            has_file=True,
            size=20000,
            transferred=20000,
            media_type="video/mp4",
        )
        cls.service_request = ServiceRequest.objects.create(
            project=cls.project, description="Put on platform."
        )

    def test_send_new_service_request_email(self):
        service_request = self.service_request

        send_new_service_request_email(service_request.id)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "[mmt-py] New service request")

    def test_send_new_service_request_email_german(self):
        service_request = self.service_request
        profile = self.alice.safe_profile
        profile.locale = Profile.LOCALE_GERMAN
        profile.save()

        send_new_service_request_email(service_request.id)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "[mmt-py] Neue Serviceanfrage")
