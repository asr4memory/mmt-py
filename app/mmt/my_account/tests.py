from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


User = get_user_model()


class ProfileTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Set up data for the whole TestCase
        cls.alice = User.objects.create_user(
            username="alice", password="password", email="alice@example.com"
        )

    def test_profile_page(self):
        """Returns profile page when logged in"""
        self.client.login(username="alice", password="password")

        response = self.client.get(reverse("account:profile"))

        self.assertContains(response, "<h1>Profile</h1>", html=True)
        self.assertContains(response, "alice", html=True)
        self.assertContains(response, "alice@example.com", html=True)

    def test_edit_profile_page(self):
        """Returns edit profile page when logged in"""
        self.client.login(username="alice", password="password")

        response = self.client.get(reverse("account:edit_profile"))

        self.assertContains(response, "<h1>Edit profile</h1>", html=True)


class RegistrationTests(TestCase):
    def test_registration_page(self):
        """Returns registration form page"""
        response = self.client.get(reverse("account:register"))

        self.assertContains(response, "<h1>Register</h1>", html=True)
