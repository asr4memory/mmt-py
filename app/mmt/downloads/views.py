import logging
import os
import threading

import aiofiles
from django.contrib.auth.decorators import login_required
from django.http import (
    StreamingHttpResponse,
    HttpResponseServerError,
    HttpResponseNotFound,
    HttpResponse,
)
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_http_methods

from .files import get_files_with_info

logger = logging.getLogger(__name__)


def debug(msg):
    logger.info(msg)
    print(msg)


@require_GET
@login_required
def download_index(request):
    user = request.user
    downloads_directory = user.download_path()
    try:
        files_with_info = get_files_with_info(downloads_directory)
    except FileNotFoundError:
        return HttpResponseServerError(
            "Downloads directory does not exist for the user."
        )

    context = {"files": files_with_info}

    return render(request, "downloads/download_index.html", context)


@require_http_methods(["GET", "DELETE"])
@login_required
def download_detail(request, filename):
    user = request.user
    downloads_directory = user.download_path()
    file_path = downloads_directory / filename

    if not file_path.is_file():
        return HttpResponseNotFound("File does not exist.")

    if request.method == "GET":
        # Download the file
        debug(f"Requested {filename} which stats {os.stat(file_path)=}.")

        response = StreamingHttpResponse(
            file_data(file_path), content_type="application/octet-stream"
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
    elif request.method == "DELETE":
        # Delete the file
        file_path.unlink()

        return HttpResponse(status=200)


async def file_data(file_path, chunk_size=65536):
    debug(f"Current threads are {threading.active_count()} opening file {file_path}.")
    async with aiofiles.open(file_path, mode="rb") as f:
        teller = 0
        while chunk := await f.read(chunk_size):
            teller += 1
            if teller % 1000 == 0:
                debug(
                    f"Current threads are {threading.active_count()} yielding chunk nr.{teller}."
                )
            yield chunk
