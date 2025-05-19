from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class CoreTests(TestCase):
    def test_primary_menu(self):
        """Primary menu shows the right amount of links when logged out."""
        response = self.client.get(reverse("welcome"))

        self.assertContains(response, "Downloads")
        self.assertContains(response, "Log in")
        self.assertContains(response, "Register")

    def test_fail_fast_for_missing_download_dir(self):
        """Fails fast if download directory is missing"""
        User.objects.create_user(username="alice", password="password")
        self.client.login(username="alice", password="password")

        response = self.client.get(reverse("welcome"))

        self.assertEqual(response.status_code, HTTPStatus.INTERNAL_SERVER_ERROR)
        self.assertEqual(response.text, "Downloads directory does not exist for the user.")

    def test_primary_menu_logged_in(self):
        """Primary menu shows the right amount of links when logged in."""
        alice = User.objects.create_user(username="alice", password="password")
        alice.create_user_directories()
        self.client.login(username="alice", password="password")

        response = self.client.get(reverse("welcome"))

        self.assertContains(response, "Log out")

    def test_welcome_page(self):
        """Welcome page works"""
        response = self.client.get(reverse("welcome"))

        self.assertContains(
            response, "<h1>Administration software for media files</h1>", html=True
        )
        self.assertContains(response, "Downloadable files")
