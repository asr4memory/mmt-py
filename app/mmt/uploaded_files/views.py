import json
from http import HTTPStatus
import os
from pathlib import Path

import aiofiles
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from django.http import JsonResponse
from django.shortcuts import redirect, get_object_or_404
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from .models import UploadedFile
from .tasks import calculate_server_checksum


@require_POST
@permission_required("uploaded_files.add_uploadedfile")
async def upload(request, pk):
    uploaded_file = await UploadedFile.objects.select_related("project").aget(pk=pk)
    project = uploaded_file.project

    user = await request.auser()
    if project.user_id != user.id:
        return JsonResponse(
            {"message": "You are not allowed to upload this file."}, status=403
        )

    # Tempfile handling
    temp_file = settings.MMT_USER_FILES_DIR / str(pk)
    is_file = os.path.isfile(temp_file)

    # No tempfile at all.
    if not is_file:
        return JsonResponse({"success": False}, status=HTTPStatus.BAD_REQUEST)

    # Move file to its final position.
    actual_file_size = os.path.getsize(temp_file)
    uploaded_file.transferred = actual_file_size
    uploaded_file.has_file = True
    await uploaded_file.asave()

    file_path = await uploaded_file.afile_path
    os.rename(temp_file, file_path)

    if uploaded_file.is_complete:
        calculate_server_checksum.delay(pk)
        return JsonResponse({"success": True})
    else:
        return JsonResponse({"success": False})


@require_POST
@permission_required("uploaded_files.change_uploadedfile", raise_exception=True)
def update(request, pk):
    user = request.user
    uploaded_file = get_object_or_404(UploadedFile, pk=pk, project__user_id=user.id)
    project = uploaded_file.project
    if project.user_id != request.user.id:
        return JsonResponse(
            {"message": "You are not allowed to update this file."}, status=403
        )

    json_data = json.loads(request.body)
    checksum_client = json_data.get("checksum_client")

    if not checksum_client:
        return JsonResponse({"message": "checksum_client is required."}, status=400)

    uploaded_file.checksum_client = checksum_client
    uploaded_file.save()

    return JsonResponse({"message": "Uploaded file updated successfully."}, status=200)


@require_POST
@permission_required("uploaded_files.delete_uploadedfile")
def delete(request, pk):
    user = request.user
    uploaded_file = get_object_or_404(UploadedFile, pk=pk, project__user_id=user.id)
    project = uploaded_file.project

    uploaded_file.delete_file()
    uploaded_file.delete()
    messages.add_message(
        request, messages.SUCCESS, _("Uploaded file deleted successfully.")
    )

    return redirect("projects:detail", pk=project.id)
