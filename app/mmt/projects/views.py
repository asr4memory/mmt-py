import json
from http import HTTPStatus

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.http import (
    HttpResponseNotFound,
    JsonResponse,
    HttpResponseServerError,
    StreamingHttpResponse,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.text import get_valid_filename
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from mmt.core.utils import file_data
from mmt.projects.forms import (
    ProcessingRequestForm,
    ProjectForm,
    UploadedFileForm,
    UploadForm,
)
from mmt.projects.models import ProcessingRequest, Project
from mmt.projects.tasks import send_new_processing_request_email
from mmt.projects.use_cases import create_project, update_project, delete_project
from mmt.projects.utils import (
    FileInfo,
    get_dir_contents,
    get_filename_suffix,
    get_files_with_info,
)
from mmt.my_account.models import Profile
from mmt.uploaded_files.models import CHUNK_SIZE, UploadedFile


#
# Views for projects
#
@require_GET
@login_required
def project_index(request):
    user = request.user
    projects = Project.objects.filter(user=user)
    context = {'projects': projects}
    return render(request, 'projects/project_index.html', context)


@require_GET
@login_required
def project_detail(request, pk):
    user = request.user
    project = get_object_or_404(Project, pk=pk, user=user)
    uploaded_files = project.uploaded_files.order_by('-created_at')
    processing_requests = project.processing_requests.all()
    has_uploaded_files = uploaded_files.exists()
    has_processing_requests = processing_requests.exists()
    show_processing_request_section = has_uploaded_files or has_processing_requests

    files_with_info = get_files_with_info(project.download_directory)
    project.downloadable_files_count = len(files_with_info)
    project.save()

    context = {
        'project': project,
        'uploaded_files': uploaded_files,
        'has_uploaded_files': has_uploaded_files,
        'processing_requests': processing_requests,
        'has_processing_requests': has_processing_requests,
        'show_processing_request_section': show_processing_request_section,
        'downloads': files_with_info,
    }
    return render(request, 'projects/project_detail.html', context)


@require_http_methods(['GET', 'POST'])
@login_required
def project_create(request):
    user = request.user
    if request.method == 'POST':
        form = ProjectForm(request.POST)
        success, project = create_project(
            title=form.data['title'], description=form.data['description'], user=user
        )

        if success:
            messages.add_message(
                request, messages.SUCCESS, _('Project created successfully.')
            )
            return redirect('projects:detail', pk=project.id)
        else:
            pass
    else:
        form = ProjectForm()

    context = {'form': form}
    return render(request, 'projects/project_create.html', context)


@require_http_methods(['GET', 'POST'])
@login_required
def project_settings(request, pk):
    user = request.user
    project = get_object_or_404(Project, pk=pk, user=user)

    if request.method == 'POST':
        form = ProjectForm(request.POST, instance=project)
        success = update_project(
            project=project,
            title=form.data['title'],
            description=form.data['description'],
        )

        if success:
            messages.add_message(
                request, messages.SUCCESS, _('Project updated successfully.')
            )
            return redirect('projects:detail', pk=project.id)
        else:
            messages.add_message(request, messages.WARNING, _('Project update failed.'))

    else:
        form = ProjectForm(instance=project)

    context = {'form': form, 'project': project}
    return render(request, 'projects/project_settings.html', context)


@require_POST
@login_required
def project_delete(request, pk):
    user = request.user
    project = get_object_or_404(Project, pk=pk, user=user)

    if delete_project(project):
        messages.add_message(
            request, messages.SUCCESS, _('Project deleted successfully.')
        )
        return redirect('projects:index')
    else:
        return HttpResponseServerError(_('Could not delete project.'))


#
# Views for uploaded files
#
@require_GET
@permission_required('uploaded_files.add_uploadedfile')
def upload(request, pk):
    user = request.user
    project = get_object_or_404(Project, pk=pk, user=user)
    form = UploadForm()
    chunked_upload = user.safe_profile.is_flag_enabled(Profile.CHUNKED_UPLOAD)
    context = {'project': project, 'form': form, 'chunked_upload': chunked_upload}
    return render(request, 'projects/upload_files.html', context)


@require_POST
@permission_required('uploaded_files.add_uploadedfile', raise_exception=True)
def create_uploaded_file(request, pk):
    user = request.user
    project = get_object_or_404(Project, pk=pk, user=user)
    try:
        json_data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'message': 'Invalid JSON'}, status=HTTPStatus.BAD_REQUEST)

    form = UploadedFileForm(json_data)
    if not form.is_valid():
        return JsonResponse({'errors': form.errors}, status=HTTPStatus.BAD_REQUEST)

    filename = form.cleaned_data['filename']
    final_filename = get_valid_filename(filename)

    if UploadedFile.objects.filter(project=project, filename=final_filename).exists():
        extension = get_filename_suffix(timezone.now())
        final_filename = f'{final_filename}.{extension}'

    uploaded_file = UploadedFile.objects.create(
        project=project,
        filename=final_filename,
        original_filename=filename,
        media_type=form.cleaned_data['content_type'],
        size=form.cleaned_data['size'],
    )

    return JsonResponse(
        {
            'id': uploaded_file.id,
            'filename': uploaded_file.filename,
            'chunk_size': CHUNK_SIZE,
        },
        status=HTTPStatus.CREATED,
    )


