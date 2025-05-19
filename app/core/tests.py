from django.test import TestCase
from django.urls import reverse


class CoreTests(TestCase):
    def test_primary_menu(self):
        """Primary menu shows the right amount of links when logged out."""
        response = self.client.get(reverse("welcome"), follow=True)

        self.assertContains(response, "Downloads")
        self.assertContains(response, "Log in")
        self.assertContains(response, "Register")


    def test_welcome_page(self):
        """Welcome page works"""
        response = self.client.get(reverse("welcome"), follow=True)

        self.assertContains(
            response, "<h1>Administration software for media files</h1>", html=True
        )
        self.assertContains(response, "Downloadable files")
