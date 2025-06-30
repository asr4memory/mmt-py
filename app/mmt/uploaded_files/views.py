from http import HTTPStatus
import json

import aiofiles
from django.conf import settings
from django.contrib.auth.decorators import permission_required
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_POST

from .models import UploadedFile
from .tasks import calculate_server_checksum, send_file_uploaded_emails


@require_POST
@permission_required("uploaded_files.add_uploadedfile")
async def upload(request, pk):
    """Upload the actual file data for an UploadedFile."""
    uploaded_file = await UploadedFile.objects.select_related("upload_job").aget(pk=pk)
    upload_job = uploaded_file.upload_job

    user = await request.auser()
    if upload_job.user_id != user.id:
        return JsonResponse(
            {"message": "You are not allowed to upload this file."},
            status=HTTPStatus.FORBIDDEN,
        )

    # User#upload_path does not work with async.
    upload_path = settings.BASE_DIR / "user_files" / user.username / "uploads"
    file_path = upload_path / upload_job.directory_name() / uploaded_file.filename

    file = request.FILES["file"]
    await handle_uploaded_file(file, file_path)

    send_file_uploaded_emails.delay(user.id, uploaded_file.filename)
    calculate_server_checksum.delay(pk)

    return JsonResponse({"success": True})


async def handle_uploaded_file(file, file_path):
    async with aiofiles.open(file_path, "wb") as f:
        for chunk in file.chunks():
            await f.write(chunk)


@require_POST
@permission_required("uploaded_files.change_uploadedfile")
def update(request, pk):
    """Update an UploadedFile with its client checksum."""
    uploaded_file = UploadedFile.objects.select_related("upload_job").get(pk=pk)
    upload_job = uploaded_file.upload_job
    if upload_job.user_id != request.user.id:
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
    """Delete an UploadedFile."""
    user = request.user
    uploaded_file = UploadedFile.objects.select_related("upload_job").get(
        pk=pk, upload_job__user_id=user.id
    )
    upload_job = uploaded_file.upload_job
    uploaded_file.delete()

    # Remove actual file.
    uploads_directory = user.upload_path()
    file_path = uploads_directory / upload_job.directory_name() / uploaded_file.filename
    try:
        file_path.unlink()
    except FileNotFoundError:
        print(f"File {uploaded_file.filename} does not exist.")

    return HttpResponse(status=200)


@require_POST
@permission_required("uploaded_files.add_uploadedfile")
def upload_chunk(request, pk, chunk):
    """Upload a chunk of file data of an UploadedFile."""
    uploaded_file = UploadedFile.objects.select_related("upload_job").get(pk=pk)
    upload_job = uploaded_file.upload_job
    user = request.user
    expected_chunk = uploaded_file.chunks_transferred

    if upload_job.user_id != user.id:
        return JsonResponse(
            {"message": "You are not allowed to upload this file."},
            status=HTTPStatus.FORBIDDEN,
        )

    if uploaded_file.status not in [
        uploaded_file.UploadStatus.CREATED,
        uploaded_file.UploadStatus.UPLOADING,
    ]:
        return JsonResponse(
            {
                "message": f"Wrong status. You cannot upload chunks for files with {uploaded_file.status} status."
            },
            status=HTTPStatus.CONFLICT,
        )

    if uploaded_file.chunk_count == uploaded_file.chunks_transferred:
        return JsonResponse(
            {"message": "All chunks for the file have already been uploaded."},
            status=HTTPStatus.GONE,
        )

    if chunk != expected_chunk:
        return JsonResponse(
            {
                "message": f"Unexpected chunk number. Expected: {expected_chunk}, received: {chunk}.",
                "expected_chunk": expected_chunk,
                "status": "conflict",
            },
            status=HTTPStatus.CONFLICT,
        )

    upload_path = user.upload_path()
    file_path = upload_path / upload_job.directory_name() / uploaded_file.filename

    with open(file_path, "ab") as f:
        f.write(request.body)

    # This whole view function does not handle race conditions well.
    uploaded_file.chunks_transferred += 1

    # Update status
    if uploaded_file.chunks_transferred == 1:
        uploaded_file.status = uploaded_file.UploadStatus.UPLOADING
    # Deliberately no elif; file could have just one chunk
    if uploaded_file.chunks_transferred == uploaded_file.chunk_count:
        uploaded_file.status = uploaded_file.UploadStatus.COMPLETE
    uploaded_file.save()

    if uploaded_file.status == uploaded_file.UploadStatus.COMPLETE:
        # Do this if the whole file has been uploaded.
        send_file_uploaded_emails.delay(user.id, uploaded_file.filename)
        calculate_server_checksum.delay(pk)
        return JsonResponse(
            {
                "success": True,
                "complete": True,
                "next_chunk": None,
            }
        )
    else:
        return JsonResponse(
            {
                "success": True,
                "complete": False,
                "next_chunk": expected_chunk + 1,
            }
        )
