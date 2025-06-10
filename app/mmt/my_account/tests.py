from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from .forms import validate_username

User = get_user_model()


class ValidateUsernameTestCase(TestCase):
    def test_too_long(self):
        """Raises if username is too long"""
        self.assertRaisesMessage(
            ValidationError,
            "hello_this_is_a_nice_username is too long",
            validate_username,
            "hello_this_is_a_nice_username",
        )

    def test_too_short(self):
        """Raises if username is too short"""
        self.assertRaisesMessage(
            ValidationError, "mac is too short", validate_username, "mac"
        )

    def test_incorrect_format(self):
        """Raises if username has an incorrect format"""
        message = "does not have the right format"
        self.assertRaisesMessage(
            ValidationError, message, validate_username, "max headroom"
        )
        self.assertRaisesMessage(
            ValidationError, message, validate_username, "Max Headroom"
        )
        self.assertRaisesMessage(
            ValidationError, message, validate_username, "max2 head"
        )
        self.assertRaisesMessage(
            ValidationError, message, validate_username, "max head."
        )

    def test_correct_format(self):
        """Does not raise if username has correct format"""
        self.assertIsNone(validate_username("exa_alice"))


class ProfileTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Set up data for the whole TestCase
        cls.alice = User.objects.create_user(
            username="alice", password="password", email="alice@example.com"
        )
        cls.alice.create_profile()

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
