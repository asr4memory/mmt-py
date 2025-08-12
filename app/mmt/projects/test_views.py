import pytest
from bs4 import BeautifulSoup
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from pytest_django.asserts import assertContains

from .models import Project
from .views import project_detail

User = get_user_model()


@pytest.mark.django_db
def test_detail_page(rf):
    bob = User.objects.create_user(
        username="bob", password="password", email="bob@example.com"
    )
    project = Project.objects.create(user=bob, name="Test")

    request = rf.get(f"/projects/{project.id}/")
    request.user = bob
    response = project_detail(request)
    breakpoint()
    soup = BeautifulSoup(response.content, "html.parser")
    project_name = soup.find(attrs={"data-testid": "project-name"})

    assert project_name is not None
    assert "Test" in project_name.get_text()
