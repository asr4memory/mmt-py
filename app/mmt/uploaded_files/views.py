import json
from http import HTTPStatus
from math import ceil

import aiofiles
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from django.http import (
    HttpResponseNotFound,
    JsonResponse,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from mmt.core.file_serving import serve_file
from mmt.my_account.models import FeatureFlag
from mmt.transcripts.models import TranscriptionJob
from mmt.transcripts.tasks import submit_transcription_job
from mmt.uploaded_files.forms import TranscriptForm, TranscriptionJobForm
from mmt.uploaded_files.media import SAMPLING_RATE
from mmt.uploaded_files.models import UploadedFile
from mmt.uploaded_files.tasks import (
    calculate_duration,
    calculate_server_checksum,
    ensure_transcript_editing_media,
)
from mmt.uploaded_files.use_cases import upload_chunk


@require_GET
@permission_required('uploaded_files.view_uploadedfile')
def detail(request, pk):
    uploaded_file = get_object_or_404(
        UploadedFile,
        pk=pk,
        project__user=request.user,
    )
    project = uploaded_file.project
    uploaded_file.update_has_file_field()
    transcripts = uploaded_file.transcripts.defer('content')
    transcription_jobs = uploaded_file.transcription_jobs.select_related(
        'transcript'
    ).defer('transcript__content')

    context = dict(
        uploaded_file=uploaded_file,
        project=project,
        transcripts=transcripts,
        transcription_jobs=transcription_jobs,
        has_active_job=_has_active_job(uploaded_file),
        asr_enabled=settings.MMT_ASR_ENABLED,
        transcription_form=TranscriptionJobForm(),
        chunked_upload_enabled=request.user.is_flag_enabled(
            FeatureFlag.Name.CHUNKED_UPLOAD
        ),
    )
    return render(request, 'uploaded_files/detail.html', context)


def _has_active_job(uploaded_file: UploadedFile) -> bool:
    return uploaded_file.transcription_jobs.exclude(
        status__in=TranscriptionJob.TERMINAL
    ).exists()


@require_GET
@permission_required('uploaded_files.view_uploadedfile', raise_exception=True)
def status(request, pk):
    uploaded_file = get_object_or_404(UploadedFile, pk=pk, project__user=request.user)
    received = list(uploaded_file.chunks.values_list('index', flat=True))
    missing = (
        [] if uploaded_file.has_file else list(uploaded_file.missing_chunk_indices())
    )

    return JsonResponse(
        {
            'id': uploaded_file.id,
            'filename': uploaded_file.filename,
            'original_filename': uploaded_file.original_filename,
            'size': uploaded_file.size,
            'media_type': uploaded_file.media_type,
            'chunks_total': ceil(uploaded_file.size / settings.MMT_UPLOAD_CHUNK_SIZE)
            if uploaded_file.size
            else 0,
            'chunks_received': received,
            'chunks_missing': missing,
            'transferred': uploaded_file.transferred_from_chunks(),
            'status': uploaded_file.status,
        }
    )


@require_GET
@permission_required('uploaded_files.view_uploadedfile')
def waveform_json(request, pk):
    user = request.user
    uploaded_file = UploadedFile.objects.select_related('project', 'waveform').get(
        pk=pk
    )
    project = uploaded_file.project

    if project.user_id != user.id:
        return JsonResponse(
            {'message': 'You are not allowed to download this uploaded file.'},
            status=403,
        )

    if not uploaded_file.has_waveform:
        return JsonResponse({'message': 'Waveform not found.'}, status=404)

    waveform = uploaded_file.waveform
    response = dict(
        waveform=waveform.data,
        waveform_sampling_rate=SAMPLING_RATE,
        waveform_length=len(waveform.data),
        waveform_max=max(waveform.data),
    )

    return JsonResponse(response)


@require_GET
@permission_required('uploaded_files.view_uploadedfile')
def stream(request, pk):
    uploaded_file = get_object_or_404(
        UploadedFile,
        pk=pk,
        project__user=request.user,
    )
    file_path, content_type = uploaded_file.stream_source()

    if not file_path.is_file():
        return HttpResponseNotFound('File does not exist.')

    return serve_file(request, file_path, content_type=content_type)


@require_GET
@permission_required('uploaded_files.view_uploadedfile')
def download(request, pk):
    uploaded_file = get_object_or_404(
        UploadedFile,
        pk=pk,
        project__user=request.user,
    )
    file_path = uploaded_file.file_path

    if not file_path.is_file():
        return HttpResponseNotFound('File does not exist.')

    return serve_file(
        request,
        file_path,
        content_type='application/octet-stream',
        as_attachment=True,
        filename=uploaded_file.filename,
    )


@require_POST
@permission_required('uploaded_files.add_uploadedfile')
async def upload(request, pk):
    uploaded_file = await UploadedFile.objects.select_related('project').aget(pk=pk)
    project = uploaded_file.project

    user = await request.auser()
    if project.user_id != user.id:
        return JsonResponse(
            {'message': 'You are not allowed to upload this file.'}, status=403
        )

    file_path = await uploaded_file.afile_path

    if 'file' in request.FILES:
        file = request.FILES['file']
        await handle_uploaded_file(file, file_path)
        uploaded_file.has_file = True
        await uploaded_file.asave()
        calculate_duration.delay(pk)
        calculate_server_checksum.delay(pk)
        return JsonResponse({'success': True})
    else:
        await uploaded_file.adelete()
        return JsonResponse({'success': False}, status=HTTPStatus.BAD_REQUEST)


async def handle_uploaded_file(file, file_path):
    async with aiofiles.open(file_path, 'wb') as f:
        for chunk in file.chunks():
            await f.write(chunk)


@require_POST
@permission_required('uploaded_files.add_uploadedfile', raise_exception=True)
def upload_chunk_view(request, pk, index):
    uploaded_file = get_object_or_404(UploadedFile, pk=pk, project__user=request.user)
    chunk_file = request.FILES.get('file')
    if not chunk_file:
        return JsonResponse(
            {'message': 'No file provided.'}, status=HTTPStatus.BAD_REQUEST
        )
    try:
        complete = upload_chunk(uploaded_file, index=index, data=chunk_file.read())
    except ValueError as e:
        return JsonResponse({'message': str(e)}, status=HTTPStatus.BAD_REQUEST)
    except Exception as e:
        return JsonResponse(
            {'message': str(e)}, status=HTTPStatus.INTERNAL_SERVER_ERROR
        )
    return JsonResponse({'complete': complete})


@require_POST
@permission_required('uploaded_files.change_uploadedfile', raise_exception=True)
def update(request, pk):
    user = request.user
    uploaded_file = get_object_or_404(UploadedFile, pk=pk, project__user_id=user.id)
    project = uploaded_file.project
    if project.user_id != request.user.id:
        return JsonResponse(
            {'message': 'You are not allowed to update this file.'}, status=403
        )

    json_data = json.loads(request.body)
    checksum_client = json_data.get('checksum_client')

    if not checksum_client:
        return JsonResponse({'message': 'checksum_client is required.'}, status=400)

    uploaded_file.checksum_client = checksum_client
    uploaded_file.save()
    uploaded_file.refresh_from_db()
    uploaded_file.log_if_corrupt()

    return JsonResponse({'message': 'Uploaded file updated successfully.'}, status=200)


@require_POST
@permission_required('uploaded_files.delete_uploadedfile')
def delete(request, pk):
    user = request.user
    uploaded_file = get_object_or_404(UploadedFile, pk=pk, project__user_id=user.id)
    project = uploaded_file.project

    uploaded_file.delete_file()
    uploaded_file.delete()
    messages.add_message(
        request, messages.SUCCESS, _('Uploaded file deleted successfully.')
    )

    return redirect('projects:detail', pk=project.id)


@require_POST
@permission_required('transcripts.add_transcriptionjob', raise_exception=True)
def transcribe(request, pk):
    uploaded_file = get_object_or_404(
        UploadedFile, pk=pk, project__user_id=request.user.id
    )

    if not settings.MMT_ASR_ENABLED:
        messages.add_message(
            request, messages.ERROR, _('Transcription is not available.')
        )
        return redirect('uploaded_files:detail', pk=uploaded_file.id)

    if not uploaded_file.has_file or not uploaded_file.is_av_media():
        messages.add_message(
            request, messages.ERROR, _('This file cannot be transcribed.')
        )
        return redirect('uploaded_files:detail', pk=uploaded_file.id)

    # A file carries at most one job that has not finished. This is a check
    # followed by a create without a database constraint, so two simultaneous
    # requests could both pass it; acceptable at this scale.
    if _has_active_job(uploaded_file):
        messages.add_message(
            request, messages.ERROR, _('This file is already being transcribed.')
        )
        return redirect('uploaded_files:detail', pk=uploaded_file.id)

    form = TranscriptionJobForm(request.POST)

    if not form.is_valid():
        messages.add_message(
            request, messages.ERROR, _('The transcription could not be started.')
        )
        return redirect('uploaded_files:detail', pk=uploaded_file.id)

    job = form.save(commit=False)
    job.uploaded_file = uploaded_file
    job.save()

    submit_transcription_job.delay(job.id)
    messages.add_message(request, messages.SUCCESS, _('Transcription started.'))

    return redirect('uploaded_files:detail', pk=uploaded_file.id)


@require_http_methods(['GET', 'POST'])
@permission_required('transcripts.add_transcript')
def transcript_create(request, pk):
    user = request.user
    uploaded_file = get_object_or_404(UploadedFile, pk=pk, project__user_id=user.id)
    project = uploaded_file.project

    if request.method == 'POST':
        form = TranscriptForm(request.POST, request.FILES)

        if form.is_valid():
            transcript = form.save(commit=False)
            transcript.uploaded_file = uploaded_file
            transcript.save()
            ensure_transcript_editing_media(uploaded_file)
            messages.add_message(
                request, messages.SUCCESS, _('Transcript created successfully.')
            )
            return redirect('transcripts:detail', pk=transcript.id)
    else:
        form = TranscriptForm()

    context = dict(form=form, uploaded_file=uploaded_file, project=project)
    return render(request, 'uploaded_files/create_transcript.html', context)
