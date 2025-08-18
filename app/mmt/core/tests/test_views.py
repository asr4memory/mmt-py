from bs4 import BeautifulSoup
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import TestCase

from mmt.core.views import welcome

User = get_user_model()


class CoreViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.alice = User.objects.create_superuser(
            username="alice", password="password", email="alice@example.com"
        )
        cls.bob = User.objects.create_user(
            username="bob", password="password", email="bob@example.com"
        )


    def test_welcome_page(self):
        response = self.client.get("/")
        soup = BeautifulSoup(response.content, "html.parser")
        hero = soup.find(attrs={"data-testid": "hero"})

        self.assertIsNotNone(hero)
        self.assertIn("Media Management Tool", hero.get_text())
        self.assertIn("Downloadable files", hero.get_text())


    def test_primary_menu(self):
        response = self.client.get("/")

        self.assertContains(response, "Downloads")
        self.assertContains(response, "Log in")
        self.assertContains(response, "Register")


    def test_user_logged_in_primary_menu(self):
        self.client.login(username="bob", password="password")
        response = self.client.get("/")

        soup = BeautifulSoup(response.content, "html.parser")
        header = soup.find("header")

        self.assertIsNotNone(header)
        self.assertIn("Log out", header.get_text())
        self.assertNotIn("Admin", header.get_text())


    def test_admin_logged_in_primary_menu(self):
        self.client.login(username="alice", password="password")
        response = self.client.get("/")

        soup = BeautifulSoup(response.content, "html.parser")
        header = soup.find("header")

        self.assertIsNotNone(header)
        self.assertIn("Admin", header.get_text())
        self.assertIn("Log out", header.get_text())
