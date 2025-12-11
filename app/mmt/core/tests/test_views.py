from bs4 import BeautifulSoup
from django.contrib.auth import get_user_model
from django.test import TestCase

from mmt.core.models import Notice

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
        self.assertIn("Log in", hero.get_text())

    def test_welcome_page_logged_in(self):
        self.client.login(username="bob", password="password")
        response = self.client.get("/")
        soup = BeautifulSoup(response.content, "html.parser")

        new_project_link = soup.find(attrs={"data-testid": "new-project-link"})
        self.assertIsNotNone(new_project_link)

    def test_primary_menu(self):
        response = self.client.get("/")

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

    def test_notice_on_welcome_page(self):
        Notice.objects.create(
            title_en="System maintenance",
            title_de="Wartungsarbeiten",
            content_en="The system is being maintained soon.",
            content_de="Es finden bald Wartungsarbeiten statt.",
        )
        response = self.client.get("/")
        soup = BeautifulSoup(response.content, "html.parser")
        notice = soup.find(attrs={"data-testid": "notice"})

        self.assertIsNotNone(notice)
        self.assertIn("System maintenance", notice.get_text())
        self.assertIn("The system is being maintained soon.", notice.get_text())

    def test_notice_not_shown_if_not_active(self):
        Notice.objects.create(
            title_en="System maintenance",
            title_de="Wartungsarbeiten",
            is_active=False,
        )
        response = self.client.get("/")
        soup = BeautifulSoup(response.content, "html.parser")
        notice = soup.find(attrs={"data-testid": "notice"})

        self.assertIsNone(notice)
