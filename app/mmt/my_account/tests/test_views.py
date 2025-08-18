from django.contrib.auth import get_user_model
from django.test import TestCase

User = get_user_model()


class MyAccountViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.bob = User.objects.create_user(
            username="bob", password="password", email="bob@example.com"
        )

    def test_profile_page(self):
        self.client.login(username="bob", password="password")
        response = self.client.get("/account/profile/")

        self.assertContains(response, "<h1>Profile</h1>", html=True)
        self.assertContains(response, "bob", html=True)
        self.assertContains(response, "bob@example.com", html=True)

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
