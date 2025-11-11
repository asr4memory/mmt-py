import aiofiles
from datetime import datetime
import json
from http import HTTPStatus

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.http import (
    JsonResponse,
    HttpResponseNotFound,
    StreamingHttpResponse,
)
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from mmt.projects.forms import ProjectForm, UploadForm, ProcessingRequestForm
from mmt.projects.models import Project, ProcessingRequest
from mmt.projects.tasks import send_new_processing_request_email
from mmt.projects.utils import (
    FileInfo,
    get_dir_contents,
    get_files_with_info,
    get_filename_suffix,
)
from mmt.uploaded_files.models import UploadedFile


#
# Views for projects
#
@require_GET
@login_required
def project_index(request):
    user = request.user
    projects = Project.objects.filter(user=user)
    context = {"projects": projects}
    return render(request, "projects/project_index.html", context)


@require_GET
@login_required
def project_detail(request, pk):
    user = request.user
    project = get_object_or_404(Project, pk=pk, user=user)
    uploaded_files = project.uploaded_files.order_by("-created_at")
    processing_requests = project.processing_requests.all()
    has_uploaded_files = len(uploaded_files) > 0
    has_processing_requests = len(processing_requests) > 0
    show_processing_request_section = has_uploaded_files or has_processing_requests

    files_with_info = get_files_with_info(project.download_directory)
    project.downloadable_files_count = len(files_with_info)
    project.save()

    context = {
        "project": project,
        "uploaded_files": uploaded_files,
        "has_uploaded_files": has_uploaded_files,
        "processing_requests": processing_requests,
        "has_processing_requests": has_processing_requests,
        "show_processing_request_section": show_processing_request_section,
        "downloads": files_with_info,
    }
    return render(request, "projects/project_detail.html", context)


@require_http_methods(["GET", "POST"])
@login_required
def project_create(request):
    user = request.user
    if request.method == "POST":
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            project.user = user
            project.save()
            project.make_project_directories()

            messages.add_message(
                request, messages.SUCCESS, _("Project created successfully.")
            )
            return redirect("projects:detail", pk=project.id)
        else:
            pass
    else:
        form = ProjectForm()

    context = {"form": form}
    return render(request, "projects/project_create.html", context)


@require_http_methods(["GET", "POST"])
@login_required
def project_settings(request, pk):
    user = request.user
    project = get_object_or_404(Project, pk=pk, user=user)
    old_project_directory = project.project_directory

    if request.method == "POST":
        form = ProjectForm(request.POST, instance=project)
        if form.is_valid():
            form.save()

            if project.project_directory != old_project_directory:
                project.rename_directory_from(old_project_directory)

            messages.add_message(
                request, messages.SUCCESS, _("Project updated successfully.")
            )
            return redirect("projects:detail", pk=project.id)
        else:
            pass
    else:
        form = ProjectForm(instance=project)

    context = {"form": form, "project": project}
    return render(request, "projects/project_settings.html", context)


@require_POST
@login_required
def project_delete(request, pk):
    user = request.user
    project = get_object_or_404(Project, pk=pk, user=user)
    project.remove_project_directories()
    project.delete()
    messages.add_message(request, messages.SUCCESS, _("Project deleted successfully."))
    return redirect("projects:index")


#
# Views for uploaded files
#


@require_GET
@permission_required("uploaded_files.add_uploadedfile")
def upload(request, pk):
    user = request.user
    project = get_object_or_404(Project, pk=pk, user=user)
    form = UploadForm()
    context = {"project": project, "form": form}
    return render(request, "projects/upload_files.html", context)


@require_POST
@permission_required("uploaded_files.add_uploadedfile", raise_exception=True)
def create_uploaded_file(request, pk):
    user = request.user
    project = get_object_or_404(Project, pk=pk, user=user)
    json_data = json.loads(request.body)

    # Error handling
    error = None
    if "filename" not in json_data:
        error = "Filename is required"
    elif "content_type" not in json_data:
        error = "Content_type is required"
    elif "size" not in json_data:
        error = "Size is required"

    if error:
        return JsonResponse({"message": error}, status=HTTPStatus.BAD_REQUEST)

    # Success path
    filename = json_data["filename"]
    content_type = json_data["content_type"]
    size = json_data["size"]

    # TODO
    # sanitized_filename = sanitize(filename)

    uploaded_file = UploadedFile(
        project=project,
        filename=filename,
        media_type=content_type,
        size=int(size),
    )

    if UploadedFile.objects.filter(project=project, filename=filename).exists():
        extension = get_filename_suffix(timezone.now())
        uploaded_file.filename = f"{filename}.{extension}"

    uploaded_file.save()

    return JsonResponse(
        {
            "id": uploaded_file.id,
            "filename": uploaded_file.filename,
        },
        status=HTTPStatus.CREATED,
    )


