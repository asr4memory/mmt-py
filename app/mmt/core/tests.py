from http import HTTPStatus

from django.conf import settings
from django.contrib.auth import get_user_model
from mmt.test import TestCase
from django.urls import reverse

User = get_user_model()


#class LogoutTests(TestCase):
#    def test_log_out_clears_all_site_data(self):
#        response = self.client.post("/log-out/")
#        self.assertEqual(response.status_code, self.assertClearSiteData(response))


class CoreTests(TestCase):
    def test_primary_menu(self):
        """Primary menu shows the right amount of links when logged out."""
        response = self.client.get(reverse("welcome"))

        self.assertContains(response, "Downloads")
        self.assertContains(response, "Log in")
        self.assertContains(response, "Register")

    def test_fail_fast_for_missing_download_dir(self):
        """Fails fast if download directory is missing"""
        user = User.objects.create_user(username="alice", password="password")
        user.destroy_user_directories()
        self.client.login(username="alice", password="password")

        response = self.client.get(reverse("welcome"))

        self.assertEqual(response.status_code, HTTPStatus.INTERNAL_SERVER_ERROR)
        self.assertEqual(
            response.text, "Downloads directory does not exist for the user."
        )

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
