import json
from http import HTTPStatus

import aiofiles
from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from django.http import (
    HttpResponseNotFound,
    JsonResponse,
    StreamingHttpResponse,
)
from django.shortcuts import render, get_object_or_404, redirect
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from mmt.core.utils import file_data
from mmt.transcripts.models import Transcript
from mmt.uploaded_files.forms import TranscriptForm
from mmt.uploaded_files.models import UploadedFile
from mmt.uploaded_files.analysis import SAMPLING_RATE
from mmt.uploaded_files.tasks import calculate_duration, calculate_server_checksum, task_extract_waveform_data
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
    transcripts = uploaded_file.transcripts.all()

    context = dict(
        uploaded_file=uploaded_file,
        project=project,
        transcripts=transcripts,
    )
    return render(request, 'uploaded_files/detail.html', context)


@require_GET
@permission_required('uploaded_files.view_uploadedfile')
def waveform_json(request, pk):
    user = request.user
    uploaded_file = UploadedFile.objects.select_related('project', 'waveform').get(pk=pk)
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
def download(request, pk):
    uploaded_file = get_object_or_404(
        UploadedFile,
        pk=pk,
        project__user=request.user,
    )
    file_path = uploaded_file.file_path

    if not file_path.is_file():
        return HttpResponseNotFound('File does not exist.')

    response = StreamingHttpResponse(
        file_data(file_path), content_type='application/octet-stream'
    )
    response['Content-Disposition'] = f'attachment; filename="{uploaded_file.filename}"'
    return response


@require_POST
@permission_required('uploaded_files.add_uploadedfile')
async def upload(request, pk):
    uploaded_file = (
        await UploadedFile.objects.select_related('project')
        .aget(pk=pk)
    )
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
    try:
        complete = upload_chunk(uploaded_file, index=index, data=request.body)
    except ValueError as e:
        return JsonResponse({'message': str(e)}, status=HTTPStatus.BAD_REQUEST)
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


@require_http_methods(['GET', 'POST'])
@permission_required('transcripts.add_transcript')
def transcript_create(request, pk):
    user = request.user
    uploaded_file = get_object_or_404(UploadedFile, pk=pk, project__user_id=user.id)
    project = uploaded_file.project

    if request.method == 'POST':
        form = TranscriptForm(request.POST)

        try:
            transcript = Transcript.objects.create(
                label=form.data['label'],
                language=form.data['language'],
                content=json.loads(form.data['content']),
                uploaded_file=uploaded_file,
            )
            if not uploaded_file.has_waveform:
                task_extract_waveform_data.delay(uploaded_file.id)
            messages.add_message(
                request, messages.SUCCESS, _('Transcript created successfully.')
            )
            return redirect('transcripts:detail', pk=transcript.id)
        except Exception:
            pass
    else:
        form = TranscriptForm()

    context = dict(form=form, uploaded_file=uploaded_file, project=project)
    return render(request, 'uploaded_files/create_transcript.html', context)
