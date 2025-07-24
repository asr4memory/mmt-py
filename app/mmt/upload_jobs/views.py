import json

from django.contrib.auth.decorators import permission_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from mmt.uploaded_files.models import UploadedFile

from .forms import UploadJobForm
from .models import UploadJob


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

            return JsonResponse({"id": upload_job.pk}, safe=False)
        else:
            return JsonResponse(form.errors, status=400)
    else:
        form = UploadJobForm()
        context = {"form": form}
        return render(request, "upload_jobs/upload_job_create.html", context)