#
# Processing request views
#
@require_http_methods(['GET', 'POST'])
@permission_required('projects.add_processingrequest')
def processing_request_create(request, pk):
    user = request.user
    project = get_object_or_404(Project, pk=pk, user=user)

    if request.method == 'POST':
        processing_request = ProcessingRequest(project=project)
        form = ProcessingRequestForm(data=request.POST, instance=processing_request)

        if form.is_valid():
            processing_request = form.save(commit=False)
            processing_request.project = project
            processing_request.uploaded_files = request.POST.getlist('uploaded_files')
            processing_request.save()

            messages.add_message(
                request, messages.SUCCESS, _('Processing request created successfully.')
            )
            send_new_processing_request_email.delay(processing_request.id)

            return redirect('projects:detail', pk=project.id)
        else:
            pass
    else:
        processing_request = ProcessingRequest(project=project)
        form = ProcessingRequestForm(instance=processing_request)

    context = {'form': form, 'project': project}
    return render(request, 'projects/processing_request_create.html', context)


@require_GET
@permission_required('projects.view_processingrequest')
def processing_request_detail(request, project_pk, pk):
    user = request.user
    processing_request = get_object_or_404(
        ProcessingRequest, pk=pk, project__pk=project_pk, project__user=user
    )
    project = processing_request.project

    context = {
        'processing_request': processing_request,
        'project': project,
        'uploaded_files_str': ', '.join(processing_request.uploaded_files),
    }
    return render(request, 'projects/processing_request_detail.html', context)


@require_POST
@permission_required('projects.delete_processingrequest')
def processing_request_delete(request, project_pk, pk):
    user = request.user
    processing_request = get_object_or_404(
        ProcessingRequest, pk=pk, project__pk=project_pk, project__user=user
    )
    project = processing_request.project

    processing_request.delete()
    messages.add_message(
        request, messages.SUCCESS, _('Processing request deleted successfully.')
    )
    return redirect('projects:detail', pk=project.id)


#
# Downloads
#
@require_http_methods(['GET', 'POST'])
@login_required
def download_detail(request, pk, filename):
    user = request.user
    project = get_object_or_404(Project, pk=pk, user=user)
    download_directory = project.download_directory
    file_path = download_directory / filename

    if not file_path.is_file():
        return HttpResponseNotFound('File does not exist.')

    if request.method == 'GET':
        file_info = FileInfo(file_path)
        context = {
            'project': project,
            'file_info': file_info,
        }
        return render(request, 'projects/download_detail.html', context)
    elif request.method == 'POST':
        # Delete the file
        file_path.unlink()
        files = get_dir_contents(project.download_directory)
        project.downloadable_files_count = len(files)
        project.save()

        messages.add_message(
            request,
            messages.SUCCESS,
            _('Deleted downloadable file %(name)s') % {'name': filename},
        )

        return redirect('projects:detail', pk=project.id)


@require_GET
@login_required
def download_download(request, pk, filename):
    user = request.user
    project = get_object_or_404(Project, pk=pk, user=user)
    download_directory = project.download_directory
    file_path = download_directory / filename

    if not file_path.is_file():
        return HttpResponseNotFound('File does not exist.')

    response = StreamingHttpResponse(
        file_data(file_path), content_type='application/octet-stream'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
