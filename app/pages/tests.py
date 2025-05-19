from django.test import TestCase
from django.urls import reverse


class PagesTests(TestCase):
    def test_privacy_page(self):
        """Privacy page works"""
        response = self.client.get(reverse("pages:privacy"), follow=True)

        self.assertContains(response, "<h1>Privacy</h1>", html=True)

    def test_terms_page(self):
        """Terms page works"""
        response = self.client.get(reverse("pages:terms"), follow=True)

        self.assertContains(response, "<h1>Terms of Use</h1>", html=True)

    def test_accessibility_page(self):
        """Accessibility page works"""
        response = self.client.get(reverse("pages:accessibility"), follow=True)

        self.assertContains(response, "<h1>Accessibility</h1>", html=True)

    def test_contact_page(self):
        """Contact page works"""
        response = self.client.get(reverse("pages:contact"), follow=True)

        self.assertContains(response, "<h1>Contact</h1>", html=True)

    def test_legal_notice_page(self):
        """Legal notice page works"""
        response = self.client.get(reverse("pages:legal_notice"), follow=True)

        self.assertContains(response, "<h1>Legal Notice</h1>", html=True)
