import pytest
from bs4 import BeautifulSoup
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from pytest_django.asserts import assertContains

from .views import edit_profile, profile

User = get_user_model()


@pytest.mark.django_db
def test_profile_page(rf):
    request = rf.get("/profile/")
    user = User.objects.create_user(
        username="bob", password="password", email="bob@example.com"
    )
    request.user = user
    response = profile(request)

    assertContains(response, "<h1>Profile</h1>", html=True)
    assertContains(response, "bob", html=True)
    assertContains(response, "bob@example.com", html=True)


@pytest.mark.django_db
def test_edit_profile_page(rf):
    request = rf.get("/profile/edit/")
    user = User.objects.create_user(
        username="bob", password="password", email="bob@example.com"
    )
    request.user = user
    response = edit_profile(request)

    assertContains(response, "<h1>Edit profile</h1>", html=True)
