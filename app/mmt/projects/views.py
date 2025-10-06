import json
from http import HTTPStatus

from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from django.db import IntegrityError
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from mmt.projects.forms import ProjectForm, UploadForm, ServiceRequestForm
from mmt.projects.models import Project, ServiceRequest
from mmt.projects.tasks import send_new_service_request_email
from mmt.uploaded_files.models import UploadedFile

#
# Views for projects
#


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
    service_requests = project.service_requests.all()
    has_uploaded_files = len(uploaded_files) > 0
    has_service_requests = len(service_requests) > 0

    context = {
        "project": project,
        "uploaded_files": uploaded_files,
        "has_uploaded_files": has_uploaded_files,
        "service_requests": service_requests,
        "has_service_requests": has_service_requests,
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
            project.create_directory()

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
def project_settings(request, pk):
    user = request.user
    project = get_object_or_404(Project, pk=pk, user=user)
    old_project_directory_path = project.directory_path

    if request.method == "POST":
        form = ProjectForm(request.POST, instance=project)
        if form.is_valid():
            form.save()

            if project.directory_path != old_project_directory_path:
                project.rename_directory_from(old_project_directory_path)

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
@permission_required("projects.delete_project")
def project_delete(request, pk):
    user = request.user
    project = get_object_or_404(Project, pk=pk, user=user)
    project.delete_directory()
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

    try:
        uploaded_file = UploadedFile.objects.create(
            project=project,
            filename=filename,
            media_type=content_type,
            size=int(size),
        )

        return JsonResponse(
            {
                "id": uploaded_file.id,
                "filename": uploaded_file.filename,
            },
            status=HTTPStatus.CREATED,
        )
    except IntegrityError:
        return JsonResponse(
            {"message": "Filename already used."},
            status=HTTPStatus.CONFLICT,
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


#
# Service request views
#

@require_http_methods(["GET", "POST"])
@permission_required("projects.add_servicerequest")
def service_request_create(request, pk):
    user = request.user
    project = get_object_or_404(Project, pk=pk, user=user)

    if request.method == "POST":
        form = ServiceRequestForm(request.POST)
        if form.is_valid():
            service_request = form.save(commit=False)
            service_request.project = project
            service_request.save()

            messages.add_message(
                request, messages.SUCCESS, _("Service request created successfully.")
            )
            send_new_service_request_email.delay(service_request.id)

            return redirect("projects:detail", pk=project.id)
        else:
            pass
    else:
        form = ServiceRequestForm()

    context = {"form": form, "project": project}
    return render(request, "projects/service_request_create.html", context)


@require_GET
@permission_required("projects.view_servicerequest")
def service_request_detail(request, project_pk, pk):
    user = request.user
    service_request = get_object_or_404(
        ServiceRequest, pk=pk, project__pk=project_pk, project__user=user
    )
    project = service_request.project

    context = {
        "service_request": service_request,
        "project": project,
    }
    return render(request, "projects/service_request_detail.html", context)
