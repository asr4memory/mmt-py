from pathlib import Path

from django.shortcuts import render
from django.views.decorators.http import require_GET

from mmt.core.models import Notice

BASE_DIR = Path(__file__).resolve().parent.parent


@require_GET
def welcome(request):
    user = request.user
    if user.is_authenticated:
        project_count = user.projects.count()
    else:
        project_count = 0

    notice = Notice.objects.filter(is_active=True).first()

    context = {'project_count': project_count, 'notice': notice}
    return render(request, 'core/welcome.html', context)
