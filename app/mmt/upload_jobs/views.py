import json
import math

from django.contrib.auth.decorators import permission_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from .forms import UploadJobForm
from .models import UploadJob
from mmt.uploaded_files.constants import UPLOADED_FILE_CHUNK_SIZE
from mmt.uploaded_files.models import UploadedFile


@require_GET
@permission_required("upload_jobs.view_uploadjob")
def index(request):
    upload_jobs = UploadJob.objects.filter(user=request.user).order_by("-created_at")
    context = {"upload_jobs": upload_jobs}
    return render(request, "upload_jobs/upload_job_index.html", context)


@require_GET
@permission_required("upload_jobs.view_uploadjob")
def detail(request, pk):
    upload_job = get_object_or_404(UploadJob, pk=pk, user=request.user)
    uploaded_files = upload_job.uploaded_files.order_by("-created_at")
    context = {"upload_job": upload_job, "uploaded_files": uploaded_files}
    return render(request, "upload_jobs/upload_job_detail.html", context)


@require_GET
@permission_required("upload_jobs.view_uploadjob")
def uploaded_file_detail(request, pk, uploaded_file_pk):
    uploaded_file = get_object_or_404(
        UploadedFile,
        pk=uploaded_file_pk,
        upload_job_id=pk,
        upload_job__user=request.user,
    )
    context = {"uploaded_file": uploaded_file, "upload_job": uploaded_file.upload_job}
    return render(request, "upload_jobs/uploaded_file_detail.html", context)


@require_http_methods(["GET", "POST"])
@permission_required("upload_jobs.add_uploadjob")
def create(request):
    if request.method == "POST":
        json_data = json.loads(request.body)
        form = UploadJobForm(json_data)
        if form.is_valid():
            data = form.cleaned_data
            upload_job = UploadJob.objects.create(
                user=request.user,
                title=data["title"],
                description=data["description"],
                language=data["language"],
                make_available_on_platform=data["make_available_on_platform"],
                transcribe=data["transcribe"],
                check_media_files=data["check_media_files"],
                replace_existing_files=data["replace_existing_files"],
            )
            # Create subdirectory.
            # TODO: All file operations should be in separate functions
            # or methods.
            uploads_directory = request.user.upload_path()
            subdirectory_path = uploads_directory / upload_job.directory_name()
            subdirectory_path.mkdir()

            return JsonResponse({"id": upload_job.pk}, safe=False)
        else:
            return JsonResponse(form.errors, status=400)
    else:
        form = UploadJobForm()
        context = {"form": form}
        return render(request, "upload_jobs/upload_job_create.html", context)


@require_POST
@permission_required("upload_jobs.delete_uploadjob")
def delete(request, pk):
    upload_job = get_object_or_404(UploadJob, pk=pk, user=request.user)
    uploads_directory = request.user.upload_path()
    subdirectory_path = uploads_directory / upload_job.directory_name()
    try:
        for file in subdirectory_path.glob("*"):
            file.unlink()
        subdirectory_path.rmdir()
    except FileNotFoundError:
        print(f"Directory {subdirectory_path} does not exist.")

    upload_job.delete()
    # TODO: Maybe display message.
    return redirect("upload_jobs:index")


@require_POST
@permission_required("uploaded_files.add_uploadedfile")
def create_uploaded_file(request, pk):
    """Register an UploadedFile without uploading data."""
    user = request.user
    upload_job = UploadJob.objects.get(pk=pk)

    if upload_job is None:
        return JsonResponse({"message": "Upload job does not exist."}, status=404)

    if upload_job.user_id != user.id:
        return JsonResponse(
            {"message": "You are not allowed to create a file for this upload job."},
            status=403,
        )

    json_data = json.loads(request.body)
    filename = json_data["filename"]
    content_type = json_data["content_type"]
    size = json_data["size"]

    error = None
    if not filename:
        error = "Filename is required."
    elif not content_type:
        error = "Content_type is required."
    elif not size:
        error = "Size is required."

    if error:
        return JsonResponse({"message": error}, status=400)

    file = UploadedFile.objects.create(
        upload_job=upload_job,
        filename=filename,
        media_type=content_type,
        size=size,
        chunk_count=math.ceil(size / UPLOADED_FILE_CHUNK_SIZE),
    )

    return JsonResponse(
        {
            "id": file.id,
            "upload_job_id": upload_job.id,
            "filename": file.filename,
            "media_type": file.media_type,
            "size": file.size,
            "chunk_count": file.chunk_count,
            "chunks_transferred": file.chunks_transferred,
        },
        status=201,
    )
