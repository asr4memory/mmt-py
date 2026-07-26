import json
import logging
from http import HTTPStatus

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ValidationError
from django.db.models import Count
from django.http import (
    HttpResponseForbidden,
    HttpResponseNotFound,
    HttpResponseServerError,
    JsonResponse,
    StreamingHttpResponse,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.text import get_valid_filename
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from mmt.core.utils import file_data
from mmt.my_account.models import FeatureFlag
from mmt.projects.exceptions import ProjectError
from mmt.projects.forms import (
    ProcessingRequestForm,
    ProjectForm,
    UploadedFileForm,
    UploadForm,
)
from mmt.projects.models import ProcessingRequest, Project
from mmt.projects.tasks import send_new_processing_request_email
from mmt.projects.use_cases import create_project, delete_project, update_project_title
from mmt.projects.utils import (
    FileInfo,
    get_dir_contents,
    get_filename_suffix,
    get_files_with_info,
)
from mmt.transcripts.models import TranscriptionJob
from mmt.uploaded_files.models import UploadedFile

logger = logging.getLogger(__name__)


#
# Views for projects
#
@require_GET
@login_required
def project_index(request):
    user = request.user
    projects = Project.objects.filter(user=user).annotate(
        uploaded_files_count=Count('uploaded_files')
    )
    context = {'projects': projects}
    return render(request, 'projects/project_index.html', context)


@require_GET
@login_required
def project_detail(request, pk):
    user = request.user
    project = get_object_or_404(Project, pk=pk, user=user)
    # The count is annotated rather than counted per row, so the number of
    # queries does not grow with the number of files.
    # Transcript sets related_query_name='transcript', so that is the name the
    # aggregate has to use.
    uploaded_files = project.uploaded_files.annotate(
        transcript_count=Count('transcript')
    ).order_by('-created_at')
    processing_requests = project.processing_requests.all()
    active_transcription_jobs = TranscriptionJob.objects.filter(
        uploaded_file__project=project,
        status__in=(
            TranscriptionJob.PENDING,
            TranscriptionJob.SUBMITTED,
            TranscriptionJob.RUNNING,
        ),
    ).select_related('uploaded_file')
    has_uploaded_files = uploaded_files.exists()
    has_processing_requests = processing_requests.exists()
    show_processing_request_section = has_uploaded_files or has_processing_requests

    try:
        files_with_info = get_files_with_info(project.download_directory)
        project.downloadable_files_count = len(files_with_info)
        project.save()
    except FileNotFoundError:
        logger.error(
            'Download directory missing for project %s (path: %s)',
            project.pk,
            project.download_directory,
            exc_info=True,
        )
        return render(
            request,
            'projects/project_detail_error.html',
            {'project': project},
            status=500,
        )

    context = {
        'project': project,
        'uploaded_files': uploaded_files,
        'has_uploaded_files': has_uploaded_files,
        'processing_requests': processing_requests,
        'has_processing_requests': has_processing_requests,
        'show_processing_request_section': show_processing_request_section,
        'downloads': files_with_info,
        'active_transcription_jobs': active_transcription_jobs,
    }
    return render(request, 'projects/project_detail.html', context)


@require_http_methods(['GET', 'POST'])
@login_required
def project_create(request):
    user = request.user
    if request.method == 'POST':
        form = ProjectForm(request.POST)
        if form.is_valid():
            try:
                project = create_project(
                    title=form.cleaned_data['title'],
                    description=form.cleaned_data['description'],
                    user=user,
                )
            except Exception:
                logging.exception('Failed to create project')
                messages.add_message(
                    request, messages.ERROR, _('Could not create project.')
                )
            else:
                messages.add_message(
                    request, messages.SUCCESS, _('Project created successfully.')
                )
                return redirect('projects:detail', pk=project.id)
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
        if form.is_valid():
            project.refresh_from_db()
            project.description = form.cleaned_data['description']
            try:
                update_project_title(project, form.cleaned_data['title'])
            except ValidationError, ProjectError:
                messages.add_message(
                    request, messages.ERROR, _('Project update failed.')
                )
            else:
                messages.add_message(
                    request, messages.SUCCESS, _('Project updated successfully.')
                )
                return redirect('projects:detail', pk=project.id)
    else:
        form = ProjectForm(instance=project)

    context = {'form': form, 'project': project}
    return render(request, 'projects/project_settings.html', context)


@require_POST
@login_required
def project_delete(request, pk):
    user = request.user
    project = get_object_or_404(Project, pk=pk, user=user)

    try:
        delete_project(project)
    except Exception:
        logging.exception(f'Could not delete project {project.pk}')
        return HttpResponseServerError(_('Could not delete project.'))

    messages.add_message(request, messages.SUCCESS, _('Project deleted successfully.'))
    return redirect('projects:index')


#
# Views for uploaded files
#
@require_GET
@permission_required('uploaded_files.add_uploadedfile')
def upload(request, pk):
    user = request.user
    project = get_object_or_404(Project, pk=pk, user=user)
    form = UploadForm()
    chunked_upload = user.is_flag_enabled(FeatureFlag.Name.CHUNKED_UPLOAD)
    context = {
        'project': project,
        'form': form,
        'chunked_upload': chunked_upload,
        'chunk_size': settings.MMT_UPLOAD_CHUNK_SIZE,
    }
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
        },
        status=HTTPStatus.CREATED,
    )


@require_POST
@permission_required('uploaded_files.add_uploadedfile', raise_exception=True)
def resumable_uploads(request, pk):
    """Report which of the given files can be resumed.

    Given a batch of ``{filename, size}`` entries, find the incomplete upload
    in this project that matches each one by original filename and size, and
    return its id, the chunk indices still missing, and whether its client
    checksum was already submitted. Files without a matching incomplete upload
    are omitted from the response. No object is created or modified; POST is
    used only to carry the JSON batch.
    """
    project = get_object_or_404(Project, pk=pk, user=request.user)
    try:
        json_data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'message': 'Invalid JSON'}, status=HTTPStatus.BAD_REQUEST)

    matches = []
    for entry in json_data.get('files', []):
        filename = entry.get('filename')
        size = entry.get('size')
        if filename is None or size is None:
            continue

        uploaded_file = (
            UploadedFile.objects.filter(
                project=project, original_filename=filename, size=size
            )
            .partial()
            .order_by('-created_at')
            .first()
        )
        if uploaded_file is None:
            continue

        matches.append(
            {
                'filename': filename,
                'size': size,
                'id': uploaded_file.id,
                'chunks_missing': sorted(uploaded_file.missing_chunk_indices()),
                'checksum_submitted': bool(uploaded_file.checksum_client),
            }
        )

    return JsonResponse({'matches': matches})


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

    if not processing_request.deletable:
        return HttpResponseForbidden(_('This processing request cannot be deleted.'))

    processing_request.delete()
    messages.add_message(
        request, messages.SUCCESS, _('Processing request deleted successfully.')
    )
    return redirect('projects:detail', pk=project.id)


#
# Downloads
#
# TODO: Split the POST delete branch into a dedicated download_delete view
# (mirroring download_download) so this view is GET-only.
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
