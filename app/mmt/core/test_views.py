import pytest
from bs4 import BeautifulSoup
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from pytest_django.asserts import assertContains

from .views import welcome

User = get_user_model()


def test_welcome_page(rf):
    request = rf.get("/")
    request.user = AnonymousUser()
    response = welcome(request)
    assert response.status_code == 200

    soup = BeautifulSoup(response.content, "html.parser")
    hero = soup.find(attrs={"data-testid": "hero"})

    assert hero is not None
    assert "Media Management Tool" in hero.get_text()
    assert "Downloadable files" in hero.get_text()


def test_primary_menu(rf):
    request = rf.get("/")
    request.user = AnonymousUser()
    response = welcome(request)

    assertContains(response, "Downloads")
    assertContains(response, "Log in")
    assertContains(response, "Register")


@pytest.mark.django_db
def test_user_logged_in_primary_menu(rf):
    bob = User.objects.create_user(
        username="bob", password="password", email="bob@example.com"
    )
    request = rf.get("/")
    request.user = bob
    response = welcome(request)

    soup = BeautifulSoup(response.content, "html.parser")
    header = soup.find("header")
    assert header is not None

    assert "Log out" in header.get_text()
    assert "Admin" not in header.get_text()


@pytest.mark.django_db
def test_admin_logged_in_primary_menu(rf):
    alice = User.objects.create_superuser(
        username="alice", password="password", email="alice@example.com"
    )
    request = rf.get("/")
    request.user = alice
    response = welcome(request)

    soup = BeautifulSoup(response.content, "html.parser")
    header = soup.find("header")
    assert header is not None
    assert "Admin" in header.get_text()
    assert "Log out" in header.get_text()