@require_GET
@permission_required("uploaded_files.view_uploadedfile")
def uploaded_file_detail(request, project_pk, uploaded_file_pk):
    uploaded_file = get_object_or_404(
        UploadedFile,
        pk=uploaded_file_pk,
        project_id=project_pk,
        project__user=request.user,
    )
    uploaded_file.update_has_file_field()

    context = {"uploaded_file": uploaded_file, "project": uploaded_file.project}
    return render(request, "projects/uploaded_file_detail.html", context)


@require_GET
@permission_required("uploaded_files.view_uploadedfile")
def uploaded_file_download(request, project_pk, uploaded_file_pk):
    uploaded_file = get_object_or_404(
        UploadedFile,
        pk=uploaded_file_pk,
        project_id=project_pk,
        project__user=request.user,
    )
    file_path = uploaded_file.file_path

    if not file_path.is_file():
        return HttpResponseNotFound("File does not exist.")

    response = StreamingHttpResponse(
        file_data(file_path), content_type="application/octet-stream"
    )
    response["Content-Disposition"] = f'attachment; filename="{uploaded_file.filename}"'
    return response


#
# Processing request views
#
@require_http_methods(["GET", "POST"])
@permission_required("projects.add_processingrequest")
def processing_request_create(request, pk):
    user = request.user
    project = get_object_or_404(Project, pk=pk, user=user)

    if request.method == "POST":
        processing_request = ProcessingRequest(project=project)
        form = ProcessingRequestForm(data=request.POST, instance=processing_request)

        if form.is_valid():
            processing_request = form.save(commit=False)
            processing_request.project = project
            processing_request.uploaded_files = request.POST.getlist("uploaded_files")
            processing_request.save()

            messages.add_message(
                request, messages.SUCCESS, _("Processing request created successfully.")
            )
            send_new_processing_request_email.delay(processing_request.id)

            return redirect("projects:detail", pk=project.id)
        else:
            pass
    else:
        processing_request = ProcessingRequest(project=project)
        form = ProcessingRequestForm(instance=processing_request)

    context = {"form": form, "project": project}
    return render(request, "projects/processing_request_create.html", context)


@require_GET
@permission_required("projects.view_processingrequest")
def processing_request_detail(request, project_pk, pk):
    user = request.user
    processing_request = get_object_or_404(
        ProcessingRequest, pk=pk, project__pk=project_pk, project__user=user
    )
    project = processing_request.project

    context = {
        "processing_request": processing_request,
        "project": project,
        "uploaded_files_str": ", ".join(processing_request.uploaded_files),
    }
    return render(request, "projects/processing_request_detail.html", context)


#
# Downloads
#
@require_http_methods(["GET", "POST"])
@login_required
def download_detail(request, pk, filename):
    user = request.user
    project = get_object_or_404(Project, pk=pk, user=user)
    download_directory = project.download_directory
    file_path = download_directory / filename

    if not file_path.is_file():
        return HttpResponseNotFound("File does not exist.")

    if request.method == "GET":
        file_info = FileInfo(file_path)
        context = {
            "project": project,
            "file_info": file_info,
        }
        return render(request, "projects/download_detail.html", context)
    elif request.method == "POST":
        # Delete the file
        file_path.unlink()
        files = get_dir_contents(project.download_directory)
        project.downloadable_files_count = len(files)
        project.save()

        return redirect("projects:detail", pk=project.id)


@require_GET
@login_required
def download_download(request, pk, filename):
    user = request.user
    project = get_object_or_404(Project, pk=pk, user=user)
    download_directory = project.download_directory
    file_path = download_directory / filename

    if not file_path.is_file():
        return HttpResponseNotFound("File does not exist.")

    response = StreamingHttpResponse(
        file_data(file_path), content_type="application/octet-stream"
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


async def file_data(file_path, chunk_size=65536):
    async with aiofiles.open(file_path, mode="rb") as f:
        teller = 0
        while chunk := await f.read(chunk_size):
            teller += 1
            if teller % 1000 == 0:
                pass
            yield chunk
