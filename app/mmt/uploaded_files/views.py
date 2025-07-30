import json
from http import HTTPStatus

import aiofiles
from django.conf import settings
from django.contrib.auth.decorators import permission_required
from django.http import JsonResponse
from django.shortcuts import redirect
from django.views.decorators.http import require_POST

from .models import UploadedFile
from .tasks import calculate_server_checksum, send_file_uploaded_emails


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

    # User#upload_path does not work with async.
    upload_path = settings.BASE_DIR / "user_files" / user.username / "uploads"
    file_path = upload_path / project.directory_name / uploaded_file.filename

    if "file" in request.FILES:
        file = request.FILES["file"]
        await handle_uploaded_file(file, file_path)
        uploaded_file.transferred = file.size
        uploaded_file.status = uploaded_file.UploadStatus.COMPLETE
        await uploaded_file.asave()
        send_file_uploaded_emails.delay(user.id, uploaded_file.filename)
        calculate_server_checksum.delay(pk)
        return JsonResponse({"success": True})
    else:
        uploaded_file.status = uploaded_file.UploadStatus.MISSING
        await uploaded_file.asave()
        return JsonResponse({"success": False}, status=HTTPStatus.BAD_REQUEST)


async def handle_uploaded_file(file, file_path):
    async with aiofiles.open(file_path, "wb") as f:
        for chunk in file.chunks():
            await f.write(chunk)


@require_POST
@permission_required("uploaded_files.change_uploadedfile")
def update(request, pk):
    uploaded_file = UploadedFile.objects.select_related("project").get(pk=pk)
    project = uploaded_file.project
    if project.user_id != request.user.id:
        return JsonResponse(
            {"message": "You are not allowed to update this file."}, status=403
        )

    json_data = json.loads(request.body)
    checksum_client = json_data["checksum_client"]

    if not checksum_client:
        return JsonResponse({"message": "checksum_client is required."}, status=400)

    uploaded_file.checksum_client = checksum_client
    uploaded_file.save()

    return JsonResponse({"message": "Upload successfully updated."}, status=200)


@require_POST
@permission_required("uploaded_files.delete_uploadedfile")
def delete(request, pk):
    user = request.user
    uploaded_file = UploadedFile.objects.select_related("project").get(
        pk=pk, project__user_id=user.id
    )
    project = uploaded_file.project
    uploaded_file.delete()

    # Remove actual file.
    uploads_directory = user.upload_path
    file_path = uploads_directory / project.directory_name / uploaded_file.filename
    try:
        file_path.unlink()
    except FileNotFoundError:
        print(f"File {uploaded_file.filename} does not exist.")

    return redirect("projects:detail", pk=project.id)
