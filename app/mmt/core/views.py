from pathlib import Path

from django.conf import settings
from django.shortcuts import render
from django.views.decorators.http import require_GET

BASE_DIR = Path(__file__).resolve().parent.parent


@require_GET
def welcome(request):
    user = request.user
    if user.is_authenticated:
        project_count = user.projects.count()
    else:
        project_count = 0

    context = {
        "project_count": project_count,
        "app_version": settings.MMT_APP_VERSION,
    }
    return render(request, "core/welcome.html", context)
