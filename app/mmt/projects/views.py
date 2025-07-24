import json

from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from mmt.uploaded_files.models import UploadedFile
from .forms import ProjectForm, UploadForm, ProcessingRequestForm
from .models import Project, ProcessingRequest


@require_GET
@permission_required("projects.view_project")
def project_index(request):
    user = request.user
    projects = Project.objects.filter(user=user)
    context = {"projects": projects}
    return render(request, "projects/project_index.html", context)


@require_GET
@permission_required("projects.view_project")
def project_detail(request, pk):
    user = request.user
    project = get_object_or_404(Project, pk=pk, user=user)
    uploaded_files = project.uploaded_files.order_by("-created_at")
    processing_requests = project.processing_requests.all()
    has_uploaded_files = len(uploaded_files) > 0
    has_processing_requests = len(processing_requests) > 0

    context = {
        "project": project,
        "uploaded_files": uploaded_files,
        "has_uploaded_files": has_uploaded_files,
        "processing_requests": processing_requests,
        "has_processing_requests": has_processing_requests,
    }
    return render(request, "projects/project_detail.html", context)


@require_http_methods(["GET", "POST"])
@permission_required("projects.add_project")
def project_create(request):
    user = request.user
    if request.method == "POST":
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            project.user = user
            project.save()

            # Create subdirectory.
            # TODO: All file operations should be in separate functions
            # or methods.
            uploads_directory = request.user.upload_path()
            subdirectory_path = uploads_directory / project.directory_name()
            subdirectory_path.mkdir()

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
@permission_required("projects.change_project")
def project_edit(request, pk):
    user = request.user
    project = get_object_or_404(Project, pk=pk, user=user)
    if request.method == "POST":
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            project.user = user
            project.save()
            messages.add_message(
                request, messages.SUCCESS, _("Project updated successfully.")
            )
            return redirect("projects:detail", pk=project.id)
        else:
            pass
    else:
        form = ProjectForm(instance=project)

    context = {"form": form, "project": project}
    return render(request, "projects/project_edit.html", context)


@require_POST
@permission_required("projects.delete_project")
def project_delete(request, pk):
    user = request.user
    project = get_object_or_404(Project, pk=pk, user=user)

    uploads_directory = request.user.upload_path()
    subdirectory_path = uploads_directory / project.directory_name()
    try:
        for file in subdirectory_path.glob("*"):
            file.unlink()
        subdirectory_path.rmdir()
    except FileNotFoundError:
        print(f"Directory {subdirectory_path} does not exist.")

    project.delete()
    messages.add_message(request, messages.SUCCESS, _("Project deleted successfully."))
    return redirect("projects:index")


@require_GET
@permission_required("uploaded_files.add_uploaded_file")
def upload(request, pk):
    user = request.user
    project = get_object_or_404(Project, pk=pk, user=user)
    form = UploadForm()
    context = {"project": project, "form": form}
    return render(request, "projects/upload_files.html", context)


@require_POST
@permission_required("uploaded_files.add_uploadedfile")
def create_uploaded_file(request, pk):
    user = request.user
    project = get_object_or_404(Project, pk=pk, user=user)

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
        project=project,
        filename=filename,
        media_type=content_type,
        size=size,
    )

    return JsonResponse(
        {
            "id": file.id,
            "filename": file.filename,
        },
        status=201,
    )


@require_GET
@permission_required("projects.view_project")
def uploaded_file_detail(request, pk, uploaded_file_pk):
    uploaded_file = get_object_or_404(
        UploadedFile,
        pk=uploaded_file_pk,
        project_id=pk,
        project__user=request.user,
    )
    context = {"uploaded_file": uploaded_file, "project": uploaded_file.project}
    return render(request, "projects/uploaded_file_detail.html", context)


@require_http_methods(["GET", "POST"])
@permission_required("projects.add_processing_request")
def processing_request_create(request, pk):
    user = request.user
    project = get_object_or_404(Project, pk=pk, user=user)

    if request.method == "POST":
        form = ProcessingRequestForm(request.POST)
        if form.is_valid():
            processing_request = form.save(commit=False)
            processing_request.project = project
            processing_request.save()

            messages.add_message(
                request, messages.SUCCESS, _("Processing request created successfully.")
            )
            return redirect("projects:detail", pk=project.id)
        else:
            pass
    else:
        form = ProcessingRequestForm()

    context = {"form": form, "project": project}
    return render(request, "projects/processing_request_create.html", context)


@require_GET
@permission_required("projects.view_processing_request")
def processing_request_detail(request, project_pk, pk):
    user = request.user
    processing_request = get_object_or_404(ProcessingRequest, pk=pk, project__pk=project_pk, project__user=user)
    project = processing_request.project

    context = {
        "processing_request": processing_request,
        "project": project,
    }
    return render(request, "projects/processing_request_detail.html", context)
