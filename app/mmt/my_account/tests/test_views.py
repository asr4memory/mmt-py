from http import HTTPStatus
from bs4 import BeautifulSoup
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.messages.storage.base import Message
from django.contrib.messages.test import MessagesTestMixin
from django.utils import timezone
from django.test import TestCase

User = get_user_model()


class MyAccountViewTests(TestCase, MessagesTestMixin):
    @classmethod
    def setUpTestData(cls):
        cls.alice = User.objects.create_user(
            username="alice", password="password", email="alice@example.com"
        )
        cls.bob = User.objects.create_user(
            username="bob", password="password", email="bob@example.com"
        )
        perm1 = Permission.objects.get(codename="view_uploadedfile")
        perm2 = Permission.objects.get(codename="add_uploadedfile")
        cls.alice.user_permissions.add(perm1, perm2)

    def test_profile_page(self):
        self.client.login(username="bob", password="password")
        response = self.client.get("/account/profile/")

        self.assertContains(response, "<h1>Profile</h1>", html=True)
        self.assertContains(response, "bob", html=True)
        self.assertContains(response, "bob@example.com", html=True)
        self.assertContains(response, "<li>Download</li>", html=True)

    def test_profile_page_permission_request_button(self):
        "Permission is not shown, button is displayed."
        self.client.login(username="bob", password="password")
        response = self.client.get("/account/profile/")

        self.assertNotContains(response, "<li>Upload</li>", html=True)
        soup = BeautifulSoup(response.content, "html.parser")
        form = soup.find(attrs={"data-testid": "request-permission-form"})
        self.assertIn("Request upload permission", form.get_text())

    def test_profile_page_permission_requested(self):
        "Once permission is requested, message is shown."
        self.bob.upload_permission_requested_at = timezone.now()
        self.bob.save()
        self.client.login(username="bob", password="password")
        response = self.client.get("/account/profile/")

        self.assertNotContains(response, "<li>Upload</li>", html=True)
        soup = BeautifulSoup(response.content, "html.parser")
        message = soup.find(attrs={"data-testid": "request-permission-message"})
        self.assertIn("Upload permission requested", message.get_text())
        form = soup.find(attrs={"data-testid": "request-permission-form"})
        self.assertIsNone(form)

    def test_profile_page_permission_available(self):
        "Permission is shown if available, button not."
        self.client.login(username="alice", password="password")
        response = self.client.get("/account/profile/")

        self.assertContains(response, "<li>Upload</li>", html=True)
        soup = BeautifulSoup(response.content, "html.parser")
        form = soup.find(attrs={"data-testid": "request-permission-form"})
        self.assertIsNone(form)

    def test_profile_page_redirect(self):
        response = self.client.get("/account/profile/")

        self.assertRedirects(response, "/accounts/login/?next=/account/profile/")

    def test_edit_profile_page(self):
        self.client.login(username="bob", password="password")
        response = self.client.get("/account/profile/edit/")

        self.assertContains(response, "<h1>Edit profile</h1>", html=True)

    def test_edit_profile_page_redirect(self):
        response = self.client.get("/account/profile/edit/")

        self.assertRedirects(response, "/accounts/login/?next=/account/profile/edit/")

    def test_edit_profile_post_request(self):
        self.client.login(username="bob", password="password")

        response = self.client.post(
            "/account/profile/edit/", {"full_name": "Bob Sanders", "locale": "de"}
        )
        self.assertRedirects(response, "/account/profile/")

        profile = self.bob.profile
        self.assertEqual(profile.full_name, "Bob Sanders")
        self.assertEqual(profile.locale, "de")

    def test_edit_profile_post_logged_out(self):
        response = self.client.post(
            "/account/profile/edit/", {"full_name": "Bob Sanders", "locale": "de"}
        )
        self.assertRedirects(response, "/accounts/login/?next=/account/profile/edit/")

    def test_post_upload_permission(self):
        "Normal upload-permission post request."
        self.client.login(username="bob", password="password")
        response = self.client.post("/account/profile/upload-permission/")

        self.assertRedirects(response, "/account/profile/")
        self.assertMessages(
            response, [Message(level=25, message="Upload permission requested.")]
        )
        bob = User.objects.get(username="Bob")
        self.assertIsNotNone(bob.upload_permission_requested_at)

    def test_get_upload_permission(self):
        "GET upload-permission request fails."
        self.client.login(username="bob", password="password")
        response = self.client.get("/account/profile/upload-permission/")

        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_post_upload_permission_logged_out(self):
        response = self.client.post("/account/profile/upload-permission/")
        self.assertRedirects(response, "/accounts/login/?next=/account/profile/upload-permission/")


    def test_debug_page_not_accessible(self):
        """Debug page is only accessible by superusers."""
        self.client.login(username="bob", password="password")
        response = self.client.get("/account/debug/")

        self.assertRedirects(response, "/")
