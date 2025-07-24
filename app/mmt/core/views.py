from pathlib import Path

from django.conf import settings
from django.http import HttpResponseServerError
from django.shortcuts import render
from django.views.decorators.http import require_GET

from mmt.downloads.files import get_files_with_info

BASE_DIR = Path(__file__).resolve().parent.parent


@require_GET
def welcome(request):
    user = request.user
    if user.is_authenticated:
        downloads_directory = user.download_path()
        try:
            files_with_info = get_files_with_info(downloads_directory)
        except FileNotFoundError:
            user.create_user_directories()
            files_with_info = get_files_with_info(downloads_directory)

        project_count = user.projects.count()
        download_job_count = len(files_with_info)
    else:
        project_count = 0
        download_job_count = 0

    context = {
        "project_count": project_count,
        "download_file_count": download_job_count,
        "app_version": settings.MMT_APP_VERSION,
    }
    return render(request, "core/welcome.html", context)
